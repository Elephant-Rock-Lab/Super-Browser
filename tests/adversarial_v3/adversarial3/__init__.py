"""Adversarial Capability Assessment Suite v3.

A unified, pluggable framework for measuring browser automation
stealth capabilities against detection vectors.

Key improvements over v1:
- Unified Vector/Target abstraction (no artificial split)
- Async-first, dependency-injected browser backend
- Plugin architecture for vectors, reporters, and engines
- Built-in controlled server + live target support
- Comprehensive offline testability
"""

__version__ = "3.0.0"
