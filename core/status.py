"""
ATLAS human-readable status layer.

Combines:

    scanner market state
    strategy decision audit
    account/risk information

without conflating those populations.
"""


def build_status(
    scanner_result,
    decision_audit,
    starting_equity,
    instrument_name,
    risk_fraction,
):

    latest = scanner_result[
        "latest"
    ]


    state = latest[
        "state"
    ]


    if state == "WAIT":

        message = (
            "No active completed setup."
        )

    elif state == "WATCH":

        message = (
            "Setup developing; "
            "waiting for confirmation."
        )

    elif state == "CONFIRMED":

        message = (
            "Scanner confirmation present. "
            "This is market-state information, "
            "not automatically an executable trade."
        )

    elif state == "INVALIDATED":

        message = (
            "Prior scanner setup invalidated."
        )

    else:

        raise ValueError(
            f"unknown scanner state: {state}"
        )


    equity = float(
        starting_equity
    )

    risk_fraction = float(
        risk_fraction
    )


    return {
        "market":
            str(
                instrument_name
            ).upper(),

        "market_state": {
            "state":
                state,

            "reason":
                latest[
                    "reason"
                ],

            "timestamp":
                latest[
                    "timestamp"
                ],

            "message":
                message,
        },

        "strategy_decision": {
            "candidates":
                decision_audit[
                    "candidates"
                ],

            "accepted_trades":
                decision_audit[
                    "accepted_trades"
                ],

            "rejected_total":
                decision_audit[
                    "rejected_total"
                ],

            "rejection_detail_status":
                decision_audit[
                    "rejection_detail_status"
                ],

            "rejection_reasons":
                decision_audit[
                    "rejection_reasons"
                ],

            "scanner_population_used":
                False,
        },

        "account": {
            "equity":
                equity,

            "risk_fraction":
                risk_fraction,

            "risk_budget":
                equity
                * risk_fraction,
        },

        "research": {
            "evaluation":
                "seen development data only",

            "edge_established":
                False,

            "live_orders":
                False,
        },
    }


def render_status(status):

    market = status[
        "market"
    ]

    market_state = status[
        "market_state"
    ]

    decision = status[
        "strategy_decision"
    ]

    account = status[
        "account"
    ]

    research = status[
        "research"
    ]


    lines = [
        "",
        "=" * 64,
        f"ATLAS — {market}",
        "=" * 64,
        "",
        "MARKET STATE",
        (
            "State:   "
            + str(
                market_state[
                    "state"
                ]
            )
        ),
        (
            "Reason:  "
            + str(
                market_state[
                    "reason"
                ]
            )
        ),
        (
            "Bar:     "
            + str(
                market_state[
                    "timestamp"
                ]
            )
        ),
        "",
        market_state[
            "message"
        ],
        "",
        "FROZEN STRATEGY DECISION AUDIT",
        (
            "Candidates:       "
            f"{decision['candidates']}"
        ),
        (
            "Accepted trades:  "
            f"{decision['accepted_trades']}"
        ),
        (
            "Rejected total:   "
            f"{decision['rejected_total']}"
        ),
        (
            "Rejection detail: "
            + decision[
                "rejection_detail_status"
            ]
        ),
    ]


    reasons = decision[
        "rejection_reasons"
    ]


    if reasons:

        lines.append("")

        lines.append(
            "REJECTION FUNNEL"
        )

        for key, value in sorted(
            reasons.items()
        ):

            lines.append(
                f"{key}: {value}"
            )


    lines.extend([
        "",
        "ACCOUNT",
        (
            "Equity:      "
            f"${account['equity']:,.2f}"
        ),
        (
            "Risk/trade:  "
            f"{account['risk_fraction'] * 100:.2f}%"
        ),
        (
            "Risk budget: "
            f"${account['risk_budget']:,.2f}"
        ),
        "",
        (
            "Evaluation: "
            + research[
                "evaluation"
            ]
        ),
        "Live orders: OFF",
        "Edge established: NO",
        "",
        "=" * 64,
    ])


    return "\n".join(
        lines
    )
