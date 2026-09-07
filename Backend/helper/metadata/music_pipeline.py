"""Persistent music metadata cache and override policy.

Recognition results live separately from the album-library document so they
survive rescans and can be reused by Telegram message id, file_unique_id, or
an audio fingerprint.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional

from Backend import db
from Backend.logger import LOGGER

try:
    from pymongo import UpdateOne
except Exception:  # pragma: no cover - pymongo is installed through motor
    UpdateOne = None


SOURCE_CONFIDENCE = {
    "manual": 1.00,
    "embedded": 0.98,
    "fingerprint": 0.96,
    "shazam": 0.95,
    "itunes": 0.86,
    "deezer": 0.84,
    "online": 0.84,
    "telegram": 0.78,
    "filename": 0.68,
    "unknown": 0.50,
}


def normalize_metadata_source(value: str) -> str:
    source = str(value or "").strip().lower()
    if "manual" in source:
        return "manual"
    if "embedded" in source or "id3" in source or "vorbis" in source or "riff" in source:
        return "embedded"
    if "fingerprint" in source and "shazam" not in source:
        return "fingerprint"
    if "shazam" in source:
        return "shazam"
    if "itunes" in source or "apple" in source:
        return "itunes"
    if "deezer" in source:
        return "deezer"
    if "online" in source or "scraper" in source:
        return "online"
    if "telegram" in source:
        return "telegram"
    if "filename" in source or "parser" in source:
        return "filename"
    return source or "unknown"


def metadata_confidence(source: str, explicit: Any = None) -> float:
    try:
        if explicit is not None:
            return max(0.0, min(1.0, float(explicit)))
    except (TypeError, ValueError):
        pass
    return SOURCE_CONFIDENCE.get(normalize_metadata_source(source), 0.50)


def _track_key(chat_id: Any, msg_id: Any) -> str:
    try:
        return f"telegram:{int(chat_id)}:{int(msg_id)}"
    except (TypeError, ValueError):
        return ""


def _public_doc(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    return {
        "title": doc.get("title") or "",
        "artist": doc.get("artist") or "",
        "album": doc.get("album") or "",
        "cover_url": doc.get("cover_url") or "",
        "genre": doc.get("genre") or "",
        "year": doc.get("year") or "",
        "source": doc.get("source") or "unknown",
        "confidence": metadata_confidence(doc.get("source"), doc.get("confidence")),
        "manual_override": bool(doc.get("manual_override", False)),
        "fingerprint": doc.get("fingerprint") or "",
        "file_unique_id": doc.get("file_unique_id") or "",
        "recognized_at": doc.get("recognized_at"),
    }


class MusicMetadataPipeline:
    collection_name = "music_metadata_cache"

    def __init__(self) -> None:
        self._memory_track: Dict[str, dict] = {}
        self._memory_file: Dict[str, str] = {}
        self._memory_fingerprint: Dict[str, str] = {}
        self._indexes_ready = False

    def _collection(self):
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            return db.dbs["tracking"][self.collection_name]
        return None

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        coll = self._collection()
        if coll is None:
            return
        try:
            await coll.create_index("file_unique_id", sparse=True)
            await coll.create_index("fingerprint", sparse=True)
            await coll.create_index("manual_override")
            self._indexes_ready = True
        except Exception as exc:
            LOGGER.debug(f"[MUSIC META CACHE] Could not ensure indexes: {exc}")

    def _remember(self, doc: dict) -> None:
        public = _public_doc(doc)
        if not public:
            return
        key = str(doc.get("_id") or "")
        if key:
            previous = self._memory_track.get(key)
            if previous:
                old_file = str(previous.get("file_unique_id") or "").strip()
                old_fingerprint = str(previous.get("fingerprint") or "").strip()
                if old_file and self._memory_file.get(old_file) == key:
                    self._memory_file.pop(old_file, None)
                if old_fingerprint and self._memory_fingerprint.get(old_fingerprint) == key:
                    self._memory_fingerprint.pop(old_fingerprint, None)
            self._memory_track[key] = public
        file_unique_id = str(doc.get("file_unique_id") or "").strip()
        if file_unique_id and key:
            self._memory_file[file_unique_id] = key
        fingerprint = str(doc.get("fingerprint") or "").strip()
        if fingerprint and key:
            self._memory_fingerprint[fingerprint] = key

    async def get_cached(
        self,
        chat_id: Any = None,
        msg_id: Any = None,
        *,
        file_unique_id: str = "",
        fingerprint: str = "",
    ) -> Optional[dict]:
        key = _track_key(chat_id, msg_id)
        if key and key in self._memory_track:
            return dict(self._memory_track[key])
        file_unique_id = str(file_unique_id or "").strip()
        if file_unique_id and file_unique_id in self._memory_file:
            cached_key = self._memory_file[file_unique_id]
            cached = self._memory_track.get(cached_key)
            if cached:
                return dict(cached)
        fingerprint = str(fingerprint or "").strip()
        if fingerprint and fingerprint in self._memory_fingerprint:
            cached_key = self._memory_fingerprint[fingerprint]
            cached = self._memory_track.get(cached_key)
            if cached:
                return dict(cached)

        coll = self._collection()
        if coll is None:
            return None
        await self._ensure_indexes()
        try:
            doc = None
            if key:
                doc = await coll.find_one({"_id": key})
            if not doc and file_unique_id:
                doc = await coll.find_one(
                    {"file_unique_id": file_unique_id},
                    sort=[("manual_override", -1), ("updated_at", -1)],
                )
            if not doc and fingerprint:
                doc = await coll.find_one(
                    {"fingerprint": fingerprint},
                    sort=[("manual_override", -1), ("confidence", -1), ("updated_at", -1)],
                )
            if doc:
                self._remember(doc)
                return _public_doc(doc)
        except Exception as exc:
            LOGGER.debug(f"[MUSIC META CACHE] Lookup failed: {exc}")
        return None

    def _build_doc(
        self,
        metadata: dict,
        *,
        chat_id: Any,
        msg_id: Any,
        file_unique_id: str = "",
        fingerprint: str = "",
        source: str = "",
        manual_override: Optional[bool] = None,
    ) -> Optional[dict]:
        key = _track_key(chat_id, msg_id)
        if not key:
            return None
        normalized_source = normalize_metadata_source(
            source or metadata.get("source") or metadata.get("metadataSource")
        )
        title = str(metadata.get("title") or metadata.get("name") or "").strip()
        if not title:
            return None
        now = time.time()
        explicit_confidence = metadata.get("confidence")
        if explicit_confidence is None:
            explicit_confidence = metadata.get("metadataConfidence")
        if manual_override is None:
            # A stale manualOverride flag carried inside an old track must not
            # turn a fresh Shazam/automatic result into another manual write.
            # Without an explicit argument, only metadata whose source itself
            # is manual is allowed to infer the lock from the payload.
            manual_flag = normalized_source == "manual" and bool(
                metadata.get("manual_override") or metadata.get("manualOverride")
            )
        else:
            manual_flag = bool(manual_override)
        return {
            "_id": key,
            "chat_id": int(chat_id),
            "msg_id": int(msg_id),
            "file_unique_id": str(
                file_unique_id
                or metadata.get("file_unique_id")
                or metadata.get("fileUniqueId")
                or ""
            ).strip(),
            "fingerprint": str(fingerprint or metadata.get("fingerprint") or "").strip(),
            "title": title,
            "artist": str(metadata.get("artist") or "").strip(),
            "album": str(metadata.get("album") or "").strip(),
            "cover_url": str(metadata.get("cover_url") or metadata.get("coverUrl") or "").strip(),
            "genre": str(metadata.get("genre") or "").strip(),
            "year": str(metadata.get("year") or "").strip(),
            "source": normalized_source,
            "confidence": metadata_confidence(
                normalized_source,
                explicit_confidence,
            ),
            "manual_override": manual_flag,
            "recognized_at": metadata.get("recognized_at") or now,
            "updated_at": now,
        }

    async def save(
        self,
        metadata: dict,
        *,
        chat_id: Any,
        msg_id: Any,
        file_unique_id: str = "",
        fingerprint: str = "",
        source: str = "",
        manual_override: Optional[bool] = None,
        force: bool = False,
    ) -> Optional[dict]:
        doc = self._build_doc(
            metadata,
            chat_id=chat_id,
            msg_id=msg_id,
            file_unique_id=file_unique_id,
            fingerprint=fingerprint,
            source=source,
            manual_override=manual_override,
        )
        if not doc:
            return None
        coll = self._collection()
        if coll is None:
            existing = self._memory_track.get(doc["_id"])
            if existing and existing.get("manual_override") and not doc["manual_override"] and not force:
                return dict(existing)
            self._remember(doc)
            return _public_doc(doc)
        await self._ensure_indexes()
        try:
            existing = await coll.find_one({"_id": doc["_id"]}, {"manual_override": 1})
            if existing and existing.get("manual_override") and not doc["manual_override"] and not force:
                cached = await coll.find_one({"_id": doc["_id"]})
                if cached:
                    self._remember(cached)
                    return _public_doc(cached)
                return None
            update_doc = {k: v for k, v in doc.items() if k != "_id"}
            await coll.update_one({"_id": doc["_id"]}, {"$set": update_doc}, upsert=True)
            self._remember(doc)
            return _public_doc(doc)
        except Exception as exc:
            LOGGER.warning(f"[MUSIC META CACHE] Save failed for {doc['_id']}: {exc}")
            existing = self._memory_track.get(doc["_id"])
            if existing and existing.get("manual_override") and not doc["manual_override"] and not force:
                return dict(existing)
            self._remember(doc)
            return _public_doc(doc)

    async def save_many(self, items: Iterable[dict]) -> int:
        docs = []
        for item in items:
            doc = self._build_doc(
                item,
                chat_id=item.get("chat_id") or item.get("chatId"),
                msg_id=item.get("msg_id") or item.get("msgId"),
                file_unique_id=item.get("file_unique_id") or item.get("fileUniqueId") or "",
                fingerprint=item.get("fingerprint") or "",
                source=item.get("metadata_source") or item.get("metadataSource") or item.get("source") or "",
                manual_override=bool(item.get("manual_override") or item.get("manualOverride")),
            )
            if doc:
                docs.append(doc)
        if not docs:
            return 0

        coll = self._collection()
        if coll is None or UpdateOne is None:
            accepted = 0
            for doc in docs:
                existing = self._memory_track.get(doc["_id"])
                if existing and existing.get("manual_override") and not doc.get("manual_override"):
                    continue
                self._remember(doc)
                accepted += 1
            return accepted
        await self._ensure_indexes()
        try:
            ids = [doc["_id"] for doc in docs]
            protected = {
                d["_id"]
                async for d in coll.find({"_id": {"$in": ids}, "manual_override": True}, {"_id": 1})
            }
            protected.update(
                key
                for key in ids
                if self._memory_track.get(key, {}).get("manual_override")
            )
            ops = []
            accepted = []
            for doc in docs:
                if doc["_id"] in protected and not doc.get("manual_override"):
                    continue
                update_doc = {k: v for k, v in doc.items() if k != "_id"}
                ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": update_doc}, upsert=True))
                accepted.append(doc)
            if ops:
                await coll.bulk_write(ops, ordered=False)
            for doc in accepted:
                self._remember(doc)
            return len(accepted)
        except Exception as exc:
            LOGGER.warning(f"[MUSIC META CACHE] Batch save failed: {exc}")
            return 0


music_metadata_pipeline = MusicMetadataPipeline()
