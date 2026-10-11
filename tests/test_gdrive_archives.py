"""Run with: python -m unittest discover -s tests -v.

Import the real uploader with application startup/services stubbed so these tests
never create Telegram sessions or require MongoDB credentials.
"""
import importlib.util
import ast
import binascii
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
import shutil
import struct
import wave
import httpx
from contextlib import nullcontext
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_uploader():
    modules = {}
    for name in ("Backend", "Backend.helper", "Backend.pyrofork", "Backend.helper.metadata", "pyrogram"):
        module = types.ModuleType(name)
        module.__path__ = [str(ROOT.joinpath(*name.split(".")))]
        modules[name] = module
    for name, attributes in {
        "pyrogram.errors": {"FloodWait": type("FloodWait", (Exception,), {})},
        "Backend.logger": {"LOGGER": Mock()},
        "Backend.pyrofork.bot": {"StreamBot": Mock()},
        "Backend.helper.observability": {
            name: Mock() for name in (
                "correlation_context", "new_id", "record_error", "record_flood_wait", "set_gauge"
            )
        },
        "Backend.helper.metadata.music_scraper": {
            name: Mock() for name in (
                "clean_audio_filename", "extract_context_from_text", "fetch_music_metadata",
                "parse_artist_and_title", "is_generic_music_query", "strip_copy_prefix",
                "fetch_album_tracklist_online", "token_similarity",
            )
        },
        "Backend.helper.metadata.audio_fingerprint": {
            "extract_embedded_audio_tags": Mock(), "recognize_audio_from_local_file": Mock(),
        },
    }.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module
    spec = importlib.util.spec_from_file_location(
        "archive_test_uploader", ROOT / "Backend/helper/gdrive_uploader.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


uploader = load_uploader()


class DirectDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_mediafire_resumes_after_interrupted_stream(self):
        first_half = b"a" * (256 * 1024)
        second_half = b"b" * (256 * 1024)

        class BrokenStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield first_half
                raise httpx.ReadError("connection dropped")

            async def aclose(self):
                pass

        class GoodStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield second_half

            async def aclose(self):
                pass

        page_url = "https://www.mediafire.com/file/test/sample.rar"
        direct_url = "https://download.mediafire.com/file/sample.rar"
        requests = []

        def handler(request):
            requests.append(request)
            if str(request.url) == page_url:
                return httpx.Response(200, headers={"Content-Type": "text/html"},
                                      text=f'<a id="downloadButton" href="{direct_url}">Download</a>')
            if len([item for item in requests if str(item.url) == direct_url]) == 1:
                self.assertIsNone(request.headers.get("Range"))
                return httpx.Response(200, headers={"Content-Length": "524288", "ETag": '"v1"'},
                                      stream=BrokenStream())
            self.assertEqual(request.headers.get("Range"), "bytes=262144-")
            self.assertEqual(request.headers.get("If-Range"), '"v1"')
            return httpx.Response(206, headers={"Content-Range": "bytes 262144-524287/524288",
                                                "Content-Length": "262144", "ETag": '"v1"'},
                                  stream=GoodStream())

        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            work = Path(folder) / "work"
            work.mkdir()
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", return_value=client):
                result = await manager._download_direct_url(page_url, str(work))
            self.assertIsNotNone(result, manager._logs)
            self.assertEqual(Path(result).read_bytes(), first_half + second_half)
            self.assertEqual(manager._download_percent, 100)
            self.assertEqual(manager._download_bytes, 524288)
            self.assertEqual(len([req for req in requests if str(req.url) == page_url]), 2)
            self.assertTrue(list(cache.glob("*.complete.json")))
            self.assertFalse(list(cache.glob("*.part")))

    async def test_partial_legacy_cache_is_not_reused(self):
        url = "https://files.example.com/song.rar"
        requests = []

        class GoodStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"good"

            async def aclose(self):
                pass

        def handler(request):
            requests.append(request)
            return httpx.Response(200, headers={"Content-Length": "4"}, stream=GoodStream())

        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            (cache / f"{url_hash}_song.rar").write_bytes(b"x" * 8192)
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", return_value=client):
                result = await manager._download_direct_url(url, folder)
            self.assertIsNotNone(result, manager._logs)
            self.assertEqual(Path(result).read_bytes(), b"good")
            self.assertEqual(len(requests), 1)

    async def test_server_ignores_range_and_restarts_download(self):
        url = "https://files.example.com/album.rar"
        requests = []

        class GoodStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"abcdefgh"

            async def aclose(self):
                pass

        def handler(request):
            requests.append(request)
            return httpx.Response(200, headers={"Content-Length": "8"}, stream=GoodStream())

        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            (cache / f"{url_hash}.download.part").write_bytes(b"abcd")
            (cache / f"{url_hash}.download.meta.json").write_text(
                json.dumps({"url": url, "filename": "album.rar", "total": 8, "etag": '"x"'}),
                encoding="utf-8")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", return_value=client):
                result = await manager._download_direct_url(url, folder)
            self.assertEqual(requests[0].headers.get("Range"), "bytes=4-")
            self.assertIsNotNone(result, manager._logs)
            self.assertEqual(Path(result).read_bytes(), b"abcdefgh")

    async def test_invalid_content_range_discards_partial_and_retries(self):
        url = "https://files.example.com/range.rar"
        requests = []

        class GoodStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"abcdefgh"

            async def aclose(self):
                pass

        def handler(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(206, headers={"Content-Range": "bytes 0-7/8",
                                                   "Content-Length": "8"}, stream=GoodStream())
            return httpx.Response(200, headers={"Content-Length": "8"}, stream=GoodStream())

        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            (cache / f"{url_hash}.download.part").write_bytes(b"old-")
            (cache / f"{url_hash}.download.meta.json").write_text(
                json.dumps({"url": url, "filename": "range.rar", "total": 8}), encoding="utf-8")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", return_value=client):
                result = await manager._download_direct_url(url, folder)
            self.assertEqual(requests[0].headers.get("Range"), "bytes=4-")
            self.assertIsNone(requests[1].headers.get("Range"))
            self.assertIsNotNone(result, manager._logs)
            self.assertEqual(Path(result).read_bytes(), b"abcdefgh")

    async def test_verified_cache_is_reused_without_network(self):
        url = "https://files.example.com/cached.rar"
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            cached_file = cache / f"{url_hash}_cached.rar"
            cached_file.write_bytes(b"correct")
            Path(f"{cached_file}.complete.json").write_text(
                json.dumps({"url_hash": url_hash, "size": 7}), encoding="utf-8")
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", side_effect=AssertionError("unexpected network")):
                result = await manager._download_direct_url(url, folder)
            self.assertEqual(Path(result).read_bytes(), b"correct")
            self.assertEqual(manager._download_percent, 100)

    async def test_truncated_response_never_becomes_valid_cache(self):
        url = "https://files.example.com/short.rar"

        class ShortStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"abcd"

            async def aclose(self):
                pass

        def handler(request):
            return httpx.Response(200, headers={"Content-Length": "8"}, stream=ShortStream())

        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "cache"
            cache.mkdir()
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            manager = uploader.GoogleDriveUploadManager()
            with patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)), patch.object(
                    uploader.httpx, "AsyncClient", return_value=client):
                result = await manager._download_direct_url(url, folder)
            self.assertIsNone(result)
            self.assertFalse(list(cache.glob("*.complete.json")))
            self.assertEqual(manager._download_percent, 50)


