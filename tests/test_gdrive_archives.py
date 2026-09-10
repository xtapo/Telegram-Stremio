"""Run with: python -m unittest discover -s tests -v.

Import the real uploader with application startup/services stubbed so these tests
never create Telegram sessions or require MongoDB credentials.
"""
import importlib.util
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
import shutil
from contextlib import nullcontext
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
