"""Controlled file/container fixtures, not playable demo footage or operator feedback."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import rrw_submission as submission
from rrw_workspace import WorkspaceError


class PacketVideoInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / 'demo.mp4'
        self.fixture = b'\0\0\0\x20ftypisomCONTROLLED_CONTAINER_HEADER_ONLY'
        self.video.write_bytes(self.fixture)
        self.output = self.root / 'packet.zip'

    def command(self):
        return ['--data-dir', str(self.root), '--output', str(self.output), '--video', str(self.video)]

    def run_cli(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return submission.main(self.command())

    def test_explicit_container_fixture_copied_exactly_and_manifest_bound(self):
        self.assertEqual(self.run_cli(), 0)
        self.assertEqual(self.video.read_bytes(), self.fixture)
        with ZipFile(self.output) as archive:
            self.assertEqual(archive.read('assets/demo.mp4'), self.fixture)
            manifest = json.loads(archive.read('MANIFEST.json'))['files']['assets/demo.mp4']
            self.assertEqual(manifest, {'sha256': hashlib.sha256(self.fixture).hexdigest(),
                                       'bytes': len(self.fixture)})
            self.assertFalse(json.loads(archive.read('READINESS.json'))['published'])

    def test_missing_directory_oversized_and_wrong_header_leave_no_output(self):
        self.video.unlink()
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.video.mkdir()
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.video.rmdir()
        with self.video.open('wb') as stream:
            stream.truncate(submission.MAX_VIDEO_BYTES + 1)
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.assertEqual(self.video.stat().st_size, submission.MAX_VIDEO_BYTES + 1)
        self.video.write_bytes(b'PRIVATE_WRONG_HEADER_FIXTURE')
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.assertEqual(self.video.read_bytes(), b'PRIVATE_WRONG_HEADER_FIXTURE')

    def test_leaf_symlink_is_refused_without_copying_target(self):
        target = self.root / 'target.mp4'; self.video.rename(target)
        try: self.video.symlink_to(target)
        except OSError: self.skipTest('Symlinks unavailable to this test account')
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.assertEqual(target.read_bytes(), self.fixture)

    def test_hard_link_is_refused_without_copying_target(self):
        target = self.root / 'target.mp4'; self.video.rename(target)
        try: os.link(target, self.video)
        except OSError: self.skipTest('Hard links unavailable to this test account')
        self.assertEqual(self.run_cli(), 1); self.assertFalse(self.output.exists())
        self.assertEqual(target.read_bytes(), self.fixture)

    def test_real_cli_fifo_refuses_promptly_without_writer_or_output(self):
        if not hasattr(os, 'mkfifo'): self.skipTest('FIFO creation unavailable on this platform')
        self.video.unlink(); os.mkfifo(self.video)
        result = subprocess.run([sys.executable, str(submission.HERE / 'rrw_submission.py'),
                                 *self.command()], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'single-link regular file', result.stderr)
        self.assertFalse(self.output.exists())

    def test_initial_invalid_type_is_refused_before_open(self):
        self.video.unlink(); self.video.mkdir()
        with patch.object(submission.os, 'open', side_effect=AssertionError('Must not open directory')):
            with self.assertRaises(WorkspaceError):
                submission.read_packet_file(self.video, 128, 'Demo file', 'Missing demo')

    def test_descriptor_and_path_changes_are_refused_with_conflict(self):
        original = self.video.stat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns')
        changed = SimpleNamespace(**{name: getattr(original, name) for name in fields})
        changed.st_mtime_ns += 1
        for moment in ('opening', 'reading', 'path'):
            with self.subTest(moment=moment):
                descriptors = [changed] if moment == 'opening' else [original, changed if moment == 'reading' else original]
                paths = [original] if moment == 'opening' else [original, changed if moment == 'path' else original]
                with patch.object(submission.os, 'fstat', side_effect=descriptors), \
                     patch.object(Path, 'stat', side_effect=paths):
                    with self.assertRaises(WorkspaceError) as error:
                        submission.read_packet_file(self.video, 128, 'Demo file', 'Missing demo')
                self.assertEqual(error.exception.status, 409)
                self.assertNotIn('CONTROLLED', str(error.exception))
        self.assertEqual(self.video.read_bytes(), self.fixture)

    def test_fifo_replacement_between_stat_and_open_is_nonblocking_and_refused(self):
        if not hasattr(os, 'mkfifo') or not hasattr(os, 'O_NONBLOCK'):
            self.skipTest('Nonblocking FIFO opens unavailable on this platform')
        original_open = os.open
        def replace_before_open(path, flags):
            self.assertTrue(flags & os.O_NONBLOCK)
            self.video.unlink(); os.mkfifo(self.video)
            return original_open(path, flags)
        with patch.object(submission.os, 'open', side_effect=replace_before_open):
            with self.assertRaises(WorkspaceError) as error:
                submission.read_packet_file(self.video, 128, 'Demo file', 'Missing demo')
        self.assertEqual(error.exception.status, 409)

    def test_real_path_replacement_after_read_is_refused(self):
        if os.name == 'nt': self.skipTest('Windows may refuse replacement of an open file')
        replacement = self.root / 'replacement.mp4'; replacement.write_bytes(self.fixture)
        original_fdopen = os.fdopen; video = self.video
        class ReplacingStream:
            def __init__(self, descriptor, mode): self.stream = original_fdopen(descriptor, mode)
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, limit):
                content = self.stream.read(limit)
                os.replace(replacement, video)
                return content
        with patch.object(submission.os, 'fdopen', side_effect=ReplacingStream):
            with self.assertRaises(WorkspaceError) as error:
                submission.read_packet_file(self.video, 128, 'Demo file', 'Missing demo')
        self.assertEqual(error.exception.status, 409)

    def test_read_is_capped_even_if_file_grows_after_descriptor_check(self):
        self.video.write_bytes(b'x' * 8)
        original = self.video.stat(); calls = []
        class GrowingStream(io.BytesIO):
            def fileno(self): return 99
            def read(self, limit):
                calls.append(limit)
                return super().read(limit)
        stream = GrowingStream(b'x' * 100)
        with patch.object(submission.os, 'open', return_value=99), \
             patch.object(submission.os, 'fdopen', return_value=stream), \
             patch.object(submission.os, 'fstat', return_value=original):
            with self.assertRaises(WorkspaceError) as error:
                submission.read_packet_file(self.video, 8, 'Demo file', 'Missing demo')
        self.assertEqual(calls, [9]); self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.video.read_bytes(), b'x' * 8)


if __name__ == '__main__': unittest.main()
