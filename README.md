# ATLAS Build 7 — verified historical research API

Read-only Python bridge to the recovered, **frozen** Candidate A Core.

## Proven locally

The Core was restored from archive SHA256
`1bb9d72bc982c3e0855083567f21262f8177ec53e600648900e835ab27ee44b3`.
Its 13 original Python modules are unchanged. All 13 SHA-256 values and the
canonical freeze manifest are checked at replay and service startup using
`core_lock.py`. The historical inputs were
recovered from R5 archive SHA256
`f619ceb2fe93c17aef7747252d6e7b11f056fb72a0b42f8b7fc7205e3091f049`.

The exact-replay gate passes with 145 candidates, 25 trades, 11 wins,
14 losses, $742.00 modeled net, 2.151530200509032 profit factor and
$295.06 maximum bar-close drawdown. **All 25 trade records match** the
canonical freeze. Floating values use an absolute tolerance of 1e-8.

These are development-data results. 97.9% of the baseline net comes from
the first four trades. There is no out-of-sample edge claim.

## Service contract

| Request | Result |
|---|---|
| `GET /health` | 200 only after exact historical replay; otherwise 503 WAIT |
| `GET /atlas/research` | Bearer-token protected historical evidence |
| Unauthenticated or wrong token | 401; no historical data returned |
| Missing `ATLAS_READ_TOKEN` | 503 WAIT |
| `POST` | 405; no order submission is implemented |

The response explicitly says `current_market_feed=false`,
`continuous_monitoring=false`, `live_orders=false`, and
`edge_established=false`. Do not interpret historical scanner state as
a real-time market signal.

The API executes `core.strategy.run_r10_repaired` and `core.app.run_atlas`
on process startup, verifies the saved fingerprint and entire trade ledger,
and serves the verified timestamped snapshot. The original Core's
`Path.home()/Documents/ATLAS` layout is satisfied via a temporary local
compatibility symlink; its source is not patched or modified.

## Local verification

From this folder, with the verified files under `processed/R5/`:

```bash
python replay_gate.py
python -m unittest discover -s tests -p 'test_integrity.py'
ATLAS_BIND_HOST=127.0.0.1 ATLAS_READ_TOKEN=local-test-token PORT=8765 python atlas_service.py
```

In another terminal:

```bash
ATLAS_TEST_TOKEN=local-test-token python tests/test_http.py
```

No third-party Python packages are required. A production service requires
Python with `zoneinfo` timezone data.

## Deployment boundary

`render.yaml` proposes a free-plan Python web service, not a deployed one.
The `.gitignore` deliberately excludes the vendor historical data from a
public GitHub repository. The service instead downloads the exact verified
R5 ZIP at startup only when the three data files are absent:

- `ATLAS_R5_URL`: HTTPS location of the original archive, supplied privately
  through hosting settings. Downloaded content and each member must match
  the frozen SHA256 hashes. A missing, changed or unavailable source yields
  a WAIT response. The existing uploaded ATLAS archive may be reused.
- `ATLAS_READ_TOKEN`: independent server-to-server read-only bearer token,
  supplied privately through hosting settings. Never put it in frontend JS.

Before deploying, verify any market-data redistribution and hosting rights,
confirm the free plan/costs, and push only the verified source and harness.
Wire the Research Desk through a server-side adapter that holds the token.
Do not alter the existing owner's Site access policy.

## Research sequence after integration

1. Reconfirm remote fingerprint and provenance.
2. Connect the Research Desk's historical replay badge and report view.
3. Keep the current market scanner OFF.
4. Acquire unseen futures/stocks data, freeze evaluation criteria, and
   test Candidate A outside its development window.
5. If that fails, document the failure and evaluate Candidate B separately.

**No live accounts, order routes, or trading authorization are present.**
