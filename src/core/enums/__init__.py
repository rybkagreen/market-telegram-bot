"""Cross-cutting service-domain enums.

Enums tied to a specific model live alongside that model
(e.g. PlacementStatus в src/db/models/placement_request.py).
This package is for enums spanning multiple services / layers,
e.g. PlacementGate which is referenced from gate-checkers,
transition service, FastAPI routers, and the Mini App contract.
"""
