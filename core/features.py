from collections import deque


FEATURE_NUMBERS = (
    "return_1",
    "ema20",
    "ema50",
    "ema20_slope",
    "atr14",
    "volume_sma20",
    "volume_ratio20",
    "prior_high20",
    "prior_low20",
)


def optional_float(value):

    if value == "":
        return None

    return float(value)


def close_enough(
    a,
    b,
    tolerance=2e-8,
):

    if a is None and b is None:
        return True

    if a is None or b is None:
        return False

    return (
        abs(a - b)
        <= tolerance
        * max(
            1,
            abs(a),
            abs(b),
        )
    )


class FeatureEngine:

    def __init__(self):

        self.reset(None)


    def reset(self, instrument_id):

        self.instrument_id = (
            instrument_id
        )

        self.highs = deque(
            maxlen=20
        )

        self.lows = deque(
            maxlen=20
        )

        self.volumes = deque(
            maxlen=20
        )

        self.true_ranges = deque(
            maxlen=14
        )

        self.ema20 = None
        self.ema50 = None

        self.previous_close = None

        self.usable_count = 0


    def process(self, row):

        instrument_id = int(
            row["instrument_id"]
        )

        if (
            instrument_id
            != self.instrument_id
        ):
            self.reset(
                instrument_id
            )

        usable = (
            row["complete"] == "1"
            and
            row["roll_mixed"] == "0"
        )

        output = {
            key: None
            for key
            in FEATURE_NUMBERS
        }

        output.update(
            feature_valid=0,
            trend_up=0,
            trend_down=0,
        )

        if not usable:
            return output

        o = float(row["open"])
        h = float(row["high"])
        l = float(row["low"])
        c = float(row["close"])
        v = float(row["volume"])

        prior_high = (
            max(self.highs)
            if len(self.highs) == 20
            else None
        )

        prior_low = (
            min(self.lows)
            if len(self.lows) == 20
            else None
        )

        volume_sma = (
            sum(self.volumes) / 20
            if len(self.volumes) == 20
            else None
        )

        ret = (
            None
            if self.previous_close
            in (None, 0)
            else
            c / self.previous_close - 1
        )

        if self.previous_close is None:

            true_range = h - l

        else:

            true_range = max(
                h - l,
                abs(
                    h
                    - self.previous_close
                ),
                abs(
                    l
                    - self.previous_close
                ),
            )

        new_ema20 = (
            c
            if self.ema20 is None
            else
            (2 / 21) * c
            + (19 / 21)
            * self.ema20
        )

        new_ema50 = (
            c
            if self.ema50 is None
            else
            (2 / 51) * c
            + (49 / 51)
            * self.ema50
        )

        slope = (
            None
            if self.ema20 is None
            else
            new_ema20
            - self.ema20
        )

        self.true_ranges.append(
            true_range
        )

        atr14 = (
            sum(self.true_ranges) / 14
            if len(self.true_ranges) == 14
            else None
        )

        self.usable_count += 1

        valid = int(
            self.usable_count >= 50
            and atr14 is not None
            and prior_high is not None
            and volume_sma is not None
        )

        output.update(
            return_1=ret,
            ema20=new_ema20,
            ema50=new_ema50,
            ema20_slope=slope,
            atr14=atr14,
            volume_sma20=volume_sma,
            volume_ratio20=(
                v / volume_sma
                if volume_sma
                else None
            ),
            prior_high20=prior_high,
            prior_low20=prior_low,
            feature_valid=valid,
            trend_up=int(
                bool(
                    valid
                    and
                    new_ema20
                    > new_ema50
                    and
                    slope > 0
                )
            ),
            trend_down=int(
                bool(
                    valid
                    and
                    new_ema20
                    < new_ema50
                    and
                    slope < 0
                )
            ),
        )

        self.ema20 = new_ema20
        self.ema50 = new_ema50
        self.previous_close = c

        self.highs.append(h)
        self.lows.append(l)
        self.volumes.append(v)

        return output
