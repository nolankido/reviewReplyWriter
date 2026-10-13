"""Regression for Windows denying reads of an already-locked byte."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rrw_web import InstanceLock
from rrw_workspace import WorkspaceError


class LockRecoveryTests(unittest.TestCase):
    def test_failed_initialization_closes_handle(self):
        with tempfile.TemporaryDirectory() as tmp:
            handle = MagicMock()
            handle.read.side_effect = PermissionError('byte already locked')
            lock = InstanceLock(tmp)
            with patch.object(Path, 'open', return_value=handle):
                with self.assertRaises(WorkspaceError):
                    lock.__enter__()
            handle.close.assert_called_once()
            self.assertIsNone(lock.handle)
