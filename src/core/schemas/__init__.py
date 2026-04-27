"""Service-domain Pydantic schemas (not API schemas).

API request/response schemas live in src/api/schemas/. This package is
for closed schemas internal to core services — e.g. TransitionMetadata
which serializes into placement_status_history.metadata_json.
"""
