from collections import Counter

from .data import iter_r5

from .features import (
    FEATURE_NUMBERS,
    FeatureEngine,
    optional_float,
    close_enough,
)

from .strategy import (
    run_r10_repaired,
)

from .risk import (
    size_long,
)

from .scanner import (
    scan_latest,
    scan_history,
)

from .decision import (
    build_decision_audit,
)

from .status import (
    build_status,
    render_status,
)


def audit_timeframe(
    timeframe,
):

    engine = FeatureEngine()

    counts = Counter()
    mismatches = []

    previous_timestamp = None


    for line, row in enumerate(
        iter_r5(timeframe),
        start=2,
    ):

        counts[
            "bars"
        ] += 1

        complete = int(
            row[
                "complete"
            ]
        )

        mixed = int(
            row[
                "roll_mixed"
            ]
        )

        feature_valid = int(
            row[
                "feature_valid"
            ]
        )

        counts[
            "complete"
        ] += complete

        counts[
            "incomplete"
        ] += (
            1 - complete
        )

        counts[
            "mixed"
        ] += mixed

        counts[
            "feature_valid"
        ] += feature_valid


        timestamp = row[
            "bar_start_utc"
        ]


        if (
            previous_timestamp is not None
            and timestamp <= previous_timestamp
        ):

            mismatches.append(
                f"{timeframe}:{line} "
                "timestamp mismatch"
            )


        previous_timestamp = timestamp


        rebuilt = engine.process(
            row
        )


        if (
            feature_valid
            != rebuilt[
                "feature_valid"
            ]
        ):

            mismatches.append(
                f"{timeframe}:{line} "
                "feature_valid mismatch"
            )


        if (
            int(
                row[
                    "trend_up"
                ]
            )
            != rebuilt[
                "trend_up"
            ]
        ):

            mismatches.append(
                f"{timeframe}:{line} "
                "trend_up mismatch"
            )


        if (
            int(
                row[
                    "trend_down"
                ]
            )
            != rebuilt[
                "trend_down"
            ]
        ):

            mismatches.append(
                f"{timeframe}:{line} "
                "trend_down mismatch"
            )


        for key in FEATURE_NUMBERS:

            stored = optional_float(
                row[key]
            )

            calculated = rebuilt[
                key
            ]

            if not close_enough(
                stored,
                calculated,
            ):

                mismatches.append(
                    f"{timeframe}:{line} "
                    f"{key} mismatch"
                )


        if len(
            mismatches
        ) >= 20:
            break


    return {
        "counts":
            dict(counts),

        "mismatches":
            mismatches,
    }


def run_strategy():

    return run_r10_repaired()


def size_setup(
    equity,
    entry,
    protective_stop,
    instrument_name,
):

    return size_long(
        equity=equity,
        entry=entry,
        protective_stop=
            protective_stop,
        instrument_name=
            instrument_name,
    )


def scan():

    return scan_latest()


def scan_all():

    return scan_history()


def decision_audit():

    return build_decision_audit(
        run_r10_repaired()
    )


def status(
    starting_equity=1000.0,
    instrument_name="MNQ",
    risk_fraction=0.01,
    print_report=True,
):

    scanner_result = (
        scan_latest()
    )

    strategy_result = (
        run_r10_repaired()
    )

    decision = (
        build_decision_audit(
            strategy_result
        )
    )

    result = build_status(
        scanner_result=
            scanner_result,

        decision_audit=
            decision,

        starting_equity=
            starting_equity,

        instrument_name=
            instrument_name,

        risk_fraction=
            risk_fraction,
    )


    if print_report:

        print(
            render_status(
                result
            )
        )


    return result


def run(
    starting_equity=1000.0,
    instrument_name="MNQ",
    risk_fraction=0.01,
    save_report=True,
):

    from .app import run_atlas

    return run_atlas(
        starting_equity=
            starting_equity,

        instrument_name=
            instrument_name,

        risk_fraction=
            risk_fraction,

        save_report=
            save_report,
    )
