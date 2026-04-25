"""
ERID marker constants.

`STUB-ERID-` describes the *provider type* (synthetic, no real ОРД),
NOT the placement mode. Do not rename to `TEST-ERID-` — placement test-mode
is a separate concept (Phase 5), and the two must stay orthogonal.
"""

ERID_STUB_PREFIX = "STUB-ERID-"
