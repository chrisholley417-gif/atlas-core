import math


DEFAULT_RISK_FRACTION = 0.01


INSTRUMENTS = {

    "MNQ": {
        "market_type":
            "future",

        "tick_size":
            0.25,

        "point_value":
            2.0,

        "quantity_increment":
            1.0,

        "minimum_quantity":
            1.0,

        # Frozen ATLAS research
        # execution assumption.
        "round_trip_fee":
            1.24,

        "stop_slippage_ticks":
            1,

        "mechanics_status":
            "frozen_research_mechanics",

        "cost_status":
            "research_assumption",
    },


    "MES": {
        "market_type":
            "future",

        "tick_size":
            0.25,

        "point_value":
            5.0,

        "quantity_increment":
            1.0,

        "minimum_quantity":
            1.0,

        # No broker-specific cost
        # assumption frozen yet.
        "round_trip_fee":
            0.0,

        "stop_slippage_ticks":
            0,

        "mechanics_status":
            "frozen_adapter_mechanics",

        "cost_status":
            "not_configured",
    },


    "MGC": {
        "market_type":
            "future",

        "tick_size":
            0.10,

        "point_value":
            10.0,

        "quantity_increment":
            1.0,

        "minimum_quantity":
            1.0,

        "round_trip_fee":
            0.0,

        "stop_slippage_ticks":
            0,

        "mechanics_status":
            "frozen_adapter_mechanics",

        "cost_status":
            "not_configured",
    },


    # Generic fractional template.
    # Not an exchange-specific
    # BTC/ETH configuration.
    "CRYPTO_TEMPLATE": {
        "market_type":
            "spot_crypto",

        "tick_size":
            0.01,

        "point_value":
            1.0,

        "quantity_increment":
            0.0001,

        "minimum_quantity":
            0.0001,

        "round_trip_fee":
            0.0,

        "stop_slippage_ticks":
            0,

        "mechanics_status":
            "template_only",

        "cost_status":
            "not_configured",
    },
}


def instrument(name):

    key = str(name).upper()

    if key not in INSTRUMENTS:

        raise ValueError(
            "Unknown ATLAS instrument: "
            + key
        )

    return dict(
        INSTRUMENTS[key]
    )


def floor_to_increment(
    value,
    increment,
):

    if increment <= 0:

        raise ValueError(
            "quantity increment "
            "must be positive"
        )

    units = math.floor(
        (
            value
            + 1e-12
        )
        / increment
    )

    result = (
        units
        * increment
    )

    decimals = max(
        0,
        len(
            str(increment)
            .rstrip("0")
            .split(".")[-1]
        )
        if "." in str(increment)
        else 0,
    )

    return round(
        result,
        decimals,
    )


def risk_budget(
    equity,
    risk_fraction=
        DEFAULT_RISK_FRACTION,
):

    equity = float(
        equity
    )

    risk_fraction = float(
        risk_fraction
    )

    if equity <= 0:

        raise ValueError(
            "equity must be positive"
        )

    if not (
        0
        < risk_fraction
        < 1
    ):

        raise ValueError(
            "risk_fraction must be "
            "between 0 and 1"
        )

    return (
        equity
        * risk_fraction
    )


def long_stop_fill(
    protective_stop,
    spec,
):

    return (
        float(
            protective_stop
        )
        - (
            float(
                spec[
                    "tick_size"
                ]
            )
            * int(
                spec[
                    "stop_slippage_ticks"
                ]
            )
        )
    )


def risk_per_unit_long(
    entry,
    protective_stop,
    spec,
):

    entry = float(
        entry
    )

    stop_fill = long_stop_fill(
        protective_stop,
        spec,
    )

    if stop_fill >= entry:

        raise ValueError(
            "long stop fill must "
            "be below entry"
        )

    price_risk = (
        entry
        - stop_fill
    )

    risk = (
        price_risk
        * float(
            spec[
                "point_value"
            ]
        )
        + float(
            spec[
                "round_trip_fee"
            ]
        )
    )

    if risk <= 0:

        raise ValueError(
            "risk per unit must "
            "be positive"
        )

    return risk


def required_equity_for_minimum(
    risk_per_unit,
    spec,
    risk_fraction=
        DEFAULT_RISK_FRACTION,
):

    minimum = float(
        spec[
            "minimum_quantity"
        ]
    )

    required_risk = (
        float(
            risk_per_unit
        )
        * minimum
    )

    return (
        required_risk
        / float(
            risk_fraction
        )
    )


def size_long(
    equity,
    entry,
    protective_stop,
    instrument_name=None,
    instrument_spec=None,
    risk_fraction=
        DEFAULT_RISK_FRACTION,
):

    if (
        instrument_name is None
        and
        instrument_spec is None
    ):

        raise ValueError(
            "instrument required"
        )

    if instrument_spec is None:

        spec = instrument(
            instrument_name
        )

        label = str(
            instrument_name
        ).upper()

    else:

        spec = dict(
            instrument_spec
        )

        label = (
            str(
                instrument_name
            ).upper()
            if instrument_name
            is not None
            else
            "CUSTOM"
        )


    budget = risk_budget(
        equity,
        risk_fraction,
    )


    unit_risk = risk_per_unit_long(
        entry,
        protective_stop,
        spec,
    )


    raw_quantity = (
        budget
        / unit_risk
    )


    quantity = floor_to_increment(
        raw_quantity,
        float(
            spec[
                "quantity_increment"
            ]
        ),
    )


    minimum = float(
        spec[
            "minimum_quantity"
        ]
    )


    if quantity < minimum:

        quantity = 0.0


    planned_risk = (
        quantity
        * unit_risk
    )


    if (
        planned_risk
        > budget
        + 1e-9
    ):

        raise ValueError(
            "risk ceiling violated"
        )


    required_equity = (
        required_equity_for_minimum(
            unit_risk,
            spec,
            risk_fraction,
        )
    )


    can_trade = (
        quantity >= minimum
    )


    return {
        "instrument":
            label,

        "market_type":
            spec[
                "market_type"
            ],

        "equity":
            float(
                equity
            ),

        "risk_fraction":
            float(
                risk_fraction
            ),

        "risk_budget":
            budget,

        "entry":
            float(
                entry
            ),

        "protective_stop":
            float(
                protective_stop
            ),

        "modeled_stop_fill":
            long_stop_fill(
                protective_stop,
                spec,
            ),

        "risk_per_unit":
            unit_risk,

        "raw_quantity":
            raw_quantity,

        "quantity":
            quantity,

        "planned_risk":
            planned_risk,

        "required_equity_for_minimum":
            required_equity,

        "can_trade":
            can_trade,

        "decision":
            (
                "SIZE"
                if can_trade
                else
                "REJECT_ACCOUNT_TOO_SMALL"
            ),

        "mechanics_status":
            spec.get(
                "mechanics_status"
            ),

        "cost_status":
            spec.get(
                "cost_status"
            ),
    }