def make_cdtext_packs(info, *, encoding="latin-1", block=0, double_byte=False):
    """Build CD-TEXT with strings sharing packs, continuation positions and CRC."""
    packs = []
    unit = 2 if double_byte else 1
    last_track = max(info)
    for kind, key in ((0x80, "title"), (0x81, "artist")):
        values = [info.get(number, {}).get(key, "").encode(encoding) + b"\0" * unit
                  for number in range(last_track + 1)]
        joined = b"".join(values)
        for offset in range(0, len(joined), 12):
            track, start = 0, 0
            while track < last_track and start + len(values[track]) <= offset:
                start += len(values[track])
                track += 1
            position = min(15, (offset - start) // unit)
            header = bytes((kind, track, len(packs), (block << 4) | position | (0x80 if double_byte else 0)))
            data = header + joined[offset:offset + 12].ljust(12, b"\0")
            packs.append(data + struct.pack(">H", binascii.crc_hqx(data, 0) ^ 0xffff))
    charset = 0x80 if encoding == "shift_jis" else 0
    data = bytes((0x8f, 0, len(packs), block << 4)) + bytes((charset, 1, last_track)) + bytes(9)
    packs.append(data + struct.pack(">H", binascii.crc_hqx(data, 0) ^ 0xffff))
    return b"".join(packs)


def create_audio_nrg(path, *, legacy=False, layout="DAO", subchannel=False, short_legacy=False,
                     cdtext=None, cdtext_encoding="latin-1"):
    """Create a small real-layout NRG with two distinguishable CD-DA tracks."""
    sector_size = 2448 if subchannel else 2352
    disc = b"".join(
        (bytes([track]) * 2352 + (b"S" * 96 if subchannel else b"")) * 2
        for track in (1, 2)
    )
    tracks = []
    for idx, track in enumerate((1, 2)):
        start = idx * sector_size * 2
        end = start + sector_size * 2
        if layout == "DAO" and legacy:
            tracks.append(
                bytes(12) + (
                    struct.pack(">HHHIII", sector_size, 0x0700, 1, start, start, end)
                    if short_legacy else struct.pack(">IIIII", sector_size, 7, start, start, end)
                )
            )
        elif layout == "DAO":
            mode = 0x1000 if subchannel else 0x0700
            tracks.append(bytes(12) + struct.pack(">HHHQQQ", sector_size, mode, 1, start, start, end))
        elif legacy:
            tracks.append(struct.pack(">IIIII", start, end - start, 7, 0, 0))
        else:
            tracks.append(struct.pack(">QQIIII", start, end - start, 7, 0, 0, 2))
    if layout == "DAO":
        payload = (struct.pack(">I", 0) + bytes(14)
                   + (struct.pack(">IBB", 0, 1, 2) if legacy and not short_legacy
                      else struct.pack(">HBB", 0, 1, 2))
                   + b"".join(tracks))
        kind = b"DAOI" if legacy else b"DAOX"
    else:
        payload = b"".join(tracks)
        kind = b"ETNF" if legacy else b"ETN2"
    metadata = kind + struct.pack(">I", len(payload)) + payload
    if cdtext:
        data = cdtext if isinstance(cdtext, bytes) else make_cdtext_packs(cdtext, encoding=cdtext_encoding)
        metadata += b"CDTX" + struct.pack(">I", len(data)) + data
    metadata += b"END!" + struct.pack(">I", 0)
    footer = (b"NERO" + struct.pack(">I", len(disc)) if legacy
              else b"NER5" + struct.pack(">Q", len(disc)))
    Path(path).write_bytes(disc + metadata + footer)
    return disc


class NrgAudioTests(unittest.TestCase):
    def test_wav_keeps_utf8_tags_readable_without_ffprobe(self):
        module = ast.parse((ROOT / "Backend/helper/metadata/audio_fingerprint.py").read_text(encoding="utf-8"))
        reader = next(node for node in module.body if isinstance(node, ast.FunctionDef)
                      and node.name == "extract_embedded_audio_tags")
        namespace = {"LOGGER": Mock()}
        exec(compile(ast.Module(body=[reader], type_ignores=[]), "riff_reader", "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "disc.nrg"
            create_audio_nrg(image, cdtext_encoding="utf-8", cdtext={
                0: {"title": "Khúc Tình Xưa", "artist": "Lệ Quyên"},
                1: {"title": "Đắm Trong Cuộc Tình"},
                2: {"title": "Yêu Người Con Gái"},
            })
            tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
            tags = namespace["extract_embedded_audio_tags"](Path(tracks[0]).read_bytes())
            self.assertEqual(tags, {"title": "Đắm Trong Cuộc Tình", "artist": "Lệ Quyên",
                                    "album": "Khúc Tình Xưa", "track": "1"})
            with (patch.object(uploader.subprocess, "run", side_effect=FileNotFoundError()),
                  patch.object(uploader, "extract_embedded_audio_tags", namespace["extract_embedded_audio_tags"])):
                self.assertEqual(uploader.read_audio_metadata_from_file(tracks[0]), tags)
            with wave.open(tracks[0], "rb") as wav:
                self.assertEqual(wav.readframes(wav.getnframes()), b"\x01" * 4704)

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe not installed")
    def test_wav_cdtext_tags_readable_by_real_ffprobe(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "disc.nrg"
            create_audio_nrg(image, cdtext_encoding="utf-8", cdtext={
                0: {"title": "Khúc Tình Xưa", "artist": "Lệ Quyên"},
                1: {"title": "Đắm Trong Cuộc Tình"},
            })
            tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
            result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                                     "-of", "json", tracks[0]], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["format"]["tags"]["title"], "Đắm Trong Cuộc Tình")
            self.assertEqual(data["format"]["tags"]["artist"], "Lệ Quyên")
            self.assertEqual(data["format"]["tags"]["album"], "Khúc Tình Xưa")
            self.assertEqual(data["streams"][0]["codec_name"], "pcm_s16le")
            self.assertEqual(data["streams"][0]["sample_rate"], "44100")

    def test_bad_crc_rejects_damaged_text_without_losing_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "disc.nrg"
            payload = bytearray(make_cdtext_packs({1: {"title": "Song One That Is Long"}, 2: {"title": "Song Two"}}))
            payload[5] ^= 1
            create_audio_nrg(image, cdtext=bytes(payload))
            tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
            self.assertEqual(Path(tracks[0]).name, "Track 01.wav")
            self.assertEqual(Path(tracks[1]).name, "02 - Song Two.wav")

    def test_vietnamese_cdtext_across_pack_boundaries_and_legacy_footer(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as temp:
                image = Path(temp) / "album.nrg"
                create_audio_nrg(image, legacy=legacy, cdtext_encoding="utf-8", cdtext={
                    0: {"title": "Khúc Tình Xưa 6", "artist": "Lệ Quyên"},
                    1: {"title": "Đắm Trong Cuộc Tình"},
                    2: {"title": "Yêu Người Con Gái"},
                })
                tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
                self.assertEqual([Path(p).name for p in tracks], [
                    "01 - Đắm Trong Cuộc Tình.wav", "02 - Yêu Người Con Gái.wav"
                ])
                info = uploader.read_nrg_cdtext(str(image))
                self.assertEqual(info[2]["artist"], "Lệ Quyên")
                self.assertEqual(info[1]["album"], "Khúc Tình Xưa 6")

    def test_cdtext_language_blocks_and_double_byte_repeat_artist(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "album.nrg"
            packs = make_cdtext_packs({
                0: {"title": "音楽アルバム", "artist": "歌手"},
                1: {"title": "最初の歌", "artist": "歌手"},
                2: {"title": "次の歌", "artist": "\t\t"},
            }, encoding="shift_jis", block=1, double_byte=True)
            create_audio_nrg(image, cdtext=packs)
            info = uploader.read_nrg_cdtext(str(image))
            self.assertEqual(info[1]["title"], "最初の歌")
            self.assertEqual(info[2]["artist"], "歌手")
            self.assertEqual(info[2]["album"], "音楽アルバム")

    def test_missing_continuation_pack_does_not_create_a_partial_title(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "album.nrg"
            payload = make_cdtext_packs({1: {"title": "A very long title that spans several packs"},
                                         2: {"title": "Song Two", "artist": "Singer"}})
            # Remove a middle title pack while retaining the rest of the disc.
            create_audio_nrg(image, cdtext=payload[:18] + payload[36:])
            info = uploader.read_nrg_cdtext(str(image))
            self.assertFalse(info.get(1, {}).get("title"))
            self.assertEqual(info[2]["title"], "Song Two")

    def test_album_only_and_malformed_cdtext_preserve_playable_audio(self):
        for payload in (make_cdtext_packs({0: {"title": "Album", "artist": "Singer"}}), b"bad CDTX"):
            with self.subTest(payload=payload[:18]), tempfile.TemporaryDirectory() as temp:
                image = Path(temp) / "disc.nrg"
                create_audio_nrg(image, cdtext=payload)
                tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
                self.assertEqual([Path(p).name for p in tracks], ["Track 01.wav", "Track 02.wav"])
                if len(payload) % 18 == 0:
                    info = uploader.read_nrg_cdtext(str(image))
                    self.assertEqual(info[1]["album"], "Album")
                    self.assertEqual(info[2]["artist"], "Singer")
                    self.assertFalse(info[1].get("title"))
                else:
                    self.assertEqual(uploader.read_nrg_cdtext(str(image)), {})

    def test_cdtext_renames_tracks_and_reads_album_and_artist(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "album.nrg"
            create_audio_nrg(image, cdtext={
                0: {"title": "Khuc Tinh Xua", "artist": "Le Quyen"},
                1: {"title": "Dam Trong Cuoc Tinh", "artist": "Le Quyen"},
                2: {"title": "Yeu / Nguoi: Con Gai", "artist": "Ca Si Khac"},
            })
            info = uploader.read_nrg_cdtext(str(image))
            self.assertEqual(info[1], {"track": "1", "title": "Dam Trong Cuoc Tinh",
                                       "artist": "Le Quyen", "album": "Khuc Tinh Xua"})
            self.assertEqual(info[2]["artist"], "Ca Si Khac")
            tracks = uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
            self.assertEqual([Path(p).name for p in tracks], [
                "01 - Dam Trong Cuoc Tinh.wav", "02 - Yeu Nguoi Con Gai.wav"
            ])
            with wave.open(tracks[0], "rb") as wav:
                self.assertEqual(wav.readframes(588 * 2), b"\x01" * (2352 * 2))

    def test_dao_legacy_and_track_at_once_are_lossless(self):
        for legacy, layout, short in ((False, "DAO", False), (True, "DAO", False),
                                     (True, "DAO", True), (False, "ETN", False),
                                     (True, "ETN", False)):
            with self.subTest(legacy=legacy, layout=layout, short=short), tempfile.TemporaryDirectory() as temp:
                image = Path(temp) / "album.nrg"
                create_audio_nrg(image, legacy=legacy, layout=layout, short_legacy=short)
                output = Path(temp) / "tracks"
                ok, msg = uploader._sync_extract_archive(str(image), str(output))
                self.assertTrue(ok, msg)
                self.assertEqual(sorted(f.name for f in output.iterdir()), ["Track 01.wav", "Track 02.wav"])
                for index in (1, 2):
                    with wave.open(str(output / f"Track {index:02d}.wav"), "rb") as track:
                        self.assertEqual((track.getnchannels(), track.getsampwidth(), track.getframerate()), (2, 2, 44100))
                        self.assertEqual(track.readframes(588 * 2), bytes([index]) * (2352 * 2))

    def test_subchannel_bytes_are_not_written_into_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "album.nrg"
            create_audio_nrg(image, subchannel=True)
            ok, msg = uploader._sync_extract_archive(str(image), str(Path(temp) / "tracks"))
            self.assertTrue(ok, msg)
            with wave.open(str(Path(temp) / "tracks/Track 01.wav"), "rb") as track:
                self.assertEqual(track.getnframes(), 588 * 2)
                self.assertNotIn(b"S" * 16, track.readframes(588 * 2))

    def test_invalid_track_bounds_leave_no_partial_wavs(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "album.nrg"
            create_audio_nrg(image)
            data = bytearray(image.read_bytes())
            # DAOX first track index-1 at payload offset 22 + 26.
            first_track_start = len(data) - 12 - 8 - (8 + 22 + 42 * 2) + 8 + 22 + 26
            data[first_track_start:first_track_start + 8] = struct.pack(">Q", 10**12)
            image.write_bytes(data)
            with self.assertRaises(uploader.NRGError):
                uploader.extract_nrg_audio(str(image), str(Path(temp) / "tracks"))
            self.assertFalse(list(Path(temp).rglob("*.wav")))

    def test_nrg_extracted_from_zip_is_detected_as_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "disc.nrg"
            create_audio_nrg(image)
            package = Path(temp) / "album.zip"
            with zipfile.ZipFile(package, "w") as zipped:
                zipped.write(image, "music/disc.nrg")
            extracted = Path(temp) / "extracted"
            self.assertTrue(uploader._sync_extract_archive(str(package), str(extracted))[0])
            self.assertTrue(uploader._sync_extract_archive(
                str(extracted / "music/disc.nrg"), str(extracted / "_nrg_tracks_001"))[0])
            self.assertEqual(len(uploader.GoogleDriveUploadManager()._collect_audio_files(str(extracted))), 2)


class CueEncodingTests(unittest.TestCase):
    def test_cue_relative_image_path_is_preserved_for_matching(self):
        with tempfile.TemporaryDirectory() as temp:
            cue_path = Path(temp) / "disc.cue"
            cue_path.write_text('FILE "CD2\\disc.nrg" BINARY\n  TRACK 01 AUDIO\n'
                                '    TITLE "Song"\n', encoding="utf-8")
            tracks = uploader.parse_cue_file(str(cue_path))
            self.assertEqual(tracks[1]["file_name"], "disc.nrg")
            self.assertTrue(uploader._cue_matches_nrg(str(cue_path), str(Path(temp) / "CD2/disc.nrg"), tracks))
            self.assertFalse(uploader._cue_matches_nrg(str(cue_path), str(Path(temp) / "CD1/disc.nrg"), tracks))
            self.assertFalse(uploader._cue_matches_nrg(str(cue_path), str(Path(temp) / "disc.nrg"), tracks))

    def test_track_title_and_artist_do_not_become_album_when_header_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            cue_path = Path(temp) / "disc.cue"
            cue_path.write_text('FILE "disc.nrg" BINARY\n  TRACK 01 AUDIO\n'
                                '    TITLE "Tên Bài"\n    PERFORMER "Ca Sĩ"\n', encoding="utf-8")
            track = uploader.parse_cue_file(str(cue_path))[1]
            self.assertEqual(track["title"], "Tên Bài")
            self.assertEqual(track["artist"], "Ca Sĩ")
            self.assertEqual(track["album"], "")

    def test_gbk_cue_keeps_chinese_artist_and_title(self):
        artist = "\u672a\u77e5\u827a\u672f\u5bb6"
        title = "\u6d4b\u8bd5\u6b4c\u66f2"
        album = "\u6d4b\u8bd5\u4e13\u8f91"
        cue_text = (
            f'PERFORMER "{artist}"\n'
            f'TITLE "{album}"\n'
            'FILE "Track02.flac" WAVE\n'
            '  TRACK 02 AUDIO\n'
            f'    TITLE "{title}"\n'
            f'    PERFORMER "{artist}"\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            cue_path = Path(temp) / "album.cue"
            cue_path.write_bytes(cue_text.encode("gbk"))
            tracks = uploader.parse_cue_file(str(cue_path))

        self.assertEqual(tracks[2]["artist"], artist)
        self.assertEqual(tracks[2]["title"], title)
        self.assertEqual(tracks[2]["album"], album)
        self.assertEqual(tracks[2]["file_name"], "Track02.flac")


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = str(Path(self.temp.name) / "album.rar")
        Path(self.archive).write_bytes(b"RAR fixture handled by mocked CLI")
        self.destination = str(Path(self.temp.name) / "extracted")
        fake_os = types.SimpleNamespace(**vars(os))
        fake_os.path = types.SimpleNamespace(**vars(os.path))
        fake_os.name = "posix"
        self.enterContext(patch.object(uploader, "os", fake_os))
        self.portable = self.enterContext(patch.object(
            uploader, "ensure_portable_7zip", side_effect=RuntimeError("offline")
        ))
        actual_exists = os.path.exists
        self.enterContext(patch.object(
            uploader.os.path, "exists",
            side_effect=lambda p: str(p) in ("/usr/bin/7z", "/usr/bin/7za")
            or (str(p).startswith(self.temp.name) and actual_exists(p)),
        ))
        self.enterContext(patch.object(
            uploader.shutil, "which",
            side_effect=lambda name: {
                "7z": "/usr/bin/7z", "7za": "/usr/bin/7za", "apt-get": "/usr/bin/apt-get"
            }.get(name),
        ))

        def run(cmd, **kwargs):
            if cmd[0] == "apt-get":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            detail = ("ERROR: Unsupported Method : album/track.wav" if cmd[0].endswith("/7z")
                      else "ERROR: Cannot open the file as archive")
            return subprocess.CompletedProcess(cmd, 2, "", detail)

        self.run = self.enterContext(patch.object(subprocess, "run", side_effect=run))

    def test_keeps_unsupported_method_when_later_fallback_cannot_open(self):
        success, message = uploader._sync_extract_archive(self.archive, self.destination)
        self.assertFalse(success)
        self.assertIn("Unsupported Method", message)

    def test_unsupported_legacy_7z_installs_and_retries_official_7zz(self):
        portable = "/app/Music/tools/7zz"
        self.portable.side_effect = None
        self.portable.return_value = portable

        def run(cmd, **kwargs):
            if cmd[0] == portable:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            detail = ("ERROR: Unsupported Method : album/track.wav"
                      if cmd[0].endswith("/7z") else "ERROR: Cannot open the file as archive")
            return subprocess.CompletedProcess(cmd, 2, "", detail)

        self.run.side_effect = run
        success, message = uploader._sync_extract_archive(self.archive, self.destination)

        self.assertTrue(success, message)
        self.portable.assert_called_once()
        self.assertEqual(self.run.call_args_list[-1].args[0][0], portable)

    def test_does_not_install_same_codec_less_package_during_upload(self):
        uploader._sync_extract_archive(self.archive, self.destination)
        self.assertFalse(any(call.args[0][0] == "apt-get" for call in self.run.call_args_list))

    def test_password_is_passed_as_one_argument_without_trimming(self):
        password = " album pass;$' "
        self.run.side_effect = lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, "", "")
        success, _ = uploader._sync_extract_archive(self.archive, self.destination, password)
        self.assertTrue(success)
        self.assertIn(f"-p{password}", self.run.call_args.args[0])
        self.assertEqual(self.run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_password_error_is_not_replaced_by_unsupported_method(self):
        def run(cmd, **kwargs):
            detail = "Wrong password" if cmd[0].endswith("/7z") else "Unsupported Method"
            return subprocess.CompletedProcess(cmd, 2, "", detail)
        self.run.side_effect = run
        success, message = uploader._sync_extract_archive(self.archive, self.destination, "wrong")
        self.assertFalse(success)
        self.assertIn("Mật khẩu giải nén không đúng", message)
        self.assertNotIn("cài 7-Zip", message)

    def test_missing_password_requests_password_instead_of_codec(self):
        self.run.side_effect = lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, 2, "", "Wrong password"
        )
        success, message = uploader._sync_extract_archive(self.archive, self.destination)
        self.assertFalse(success)
        self.assertIn("Vui lòng nhập mật khẩu", message)

    def test_missing_archiver_is_not_reported_as_password_problem(self):
        with patch.object(uploader.os.path, "exists", return_value=False):
            success, message = uploader._sync_extract_archive(self.archive, self.destination, "provided")
        self.assertFalse(success)
        self.assertIn("Không tìm thấy công cụ", message)
        self.assertNotIn("kiểm tra mật khẩu", message)

    def test_missing_archiver_recovers_and_uses_password_in_same_request(self):
        self.portable.side_effect = None
        self.portable.return_value = "/app/Music/tools/7zz"
        self.run.side_effect = lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, "", "")
        with patch.object(uploader.os.path, "exists", return_value=False):
            success, message = uploader._sync_extract_archive(self.archive, self.destination, "provided")
        self.assertTrue(success, message)
        self.assertEqual(self.run.call_args.args[0][0], "/app/Music/tools/7zz")
        self.assertIn("-pprovided", self.run.call_args.args[0])
        self.portable.assert_called_once()

    def test_timeout_does_not_expose_password_in_logs_or_error(self):
        password = " secret' pass "
        self.run.side_effect = lambda cmd, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd, 300)
        )
        uploader.LOGGER.reset_mock()
        success, message = uploader._sync_extract_archive(self.archive, self.destination, password)
        self.assertFalse(success)
        self.assertNotIn(password, message)
        self.assertNotIn("secret", str(uploader.LOGGER.mock_calls))

    def test_official_7zz_is_used_before_legacy_tools(self):
        previous_exists = uploader.os.path.exists.side_effect
        with patch.object(uploader.os.path, "exists", side_effect=lambda p:
                          str(p) == "/usr/local/bin/7zz" or previous_exists(p)):
            self.run.side_effect = lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, "", "")
            success, _ = uploader._sync_extract_archive(self.archive, self.destination)
        self.assertTrue(success)
        self.assertEqual(self.run.call_args_list[0].args[0][0], "/usr/local/bin/7zz")

    def test_successful_fallback_starts_without_partial_files(self):
        def run(cmd, **kwargs):
            partial = Path(self.destination) / "partial.wav"
            if cmd[0].endswith("/7z"):
                partial.write_bytes(b"incomplete")
                return subprocess.CompletedProcess(cmd, 2, "", "Unsupported Method")
            self.assertFalse(partial.exists())
            (Path(self.destination) / "track.wav").write_bytes(b"complete")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        self.run.side_effect = run
        success, _ = uploader._sync_extract_archive(self.archive, self.destination)
        self.assertTrue(success)
        self.assertEqual((Path(self.destination) / "track.wav").read_bytes(), b"complete")

    def test_zip_still_extracts_without_external_tools(self):
        archive = str(Path(self.temp.name) / "album.zip")
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("album/track.wav", b"audio bytes")
        with patch.object(uploader.os.path, "exists", return_value=False):
            success, _ = uploader._sync_extract_archive(archive, self.destination)
        self.assertTrue(success)
        self.assertEqual((Path(self.destination) / "album/track.wav").read_bytes(), b"audio bytes")
        self.run.assert_not_called()


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def run_nrg_package(self, source, temp, *, as_document=False):
        client = Mock(is_connected=True)
        client.send_audio = AsyncMock(return_value=types.SimpleNamespace(id=401))
        client.send_document = AsyncMock(return_value=types.SimpleNamespace(id=402))
        manager = uploader.GoogleDriveUploadManager()
        manager._download_direct_url = AsyncMock(return_value=str(source))
        manager._index_uploaded_tracks = AsyncMock()
        music_routes = types.ModuleType("Backend.fastapi.routes.music_routes")
        music_routes._db_load_library = AsyncMock(return_value=[])
        music_routes._db_save_library = AsyncMock()
        fingerprint = AsyncMock(return_value=None)
        with (
            patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
            patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(Path(temp) / "cache")),
            patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(client, "bot"))),
            patch.object(uploader, "_cleanup_old_temp_files"),
            patch.object(uploader, "extract_context_from_text", return_value=("", "")),
            patch.object(uploader, "read_audio_metadata_from_file", return_value={}),
            patch.object(uploader, "clean_audio_filename", side_effect=lambda name: Path(name).stem),
            patch.object(uploader, "parse_artist_and_title", return_value=("", "", "")),
            patch.object(uploader, "recognize_audio_from_local_file", fingerprint),
            patch.object(uploader, "strip_copy_prefix", side_effect=lambda value: value),
            patch.object(uploader, "is_generic_music_query", side_effect=lambda title, *args: title.startswith("Track")),
            patch.object(uploader.asyncio, "sleep", AsyncMock()),
            patch.dict(sys.modules, {music_routes.__name__: music_routes}),
        ):
            await manager._run_upload_pipeline(
                "url", [("direct", "https://example.com/album", "url")],
                "-100123", "", "", False, as_document,
            )
        self.assertEqual(manager._status, "completed", manager._error_message)
        return client, manager, fingerprint

    async def test_multiple_nrgs_keep_own_album_and_cue_for_missing_cdtext(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "collection.zip"
            first = Path(temp) / "disc1.nrg"
            second = Path(temp) / "disc2.nrg"
            create_audio_nrg(first, cdtext_encoding="utf-8", cdtext={
                0: {"title": "Album Một", "artist": "Ca Sĩ Một"},
                1: {"title": "Bài Một"}, 2: {"title": "Bài Hai"},
            })
            create_audio_nrg(second)
            with zipfile.ZipFile(source, "w") as zipped:
                # The same disc name in separate folders must not mix CUEs.
                zipped.write(first, "disc1/disc.nrg")
                zipped.write(second, "disc2/disc.nrg")
                for name, album, artist, titles in (
                    ("disc1", "Wrong Album", "Wrong Artist", ("Wrong One", "Wrong Two")),
                    ("disc2", "Album Hai", "Ca Sĩ Hai", ("Bài Ba", "Bài Bốn")),
                ):
                    zipped.writestr(f"{name}/disc.cue", f'TITLE "{album}"\nPERFORMER "{artist}"\n'
                                    'FILE "disc.nrg" BINARY\n'
                                    f'  TRACK 01 AUDIO\n    TITLE "{titles[0]}"\n'
                                    f'  TRACK 02 AUDIO\n    TITLE "{titles[1]}"\n')
            client, manager, fingerprint = await self.run_nrg_package(source, temp)
            self.assertEqual([call.kwargs["title"] for call in client.send_audio.call_args_list],
                             ["Bài Một", "Bài Hai", "Bài Ba", "Bài Bốn"])
            self.assertEqual([track["album"] for track in manager._uploaded_tracks],
                             ["Album Một"] * 2 + ["Album Hai"] * 2)
            self.assertEqual([track["artist"] for track in manager._uploaded_tracks],
                             ["Ca Sĩ Một"] * 2 + ["Ca Sĩ Hai"] * 2)
            fingerprint.assert_not_awaited()

    async def test_document_upload_uses_cdtext_filename_and_caption(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "disc.nrg"
            create_audio_nrg(image, cdtext_encoding="utf-8", cdtext={
                0: {"title": "Album", "artist": "Ca Sĩ"},
                1: {"title": "Bài Một"}, 2: {"title": "Bài Hai"},
            })
            client, _, fingerprint = await self.run_nrg_package(image, temp, as_document=True)
            client.send_audio.assert_not_awaited()
            self.assertEqual([Path(call.kwargs["document"]).name for call in client.send_document.call_args_list],
                             ["01 - Bài Một.wav", "02 - Bài Hai.wav"])
            self.assertIn("Ca Sĩ", client.send_document.call_args_list[0].kwargs["caption"])
            fingerprint.assert_not_awaited()

    async def test_cdtext_titles_and_artists_used_for_telegram_direct_and_zip(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed), tempfile.TemporaryDirectory() as temp:
                image = Path(temp) / "disc.nrg"
                create_audio_nrg(image, cdtext={
                    0: {"title": "Ten Album", "artist": "Ca Si"},
                    1: {"title": "Bai Hat Mot", "artist": "Ca Si"},
                    2: {"title": "Bai Hat Hai", "artist": "Khach Moi"},
                })
                source = image
                if compressed:
                    source = Path(temp) / "album.zip"
                    with zipfile.ZipFile(source, "w") as zipped:
                        zipped.write(image, "disc.nrg")
                client = Mock(is_connected=True)
                client.send_audio = AsyncMock(side_effect=[
                    types.SimpleNamespace(id=301), types.SimpleNamespace(id=302)
                ])
                manager = uploader.GoogleDriveUploadManager()
                manager._download_direct_url = AsyncMock(return_value=str(source))
                manager._index_uploaded_tracks = AsyncMock()
                music_routes = types.ModuleType("Backend.fastapi.routes.music_routes")
                music_routes._db_load_library = AsyncMock(return_value=[])
                music_routes._db_save_library = AsyncMock()
                with (
                    patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
                    patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(Path(temp) / "cache")),
                    patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(client, "bot"))),
                    patch.object(uploader, "_cleanup_old_temp_files"),
                    patch.object(uploader, "extract_context_from_text", return_value=("", "")),
                    patch.object(uploader, "read_audio_metadata_from_file", return_value={}),
                    patch.object(uploader, "clean_audio_filename", side_effect=lambda name: Path(name).stem),
                    patch.object(uploader, "strip_copy_prefix", side_effect=lambda value: value),
                    patch.object(uploader, "is_generic_music_query", side_effect=lambda title, *args: title.startswith("Track")),
                    patch.object(uploader.asyncio, "sleep", AsyncMock()),
                    patch.dict(sys.modules, {music_routes.__name__: music_routes}),
                ):
                    await manager._run_upload_pipeline(
                        "url", [("direct", "https://example.com/album", "url")],
                        "-100123", "", "", False, False,
                    )
                self.assertEqual(manager._status, "completed", manager._error_message)
                calls = client.send_audio.call_args_list
                self.assertEqual([call.kwargs["title"] for call in calls], ["Bai Hat Mot", "Bai Hat Hai"])
                self.assertEqual([call.kwargs["performer"] for call in calls], ["Ca Si", "Khach Moi"])
                self.assertEqual([Path(call.kwargs["audio"]).name for call in calls], [
                    "01 - Bai Hat Mot.wav", "02 - Bai Hat Hai.wav"
                ])
                self.assertEqual([item["album"] for item in manager._uploaded_tracks], ["Ten Album"] * 2)

    async def test_nrg_from_direct_link_or_zip_uploads_each_wav_track(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed), tempfile.TemporaryDirectory() as temp:
                image = Path(temp) / "album.nrg"
                create_audio_nrg(image)
                source = image
                if compressed:
                    source = Path(temp) / "album.zip"
                    with zipfile.ZipFile(source, "w") as zipped:
                        zipped.write(image, "album/disc.nrg")
                client = Mock(is_connected=True)
                client.send_audio = AsyncMock(side_effect=[
                    types.SimpleNamespace(id=201), types.SimpleNamespace(id=202)
                ])
                manager = uploader.GoogleDriveUploadManager()
                manager._download_direct_url = AsyncMock(return_value=str(source))
                manager._index_uploaded_tracks = AsyncMock()
                music_routes = types.ModuleType("Backend.fastapi.routes.music_routes")
                music_routes._db_load_library = AsyncMock(return_value=[])
                music_routes._db_save_library = AsyncMock()
                with (
                    patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
                    patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(Path(temp) / "cache")),
                    patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(client, "bot"))),
                    patch.object(uploader, "_cleanup_old_temp_files"),
                    patch.object(uploader, "extract_context_from_text", return_value=("", "")),
                    patch.object(uploader, "read_audio_metadata_from_file", return_value={
                        "title": "Recorded song", "artist": "Artist", "album": "Album"
                    }),
                    patch.object(uploader, "strip_copy_prefix", side_effect=lambda value: value),
                    patch.object(uploader, "is_generic_music_query", return_value=False),
                    patch.object(uploader.asyncio, "sleep", AsyncMock()),
                    patch.dict(sys.modules, {music_routes.__name__: music_routes}),
                ):
                    await manager._run_upload_pipeline(
                        "url", [("direct", "https://example.com/album", "url")],
                        "-100123", "Artist", "Album", False, False,
                    )
                self.assertEqual(manager._status, "completed", manager._error_message)
                self.assertEqual(client.send_audio.await_count, 2)
                sent_files = [Path(call.kwargs["audio"]).name for call in client.send_audio.call_args_list]
                self.assertEqual(sent_files, ["Track 01.wav", "Track 02.wav"])

    async def test_start_forwards_password_without_exposing_it_in_status(self):
        manager = uploader.GoogleDriveUploadManager()
        manager._run_upload_pipeline = AsyncMock()
        password = " album pass;$ "
        with (
            patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(Mock(), "bot"))),
            patch.object(uploader, "correlation_context", return_value=nullcontext()),
        ):
            result = await manager.start(
                "https://example.com/album.rar", "-100123", archive_password=password
            )
            await manager._task
        self.assertTrue(result["ok"])
        self.assertEqual(manager._run_upload_pipeline.call_args.kwargs["archive_password"], password)
        self.assertNotIn(password, str(manager.get_status()))

    async def test_failed_extraction_reports_error_and_preserves_download_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            cache.mkdir()
            archive = cache / "file123_album.rar"
            archive.write_bytes(b"cached archive")
            manager = uploader.GoogleDriveUploadManager()
            manager._download_gdrive_file = AsyncMock(return_value=str(archive))
            with (
                patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
                patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)),
                patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(Mock(), "bot"))),
                patch.object(uploader, "_extract_archive", AsyncMock(return_value=(False, "Unsupported Method"))) as extract,
                patch.object(uploader, "_cleanup_old_temp_files"),
            ):
                await manager._run_upload_pipeline(
                    "source", [("file", "file123", "source")], "-100123", "", "", False, False,
                    archive_password=" album pass;$ ",
                )
                self.assertEqual(extract.call_args.args[2], " album pass;$ ")
            self.assertEqual(manager._status, "error")
            self.assertIn("Unsupported Method", manager._error_message)
            self.assertFalse(any("🎉" in entry["msg"] for entry in manager._logs))
            self.assertFalse(any("Không tìm thấy bài hát" in entry["msg"] for entry in manager._logs))
            self.assertTrue(archive.exists())

    async def run_audio_queue(self, *, failed_archive=False, send_failure=False, cancel=False):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            cache.mkdir()
            paths = {"audio": cache / "audio_track.wav"}
            if failed_archive:
                paths = {"rar": cache / "rar_album.rar", **paths}
            for path in paths.values():
                path.write_bytes(b"downloaded content")
            manager = uploader.GoogleDriveUploadManager()
            client = Mock(is_connected=True)
            client.send_audio = AsyncMock(
                side_effect=OSError("upload failed") if send_failure else None,
                return_value=types.SimpleNamespace(id=123),
            )

            async def download(file_id, *args, **kwargs):
                if cancel:
                    manager._cancel_requested = True
                return str(paths[file_id])

            manager._download_gdrive_file = download
            manager._index_uploaded_tracks = AsyncMock()
            music_routes = types.ModuleType("Backend.fastapi.routes.music_routes")
            music_routes._db_load_library = AsyncMock(return_value=[])
            music_routes._db_save_library = AsyncMock()
            with (
                patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
                patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)),
                patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(client, "bot"))),
                patch.object(uploader, "_extract_archive", AsyncMock(return_value=(False, "Unsupported Method"))),
                patch.object(uploader, "_cleanup_old_temp_files"),
                patch.object(uploader, "read_audio_metadata_from_file", return_value={
                    "title": "Song", "artist": "Singer", "album": "Album"
                }),
                patch.object(uploader, "strip_copy_prefix", side_effect=lambda value: value),
                patch.object(uploader, "is_generic_music_query", return_value=False),
                patch.object(uploader.asyncio, "sleep", AsyncMock()),
                patch.object(uploader, "record_error", AsyncMock()) as record_error,
                patch.dict(sys.modules, {music_routes.__name__: music_routes}),
            ):
                await manager._run_upload_pipeline(
                    "source", [("file", key, key) for key in paths], "-100123", "", "", False, False
                )
                record_error.assert_not_awaited()
            return manager, {key: path.exists() for key, path in paths.items()}, client

    async def test_mixed_queue_uploads_next_item_but_keeps_failed_archive(self):
        manager, cached, client = await self.run_audio_queue(failed_archive=True)
        self.assertEqual(manager._status, "error")
        self.assertEqual(len(manager._uploaded_tracks), 1)
        self.assertIn("Unsupported Method", manager._error_message)
        self.assertTrue(cached["rar"])
        self.assertFalse(cached["audio"])
        client.send_audio.assert_awaited_once()

    async def test_successful_upload_is_completed_and_cache_is_removed(self):
        manager, cached, _ = await self.run_audio_queue()
        self.assertEqual(manager._status, "completed")
        self.assertEqual(len(manager._uploaded_tracks), 1)
        self.assertFalse(cached["audio"])

    async def test_successful_direct_url_upload_removes_hashed_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            cache.mkdir()
            url = "https://www.mediafire.com/file/example/track.wav/file"
            url_hash = uploader.hashlib.md5(url.encode()).hexdigest()[:12]
            cached_file = cache / f"{url_hash}_track.wav"
            cached_file.write_bytes(b"downloaded content")

            manager = uploader.GoogleDriveUploadManager()
            manager._download_direct_url = AsyncMock(return_value=str(cached_file))
            manager._index_uploaded_tracks = AsyncMock()
            client = Mock(is_connected=True)
            client.send_audio = AsyncMock(return_value=types.SimpleNamespace(id=123))
            music_routes = types.ModuleType("Backend.fastapi.routes.music_routes")
            music_routes._db_load_library = AsyncMock(return_value=[])
            music_routes._db_save_library = AsyncMock()

            with (
                patch.object(uploader, "TEMP_UPLOAD_DIR", temp),
                patch.object(uploader, "CACHE_DOWNLOAD_DIR", str(cache)),
                patch.object(uploader, "_get_upload_client", AsyncMock(return_value=(client, "bot"))),
                patch.object(uploader, "_cleanup_old_temp_files"),
                patch.object(uploader, "read_audio_metadata_from_file", return_value={
                    "title": "Song", "artist": "Singer", "album": "Album"
                }),
                patch.object(uploader, "strip_copy_prefix", side_effect=lambda value: value),
                patch.object(uploader, "is_generic_music_query", return_value=False),
                patch.object(uploader.asyncio, "sleep", AsyncMock()),
                patch.object(uploader, "record_error", AsyncMock()),
                patch.dict(sys.modules, {music_routes.__name__: music_routes}),
            ):
                await manager._run_upload_pipeline(
                    url, [("direct", url, url)], "-100123", "", "", False, False
                )

            self.assertEqual(manager._status, "completed")
            self.assertFalse(cached_file.exists())

    async def test_failed_telegram_upload_is_error_and_keeps_cache(self):
        manager, cached, client = await self.run_audio_queue(send_failure=True)
        self.assertEqual(manager._status, "error")
        self.assertTrue(cached["audio"])
        self.assertEqual(client.send_audio.await_count, 3)

    async def test_cancellation_is_not_overwritten_by_completion(self):
        manager, cached, client = await self.run_audio_queue(cancel=True)
        self.assertEqual(manager._status, "cancelled")
        self.assertTrue(cached["audio"])
        client.send_audio.assert_not_awaited()


