"""GAP-03 Visual Verification — look-act-look cycle with perceptual hashing."""

from super_browser.verification.ax_diff import diff_ax_trees
from super_browser.verification.hasher import (
    HasherCache,
    compute_dhash,
    compute_hash,
    compute_phash,
)
from super_browser.verification.types import (
    ActionVerifiability,
    AXDiffResult,
    PerceptualHash,
    VerificationActionType,
    VerificationLevel,
    VerificationResult,
    VerificationSnapshot,
    VerifierConfig,
    VLMVerificationDetail,
)
from super_browser.verification.verifier import VisualVerifier

__all__ = [
    "ActionVerifiability",
    "AXDiffResult",
    "HasherCache",
    "PerceptualHash",
    "VerifierConfig",
    "VerificationActionType",
    "VerificationLevel",
    "VerificationResult",
    "VerificationSnapshot",
    "VisualVerifier",
    "VLMVerificationDetail",
    "compute_dhash",
    "compute_hash",
    "compute_phash",
    "diff_ax_trees",
]
