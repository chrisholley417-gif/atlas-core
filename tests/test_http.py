"""Black-box smoke tests for a running ATLAS read-only bridge."""

import json
import os
import urllib.error
import urllib.request


BASE = os.environ.get("ATLAS_TEST_BASE", "http://127.0.0.1:8765")
TOKEN = os.environ.get("ATLAS_TEST_TOKEN", "")


def request(path: str, *, method: str = "GET", token: str | None = None):
    headers = {"Authorization": "Bearer " + token} if token is not None else {}
    req = urllib.request.Request(BASE + path, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    if not TOKEN:
        raise SystemExit("ATLAS_TEST_TOKEN must be set to local test token")
    code, body = request("/health")
    assert code == 200 and body["engine_ready"] is True, (code, body)
    assert body["live_orders"] is False and body["current_market_feed"] is False

    code, body = request("/atlas/research")
    assert code == 401 and body["status"] == "UNAUTHORIZED", (code, body)

    code, body = request("/atlas/research", token="wrong-token")
    assert code == 401 and body["status"] == "UNAUTHORIZED", (code, body)

    code, body = request("/atlas/research", token=TOKEN)
    assert code == 200 and body["status"] == "REPRODUCED_HISTORICAL", (code, body)
    assert body["connection"]["candidate_a_reproduced"] is True
    assert body["truth"]["edge_established"] is False
    assert body["strategy_checkpoint"]["trade_count"] == 25
    assert body["strategy_checkpoint"]["net"] == 742.0
    assert body["reproduction_checks"]["trade_ledger"] is True

    code, body = request("/atlas/research", method="POST", token=TOKEN)
    assert code == 405 and body["live_orders"] is False, (code, body)

    print("[PASS] health; unauthorized and incorrect token; verified research; POST disabled")


if __name__ == "__main__":
    main()
