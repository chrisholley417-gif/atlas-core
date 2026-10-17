import bisect

import math

from collections import (

    Counter,

    deque,

)

from datetime import (

    datetime,

    timedelta,

    timezone,

)

from zoneinfo import ZoneInfo

from .data import iter_r5

from .execution import (

    DEFAULT_TICK_SIZE,

    DEFAULT_POINT_VALUE,

    DEFAULT_ROUND_TRIP_FEE,

    nearest_tick,

    floor_tick,

    long_risk_per_contract,

    long_target_for_net_r,

    long_exit_fill,

    long_pnl,

)

END = datetime(

    2024,

    9,

    25,

    tzinfo=timezone.utc,

)

CT = ZoneInfo(

    "America/Chicago"

)

TICK = DEFAULT_TICK_SIZE

POINT_VALUE = (

    DEFAULT_POINT_VALUE

)

ROUND_TRIP_FEE = (

    DEFAULT_ROUND_TRIP_FEE

)

# ATLAS_R11_PARAMETERS
R11_PARAMS = {
    "support_band_atr": 0.25,
    "close_location": 0.65,
    "volume_ratio": 1.00,
    "stop_offset_atr": 0.25,
    "min_stop_atr": 0.50,
    "max_stop_atr": 1.50,
    "net_rr": 2.00,
}

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

    last = None

    for original in iter_r5(

        timeframe

    ):

        row = dict(

            original

        )

        t = dt(

            row["bar_start_utc"]

        )

        if t >= END:

            break

        if (

            last is not None

            and

            t <= last

        ):

            raise ValueError(

                f"{timeframe}: "

                "unsorted timestamps"

            )

        if (

            t

            + timedelta(

                minutes=minutes

            )

            > END

        ):

            break

        row["_t"] = t

        rows.append(

            row

        )

        last = t

    return rows