class EncryptedArchiveIntegrationTests(unittest.TestCase):
    """Real encrypted files; the RAR test uses a locally available console archiver."""

    def test_rar5_passwords_with_real_archiver(self):
        archiver = next((p for p in (
            shutil.which("7zz"), shutil.which("unrar"),
            r"C:\Program Files\WinRAR\UnRAR.exe", shutil.which("7z"),
        ) if p and os.path.isfile(p)), None)
        if not archiver:
            self.skipTest("Install 7-Zip or UnRAR to run the real RAR5 test")
        actual_exists = os.path.exists
        with tempfile.TemporaryDirectory() as temp, (
            patch.object(uploader.shutil, "which", side_effect=lambda name:
                         archiver if name == Path(archiver).stem else None)
        ), patch.object(uploader.os.path, "exists", side_effect=lambda p:
                        str(p) == archiver or (str(p).startswith(temp) and actual_exists(p))):
            for filename, password, expected_success in (
                ("password-album.rar", "", False),
                ("password-album.rar", "wrong password", False),
                ("password-album.rar", " album pass;$ ", True),
                ("plain-album.rar", "", True),
            ):
                fixture = ROOT / "tests/fixtures" / filename
                with self.subTest(archive=filename, expected_success=expected_success):
                    destination = str(Path(temp) / str(len(password)))
                    success, message = uploader._sync_extract_archive(str(fixture), destination, password)
                    if expected_success:
                        self.assertTrue(success, message)
                        self.assertEqual(
                            (Path(destination) / "track.wav").read_bytes(),
                            b"RIFF" + b"archive password regression test\n" * 4,
                        )
                    else:
                        self.assertFalse(success)
                        self.assertIn("mật khẩu", message.lower())

    def test_7z_password_with_real_python_backend(self):
        import py7zr
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "track.wav"
            source.write_bytes(b"test audio")
            archive = Path(temp) / "album.7z"
            with py7zr.SevenZipFile(archive, "w", password=" album pass;$ ", header_encryption=True) as output:
                output.write(source, "track.wav")
            actual_exists = os.path.exists
            with (
                patch.object(uploader.shutil, "which", return_value=None),
                patch.object(uploader.os.path, "exists", side_effect=lambda p:
                             str(p).startswith(temp) and actual_exists(p)),
            ):
                success, message = uploader._sync_extract_archive(str(archive), str(Path(temp) / "missing"))
                self.assertFalse(success)
                self.assertIn("Vui lòng nhập mật khẩu", message)
                success, message = uploader._sync_extract_archive(
                    str(archive), str(Path(temp) / "wrong"), "wrong password"
                )
                self.assertFalse(success)
                self.assertIn("mật khẩu", message.lower())
                destination = str(Path(temp) / "correct")
                success, message = uploader._sync_extract_archive(str(archive), destination, " album pass;$ ")
                self.assertTrue(success, message)
                self.assertEqual((Path(destination) / "track.wav").read_bytes(), b"test audio")


class UploadEndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Execute the actual endpoint body without unrelated app startup imports.
        from fastapi.responses import JSONResponse
        source = ROOT / "Backend/fastapi/routes/music/gdrive.py"
        endpoint = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body
                        if isinstance(node, ast.AsyncFunctionDef) and node.name == "start_gdrive_upload")
        endpoint.decorator_list = []
        namespace = {"Depends": lambda dependency: None, "require_auth": Mock(), "JSONResponse": JSONResponse}
        exec(compile(ast.Module(body=[endpoint], type_ignores=[]), str(source), "exec"), namespace)
        self.endpoint = namespace["start_gdrive_upload"]

    async def test_endpoint_forwards_optional_password_exactly(self):
        modules = {name: types.ModuleType(name) for name in (
            "Backend", "Backend.helper", "Backend.helper.gdrive_uploader"
        )}
        manager = Mock()
        manager.start = AsyncMock(return_value={"ok": True, "message": "started"})
        manager.get_status.return_value = {"status": "downloading"}
        modules["Backend.helper.gdrive_uploader"].gdrive_upload_manager = manager
        for value in (None, " pass with spaces;$ "):
            payload = {"url": "https://example.com/album.rar", "channel_id": "-100123"}
            if value is not None:
                payload["archive_password"] = value
            with patch.dict(sys.modules, modules), patch("importlib.reload", side_effect=lambda module: module):
                response = await self.endpoint(payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(manager.start.call_args.kwargs["archive_password"], value or "")
            self.assertNotIn(b"archive_password", response.body)

    async def test_endpoint_rejects_invalid_password_without_echoing_it(self):
        for value in (123, None, ["secret"], "secret\x00"):
            response = await self.endpoint({
                "url": "https://example.com/album.rar", "channel_id": "-100123", "archive_password": value,
            })
            self.assertEqual(response.status_code, 400)
            self.assertNotIn(b"secret", response.body)


if __name__ == "__main__":
    unittest.main()
