"""

ATLAS Core execution simulator.

Research simulation only.

Owns:

- tick rounding

- protective stop rounding

- modeled stop fill

- planned risk

- target construction

- OHLC exit resolution

- realized long P&L

Does NOT:

- generate signals

- size accounts

- place live orders

"""

import math

from decimal import (

    Decimal,

    ROUND_FLOOR,

)

DEFAULT_TICK_SIZE = 0.25

DEFAULT_POINT_VALUE = 2.0

DEFAULT_ROUND_TRIP_FEE = 1.24

def nearest_tick(

    value,

    tick_size=DEFAULT_TICK_SIZE,

):

    tick_size = float(

        tick_size

    )

    return round(

        round(

            float(value)

            / tick_size

        )

        * tick_size,

        10,

    )

def floor_tick(

    value,

    tick_size=DEFAULT_TICK_SIZE,

):

    tick = Decimal(

        str(tick_size)

    )

    value_d = Decimal(

        str(value)

    )

    ticks = (

        value_d / tick

    ).to_integral_value(

        rounding=ROUND_FLOOR

    )

    return float(

        ticks * tick

    )

def ceil_tick(

    value,

    tick_size=DEFAULT_TICK_SIZE,

):

    tick_size = float(

        tick_size

    )

    return round(

        math.ceil(

            (

                float(value)

                - 1e-12

            )

            / tick_size

        )

        * tick_size,

        10,

    )

def long_stop_fill(

    protective_stop,

    tick_size=DEFAULT_TICK_SIZE,

    stop_slippage_ticks=1,

):

    return (

        float(protective_stop)

        - (

            float(tick_size)

            * int(stop_slippage_ticks)

        )

    )

def long_risk_per_contract(

    entry,

    protective_stop,

    tick_size=DEFAULT_TICK_SIZE,

    point_value=DEFAULT_POINT_VALUE,

    round_trip_fee=DEFAULT_ROUND_TRIP_FEE,

    stop_slippage_ticks=1,

):

    entry = float(

        entry

    )

    modeled_stop = long_stop_fill(

        protective_stop=

            protective_stop,

        tick_size=

            tick_size,

        stop_slippage_ticks=

            stop_slippage_ticks,

    )

    if modeled_stop >= entry:

        raise ValueError(

            "long modeled stop fill "

            "must be below entry"

        )

    return (

        (

            entry

            - modeled_stop

        )

        * float(point_value)

        + float(round_trip_fee)

    )

def long_target_for_net_r(

    entry,

    risk_per_contract,

    reward_multiple=2.0,

    tick_size=DEFAULT_TICK_SIZE,

    point_value=DEFAULT_POINT_VALUE,

    round_trip_fee=DEFAULT_ROUND_TRIP_FEE,

    target_slippage_ticks=1,

):

    raw_target = (

        float(entry)

        + (

            (

                float(reward_multiple)

                * float(risk_per_contract)

            )

            + float(round_trip_fee)

        )

        / float(point_value)

        + (

            float(tick_size)

            * int(target_slippage_ticks)

        )

    )

    return ceil_tick(

        raw_target,

        tick_size,

    )

def long_exit_fill(

    open_price,

    high,

    low,

    protective_stop,

    target,

    session_exit=False,

    tick_size=DEFAULT_TICK_SIZE,

):

    o = float(open_price)

    h = float(high)

    l = float(low)

    stop = float(

        protective_stop

    )

    target = float(

        target

    )

    tick = float(

        tick_size

    )

    # Opening gap through stop.

    if o <= stop:

        return (

            nearest_tick(

                o - tick,

                tick,

            ),

            "gap_or_open_stop",

        )

    # Frozen R10 session behavior.

    if session_exit:

        return (

            nearest_tick(

                o - tick,

                tick,

            ),

            "session_exit",

        )

    # Open already at/above target.

    if o >= target:

        return (

            nearest_tick(

                target - tick,

                tick,

            ),

            "target_at_open_conservative",

        )

    # Intrabar stop.

    # If both stop and target occur,

    # frozen policy is stop first.

    if l <= stop:

        reason = (

            "both_hit_stop_first"

            if h >= target

            else

            "stop"

        )

        return (

            nearest_tick(

                stop - tick,

                tick,

            ),

            reason,

        )

    # Intrabar target.

    if h >= target:

        return (

            nearest_tick(

                target - tick,

                tick,

            ),

            "target",

        )

    return None

def long_pnl(

    entry,

    exit_price,

    quantity=1,

    point_value=DEFAULT_POINT_VALUE,

    round_trip_fee=DEFAULT_ROUND_TRIP_FEE,

):

    quantity = float(

        quantity

    )

    pnl_one = (

        (

            float(exit_price)

            - float(entry)

        )

        * float(point_value)

        - float(round_trip_fee)

    )

    return (

        pnl_one

        * quantity

    )

