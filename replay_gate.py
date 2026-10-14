"""Reproduce frozen ATLAS Candidate A without changing Core Build 7.

Runs only historical research. It has no exchange credentials or order routes.
The original modules remain byte-for-byte unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from core_lock import verify_core_sources


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "manifests" / "ATLAS_CANDIDATE_A_CANONICAL_FREEZE.json"
INPUT_HASHES = {
    "15m": "f0fbbb897aa2ea2a04885a5a3b118bbfe5d42c4588c1ea23396b33dd79e8b031",
    "1h": "c8a603db3c6a217821acc3ea18bbb087df9c3895c18e521b495b6897735cf0c1",
    "4h": "60ded5828e25678ed3fa9780e77c8794de338eafca931a1a216685c4c30dfab6",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    print("ATLAS BUILD 7 — FROZEN REPRODUCTION GATE", flush=True)
    verify_core_sources(ROOT, digest)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    for module in freeze["core_source_hashes"].values():
        path = ROOT / module["path"]
        if digest(path) != module["sha256"]:
            raise RuntimeError("Frozen Core source hash mismatch: " + str(path))
    for timeframe, expected in INPUT_HASHES.items():
        path = ROOT / "processed" / "R5" / f"NQ_v0_R5_{timeframe}.csv.gz"
        if digest(path) != expected:
            raise RuntimeError("Frozen market data mismatch: " + str(path))
    print("[PASS] All 13 Core sources and 3 market-data identities", flush=True)

    sys.path.insert(0, str(ROOT))
    # This redirects only this process's Path.home() calls to a temporary
    # compatibility layout; no original ATLAS code or files are modified.
    with tempfile.TemporaryDirectory(prefix="atlas-replay-home-") as home_dir:
        runtime_home = Path(home_dir)
        documents = runtime_home / "Documents"
        documents.mkdir()
        (documents / "ATLAS").symlink_to(ROOT, target_is_directory=True)
        with patch.object(Path, "home", return_value=runtime_home):
            from core.strategy import run_r10_repaired

            result = run_r10_repaired()

    canonical = freeze["result"]
    metrics = (
        "candidates", "trade_count", "wins", "losses", "net",
        "profit_factor", "max_bar_close_drawdown",
    )
    for key in metrics:
        observed, expected = result.get(key), canonical.get(key)
        numeric_match = (
            isinstance(observed, (float, int))
            and isinstance(expected, (float, int))
            and math.isclose(observed, expected, rel_tol=0, abs_tol=1e-8)
        )
        if not (observed == expected or numeric_match):
            raise RuntimeError(
                f"Candidate A {key} mismatch: got {observed!r}, "
                f"expected {expected!r}"
            )
    if result.get("trades") != canonical.get("trades"):
        raise RuntimeError("Candidate A individual trade ledger mismatch")

    print("[PASS] All seven fingerprint metrics exact", flush=True)
    print("[PASS] All 25 individual trade records exact", flush=True)
    print(json.dumps({key: result[key] for key in metrics}, sort_keys=True))
    print("REPRODUCED — seen historical data only; no live orders", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print("[FAIL] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
