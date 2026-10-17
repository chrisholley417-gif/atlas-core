"""
ATLAS Core application orchestrator — Build 7.
"""

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

import hashlib
import json
import os


from .ledger import (
    replay_one_contract,
    replay_account_risk,
)

from .scanner import (
    scan_history,
)

from .decision import (
    build_decision_audit,
)

from .status import (
    build_status,
)


ROOT = (
    Path.home()
    / "Documents"
    / "ATLAS"
)

RUNS = ROOT / "runs"


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def write_json_atomic(
    path,
    payload,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    text = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    with temp.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        f.write(text)
        f.flush()
        os.fsync(f.fileno())

    os.replace(
        temp,
        path,
    )


def run_atlas(
    starting_equity=1000.0,
    instrument_name="MNQ",
    risk_fraction=0.01,
    save_report=True,
):

    from .atlas import (
        audit_timeframe,
    )

    from .strategy import (
        run_r10_repaired,
    )


    starting_equity = float(
        starting_equity
    )

    risk_fraction = float(
        risk_fraction
    )


    if starting_equity <= 0:
        raise ValueError(
            "starting_equity must be positive"
        )


    if not (
        0 < risk_fraction < 1
    ):
        raise ValueError(
            "risk_fraction must be between 0 and 1"
        )


    feature_health = {}


    for timeframe in (
        "15m",
        "1h",
        "4h",
    ):

        result = audit_timeframe(
            timeframe
        )

        if result[
            "mismatches"
        ]:
            raise ValueError(
                f"{timeframe}: feature audit failed"
            )

        feature_health[
            timeframe
        ] = result[
            "counts"
        ]


    strategy = (
        run_r10_repaired()
    )


    decision = (
        build_decision_audit(
            strategy
        )
    )


    one_contract = (
        replay_one_contract(
            strategy[
                "trades"
            ],
            starting_equity=1000.0,
        )
    )


    account = (
        replay_account_risk(
            strategy[
                "trades"
            ],
            starting_equity=
                starting_equity,
            instrument_name=
                instrument_name,
            risk_fraction=
                risk_fraction,
        )
    )


    scanner_history = (
        scan_history()
    )


    scanner_latest = {
        "mode":
            "latest_completed_historical_state",

        "evaluation":
            scanner_history[
                "evaluation"
            ],

        "latest":
            scanner_history[
                "latest"
            ],

        "event_counts":
            scanner_history[
                "event_counts"
            ],

        "event_count":
            scanner_history[
                "event_count"
            ],
    }


    status = build_status(
        scanner_result=
            scanner_latest,

        decision_audit=
            decision,

        starting_equity=
            starting_equity,

        instrument_name=
            instrument_name,

        risk_fraction=
            risk_fraction,
    )


    report = {
        "application":
            "ATLAS Core",

        "version":
            "v1-build-7",

        "created_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "mode":
            "historical_research",

        "evaluation_status":
            "seen development data only",

        "live_orders":
            False,

        "profitability_claim":
            False,

        "pipeline": {
            "data":
                "PASS",
            "features":
                "PASS",
            "strategy":
                "PASS",
            "risk":
                "PASS",
            "execution":
                "PASS",
            "ledger":
                "PASS",
            "scanner":
                "PASS",
            "decision":
                "PASS",
            "status":
                "PASS",
        },

        "feature_health":
            feature_health,

        "scanner":
            scanner_latest,

        "decision_audit":
            decision,

        "status":
            status,

        "strategy_checkpoint": {
            "candidates":
                strategy[
                    "candidates"
                ],
            "trade_count":
                strategy[
                    "trade_count"
                ],
            "wins":
                strategy[
                    "wins"
                ],
            "losses":
                strategy[
                    "losses"
                ],
            "net":
                strategy[
                    "net"
                ],
            "ending_equity":
                strategy[
                    "ending_equity"
                ],
            "profit_factor":
                strategy[
                    "profit_factor"
                ],
            "max_bar_close_drawdown":
                strategy[
                    "max_bar_close_drawdown"
                ],
        },

        "one_contract_ledger":
            one_contract,

        "account_ledger":
            account,
    }


    if save_report:

        RUNS.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_time = (
            datetime.now(
                timezone.utc
            )
            .strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )

        report_path = (
            RUNS
            / (
                "ATLAS_BUILD7_RUN_"
                + safe_time
                + ".json"
            )
        )

        write_json_atomic(
            report_path,
            report,
        )

        report[
            "saved_report"
        ] = str(
            report_path
        )

        report[
            "saved_report_sha256"
        ] = sha256(
            report_path
        )


    return report
