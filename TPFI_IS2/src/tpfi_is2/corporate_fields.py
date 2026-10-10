"""CorporateData field names from the TPFI consigna."""

from typing import Any

# DynamoDB attribute names for CorporateData tuples (Table 1 in consigna).
CORPORATE_DATA_FIELDS: frozenset[str] = frozenset(
    {
        "cp",
        "CUIT",
        "domicilio",
        "idreq",
        "idSeq",
        "localidad",
        "provincia",
        "sede",
        "seqID",
        "telefono",
        "web",
    }
)

REQUEST_META_KEYS: frozenset[str] = frozenset({"ACTION", "UUID", "SESSION_ID", "ID"})


def corporate_updates_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return CorporateData fields present in a client/server JSON payload."""
    return {key: value for key, value in payload.items() if key in CORPORATE_DATA_FIELDS}


def has_corporate_updates(payload: dict[str, Any]) -> bool:
    """True if payload carries at least one CorporateData field to write."""
    return bool(corporate_updates_from_payload(payload))
