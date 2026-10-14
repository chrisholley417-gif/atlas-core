"""Read-only HTTP bridge to the *unchanged* ATLAS Core Build 7.

No market feeds, broker credentials, order routes, or continuous monitoring.
The sole research response is a verified, timestamped historical replay.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import math
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from core_lock import verify_core_sources


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifests" / "ATLAS_CANDIDATE_A_CANONICAL_FREEZE.json"
R5_ARCHIVE_SHA = "f619ceb2fe93c17aef7747252d6e7b11f056fb72a0b42f8b7fc7205e3091f049"
R5_HASHES = {
    "15m": "f0fbbb897aa2ea2a04885a5a3b118bbfe5d42c4588c1ea23396b33dd79e8b031",
    "1h": "c8a603db3c6a217821acc3ea18bbb087df9c3895c18e521b495b6897735cf0c1",
    "4h": "60ded5828e25678ed3fa9780e77c8794de338eafca931a1a216685c4c30dfab6",
}
R5_NAMES = {tf: f"processed/R5/NQ_v0_R5_{tf}.csv.gz" for tf in R5_HASHES}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_verified_inputs() -> None:
    """Use existing files, or fetch only the exact preverified R5 ZIP.

    Never overwrite an existing mismatched file; fail closed on corruption.
    Public source repositories must not contain vendor historical data.
    """
    missing = [tf for tf, name in R5_NAMES.items() if not (ROOT / name).is_file()]
    for tf, name in R5_NAMES.items():
        path = ROOT / name
        if path.exists() and sha256(path) != R5_HASHES[tf]:
            raise RuntimeError(f"R5 input SHA256 mismatch: {tf}")
    if not missing:
        return

    source_url = os.environ.get("ATLAS_R5_URL", "")
    if not source_url.startswith("https://"):
        raise RuntimeError("Missing R5 inputs and secure ATLAS_R5_URL")
    with urllib.request.urlopen(source_url, timeout=90) as response:
        archive_bytes = response.read(20 * 1024 * 1024 + 1)
    if len(archive_bytes) > 20 * 1024 * 1024:
        raise RuntimeError("R5 archive exceeds verified upload size limit")
    if hashlib.sha256(archive_bytes).hexdigest() != R5_ARCHIVE_SHA:
        raise RuntimeError("Downloaded R5 archive identity mismatch")

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        if set(archive.namelist()) != set(R5_NAMES.values()):
            raise RuntimeError("Unexpected R5 archive member list")
        if archive.testzip() is not None:
            raise RuntimeError("R5 archive CRC failure")
        for tf in missing:
            name = R5_NAMES[tf]
            target = ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            staged = target.with_suffix(target.suffix + ".download")
            try:
                with archive.open(name) as inp, staged.open("xb") as out:
                    shutil.copyfileobj(inp, out, length=1024 * 1024)
                if sha256(staged) != R5_HASHES[tf]:
                    raise RuntimeError(f"Downloaded R5 member identity mismatch: {tf}")
                staged.replace(target)
            finally:
                staged.unlink(missing_ok=True)


def build_historical_snapshot() -> dict:
    verify_core_sources(ROOT, sha256)
    freeze = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for source in freeze["core_source_hashes"].values():
        if sha256(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError("Recovered Core source identity mismatch")
    ensure_verified_inputs()
    for tf, name in R5_NAMES.items():
        if sha256(ROOT / name) != R5_HASHES[tf]:
            raise RuntimeError(f"R5 input identity mismatch: {tf}")

    # Isolated compatibility layout for Core's original Path.home()/Documents/ATLAS.
    # The original source files are never edited or given a live account.
    with tempfile.TemporaryDirectory(prefix="atlas-core-home-") as home_dir:
        home = Path(home_dir)
        documents = home / "Documents"
        documents.mkdir()
        (documents / "ATLAS").symlink_to(ROOT, target_is_directory=True)
        sys.path.insert(0, str(ROOT))
        with patch.object(Path, "home", return_value=home):
            from core.strategy import run_r10_repaired
            from core.app import run_atlas

            strategy = run_r10_repaired()
            report = run_atlas(
                starting_equity=1000.0,
                instrument_name="MNQ",
                risk_fraction=0.01,
                save_report=False,
            )

    baseline = freeze["result"]
    keys = (
        "candidates", "trade_count", "wins", "losses", "net",
        "profit_factor", "max_bar_close_drawdown",
    )
    for key in keys:
        actual, expected = strategy.get(key), baseline.get(key)
        if not isinstance(actual, (int, float)) or not math.isclose(
            actual, expected, rel_tol=0, abs_tol=1e-8
        ):
            raise RuntimeError(f"Frozen Candidate A metric mismatch: {key}")
        if not math.isclose(
            report["strategy_checkpoint"][key], expected, rel_tol=0, abs_tol=1e-8
        ):
            raise RuntimeError(f"Core application replay mismatch: {key}")
    if strategy["trades"] != baseline["trades"]:
        raise RuntimeError("Frozen Candidate A individual trade ledger mismatch")

    return {
        "schema": "atlas.research_desk.engine.v1",
        "status": "REPRODUCED_HISTORICAL",
        "engine": {
            "application": report["application"],
            "version": report["version"],
            "source": "unchanged verified Python Core Build 7",
        },
        "connection": {
            "python_core_executed": True,
            "candidate_a_reproduced": True,
            "current_market_feed": False,
            "live_orders": False,
            "continuous_monitoring": False,
        },
        "truth": {
            "candidate_a_frozen": True,
            "historical_data_only": True,
            "edge_established": False,
            "profitability_claim": False,
        },
        "pipeline": report["pipeline"],
        "research_status": report["status"]["research"],
        "scanner": report["scanner"],
        "strategy_checkpoint": report["strategy_checkpoint"],
        "input_provenance": {
            "freeze_identity_sha256": freeze["identity_sha256"],
            "all_13_core_sources_verified": True,
            "r5_member_sha256": R5_HASHES,
            "r5_archive_sha256": R5_ARCHIVE_SHA,
        },
        "reproduction_checks": {key: True for key in keys} | {"trade_ledger": True},
        "generated_at_utc": report["created_utc"],
    }


SNAPSHOT: dict | None = None
STARTUP_ERROR: str | None = None


class AtlasHandler(BaseHTTPRequestHandler):
    def respond(self, code: int, payload: dict) -> None:
        content = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            self.respond(200 if SNAPSHOT is not None else 503, {
                "service": "ATLAS Build 7 Python Bridge",
                "status": "REPRODUCED_HISTORICAL" if SNAPSHOT else "WAIT",
                "engine_ready": SNAPSHOT is not None,
                "current_market_feed": False,
                "live_orders": False,
                "blocker": None if SNAPSHOT else STARTUP_ERROR,
            })
            return
        if path != "/atlas/research":
            self.respond(404, {"status": "NOT_FOUND"})
            return
        token = os.environ.get("ATLAS_READ_TOKEN", "")
        if not token:
            self.respond(503, {"status": "WAIT", "code": "READ_TOKEN_NOT_CONFIGURED"})
            return
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + token):
            self.respond(401, {"status": "UNAUTHORIZED"})
            return
        if SNAPSHOT is None:
            self.respond(503, {"status": "WAIT", "code": "REPRODUCTION_NOT_VERIFIED"})
            return
        self.respond(200, SNAPSHOT)

    def do_POST(self) -> None:
        self.respond(405, {"status": "METHOD_NOT_ALLOWED", "live_orders": False})

    def log_message(self, _format: str, *_args: object) -> None:
        # Do not log authorization headers, request paths, or user data.
        return


def main() -> None:
    global SNAPSHOT, STARTUP_ERROR
    try:
        SNAPSHOT = build_historical_snapshot()
        print("ATLAS: exact historical Build 7 replay verified", flush=True)
    except (OSError, RuntimeError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        STARTUP_ERROR = str(exc)
        print("ATLAS WAIT: " + STARTUP_ERROR, flush=True)

    port = int(os.environ.get("PORT", "8000"))
    listen_host = os.environ.get("ATLAS_BIND_HOST", "0.0.0.0")
    server = HTTPServer((listen_host, port), AtlasHandler)
    print(f"ATLAS bridge listening on port {port}; live orders disabled", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
