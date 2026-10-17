"""
ATLAS Core ledger.

Turns completed strategy/execution trades into:
- immutable normalized trade records
- account-sizing replay records
- summary statistics

Research only.
No live orders.
"""

import math

from .risk import size_long


def normalize_trade(trade):

    required = (
        "signal_time",
        "entry_time",
        "exit_bar_start",
        "reason",
        "entry",
        "stop",
        "target",
        "exit",
        "pnl_one_contract",
    )


    for key in required:

        if key not in trade:

            raise ValueError(
                "trade missing field: "
                + key
            )


    return {
        "signal_time":
            str(
                trade[
                    "signal_time"
                ]
            ),

        "entry_time":
            str(
                trade[
                    "entry_time"
                ]
            ),

        "exit_bar_start":
            str(
                trade[
                    "exit_bar_start"
                ]
            ),

        "reason":
            str(
                trade[
                    "reason"
                ]
            ),

        "entry":
            float(
                trade[
                    "entry"
                ]
            ),

        "stop":
            float(
                trade[
                    "stop"
                ]
            ),

        "target":
            float(
                trade[
                    "target"
                ]
            ),

        "exit":
            float(
                trade[
                    "exit"
                ]
            ),

        "pnl_one_contract":
            float(
                trade[
                    "pnl_one_contract"
                ]
            ),
    }


def summarize_pnls(
    pnls,
    starting_equity,
):

    pnls = [
        float(x)
        for x in pnls
    ]


    equity = float(
        starting_equity
    )

    peak = equity

    max_closed_trade_drawdown = 0.0


    for pnl in pnls:

        equity += pnl

        peak = max(
            peak,
            equity,
        )

        max_closed_trade_drawdown = max(
            max_closed_trade_drawdown,
            peak - equity,
        )


    wins = [
        x
        for x in pnls
        if x > 0
    ]


    losses = [
        x
        for x in pnls
        if x < 0
    ]


    gross_profit = sum(
        wins
    )

    gross_loss = -sum(
        losses
    )


    profit_factor = (
        gross_profit
        / gross_loss
        if gross_loss > 0
        else None
    )


    return {
        "trade_count":
            len(pnls),

        "wins":
            len(wins),

        "losses":
            len(losses),

        "net":
            sum(pnls),

        "ending_equity":
            equity,

        "gross_profit":
            gross_profit,

        "gross_loss":
            gross_loss,

        "profit_factor":
            profit_factor,

        "max_closed_trade_drawdown":
            max_closed_trade_drawdown,
    }


def replay_one_contract(
    trades,
    starting_equity=1000.0,
):

    normalized = [
        normalize_trade(x)
        for x in trades
    ]


    summary = summarize_pnls(
        [
            x[
                "pnl_one_contract"
            ]
            for x in normalized
        ],
        starting_equity,
    )


    return {
        "mode":
            "one_contract_replay",

        "starting_equity":
            float(
                starting_equity
            ),

        "summary":
            summary,

        "trades":
            normalized,
    }


def replay_account_risk(
    trades,
    starting_equity,
    instrument_name="MNQ",
    risk_fraction=0.01,
):

    equity = float(
        starting_equity
    )


    if equity <= 0:

        raise ValueError(
            "starting equity "
            "must be positive"
        )


    normalized = [
        normalize_trade(x)
        for x in trades
    ]


    records = []

    realized_pnls = []

    sized_trades = 0

    rejected_trades = 0


    for number, trade in enumerate(
        normalized,
        start=1,
    ):

        equity_before = equity


        sizing = size_long(
            equity=
                equity_before,

            entry=
                trade[
                    "entry"
                ],

            protective_stop=
                trade[
                    "stop"
                ],

            instrument_name=
                instrument_name,

            risk_fraction=
                risk_fraction,
        )


        quantity = float(
            sizing[
                "quantity"
            ]
        )


        if quantity > 0:

            realized = (
                trade[
                    "pnl_one_contract"
                ]
                * quantity
            )

            equity += realized

            sized_trades += 1

            decision = "TAKEN"

        else:

            realized = 0.0

            rejected_trades += 1

            decision = (
                "REJECT_ACCOUNT_TOO_SMALL"
            )


        if (
            float(
                sizing[
                    "planned_risk"
                ]
            )
            > float(
                sizing[
                    "risk_budget"
                ]
            )
            + 1e-9
        ):

            raise ValueError(
                "ledger risk ceiling "
                "violation"
            )


        realized_pnls.append(
            realized
        )


        records.append(
            {
                "trade_number":
                    number,

                "signal_time":
                    trade[
                        "signal_time"
                    ],

                "entry_time":
                    trade[
                        "entry_time"
                    ],

                "exit_bar_start":
                    trade[
                        "exit_bar_start"
                    ],

                "reason":
                    trade[
                        "reason"
                    ],

                "entry":
                    trade[
                        "entry"
                    ],

                "stop":
                    trade[
                        "stop"
                    ],

                "target":
                    trade[
                        "target"
                    ],

                "exit":
                    trade[
                        "exit"
                    ],

                "equity_before":
                    equity_before,

                "risk_budget":
                    float(
                        sizing[
                            "risk_budget"
                        ]
                    ),

                "risk_per_unit":
                    float(
                        sizing[
                            "risk_per_unit"
                        ]
                    ),

                "quantity":
                    quantity,

                "planned_risk":
                    float(
                        sizing[
                            "planned_risk"
                        ]
                    ),

                "decision":
                    decision,

                "pnl_one_contract":
                    trade[
                        "pnl_one_contract"
                    ],

                "realized_pnl":
                    realized,

                "equity_after":
                    equity,
            }
        )


    summary = summarize_pnls(
        realized_pnls,
        starting_equity,
    )


    summary[
        "sized_trades"
    ] = sized_trades


    summary[
        "rejected_trades"
    ] = rejected_trades


    return {
        "mode":
            "dynamic_current_equity_risk",

        "instrument":
            str(
                instrument_name
            ).upper(),

        "risk_fraction":
            float(
                risk_fraction
            ),

        "starting_equity":
            float(
                starting_equity
            ),

        "summary":
            summary,

        "trades":
            records,
    }
