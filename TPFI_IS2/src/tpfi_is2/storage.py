"""Singleton access to CorporateData / CorporateLog (AWS or in-memory for tests)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

from tpfi_is2.corporate_fields import CORPORATE_DATA_FIELDS
from tpfi_is2.json_util import dynamodb_to_json


class CorporateDataGateway(Protocol):
    def get_record(self, record_id: str) -> dict[str, Any] | None: ...

    def merge_record(self, record_id: str, updates: dict[str, Any]) -> dict[str, Any]: ...

    def list_records(self) -> list[dict[str, Any]]: ...


class CorporateLogGateway(Protocol):
    def write_audit(
        self,
        *,
        cpu_uuid: str,
        session_id: str,
        action: str,
        record_id: str | None = None,
    ) -> None: ...


def _blank_record(record_id: str) -> dict[str, Any]:
    item = {field: "" for field in CORPORATE_DATA_FIELDS}
    item["id"] = record_id
    return item


def _merge_item(existing: dict[str, Any] | None, record_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    merged = _blank_record(record_id)
    if existing:
        merged.update({k: dynamodb_to_json(v) for k, v in existing.items() if k != "id"})
        merged["id"] = record_id
    for key, value in updates.items():
        if key in CORPORATE_DATA_FIELDS:
            merged[key] = value
    return merged


def _to_dynamo(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(value, float):
            out[key] = Decimal(str(value))
        else:
            out[key] = value
    return out


class MemoryCorporateDataGateway:
    """In-memory CorporateData (tests and local demos without AWS)."""

    _instance: MemoryCorporateDataGateway | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._records_lock = threading.Lock()

    @classmethod
    def instance(cls) -> MemoryCorporateDataGateway:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        with self._records_lock:
            item = self._records.get(record_id)
            return dict(item) if item else None

    def merge_record(self, record_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._records_lock:
            existing = self._records.get(record_id)
            merged = _merge_item(existing, record_id, updates)
            self._records[record_id] = merged
            return dict(merged)

    def list_records(self) -> list[dict[str, Any]]:
        with self._records_lock:
            return [dict(item) for item in self._records.values()]


class MemoryCorporateLogGateway:
    """In-memory CorporateLog."""

    _instance: MemoryCorporateLogGateway | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._entries_lock = threading.Lock()

    @classmethod
    def instance(cls) -> MemoryCorporateLogGateway:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def write_audit(
        self,
        *,
        cpu_uuid: str,
        session_id: str,
        action: str,
        record_id: str | None = None,
    ) -> None:
        entry = {
            "id": str(uuid.uuid4()),
            "CPUid": cpu_uuid,
            "sessionid": session_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if record_id is not None:
            entry["record_id"] = record_id
        with self._entries_lock:
            self._entries.append(entry)

    @property
    def entries(self) -> list[dict[str, Any]]:
        with self._entries_lock:
            return list(self._entries)


class AwsCorporateDataSingleton:
    """Singleton gateway to DynamoDB table CorporateData."""

    _instance: AwsCorporateDataSingleton | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        import boto3

        self._table = boto3.resource("dynamodb").Table("CorporateData")

    @classmethod
    def instance(cls) -> AwsCorporateDataSingleton:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"id": record_id})
        item = response.get("Item")
        return dynamodb_to_json(item) if item else None

    def merge_record(self, record_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_record(record_id)
        merged = _merge_item(existing, record_id, updates)
        self._table.put_item(Item=_to_dynamo(merged))
        return merged

    def list_records(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        response = self._table.scan()
        items.extend(dynamodb_to_json(i) for i in response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(dynamodb_to_json(i) for i in response.get("Items", []))
        return items


class AwsCorporateLogSingleton:
    """Singleton gateway to DynamoDB table CorporateLog."""

    _instance: AwsCorporateLogSingleton | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        import boto3

        self._table = boto3.resource("dynamodb").Table("CorporateLog")

    @classmethod
    def instance(cls) -> AwsCorporateLogSingleton:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def write_audit(
        self,
        *,
        cpu_uuid: str,
        session_id: str,
        action: str,
        record_id: str | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "CPUid": cpu_uuid,
            "sessionid": session_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if record_id is not None:
            entry["record_id"] = record_id
        self._table.put_item(Item=entry)


def default_data_gateway() -> CorporateDataGateway:
    import os

    if os.environ.get("TPFI_USE_MEMORY", "").lower() in ("1", "true", "yes"):
        return MemoryCorporateDataGateway.instance()
    return AwsCorporateDataSingleton.instance()


def default_log_gateway() -> CorporateLogGateway:
    import os

    if os.environ.get("TPFI_USE_MEMORY", "").lower() in ("1", "true", "yes"):
        return MemoryCorporateLogGateway.instance()
    return AwsCorporateLogSingleton.instance()
