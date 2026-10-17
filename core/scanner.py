"""
ATLAS Core scanner / state engine.

Application state:

    WAIT
    WATCH
    CONFIRMED
    INVALIDATED

This layer does NOT alter the frozen historical
strategy or execution engine.

It interprets completed R5 bars using the same
higher-timeframe context and confirmation concepts
used by the frozen R10 strategy.

Research only.
No live orders.
"""

import bisect
import math

from collections import deque

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from zoneinfo import ZoneInfo


from .data import iter_r5


END = datetime(
    2024,
    9,
    25,
    tzinfo=timezone.utc,
)


CT = ZoneInfo(
    "America/Chicago"
)


VALID_STATES = (
    "WAIT",
    "WATCH",
    "CONFIRMED",
    "INVALIDATED",
)


def dt(value):

    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )


def good(row):

    return (
        row["complete"] == "1"
        and
        row["roll_mixed"] == "0"
    )


def load_rows(
    timeframe,
    minutes,
):

    rows = []

    previous = None


    for original in iter_r5(
        timeframe
    ):

        row = dict(
            original
        )

        t = dt(
            row[
                "bar_start_utc"
            ]
        )


        if t >= END:

            break


        if (
            t
            + timedelta(
                minutes=minutes
            )
            > END
        ):

            break


        if (
            previous is not None
            and
            t <= previous
        ):

            raise ValueError(
                f"{timeframe}: "
                "timestamps not increasing"
            )


        row["_t"] = t

        rows.append(
            row
        )

        previous = t


    return rows


def higher_context(
    finish,
    instrument_id,
    higher,
):

    result = {}


    for timeframe in (
        "1h",
        "4h",
    ):

        rows, ends = (
            higher[
                timeframe
            ]
        )


        index = (
            bisect.bisect_right(
                ends,
                finish,
            )
            - 1
        )


        if index < 0:

            return None


        row = rows[index]


        if (
            not good(row)
            or
            row[
                "feature_valid"
            ]
            != "1"
            or
            int(
                row[
                    "instrument_id"
                ]
            )
            != instrument_id
        ):

            return None


        result[
            timeframe
        ] = row


    return result


def base_context_passes(
    one_hour,
    four_hour,
):

    four_ok = (
        four_hour[
            "trend_up"
        ]
        == "1"
        and
        float(
            four_hour[
                "close"
            ]
        )
        > float(
            four_hour[
                "ema20"
            ]
        )
    )


    one_ok = (
        one_hour[
            "trend_up"
        ]
        == "1"
        and
        float(
            one_hour[
                "close"
            ]
        )
        >= float(
            one_hour[
                "ema50"
            ]
        )
    )


    return (
        four_ok
        and
        one_ok
    )


def state_record(
    state,
    timestamp,
    reason,
    **extra,
):

    if state not in VALID_STATES:

        raise ValueError(
            "invalid scanner state"
        )


    record = {
        "state":
            state,

        "timestamp":
            timestamp.isoformat(),

        "reason":
            reason,
    }


    record.update(
        extra
    )


    return record