def run_r10_repaired():

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

    equity = 1000.0

    peak = equity

    maxdd = 0.0

    maxddpct = 0.0

    position = None

    pending = None

    recent = deque(

        maxlen=4

    )

    previous = None

    day = None

    day_trades = 0

    trades = []

    counts = Counter()

    candidates = 0

    def mtm(close):

        if position is None:

            return equity

        return (

            equity

            + (

                (

                    nearest_tick(

                        close - TICK

                    )

                    - position[

                        "entry"

                    ]

                )

                * POINT_VALUE

                - ROUND_TRIP_FEE

            )

        )

    def close_position(

        price,

        reason,

        timestamp,

    ):

        nonlocal equity

        nonlocal position

        p = position

        pnl_one = long_pnl(

            entry=

                p["entry"],

            exit_price=

                price,

            quantity=

                1,

            point_value=

                POINT_VALUE,

            round_trip_fee=

                ROUND_TRIP_FEE,

        )

        equity += pnl_one

        trades.append(

            {

                "signal_time":

                    p[

                        "signal_time"

                    ],

                "entry_time":

                    p[

                        "entry_time"

                    ],

                "exit_bar_start":

                    timestamp.isoformat(),

                "reason":

                    reason,

                "entry":

                    p["entry"],

                "stop":

                    p["stop"],

                "target":

                    p["target"],

                "exit":

                    price,

                "contracts":

                    1,

                "risk_per_contract":

                    p["risk"],

                "planned_risk":

                    p["risk"],

                "pnl_one_contract":

                    pnl_one,

                "pnl":

                    pnl_one,

                "equity_after":

                    equity,

            }

        )

        position = None

    for bar in bars:

        t = bar["_t"]

        finish = (

            t

            + timedelta(

                minutes=15

            )

        )

        local = t.astimezone(

            CT

        )

        date = (

            local.date()

            .isoformat()

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

                f"Nonfinite OHLC at {t}"

            )

        if not (

            l

            <= min(o, c)

            <= max(o, c)

            <= h

        ):

            raise ValueError(

                f"Invalid OHLC at {t}"

            )

        inst = int(

            bar[

                "instrument_id"

            ]

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

        if date != day:

            day = date

            day_trades = 0

        # ==============================================================

        # PENDING NEXT-BAR ENTRY

        # ==============================================================

        if pending is not None:

            p = pending

            pending = None

            if t != p["end"]:

                counts[

                    "missing_next_open"

                ] += 1

            elif day_trades >= 2:

                counts[

                    "daily_trade_cap"

                ] += 1

            else:

                entry = nearest_tick(

                    o + TICK

                )

                stop_bound = min(

                    (

                        p[

                            "confirmation_low"

                        ]

                        - (

                            0.25

                            * p["atr"]

                        )

                    ),

                    (

                        entry

                        - (

                            0.50

                            * p["atr"]

                        )

                    ),

                )

                # R10.2 repair:

                # protective long stop

                # floors to tick.

                stop = floor_tick(

                    stop_bound,

                    TICK,

                )

                distance = (

                    entry - stop

                )

                if (

                    distance <= 0

                    or

                    distance

                    > (

                        1.50

                        * p["atr"]

                    )

                ):

                    counts[

                        "stop_distance"

                    ] += 1

                else:

                    risk = (

                        long_risk_per_contract(

                            entry=

                                entry,

                            protective_stop=

                                stop,

                            tick_size=

                                TICK,

                            point_value=

                                POINT_VALUE,

                            round_trip_fee=

                                ROUND_TRIP_FEE,

                            stop_slippage_ticks=

                                1,

                        )

                    )

                    target = (

                        long_target_for_net_r(

                            entry=

                                entry,

                            risk_per_contract=

                                risk,

                            reward_multiple=

                                2.0,

                            tick_size=

                                TICK,

                            point_value=

                                POINT_VALUE,

                            round_trip_fee=

                                ROUND_TRIP_FEE,

                            target_slippage_ticks=

                                1,

                        )

                    )

                    if (

                        target

                        > p[

                            "resistance"

                        ]

                    ):

                        counts[

                            "insufficient_room"

                        ] += 1

                    else:

                        position = {

                            "signal_time":

                                p[

                                    "signal_time"

                                ],

                            "entry_time":

                                t.isoformat(),

                            "entry":

                                entry,

                            "stop":

                                stop,

                            "target":

                                target,

                            "risk":

                                risk,

                            "inst":

                                p[

                                    "inst"

                                ],

                        }

                        day_trades += 1

        # ==============================================================

        # POSITION EXECUTION

        # ==============================================================

        if position is not None:

            if (

                not good(bar)

                or

                inst

                != position[

                    "inst"

                ]

                or

                (

                    previous

                    is not None

                    and

                    not contiguous

                )

            ):

                raise ValueError(

                    "Indeterminate execution "

                    f"while exposed at {t}"

                )

            result = long_exit_fill(

                open_price=

                    o,

                high=

                    h,

                low=

                    l,

                protective_stop=

                    position[

                        "stop"

                    ],

                target=

                    position[

                        "target"

                    ],

                session_exit=

                    (

                        (

                            local.hour,

                            local.minute,

                        )

                        >= (

                            15,

                            0,

                        )

                    ),

                tick_size=

                    TICK,

            )

            if result:

                close_position(

                    result[0],

                    result[1],

                    t,

                )

        # ==============================================================

        # BAR-CLOSE DRAWDOWN

        # ==============================================================

        marked = mtm(

            c

        )

        peak = max(

            peak,

            marked,

        )

        maxdd = max(

            maxdd,

            peak - marked,

        )

        if peak > 0:

            maxddpct = max(

                maxddpct,

                (

                    peak - marked

                )

                / peak,

            )

        # ==============================================================

        # FOUR-BAR READINESS

        # ==============================================================

        if (

            not contiguous

            or

            not same_contract

            or

            not good(bar)

        ):

            recent.clear()

        if good(bar):

            recent.append(

                l

            )

        previous = bar

        if position is not None:

            continue

        # ==============================================================

        # SIGNAL BAR

        # ==============================================================

        if (

            not good(bar)

            or

            bar[

                "feature_valid"

            ]

            != "1"

        ):

            counts[

                "invalid_signal_bar"

            ] += 1

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

            continue

        context = {}

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

            if index >= 0:

                context[

                    timeframe

                ] = rows[index]

        if len(context) < 2:

            counts[

                "higher_tf_warmup"

            ] += 1

            continue

        one_hour = (

            context["1h"]

        )

        four_hour = (

            context["4h"]

        )

        if any(

            (

                x[

                    "feature_valid"

                ]

                != "1"

            )

            or

            (

                not good(x)

            )

            or

            (

                int(

                    x[

                        "instrument_id"

                    ]

                )

                != inst

            )

            for x in (

                one_hour,

                four_hour,

            )

        ):

            counts[

                "higher_tf_invalid"

            ] += 1

            continue

        if (

            four_hour[

                "trend_up"

            ]

            != "1"

            or

            float(

                four_hour[

                    "close"

                ]

            )

            <= float(

                four_hour[

                    "ema20"

                ]

            )

        ):

            counts[

                "4h_trend"

            ] += 1

            continue

        if (

            one_hour[

                "trend_up"

            ]

            != "1"

            or

            float(

                one_hour[

                    "close"

                ]

            )

            < float(

                one_hour[

                    "ema50"

                ]

            )

        ):

            counts[

                "1h_context"

            ] += 1

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

        if (

            not math.isfinite(

                atr15

            )

            or

            atr15 <= 0

        ):

            raise ValueError(

                f"Invalid ATR at {t}"

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

        if not touch:

            counts[

                "no_support_touch"

            ] += 1

            continue

        close_location = (

            (c - l)

            /

            (

                h - l

                if h > l

                else 1

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

        if not recovery:

            counts[

                "no_confirmation"

            ] += 1

            continue

        if len(recent) < 4:

            counts[

                "swing_warmup"

            ] += 1

            continue

        candidates += 1

        pending = {

            "end":

                finish,

            "signal_time":

                t.isoformat(),

            "inst":

                inst,

            "confirmation_low":

                recent[-1],

            "atr":

                atr15,

            "resistance":

                float(

                    one_hour[

                        "prior_high20"

                    ]

                ),

        }

    # ==================================================================

    # DEVELOPMENT CUTOFF

    # ==================================================================

    if position is not None:

        last = bars[-1]

        if (

            last["_t"]

            + timedelta(

                minutes=15

            )

            != END

        ):

            raise ValueError(

                "Final development "

                "bar missing"

            )

        close_position(

            nearest_tick(

                float(

                    last[

                        "close"

                    ]

                )

                - TICK

            ),

            "development_cutoff_close",

            last["_t"],

        )

    if pending is not None:

        counts[

            "pending_cancelled_at_cutoff"

        ] += 1

    pnls = [

        trade["pnl"]

        for trade in trades

    ]

    wins = [

        pnl

        for pnl in pnls

        if pnl > 0

    ]

    losses = [

        pnl

        for pnl in pnls

        if pnl < 0

    ]

    pf = (

        sum(wins)

        / -sum(losses)

        if losses

        else None

    )

    return {

        "version":

            "R10.2-repaired-core-build4",

        "evaluation":

            "seen development data",

        "candidates":

            candidates,

        "trade_count":

            len(trades),

        "wins":

            len(wins),

        "losses":

            len(losses),

        "net":

            sum(pnls),

        "ending_equity":

            equity,

        "profit_factor":

            pf,

        "max_bar_close_drawdown":

            maxdd,

        "max_bar_close_drawdown_fraction":

            maxddpct,

        "counts":

            dict(counts),

        "trades":

            trades,

    }

