import csv
import gzip
import hashlib

from .config import (
    ATLAS_ROOT,
    R5_HASHES,
)


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def r5_path(timeframe):

    if timeframe not in R5_HASHES:
        raise ValueError(
            "Unsupported timeframe: "
            + str(timeframe)
        )

    return (
        ATLAS_ROOT
        / "processed"
        / "R5"
        / f"NQ_v0_R5_{timeframe}.csv.gz"
    )


def verify_r5(timeframe):

    path = r5_path(timeframe)

    if not path.is_file():
        raise ValueError(
            f"Missing R5 {timeframe}"
        )

    actual = sha256(path)

    expected = R5_HASHES[timeframe]

    if actual != expected:
        raise ValueError(
            f"R5 {timeframe} SHA mismatch"
        )

    return path


def iter_r5(timeframe):

    path = verify_r5(timeframe)

    with gzip.open(
        path,
        "rt",
        encoding="utf-8",
        newline="",
    ) as f:

        yield from csv.DictReader(f)