def scan_history():

    bars = load_rows(
        "15m",
        15,
    )


    higher = {}


    for timeframe, minutes in (
        ("1h", 60),
        ("4h", 240),
    ):

        rows = load_rows(
            timeframe,
            minutes,
        )


        ends = [
            row["_t"]
            + timedelta(
                minutes=minutes
            )
            for row in rows
        ]


        higher[
            timeframe
        ] = (
            rows,
            ends,
        )


    events = []

    recent = deque(
        maxlen=4
    )

    previous = None

    watch = None

    latest = None


    for bar in bars:

        t = bar["_t"]

        finish = (
            t
            + timedelta(
                minutes=15
            )
        )


        inst = int(
            bar[
                "instrument_id"
            ]
        )


        o = float(
            bar["open"]
        )

        h = float(
            bar["high"]
        )

        l = float(
            bar["low"]
        )

        c = float(
            bar["close"]
        )


        if not all(
            math.isfinite(x)
            for x in (
                o,
                h,
                l,
                c,
            )
        ):

            raise ValueError(
                f"invalid scanner OHLC at {t}"
            )


        contiguous = (
            previous is not None
            and
            t
            == (
                previous["_t"]
                + timedelta(
                    minutes=15
                )
            )
        )


        same_contract = (
            previous is not None
            and
            inst
            == int(
                previous[
                    "instrument_id"
                ]
            )
        )


        # ==========================================================
        # DATA / ROLL BREAK
        # ==========================================================

        if (
            not good(bar)
            or
            (
                previous is not None
                and
                (
                    not contiguous
                    or
                    not same_contract
                )
            )
        ):

            if watch is not None:

                latest = state_record(
                    "INVALIDATED",
                    t,
                    "data_or_contract_break",
                    watch_started=
                        watch[
                            "started"
                        ],
                )

                events.append(
                    latest
                )

                watch = None


            recent.clear()


            latest = state_record(
                "WAIT",
                t,
                "data_not_scannable",
            )


            previous = bar

            continue


        recent.append(
            l
        )


        # ==========================================================
        # WATCH EXPIRATION
        # ==========================================================

        if watch is not None:

            watch[
                "bars_elapsed"
            ] += 1


            if (
                inst
                != watch[
                    "instrument_id"
                ]
            ):

                latest = state_record(
                    "INVALIDATED",
                    t,
                    "contract_changed",
                    watch_started=
                        watch[
                            "started"
                        ],
                )

                events.append(
                    latest
                )

                watch = None


            elif (
                c
                <= watch[
                    "support"
                ]
            ):

                latest = state_record(
                    "INVALIDATED",
                    t,
                    "support_failed",
                    watch_started=
                        watch[
                            "started"
                        ],

                    support=
                        watch[
                            "support"
                        ],
                )

                events.append(
                    latest
                )

                watch = None


            elif (
                watch is not None
                and
                watch[
                    "bars_elapsed"
                ]
                > 4
            ):

                latest = state_record(
                    "INVALIDATED",
                    t,
                    "watch_expired",
                    watch_started=
                        watch[
                            "started"
                        ],
                )

                events.append(
                    latest
                )

                watch = None


        # ==========================================================
        # SCANNABLE BAR
        # ==========================================================

        if (
            bar[
                "feature_valid"
            ]
            != "1"
        ):

            latest = state_record(
                "WAIT",
                t,
                "15m_features_not_ready",
            )

            previous = bar

            continue


        end_ct = (
            finish.astimezone(
                CT
            )
        )


        if not (
            (
                8,
                30,
            )
            <= (
                end_ct.hour,
                end_ct.minute,
            )
            <= (
                13,
                30,
            )
        ):

            latest = state_record(
                "WAIT",
                t,
                "outside_research_window",
            )

            previous = bar

            continue


        context = higher_context(
            finish,
            inst,
            higher,
        )


        if context is None:

            latest = state_record(
                "WAIT",
                t,
                "higher_timeframe_not_ready",
            )

            previous = bar

            continue


        one_hour = (
            context["1h"]
        )

        four_hour = (
            context["4h"]
        )


        if not base_context_passes(
            one_hour,
            four_hour,
        ):

            if watch is not None:

                latest = state_record(
                    "INVALIDATED",
                    t,
                    "higher_timeframe_context_failed",
                    watch_started=
                        watch[
                            "started"
                        ],
                )

                events.append(
                    latest
                )

                watch = None


            latest = state_record(
                "WAIT",
                t,
                "trend_context_not_long",
            )

            previous = bar

            continue


        support = float(
            one_hour[
                "ema20"
            ]
        )


        atr1 = float(
            one_hour[
                "atr14"
            ]
        )


        atr15 = float(
            bar[
                "atr14"
            ]
        )


        resistance = float(
            one_hour[
                "prior_high20"
            ]
        )


        if (
            not math.isfinite(
                atr15
            )
            or
            atr15 <= 0
        ):

            raise ValueError(
                f"invalid scanner ATR at {t}"
            )


        touch = (
            l
            <= (
                support
                + (
                    0.25
                    * atr1
                )
            )
            and
            h
            >= (
                support
                - (
                    0.25
                    * atr1
                )
            )
        )


        close_location = (
            (c - l)
            /
            (
                h - l
                if h > l
                else 1.0
            )
        )


        recovery = (
            c > support
            and
            c > o
            and
            close_location >= 0.65
            and
            float(
                bar[
                    "volume_ratio20"
                ]
            )
            >= 1.0
        )


        # ==========================================================
        # CONFIRM EXISTING WATCH
        # ==========================================================

        if (
            watch is not None
            and
            recovery
        ):

            latest = state_record(
                "CONFIRMED",
                t,
                "watch_recovered",
                watch_started=
                    watch[
                        "started"
                    ],

                support=
                    support,

                resistance=
                    resistance,

                atr15=
                    atr15,

                confirmation_low=
                    l,

                instrument_id=
                    inst,
            )


            events.append(
                latest
            )


            watch = None

            previous = bar

            continue


        # ==========================================================
        # IMMEDIATE CONFIRMATION
        #
        # This matches the frozen R10 concept:
        # support touch + recovery on same completed candle.
        # ==========================================================

        if (
            touch
            and
            recovery
            and
            len(recent) >= 4
        ):

            latest = state_record(
                "CONFIRMED",
                t,
                "support_touch_and_recovery",
                support=
                    support,

                resistance=
                    resistance,

                atr15=
                    atr15,

                confirmation_low=
                    recent[-1],

                instrument_id=
                    inst,
            )


            events.append(
                latest
            )


            previous = bar

            continue


        # ==========================================================
        # WATCH
        # ==========================================================

        if touch:

            if watch is None:

                watch = {
                    "started":
                        t.isoformat(),

                    "instrument_id":
                        inst,

                    "support":
                        support,

                    "resistance":
                        resistance,

                    "atr15":
                        atr15,

                    "bars_elapsed":
                        0,
                }


                latest = state_record(
                    "WATCH",
                    t,
                    "support_touched_waiting_for_recovery",
                    support=
                        support,

                    resistance=
                        resistance,

                    atr15=
                        atr15,

                    instrument_id=
                        inst,
                )


                events.append(
                    latest
                )


            else:

                latest = state_record(
                    "WATCH",
                    t,
                    "watch_still_active",
                    watch_started=
                        watch[
                            "started"
                        ],

                    bars_elapsed=
                        watch[
                            "bars_elapsed"
                        ],

                    support=
                        watch[
                            "support"
                        ],

                    resistance=
                        watch[
                            "resistance"
                        ],
                )


            previous = bar

            continue


        # ==========================================================
        # EXISTING WATCH REMAINS ACTIVE
        # ==========================================================

        if watch is not None:

            latest = state_record(
                "WATCH",
                t,
                "waiting_for_recovery",
                watch_started=
                    watch[
                        "started"
                    ],

                bars_elapsed=
                    watch[
                        "bars_elapsed"
                    ],

                support=
                    watch[
                        "support"
                    ],

                resistance=
                    watch[
                        "resistance"
                    ],
            )


            previous = bar

            continue


        # ==========================================================
        # DEFAULT
        # ==========================================================

        latest = state_record(
            "WAIT",
            t,
            "no_support_setup",
        )


        previous = bar


    if latest is None:

        latest = {
            "state":
                "WAIT",

            "timestamp":
                None,

            "reason":
                "no_scannable_bars",
        }


    counts = {
        state: 0
        for state in VALID_STATES
    }


    for event in events:

        counts[
            event[
                "state"
            ]
        ] += 1


    return {
        "mode":
            "historical_state_replay",

        "evaluation":
            "seen development data",

        "states":
            list(
                VALID_STATES
            ),

        "latest":
            latest,

        "event_counts":
            counts,

        "event_count":
            len(events),

        "events":
            events,
    }


def scan_latest():

    result = scan_history()


    return {
        "mode":
            "latest_completed_historical_state",

        "evaluation":
            result[
                "evaluation"
            ],

        "latest":
            result[
                "latest"
            ],

        "event_counts":
            result[
                "event_counts"
            ],

        "event_count":
            result[
                "event_count"
            ],
    }
