"""Run with: python -m unittest discover -s tests -v.

Import the real uploader with application startup/services stubbed so these tests
never create Telegram sessions or require MongoDB credentials.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_uploader():
    modules = {}
    for name in ("Backend", "Backend.helper", "Backend.pyrofork", "Backend.helper.metadata"):
        module = types.ModuleType(name)
        module.__path__ = [str(ROOT.joinpath(*name.split(".")))]
        modules[name] = module
    for name, attributes in {
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


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = str(Path(self.temp.name) / "album.rar")
        Path(self.archive).write_bytes(b"RAR fixture handled by mocked CLI")
        self.destination = str(Path(self.temp.name) / "extracted")
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
        fake_os = types.SimpleNamespace(**vars(os))
        fake_os.name = "posix"
        self.enterContext(patch.object(uploader, "os", fake_os))

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

    def test_does_not_install_same_codec_less_package_during_upload(self):
        uploader._sync_extract_archive(self.archive, self.destination)
        self.assertFalse(any(call.args[0][0] == "apt-get" for call in self.run.call_args_list))

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
        with patch.object(uploader.os.path, "exists", side_effect=lambda p:
                          str(p).startswith(self.temp.name) and Path(p).exists()):
            success, _ = uploader._sync_extract_archive(archive, self.destination)
        self.assertTrue(success)
        self.assertEqual((Path(self.destination) / "album/track.wav").read_bytes(), b"audio bytes")
        self.run.assert_not_called()


class PipelineTests(unittest.IsolatedAsyncioTestCase):
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
                patch.object(uploader, "_extract_archive", AsyncMock(return_value=(False, "Unsupported Method"))),
                patch.object(uploader, "_cleanup_old_temp_files"),
            ):
                await manager._run_upload_pipeline(
                    "source", [("file", "file123", "source")], "-100123", "", "", False, False
                )
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


if __name__ == "__main__":
    unittest.main()
