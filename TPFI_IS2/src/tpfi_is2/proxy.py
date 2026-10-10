"""Proxy for CorporateData access (audit + validation before DynamoDB)."""

from __future__ import annotations

from typing import Any

from tpfi_is2.corporate_fields import corporate_updates_from_payload
from tpfi_is2.storage import CorporateDataGateway, CorporateLogGateway


class CorporateDataProxy:
    """Proxy pattern: every operation is logged and validated before hitting storage."""

    def __init__(
        self,
        data: CorporateDataGateway | None = None,
        log: CorporateLogGateway | None = None,
    ) -> None:
        from tpfi_is2.storage import default_data_gateway, default_log_gateway

        self._data = data if data is not None else default_data_gateway()
        self._log = log if log is not None else default_log_gateway()

    def get(self, *, cpu_uuid: str, session_id: str, record_id: str) -> dict[str, Any]:
        self._log.write_audit(cpu_uuid=cpu_uuid, session_id=session_id, action="get", record_id=record_id)
        item = self._data.get_record(record_id)
        if item is None:
            return {"Error": f"Record not found: {record_id}"}
        return item

    def list_all(self, *, cpu_uuid: str, session_id: str) -> list[dict[str, Any]] | dict[str, Any]:
        self._log.write_audit(cpu_uuid=cpu_uuid, session_id=session_id, action="list")
        try:
            return self._data.list_records()
        except OSError as exc:
            return {"Error": str(exc)}

    def set_fields(self, *, cpu_uuid: str, session_id: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        updates = corporate_updates_from_payload(payload)
        self._log.write_audit(cpu_uuid=cpu_uuid, session_id=session_id, action="set", record_id=record_id)
        try:
            return self._data.merge_record(record_id, updates)
        except OSError as exc:
            return {"Error": str(exc)}
