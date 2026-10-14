"""Immutable SHA-256 identities of every recovered Core Build 7 source file.

The original archive was SHA-256 1bb9d72bc982c3e0855083567f21262f8177ec53e600648900e835ab27ee44b3.
This bridge lock is distinct from the original Candidate A freeze manifest.
"""

from pathlib import Path


CORE_SOURCE_SHA256 = {
    "__init__.py": "41ea3682cfb85cbe7d24355131611c5c1f65a2d6e416620b964726d4f2bfafd2",
    "app.py": "d106bcfa9c2b86e7faaad8e353f8a791c2da76bbe917e2489c6232dc757417b2",
    "atlas.py": "8a4fb29665808f034960d05865d428200a3c086aefe0400a48086a236f3598e9",
    "config.py": "53184f994ab29adb32d7ec370e0073145c4a9278a0bb37622a4f61185ce689b3",
    "data.py": "90a3d08497e7c90ec1ee58f4e208328711e9bbcfa72c4a474e9c5ebf0116eacc",
    "decision.py": "ce840c340b56b7029085cdf16809da89da6ff2ba873fbd3b4f4330efc4ea6b02",
    "execution.py": "155a49fd4bad0a14380a7126645a6bade6187a1efbcb0950de1b4091829428a3",
    "features.py": "b22b231744e0d17e545e63d9f00888a4c4731c0511761cde778a078731b460f2",
    "ledger.py": "5223348d6c6d2faeabf9e31cec6f8053ffe4333ff8d2cf5f66526ed3fa92f61a",
    "risk.py": "9bd9f5803a87c936c8a796a5b28c44f4d344e18f349f6a1f8ca34a6e019808e5",
    "scanner.py": "2b5acb7135bb7c46116056ce725860e103eba3def3204ebdfc4b39c560e79fc7",
    "status.py": "3b12f915947083acaa59d3b001bb2763ed100f273c6cb327cbc91950c176fdec",
    "strategy.py": "2b30b0e407c2e9400b906a168aa2119db97428fb19acf42bb3c832a82ec4a876",
}

FREEZE_MANIFEST_SHA256 = "843a2936129af7c2b32596a012b4ea6d6b6dbafd931844a74fd45b60bd1ff0a9"


def verify_core_sources(root: Path, digest) -> None:
    core = root / "core"
    present = {path.name for path in core.glob("*.py")}
    if present != set(CORE_SOURCE_SHA256):
        raise RuntimeError("Recovered Core module list differs from 13-file archive")
    for filename, expected in CORE_SOURCE_SHA256.items():
        if digest(core / filename) != expected:
            raise RuntimeError("Recovered Core source identity mismatch: " + filename)
    manifest = root / "manifests" / "ATLAS_CANDIDATE_A_CANONICAL_FREEZE.json"
    if digest(manifest) != FREEZE_MANIFEST_SHA256:
        raise RuntimeError("Candidate A freeze manifest identity mismatch")
