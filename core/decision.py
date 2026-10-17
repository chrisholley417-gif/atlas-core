"""
ATLAS strategy decision audit.

Scanner state and strategy decisions are different things.

scanner.py:
    describes market/setup state.

strategy.py:
    owns the frozen R10.2 strategy.

decision.py:
    summarizes the strategy's own candidate/trade funnel
    without pretending scanner events are strategy candidates.

No strategy rules are changed here.
"""


KNOWN_REJECTION_KEYS = (
    "expired_or_invalid_next_bar",
    "stop_distance",
    "net_rr",
    "insufficient_room",
    "daily_trade_cap",
    "daily_loss_stop",
    "open_at_cutoff",
)


def _integer(value, name):

    try:
        result = int(value)

    except Exception as exc:
        raise ValueError(
            f"{name} is not integer-like"
        ) from exc

    if result < 0:
        raise ValueError(
            f"{name} cannot be negative"
        )

    return result


def build_decision_audit(
    strategy_result,
):

    candidates = _integer(
        strategy_result[
            "candidates"
        ],
        "candidates",
    )

    trades = _integer(
        strategy_result[
            "trade_count"
        ],
        "trade_count",
    )


    if trades > candidates:
        raise ValueError(
            "trade count exceeds candidate count"
        )


    rejected_total = (
        candidates - trades
    )


    # --------------------------------------------------------------
    # Look for an already-existing strategy-owned rejection funnel.
    #
    # We do NOT manufacture rejection reasons if the frozen strategy
    # does not currently expose them.
    # --------------------------------------------------------------

    source = None


    for key in (
        "rejections",
        "rejection_counts",
        "funnel",
        "post_confirmation_funnel",
    ):

        value = strategy_result.get(
            key
        )

        if isinstance(
            value,
            dict,
        ):

            source = value
            break


    reasons = {}


    if source is not None:

        for key in KNOWN_REJECTION_KEYS:

            if key in source:

                reasons[key] = _integer(
                    source[key],
                    key,
                )


    classified_rejections = sum(
        reasons.values()
    )


    # Some frozen strategy versions only return the final candidate
    # and trade counts. That is acceptable. We preserve the exact
    # known rejected total but label its internal composition as
    # unavailable rather than inventing categories.
    if classified_rejections == 0:

        detail_status = (
            "TOTAL_ONLY"
        )

        unclassified_rejections = (
            rejected_total
        )


    else:

        if classified_rejections > rejected_total:

            raise ValueError(
                "strategy rejection categories exceed "
                "total rejected candidates"
            )

        unclassified_rejections = (
            rejected_total
            - classified_rejections
        )

        detail_status = (
            "DETAILED"
            if unclassified_rejections == 0
            else "PARTIAL"
        )


    return {
        "candidate_population":
            "frozen_strategy",

        "candidates":
            candidates,

        "accepted_trades":
            trades,

        "rejected_total":
            rejected_total,

        "classified_rejections":
            classified_rejections,

        "unclassified_rejections":
            unclassified_rejections,

        "rejection_detail_status":
            detail_status,

        "rejection_reasons":
            reasons,

        "reconciles":
            (
                trades
                + rejected_total
                == candidates
            ),

        "scanner_population_used":
            False,
    }
