from __future__ import annotations

import json
import os
import secrets
import shutil
import threading
import time
from typing import Dict, Iterable, Optional

from Backend.logger import LOGGER


AUDIO_CACHE_DIR = os.path.abspath(os.path.join("Music", "cache"))
BLOCK_CACHE_DIR = os.path.join(AUDIO_CACHE_DIR, "blocks")
CACHE_STATS_FILE = os.path.join(AUDIO_CACHE_DIR, "cache_stats.json")

BLOCK_SIZE = 1024 * 1024
VALID_CACHE_LIMITS_GB = (2, 5, 10, 20)
PLAYBACK_WINDOW_TTL = 15 * 60
FREQUENT_WINDOW_SECONDS = 7 * 24 * 60 * 60
FREQUENT_PLAY_THRESHOLD = 3
FAVORITE_HINT_TTL = 30 * 24 * 60 * 60

TIER_PRIORITY = {
    "cold": 0,
    "warm": 1,
    "favorite": 2,
    "hot": 3,
}


class SmartAudioCache:
    """Block-based audio cache with tier-aware eviction and lightweight telemetry."""

    def __init__(self) -> None:
        os.makedirs(BLOCK_CACHE_DIR, exist_ok=True)
        self._lock = threading.RLock()
        self._playback_windows: Dict[str, tuple[Dict[str, str], float]] = {}
        self._stats = self._load_stats()
        self._last_stats_flush = 0.0
        self._last_cleanup = 0.0
        self._cleanup_pending = False

    @staticmethod
    def _safe_cache_key(cache_key: str) -> str:
        return "".join(ch for ch in str(cache_key) if ch.isalnum() or ch in ("_", "-"))[:160]

    def _track_dir(self, cache_key: str) -> str:
        return os.path.join(BLOCK_CACHE_DIR, self._safe_cache_key(cache_key))

    def _meta_path(self, cache_key: str) -> str:
        return os.path.join(self._track_dir(cache_key), "meta.json")

    def _block_path(self, cache_key: str, offset: int) -> str:
        return os.path.join(self._track_dir(cache_key), f"{int(offset):016d}.blk")

    @staticmethod
    def _read_json(path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _write_json_atomic(path: str, data: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{secrets.token_hex(4)}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)

    def _load_meta(self, cache_key: str) -> dict:
        return self._read_json(self._meta_path(cache_key))

    def _save_meta(self, cache_key: str, meta: dict) -> None:
        self._write_json_atomic(self._meta_path(cache_key), meta)

    def _load_stats(self) -> dict:
        base = {
            "block_hits": 0,
            "block_misses": 0,
            "legacy_hits": 0,
            "bytes_saved": 0,
            "telegram_bytes_fetched": 0,
        }
        stored = self._read_json(CACHE_STATS_FILE)
        for key in base:
            try:
                base[key] = max(0, int(stored.get(key, base[key])))
            except (TypeError, ValueError):
                pass
        return base

    def _flush_stats_if_due(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_stats_flush < 10:
            return
        try:
            self._write_json_atomic(CACHE_STATS_FILE, self._stats)
            self._last_stats_flush = now
        except Exception as exc:
            LOGGER.debug("[MUSIC CACHE] Failed to persist cache stats: %s", exc)

    @staticmethod
    def get_limit_gb() -> int:
        try:
            from Backend.helper.settings_manager import SettingsManager

            value = int(SettingsManager.current().audio_cache_size_gb)
            return value if value in VALID_CACHE_LIMITS_GB else 2
        except Exception:
            return 2

    @classmethod
    def get_limit_bytes(cls) -> int:
        return cls.get_limit_gb() * 1024 * 1024 * 1024

    def set_playback_window(self, owner: str, ordered_keys: Iterable[str]) -> Dict[str, str]:
        owner = str(owner or "direct")
        tiers: Dict[str, str] = {}
        for idx, raw_key in enumerate(ordered_keys):
            cache_key = self._safe_cache_key(raw_key)
            if not cache_key:
                continue
            tiers[cache_key] = "hot" if idx == 0 else "warm"
        with self._lock:
            if tiers:
                self._playback_windows[owner] = (tiers, time.time() + PLAYBACK_WINDOW_TTL)
            else:
                self._playback_windows.pop(owner, None)
        return tiers

    def mark_hot(self, owner: str, cache_key: str) -> None:
        """Promote one track to hot without dropping warm lookahead for the same player."""
        owner = str(owner or "direct")
        cache_key = self._safe_cache_key(cache_key)
        if not cache_key:
            return
        now = time.time()
        with self._lock:
            tiers, expires_at = self._playback_windows.get(owner, ({}, 0.0))
            current = dict(tiers) if expires_at > now else {}
            for key, tier in list(current.items()):
                if tier == "hot" and key != cache_key:
                    current[key] = "warm"
            current[cache_key] = "hot"
            self._playback_windows[owner] = (current, now + PLAYBACK_WINDOW_TTL)

    def _active_tiers(self, now: Optional[float] = None) -> Dict[str, str]:
        now = now or time.time()
        merged: Dict[str, str] = {}
        with self._lock:
            for owner, (tiers, expires_at) in list(self._playback_windows.items()):
                if expires_at <= now:
                    self._playback_windows.pop(owner, None)
                    continue
                for cache_key, tier in tiers.items():
                    current = merged.get(cache_key, "cold")
                    if TIER_PRIORITY.get(tier, 0) > TIER_PRIORITY.get(current, 0):
                        merged[cache_key] = tier
        return merged

    def mark_play(self, cache_key: str) -> None:
        cache_key = self._safe_cache_key(cache_key)
        if not cache_key:
            return
        now = time.time()
        with self._lock:
            meta = self._load_meta(cache_key)
            recent = []
            for value in meta.get("recent_plays", []):
                try:
                    ts = float(value)
                except (TypeError, ValueError):
                    continue
                if now - ts <= FREQUENT_WINDOW_SECONDS:
                    recent.append(ts)
            if not recent or now - recent[-1] >= 30:
                recent.append(now)
            meta["recent_plays"] = recent[-12:]
            meta["last_played"] = now
            self._save_meta(cache_key, meta)

    def hint_favorite(self, cache_key: str) -> None:
        cache_key = self._safe_cache_key(cache_key)
        if not cache_key:
            return
        with self._lock:
            meta = self._load_meta(cache_key)
            meta["favorite_hint_until"] = time.time() + FAVORITE_HINT_TTL
            self._save_meta(cache_key, meta)

    def clear_favorite_hint(self, cache_key: str) -> None:
        cache_key = self._safe_cache_key(cache_key)
        if not cache_key:
            return
        with self._lock:
            meta = self._load_meta(cache_key)
            if "favorite_hint_until" in meta:
                meta.pop("favorite_hint_until", None)
                self._save_meta(cache_key, meta)

    def tier_for(self, cache_key: str, explicit_favorite: bool = False) -> str:
        cache_key = self._safe_cache_key(cache_key)
        now = time.time()
        active = self._active_tiers(now)
        if active.get(cache_key) == "hot":
            return "hot"

        meta = self._load_meta(cache_key)
        recent = []
        for value in meta.get("recent_plays", []):
            try:
                ts = float(value)
            except (TypeError, ValueError):
                continue
            if now - ts <= FREQUENT_WINDOW_SECONDS:
                recent.append(ts)

        favorite_hint = False
        try:
            favorite_hint = float(meta.get("favorite_hint_until") or 0) > now
        except (TypeError, ValueError):
            favorite_hint = False

        if explicit_favorite or favorite_hint or len(recent) >= FREQUENT_PLAY_THRESHOLD:
            return "favorite"
        if active.get(cache_key) == "warm":
            return "warm"
        return "cold"

    def read_block(
        self,
        cache_key: str,
        offset: int,
        file_size: int,
        served_bytes: Optional[int] = None,
        count_stats: bool = True,
    ) -> Optional[bytes]:
        expected = max(0, min(BLOCK_SIZE, int(file_size) - int(offset)))
        if expected <= 0:
            return None
        path = self._block_path(cache_key, offset)
        try:
            if not os.path.isfile(path) or os.path.getsize(path) != expected:
                raise FileNotFoundError(path)
            with open(path, "rb") as fh:
                data = fh.read()
            if len(data) != expected:
                raise IOError("cached block size mismatch")
            try:
                os.utime(path, None)
            except Exception:
                pass
            if count_stats:
                with self._lock:
                    self._stats["block_hits"] += 1
                    self._stats["bytes_saved"] += max(0, int(served_bytes if served_bytes is not None else len(data)))
                    self._flush_stats_if_due()
            return data
        except Exception:
            if count_stats:
                with self._lock:
                    self._stats["block_misses"] += 1
                    self._flush_stats_if_due()
            return None

    def record_legacy_hit(self, served_bytes: int) -> None:
        with self._lock:
            self._stats["legacy_hits"] += 1
            self._stats["bytes_saved"] += max(0, int(served_bytes))
            self._flush_stats_if_due()

    def write_block(
        self,
        cache_key: str,
        offset: int,
        data: bytes,
        file_size: int,
        file_name: str,
        mime_type: str,
        tier: str,
    ) -> bool:
        cache_key = self._safe_cache_key(cache_key)
        offset = int(offset)
        file_size = int(file_size)
        expected = max(0, min(BLOCK_SIZE, file_size - offset))
        if not cache_key or offset < 0 or offset % BLOCK_SIZE != 0 or expected <= 0 or len(data) != expected:
            return False

        path = self._block_path(cache_key, offset)
        with self._lock:
            self._stats["telegram_bytes_fetched"] += len(data)
            self._flush_stats_if_due()

        if os.path.isfile(path):
            try:
                if os.path.getsize(path) == expected:
                    return False
            except Exception:
                pass

        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{secrets.token_hex(4)}.tmp"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
            with self._lock:
                meta = self._load_meta(cache_key)
                previous_tier = str(meta.get("tier") or "cold")
                if TIER_PRIORITY.get(tier, 0) < TIER_PRIORITY.get(previous_tier, 0):
                    tier = previous_tier
                meta.update({
                    "cache_key": cache_key,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "file_size": file_size,
                    "block_size": BLOCK_SIZE,
                    "tier": tier,
                    "last_access": time.time(),
                })
                self._save_meta(cache_key, meta)
            return True
        except Exception as exc:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            LOGGER.debug("[MUSIC CACHE] Failed to store block %s@%s: %s", cache_key, offset, exc)
            return False

    def should_schedule_cleanup(self) -> bool:
        with self._lock:
            now = time.time()
            if self._cleanup_pending or now - self._last_cleanup < 30:
                return False
            self._cleanup_pending = True
            return True

    def _cleanup_track_dir_if_empty(self, track_dir: str) -> None:
        try:
            if not any(name.endswith(".blk") for name in os.listdir(track_dir)):
                meta_path = os.path.join(track_dir, "meta.json")
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                os.rmdir(track_dir)
        except Exception:
            pass

    def cleanup(self) -> dict:
        now = time.time()
        limit = self.get_limit_bytes()
        active = self._active_tiers(now)
        entries = []
        total_size = 0

        try:
            for root, _, names in os.walk(BLOCK_CACHE_DIR):
                cache_key = os.path.basename(root) if root != BLOCK_CACHE_DIR else ""
                if not cache_key:
                    continue
                meta = self._read_json(os.path.join(root, "meta.json"))
                tier = active.get(cache_key) or self.tier_for(cache_key)
                for name in names:
                    if not name.endswith(".blk"):
                        continue
                    path = os.path.join(root, name)
                    try:
                        stat = os.stat(path)
                    except Exception:
                        continue
                    total_size += stat.st_size
                    entries.append((path, stat.st_atime, stat.st_size, tier, cache_key))

            # Keep old full-file cache readable during migration, but let eviction
            # treat it as cold data so block cache naturally replaces it.
            for name in os.listdir(AUDIO_CACHE_DIR):
                path = os.path.join(AUDIO_CACHE_DIR, name)
                if not os.path.isfile(path):
                    continue
                if name.endswith(".tmp"):
                    try:
                        if now - os.path.getmtime(path) > 3600:
                            os.remove(path)
                    except Exception:
                        pass
                    continue
                if not name.endswith(".dat"):
                    continue
                try:
                    stat = os.stat(path)
                except Exception:
                    continue
                total_size += stat.st_size
                cache_key = os.path.splitext(name)[0]
                entries.append((path, stat.st_atime, stat.st_size, "cold", cache_key))

            removed = 0
            if total_size > limit:
                target = int(limit * 0.80)
                entries.sort(key=lambda item: (TIER_PRIORITY.get(item[3], 0), item[1]))
                # Active hot/warm blocks are skipped in the first pass.
                passes = (False, True)
                for allow_pinned in passes:
                    for path, _, size, tier, cache_key in list(entries):
                        if total_size <= target:
                            break
                        if not os.path.exists(path):
                            continue
                        is_pinned = active.get(cache_key) in ("hot", "warm")
                        if is_pinned and not allow_pinned:
                            continue
                        try:
                            os.remove(path)
                            total_size -= size
                            removed += size
                            if path.endswith(".dat"):
                                meta_path = path[:-4] + ".json"
                                if os.path.exists(meta_path):
                                    os.remove(meta_path)
                            else:
                                self._cleanup_track_dir_if_empty(os.path.dirname(path))
                        except Exception:
                            continue
                    if total_size <= target:
                        break

            return {"size_bytes": max(0, total_size), "removed_bytes": removed, "limit_bytes": limit}
        finally:
            with self._lock:
                self._last_cleanup = time.time()
                self._cleanup_pending = False

    def get_stats(self) -> dict:
        now = time.time()
        active = self._active_tiers(now)
        tier_bytes = {"hot": 0, "warm": 0, "favorite": 0, "cold": 0}
        total_size = 0
        block_count = 0
        track_count = 0

        try:
            for name in os.listdir(BLOCK_CACHE_DIR):
                track_dir = os.path.join(BLOCK_CACHE_DIR, name)
                if not os.path.isdir(track_dir):
                    continue
                bytes_for_track = 0
                blocks_for_track = 0
                for block_name in os.listdir(track_dir):
                    if not block_name.endswith(".blk"):
                        continue
                    try:
                        size = os.path.getsize(os.path.join(track_dir, block_name))
                    except Exception:
                        continue
                    bytes_for_track += size
                    blocks_for_track += 1
                if not blocks_for_track:
                    continue
                tier = active.get(name) or self.tier_for(name)
                tier_bytes[tier if tier in tier_bytes else "cold"] += bytes_for_track
                total_size += bytes_for_track
                block_count += blocks_for_track
                track_count += 1

            legacy_bytes = 0
            for name in os.listdir(AUDIO_CACHE_DIR):
                if not name.endswith(".dat"):
                    continue
                path = os.path.join(AUDIO_CACHE_DIR, name)
                if os.path.isfile(path):
                    try:
                        legacy_bytes += os.path.getsize(path)
                    except Exception:
                        pass
            total_size += legacy_bytes
            tier_bytes["cold"] += legacy_bytes
        except Exception as exc:
            LOGGER.debug("[MUSIC CACHE] Failed to inspect cache stats: %s", exc)

        with self._lock:
            stats = dict(self._stats)
            self._flush_stats_if_due(force=True)

        hits = int(stats.get("block_hits", 0)) + int(stats.get("legacy_hits", 0))
        misses = int(stats.get("block_misses", 0))
        total_lookups = hits + misses
        limit_bytes = self.get_limit_bytes()
        return {
            "limit_gb": self.get_limit_gb(),
            "limit_bytes": limit_bytes,
            "size_bytes": total_size,
            "usage_percent": round((total_size / limit_bytes * 100) if limit_bytes else 0.0, 1),
            "tracks": track_count,
            "blocks": block_count,
            "hits": hits,
            "misses": misses,
            "hit_rate": round((hits / total_lookups * 100) if total_lookups else 0.0, 1),
            "bandwidth_saved_bytes": int(stats.get("bytes_saved", 0)),
            "telegram_bytes_fetched": int(stats.get("telegram_bytes_fetched", 0)),
            "tiers": tier_bytes,
        }

    def clear(self, reset_stats: bool = False) -> dict:
        removed = 0
        try:
            if os.path.isdir(BLOCK_CACHE_DIR):
                for root, _, names in os.walk(BLOCK_CACHE_DIR):
                    for name in names:
                        path = os.path.join(root, name)
                        try:
                            removed += os.path.getsize(path)
                        except Exception:
                            pass
                shutil.rmtree(BLOCK_CACHE_DIR, ignore_errors=True)
            os.makedirs(BLOCK_CACHE_DIR, exist_ok=True)

            for name in os.listdir(AUDIO_CACHE_DIR):
                if not name.endswith((".dat", ".tmp")):
                    continue
                path = os.path.join(AUDIO_CACHE_DIR, name)
                if not os.path.isfile(path):
                    continue
                try:
                    removed += os.path.getsize(path)
                    os.remove(path)
                    if name.endswith(".dat"):
                        meta_path = path[:-4] + ".json"
                        if os.path.exists(meta_path):
                            os.remove(meta_path)
                except Exception:
                    pass

            if reset_stats:
                with self._lock:
                    self._stats = {
                        "block_hits": 0,
                        "block_misses": 0,
                        "legacy_hits": 0,
                        "bytes_saved": 0,
                        "telegram_bytes_fetched": 0,
                    }
                    self._flush_stats_if_due(force=True)
        finally:
            with self._lock:
                self._last_cleanup = time.time()
                self._cleanup_pending = False
        return {"removed_bytes": removed}


smart_audio_cache = SmartAudioCache()
