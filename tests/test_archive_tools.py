import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "portable_archive_tools", Path(__file__).resolve().parents[1] / "Backend/helper/archive_tools.py"
)
archive_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive_tools)


class PortableArchiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:xz") as archive:
            for name, content in (("7zz", b"synthetic binary"), ("License.txt", b"test license")):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        self.data = data.getvalue()
        self.enterContext(patch.object(archive_tools.platform, "system", return_value="Linux"))
        self.enterContext(patch.object(archive_tools.platform, "machine", return_value="x86_64"))
        self.enterContext(patch.object(archive_tools, "_retry_after", 0))
        self.enterContext(patch.dict(archive_tools._ASSETS, {
            "x86_64": ("x64", hashlib.sha256(self.data).hexdigest()),
        }))
        self.download = self.enterContext(patch.object(
            archive_tools.urllib.request, "urlopen", side_effect=lambda *a, **kw: io.BytesIO(self.data)
        ))
        self.run = self.enterContext(patch.object(
            archive_tools.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, "Formats: Rar Rar5", ""),
        ))

    def test_install_and_reuse_without_second_download(self):
        installed = archive_tools.ensure_portable_7zip(self.temp.name)
        self.assertEqual(Path(installed).read_bytes(), b"synthetic binary")
        self.assertEqual(Path(installed).with_name("License.txt").read_bytes(), b"test license")
        self.assertEqual(archive_tools.ensure_portable_7zip(self.temp.name), installed)
        self.download.assert_called_once()
        self.run.assert_called_once()
        self.assertFalse(list(Path(self.temp.name).rglob("install-*")))

    def test_hash_mismatch_never_executes_download(self):
        self.download.side_effect = lambda *a, **kw: io.BytesIO(b"tampered")
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            archive_tools.ensure_portable_7zip(self.temp.name)
        self.run.assert_not_called()
        self.assertFalse(list(Path(self.temp.name).rglob("7zz")))

    def test_unusable_binary_is_not_installed(self):
        self.run.return_value = subprocess.CompletedProcess([], 127, "", "loader unavailable")
        with self.assertRaisesRegex(RuntimeError, "không chạy được"):
            archive_tools.ensure_portable_7zip(self.temp.name)
        self.assertFalse(list(Path(self.temp.name).rglob("7zz")))

    def test_failed_download_has_cooldown(self):
        self.download.side_effect = OSError("offline")
        with self.assertRaises(OSError):
            archive_tools.ensure_portable_7zip(self.temp.name)
        with self.assertRaisesRegex(RuntimeError, "một phút"):
            archive_tools.ensure_portable_7zip(self.temp.name)
        self.download.assert_called_once()

    def test_unsupported_platform_never_downloads(self):
        with patch.object(archive_tools.platform, "system", return_value="Windows"):
            with self.assertRaisesRegex(RuntimeError, "cài 7-Zip"):
                archive_tools.ensure_portable_7zip(self.temp.name)
        self.download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
