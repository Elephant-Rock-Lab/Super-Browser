"""Detection vector registry.

All vectors are registered here for discovery by the harness.
"""

from adversarial3.vectors.automation import AUTOMATION_VECTORS
from adversarial3.vectors.behavioral import BEHAVIORAL_VECTORS
from adversarial3.vectors.controlled import CONTROLLED_VECTORS
from adversarial3.vectors.ejector import EJECTOR_VECTORS
from adversarial3.vectors.fingerprint import FINGERPRINT_VECTORS
from adversarial3.vectors.network import NETWORK_VECTORS

# Core vectors — always registered, evaluated via Vector protocol
ALL_VECTORS = (
    FINGERPRINT_VECTORS
    + AUTOMATION_VECTORS
    + EJECTOR_VECTORS
    + BEHAVIORAL_VECTORS
    + NETWORK_VECTORS
    + CONTROLLED_VECTORS
)

VECTORS_BY_TIER: dict = {}
for v in ALL_VECTORS:
    VECTORS_BY_TIER.setdefault(v.tier, []).append(v)
