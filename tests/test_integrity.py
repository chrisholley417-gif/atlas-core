"""Fail-closed assertions for the verified, read-only Build 7 bridge."""

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core_lock
from atlas_service import build_historical_snapshot


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceLockTests(unittest.TestCase):
    def test_all_original_core_files_and_freeze_match(self):
        core_lock.verify_core_sources(ROOT, digest)

    def test_source_change_blocks_replay(self):
        tampered = dict(core_lock.CORE_SOURCE_SHA256)
        tampered["strategy.py"] = "0" * 64
        with patch.object(core_lock, "CORE_SOURCE_SHA256", tampered):
            with self.assertRaisesRegex(RuntimeError, "strategy.py"):
                core_lock.verify_core_sources(ROOT, digest)

    def test_freeze_change_blocks_replay(self):
        with patch.object(core_lock, "FREEZE_MANIFEST_SHA256", "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "freeze manifest"):
                core_lock.verify_core_sources(ROOT, digest)

    def test_historical_only_snapshot(self):
        snapshot = build_historical_snapshot()
        self.assertEqual(snapshot["status"], "REPRODUCED_HISTORICAL")
        self.assertTrue(snapshot["input_provenance"]["all_13_core_sources_verified"])
        self.assertEqual(snapshot["strategy_checkpoint"]["trade_count"], 25)
        self.assertFalse(snapshot["connection"]["current_market_feed"])
        self.assertFalse(snapshot["connection"]["continuous_monitoring"])
        self.assertFalse(snapshot["connection"]["live_orders"])
        self.assertFalse(snapshot["truth"]["edge_established"])


if __name__ == "__main__":
    unittest.main()
