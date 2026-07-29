#!/usr/bin/env python3
"""AI Supervisor V5 Connector alpha.

The connector runs inside Home Assistant. It builds a redacted project snapshot,
transfers it to the paired Windows Engine, receives reviewable proposals and can
apply a tightly limited multi-file YAML transaction under packages/ after an
explicit confirmation, a Home Assistant backup and a configuration check.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid

import websocket
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

APP_VERSION = "5.0.0-alpha4"
PORT = int(os.environ.get("PORT", "8099"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
STATIC_DIR = Path(__file__).resolve().parent / "static"
OPTIONS_PATH = DATA_DIR / "options.json"
SETTINGS_PATH = DATA_DIR / "v5_settings.json"
LAST_SNAPSHOT_PATH = DATA_DIR / "last_snapshot.json"
LAST_ENGINE_RESULT_PATH = DATA_DIR / "last_engine_result.json"
PROPOSALS_PATH = DATA_DIR / "proposals.json"
APPLY_HISTORY_PATH = DATA_DIR / "apply_history.json"
LOCAL_BACKUP_DIR = DATA_DIR / "file_backups"
HA_CONFIG_DIR = Path(os.environ.get("HOMEASSISTANT_CONFIG_DIR", "/homeassistant"))
HA_BASE_URL = os.environ.get("HA_BASE_URL", "http://supervisor/core/api").rstrip("/")
SUPERVISOR_BASE_URL = os.environ.get("SUPERVISOR_BASE_URL", "http://supervisor").rstrip("/")
HA_WS_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
MAX_BODY = 2 * 1024 * 1024
MAX_FILES = 600
MAX_FILE_BYTES = 320 * 1024
MAX_PROPOSALS = 40
MAX_HISTORY = 100
MAX_CHANGES = 3
ALLOWED_WRITE_ROOT = "packages/"
ALLOWED_WRITE_SUFFIXES = {".yaml", ".yml"}

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("ai_supervisor_v5_connector")
LOCK = threading.RLock()

ENTITY_RE = re.compile(r"\b[a-z_][a-z0-9_]*\.[a-z0-9_]+\b")
SECRET_PATTERNS = [
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"(?i)((?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|password|passwd|secret|token)\s*[=:]\s*)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"\b(?:sk|sess|pat|ghp)_[A-Za-z0-9_-]{12,}\b"), "<redacted-token>"),
]
EXCLUDED_NAMES = {
    "secrets.yaml",
    "home-assistant_v2.db",
    "home-assistant_v2.db-shm",
    "home-assistant_v2.db-wal",
    "home-assistant.log",
    "home-assistant.log.1",
    ".HA_VERSION",
}
EXCLUDED_PARTS = {
    ".storage",
    ".git",
    "backups",
    "backup",
    "media",
    "tts",
    "deps",
    "node_modules",
    "__pycache__",
}
TEXT_SUFFIXES = {".yaml", ".yml", ".json", ".py", ".js", ".md", ".txt"}
HIGH_RISK_DOMAINS = {
    "alarm_control_panel",
    "lock",
    "climate",
    "cover",
    "water_heater",
    "switch",
    "valve",
}


class DuplicateYamlKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: StrictLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise DuplicateYamlKeyError(f"Duplicate YAML key '{key}' at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


def _construct_unknown(loader: StrictLoader, tag_suffix: str, node: yaml.nodes.Node) -> Any:
    if isinstance(node, yaml.nodes.ScalarNode):
        return f"!{tag_suffix} {loader.construct_scalar(node)}"
    if isinstance(node, yaml.nodes.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.nodes.MappingNode):
        return loader.construct_mapping(node)
    return None


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
StrictLoader.add_multi_constructor("!", _construct_unknown)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    temp.replace(path)


def redact(text: str) -> str:
    value = re.sub(r"!secret\s+[^\s#]+", "!secret <redacted>", text)
    for pattern, replacement in SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def load_options() -> dict[str, Any]:
    raw = read_json(OPTIONS_PATH, {})
    return {
        "language": str(raw.get("language", "lt")),
        "engine_url": str(raw.get("engine_url", "")).strip().rstrip("/"),
        "engine_token": str(raw.get("engine_token", "")).strip(),
        "allow_package_writes": bool(raw.get("allow_package_writes", False)),
        "max_snapshot_mb": max(2, min(20, int(raw.get("max_snapshot_mb", 8)))),
    }


def load_settings() -> dict[str, Any]:
    options = load_options()
    saved = read_json(SETTINGS_PATH, {})
    return {
        "engine_url": str(saved.get("engine_url") or options["engine_url"]).strip().rstrip("/"),
        "engine_token": str(saved.get("engine_token") or options["engine_token"]).strip(),
        "paired_at": saved.get("paired_at"),
        "engine_name": saved.get("engine_name", ""),
    }


def public_settings() -> dict[str, Any]:
    value = load_settings()
    return {
        "engine_url": value["engine_url"],
        "engine_token_set": bool(value["engine_token"]),
        "paired_at": value.get("paired_at"),
        "engine_name": value.get("engine_name", ""),
        "allow_package_writes": load_options()["allow_package_writes"],
    }


class APIError(RuntimeError):
    pass


class HAClient:
    def request(self, method: str, path: str, payload: Any = None, *, timeout: int = 60, text: bool = False) -> Any:
        if not TOKEN:
            raise APIError("SUPERVISOR_TOKEN is unavailable")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{HA_BASE_URL}/{path.lstrip('/')}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
                "Accept": "text/plain" if text else "application/json",
                "User-Agent": f"ai-supervisor-v5-connector/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                if text:
                    return raw
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise APIError(f"Home Assistant API {method} /{path.lstrip('/')} HTTP {exc.code}: {body[:800]}") from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Home Assistant API unavailable: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise APIError(f"Invalid Home Assistant API response: {exc}") from exc

    def config(self) -> dict[str, Any]:
        value = self.request("GET", "/config")
        return value if isinstance(value, dict) else {}

    def states(self) -> list[dict[str, Any]]:
        value = self.request("GET", "/states")
        return value if isinstance(value, list) else []

    def check_config(self) -> dict[str, Any]:
        """Run and normalise a Home Assistant configuration check."""
        supervisor_error: Exception | None = None
        try:
            # SupervisorClient unwraps a successful {result: ok, data: ...}
            # response. An empty data object is therefore still a successful
            # configuration check.
            value = SupervisorClient().request("POST", "/core/check", {}, timeout=180)
            return {
                "result": "valid",
                "source": "supervisor/core/check",
                "message": "Home Assistant configuration is valid.",
                "details": value if isinstance(value, dict) else {"raw": value},
            }
        except APIError as exc:
            supervisor_error = exc
            LOGGER.warning("Supervisor configuration check failed, trying Core REST fallback: %s", exc)

        try:
            value = self.request("POST", "/config/core/check_config", None, timeout=180)
            if isinstance(value, dict):
                result = str(value.get("result", "")).lower()
                if result == "valid" or value.get("valid") is True:
                    return {
                        "result": "valid",
                        "source": "core-rest",
                        "message": "Home Assistant configuration is valid.",
                        "details": value,
                    }
                return {
                    "result": "invalid",
                    "source": "core-rest",
                    "message": str(value.get("errors") or value.get("message") or value),
                    "details": value,
                }
            return {"result": "unknown", "source": "core-rest", "raw": value}
        except APIError as core_exc:
            raise APIError(
                f"Configuration check failed via Supervisor ({supervisor_error}) "
                f"and Core REST API ({core_exc})"
            ) from core_exc


class HAWebSocketClient:
    """Small synchronous client for the Home Assistant WebSocket proxy."""

    def call_many(
        self,
        commands: list[tuple[str, dict[str, Any]]],
        *,
        timeout: int = 45,
    ) -> tuple[dict[str, Any], list[str]]:
        if not TOKEN:
            raise APIError("SUPERVISOR_TOKEN is unavailable")
        results: dict[str, Any] = {}
        warnings: list[str] = []
        sock = None
        try:
            sock = websocket.create_connection(
                HA_WS_URL,
                timeout=timeout,
                header=[f"User-Agent: ai-supervisor-v5-connector/{APP_VERSION}"],
            )
            hello = json.loads(sock.recv())
            if hello.get("type") != "auth_required":
                raise APIError(f"Unexpected WebSocket greeting: {hello}")
            sock.send(json.dumps({"type": "auth", "access_token": TOKEN}))
            auth = json.loads(sock.recv())
            if auth.get("type") != "auth_ok":
                raise APIError(str(auth.get("message") or "Home Assistant WebSocket authentication failed"))

            pending: dict[int, str] = {}
            for number, (name, command) in enumerate(commands, start=1):
                payload = {"id": number, **command}
                pending[number] = name
                sock.send(json.dumps(payload))

            while pending:
                message = json.loads(sock.recv())
                if message.get("type") != "result":
                    continue
                message_id = message.get("id")
                if message_id not in pending:
                    continue
                name = pending.pop(message_id)
                if message.get("success") is True:
                    results[name] = message.get("result")
                else:
                    error = message.get("error") or {}
                    detail = error.get("message") if isinstance(error, dict) else str(error)
                    warnings.append(f"WebSocket {name}: {detail or 'command failed'}")
        except (websocket.WebSocketException, OSError, ValueError, json.JSONDecodeError) as exc:
            raise APIError(f"Home Assistant WebSocket unavailable: {exc}") from exc
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        return results, warnings


class SupervisorClient:
    def request(self, method: str, path: str, payload: Any = None, *, timeout: int = 600) -> Any:
        if not TOKEN:
            raise APIError("SUPERVISOR_TOKEN is unavailable")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{SUPERVISOR_BASE_URL}/{path.lstrip('/')}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"ai-supervisor-v5-connector/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                value = json.loads(raw) if raw else {}
                if isinstance(value, dict) and value.get("result") == "error":
                    raise APIError(str(value.get("message") or value))
                if isinstance(value, dict) and value.get("result") == "ok" and "data" in value:
                    return value["data"]
                return value
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise APIError(f"Supervisor API HTTP {exc.code}: {body[:800]}") from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Supervisor API unavailable: {exc.reason}") from exc

    def backup(self, name: str) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(2):
            try:
                value = self.request(
                    "POST",
                    "/backups/new/partial",
                    {
                        "name": name[:120],
                        "homeassistant": True,
                        "homeassistant_exclude_database": True,
                        "compressed": True,
                        "location": None,
                        "background": False,
                    },
                )
                return value if isinstance(value, dict) else {"value": value}
            except APIError as exc:
                last = exc
                if attempt == 0 and any(word in str(exc).lower() for word in ("freeze", "another job", "already in progress")):
                    time.sleep(2)
                    continue
                break
        raise APIError(f"Backup failed; no file was changed. {last}")


class EngineClient:
    def __init__(self) -> None:
        settings = load_settings()
        self.url = settings["engine_url"]
        self.token = settings["engine_token"]

    def request(self, method: str, path: str, payload: Any = None, *, timeout: int = 360, auth: bool = True) -> dict[str, Any]:
        if not self.url:
            raise APIError("Windows Engine address is not configured")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"ai-supervisor-v5-connector/{APP_VERSION}",
        }
        if auth:
            if not self.token:
                raise APIError("Windows Engine is not paired")
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.url}/{path.lstrip('/')}", data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                value = json.loads(raw) if raw else {}
                if not isinstance(value, dict):
                    raise APIError("Engine returned a non-object response")
                return value
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise APIError(f"Windows Engine HTTP {exc.code}: {body[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Windows Engine unavailable: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise APIError(f"Invalid Windows Engine response: {exc}") from exc


def safe_relative(path: Path) -> str:
    return path.relative_to(HA_CONFIG_DIR).as_posix()


def include_file(path: Path) -> bool:
    try:
        relative = path.relative_to(HA_CONFIG_DIR)
    except ValueError:
        return False
    if path.name in EXCLUDED_NAMES or path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if any(part.startswith(".") for part in relative.parts):
        return False
    return True


def compact_state(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    keep = {}
    for key in ("friendly_name", "device_class", "unit_of_measurement", "id", "mode", "current_position", "temperature", "current_temperature"):
        if key in attrs:
            keep[key] = attrs[key]
    return {
        "entity_id": str(item.get("entity_id", "")),
        "state": str(item.get("state", "")),
        "attributes": keep,
        "last_changed": item.get("last_changed"),
    }


def compact_entity_registry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": str(item.get("entity_id", "")),
        "platform": item.get("platform"),
        "device_id": item.get("device_id"),
        "area_id": item.get("area_id"),
        "disabled_by": item.get("disabled_by"),
        "hidden_by": item.get("hidden_by"),
        "name": item.get("name"),
        "original_name": item.get("original_name"),
        "aliases": item.get("aliases") if isinstance(item.get("aliases"), list) else [],
        "labels": item.get("labels") if isinstance(item.get("labels"), list) else [],
    }


def compact_device_registry(item: dict[str, Any]) -> dict[str, Any]:
    # Deliberately omit identifiers, connections and serial numbers.
    return {
        "id": str(item.get("id", "")),
        "name": item.get("name"),
        "name_by_user": item.get("name_by_user"),
        "manufacturer": item.get("manufacturer"),
        "model": item.get("model"),
        "model_id": item.get("model_id"),
        "area_id": item.get("area_id"),
        "disabled_by": item.get("disabled_by"),
        "via_device_id": item.get("via_device_id"),
        "labels": item.get("labels") if isinstance(item.get("labels"), list) else [],
    }


def compact_area_registry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "area_id": str(item.get("area_id", "")),
        "name": item.get("name"),
        "floor_id": item.get("floor_id"),
        "aliases": item.get("aliases") if isinstance(item.get("aliases"), list) else [],
        "labels": item.get("labels") if isinstance(item.get("labels"), list) else [],
    }


def collect_home_assistant_inventory() -> dict[str, Any]:
    commands = [
        ("states", {"type": "get_states"}),
        ("config", {"type": "get_config"}),
        ("entity_registry", {"type": "config/entity_registry/list"}),
        ("device_registry", {"type": "config/device_registry/list"}),
        ("area_registry", {"type": "config/area_registry/list"}),
    ]
    results: dict[str, Any] = {}
    warnings: list[str] = []
    try:
        results, warnings = HAWebSocketClient().call_many(commands)
    except APIError as exc:
        warnings.append(str(exc))

    states_raw = results.get("states") if isinstance(results.get("states"), list) else []
    config = results.get("config") if isinstance(results.get("config"), dict) else {}
    entity_raw = results.get("entity_registry") if isinstance(results.get("entity_registry"), list) else []
    device_raw = results.get("device_registry") if isinstance(results.get("device_registry"), list) else []
    area_raw = results.get("area_registry") if isinstance(results.get("area_registry"), list) else []

    # REST remains a fallback for older or temporarily unavailable WebSocket APIs.
    client = HAClient()
    if not states_raw:
        try:
            states_raw = client.states()
        except APIError as exc:
            warnings.append(str(exc))
    if not config:
        try:
            config = client.config()
        except APIError as exc:
            warnings.append(str(exc))

    states = [compact_state(item) for item in states_raw if isinstance(item, dict)]
    entity_registry = [compact_entity_registry(item) for item in entity_raw if isinstance(item, dict) and item.get("entity_id")]
    device_registry = [compact_device_registry(item) for item in device_raw if isinstance(item, dict) and item.get("id")]
    area_registry = [compact_area_registry(item) for item in area_raw if isinstance(item, dict) and item.get("area_id")]
    inventory_status = {
        "states": "complete" if states else "unavailable",
        "entity_registry": "complete" if "entity_registry" in results else "unavailable",
        "device_registry": "complete" if "device_registry" in results else "unavailable",
        "area_registry": "complete" if "area_registry" in results else "unavailable",
    }
    if inventory_status["entity_registry"] == "complete":
        entity_validation = "complete"
    elif states:
        entity_validation = "partial"
    else:
        entity_validation = "unavailable"
    return {
        "states": states,
        "config": config,
        "entity_registry": entity_registry,
        "device_registry": device_registry,
        "area_registry": area_registry,
        "inventory_status": inventory_status,
        "entity_validation": entity_validation,
        "warnings": list(dict.fromkeys(warnings)),
    }


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "home_assistant_yaml"
    if suffix == ".json":
        return "json"
    if suffix in {".py", ".js"}:
        return "source_code"
    if suffix in {".md", ".txt"}:
        return "documentation"
    return "text"



def build_snapshot() -> dict[str, Any]:
    options = load_options()
    limit = options["max_snapshot_mb"] * 1024 * 1024
    files: list[dict[str, Any]] = []
    total = 0
    truncated = False
    for path in sorted(HA_CONFIG_DIR.rglob("*")):
        if not path.is_file() or not include_file(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            files.append({"path": safe_relative(path), "size": size, "omitted": "file_too_large"})
            continue
        if len(files) >= MAX_FILES or total + size > limit:
            truncated = True
            break
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        clean = redact(text)
        files.append(
            {
                "path": safe_relative(path),
                "size": size,
                "sha256": sha256_text(text),
                "content": clean,
                "kind": file_kind(path),
            }
        )
        total += len(clean.encode("utf-8"))
    inventory = collect_home_assistant_inventory()
    states = inventory["states"]
    config = inventory["config"]
    api_warnings = inventory["warnings"]
    snapshot = {
        "schema_version": 2,
        "snapshot_id": str(uuid.uuid4()),
        "created_at": utc_now(),
        "connector_version": APP_VERSION,
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
        },
        "files": files,
        "file_count": len(files),
        "payload_bytes": total,
        "truncated": truncated,
        "states": states,
        "state_count": len(states),
        "entity_registry": inventory["entity_registry"],
        "entity_registry_count": len(inventory["entity_registry"]),
        "device_registry": inventory["device_registry"],
        "device_registry_count": len(inventory["device_registry"]),
        "area_registry": inventory["area_registry"],
        "area_registry_count": len(inventory["area_registry"]),
        "inventory_status": inventory["inventory_status"],
        "entity_validation": inventory["entity_validation"],
        "api_warnings": api_warnings,
        "policy": {
            "secrets_excluded": True,
            "storage_excluded": True,
            "database_excluded": True,
            "write_scope": "packages/*.yaml only",
        },
    }
    with LOCK:
        write_json(LAST_SNAPSHOT_PATH, snapshot)
    return snapshot


def pair_engine(incoming: dict[str, Any]) -> dict[str, Any]:
    url = str(incoming.get("engine_url", "")).strip().rstrip("/")
    code = str(incoming.get("pairing_code", "")).strip()
    if not re.match(r"^https?://[^\s]+$", url):
        raise ValueError("Enter a valid Engine address, for example http://192.168.1.50:8765")
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("Pairing code must contain 6 digits")
    saved = read_json(SETTINGS_PATH, {})
    write_json(SETTINGS_PATH, {**saved, "engine_url": url, "engine_token": ""})
    response = EngineClient().request(
        "POST",
        "/v1/pair",
        {"code": code, "connector_name": "Home Assistant AI Supervisor V5", "connector_version": APP_VERSION},
        auth=False,
        timeout=30,
    )
    token = str(response.get("token", ""))
    if len(token) < 24:
        raise APIError("Engine did not return a valid pairing token")
    settings = {
        "engine_url": url,
        "engine_token": token,
        "paired_at": utc_now(),
        "engine_name": str(response.get("engine_name", "Windows Engine")),
    }
    write_json(SETTINGS_PATH, settings)
    return {"ok": True, **public_settings()}


def engine_health() -> dict[str, Any]:
    try:
        return EngineClient().request("GET", "/health", timeout=8, auth=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def sync_snapshot() -> dict[str, Any]:
    snapshot = build_snapshot()
    result = EngineClient().request("POST", "/v1/snapshot", snapshot, timeout=180)
    with LOCK:
        write_json(LAST_ENGINE_RESULT_PATH, result)
    return result


def store_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    proposal = dict(proposal)
    proposal.setdefault("proposal_id", str(uuid.uuid4()))
    proposal.setdefault("created_at", utc_now())
    proposal["connector_validation"] = validate_proposal(proposal)
    with LOCK:
        items = read_json(PROPOSALS_PATH, [])
        if not isinstance(items, list):
            items = []
        items.insert(0, proposal)
        write_json(PROPOSALS_PATH, items[:MAX_PROPOSALS])
    return proposal


def analyse_process(query: str) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("Describe the process or problem to analyse")
    if len(query) > 4000:
        raise ValueError("Query is too long")
    snapshot = read_json(LAST_SNAPSHOT_PATH, None)
    if not isinstance(snapshot, dict):
        sync_snapshot()
    result = EngineClient().request(
        "POST", "/v1/process/analyse", {"query": query, "language": load_options()["language"]}, timeout=420
    )
    return store_proposal(result)


def normalise_target_path(value: str) -> tuple[str, Path]:
    raw = value.strip().replace("\\", "/").lstrip("/")
    if raw.startswith("homeassistant/"):
        raw = raw[len("homeassistant/"):]
    if raw.startswith("config/"):
        raw = raw[len("config/"):]
    candidate = (HA_CONFIG_DIR / raw).resolve()
    root = HA_CONFIG_DIR.resolve()
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("Change path escapes Home Assistant configuration") from exc
    if not relative.startswith(ALLOWED_WRITE_ROOT):
        raise ValueError("This release can write only files inside packages/")
    if candidate.suffix.lower() not in ALLOWED_WRITE_SUFFIXES:
        raise ValueError("Only .yaml and .yml files are writable")
    if candidate.name.lower() == "secrets.yaml" or ".storage" in candidate.parts:
        raise ValueError("Protected Home Assistant files cannot be changed")
    return relative, candidate


def strict_yaml_validate(text: str) -> None:
    if not text.strip():
        raise ValueError("Proposed YAML is empty")
    try:
        yaml.load(text, Loader=StrictLoader)
    except (yaml.YAMLError, DuplicateYamlKeyError) as exc:
        raise ValueError(f"Invalid proposed YAML: {exc}") from exc


def risk_from_changes(changes: list[dict[str, Any]]) -> str:
    entities: set[str] = set()
    for change in changes:
        entities.update(ENTITY_RE.findall(str(change.get("new_content", ""))))
    domains = {entity.split(".", 1)[0] for entity in entities}
    return "high" if domains & HIGH_RISK_DOMAINS else "medium"


def validate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    changes = proposal.get("changes")
    validated: list[dict[str, Any]] = []
    if not isinstance(changes, list) or not changes:
        errors.append("Engine did not provide file changes")
        changes = []
    if len(changes) > MAX_CHANGES:
        errors.append(f"This release allows at most {MAX_CHANGES} files per transaction")
    for item in changes[:MAX_CHANGES]:
        if not isinstance(item, dict):
            errors.append("Invalid change entry")
            continue
        try:
            relative, path = normalise_target_path(str(item.get("path", "")))
            new_content = str(item.get("new_content", ""))
            strict_yaml_validate(new_content)
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            expected = str(item.get("base_sha256", ""))
            current_hash = sha256_text(current)
            if expected and expected != current_hash:
                errors.append(f"{relative}: file changed after analysis")
            validated.append(
                {
                    "path": relative,
                    "current_sha256": current_hash,
                    "new_sha256": sha256_text(new_content),
                    "exists": path.exists(),
                }
            )
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            errors.append(str(exc))
    risk = risk_from_changes(changes if isinstance(changes, list) else [])
    return {
        "valid": not errors and bool(validated),
        "errors": errors,
        "changes": validated,
        "connector_risk": risk,
        "write_scope": "packages/ only",
    }


def find_proposal(proposal_id: str) -> dict[str, Any]:
    items = read_json(PROPOSALS_PATH, [])
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and item.get("proposal_id") == proposal_id:
            return item
    raise ValueError("Proposal not found")


def update_proposal(proposal_id: str, update: dict[str, Any]) -> None:
    items = read_json(PROPOSALS_PATH, [])
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict) and item.get("proposal_id") == proposal_id:
            item.update(update)
            break
    write_json(PROPOSALS_PATH, items[:MAX_PROPOSALS])


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".ai-supervisor.tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def apply_proposal(incoming: dict[str, Any]) -> dict[str, Any]:
    if not load_options()["allow_package_writes"]:
        raise ValueError("Enable allow_package_writes in the App Configuration tab first")
    proposal_id = str(incoming.get("proposal_id", "")).strip()
    confirmation = str(incoming.get("confirmation", "")).strip()
    expected = f"PATVIRTINU {proposal_id[:8].upper()}"
    if confirmation != expected:
        raise ValueError(f"Type exactly: {expected}")
    proposal = find_proposal(proposal_id)
    validation = validate_proposal(proposal)
    if not validation["valid"]:
        raise ValueError("Proposal is blocked: " + "; ".join(validation["errors"]))
    if proposal.get("applied_at"):
        raise ValueError("Proposal has already been applied")
    changes = proposal.get("changes", [])
    transaction_id = str(uuid.uuid4())
    transaction_dir = LOCAL_BACKUP_DIR / transaction_id
    transaction_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[dict[str, Any]] = []
    for item in changes:
        relative, path = normalise_target_path(str(item.get("path", "")))
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        base_hash = str(item.get("base_sha256", ""))
        if base_hash and base_hash != sha256_text(current):
            raise ValueError(f"{relative} changed after the proposal was generated")
        new_content = str(item.get("new_content", ""))
        strict_yaml_validate(new_content)
        local_copy = transaction_dir / relative
        local_copy.parent.mkdir(parents=True, exist_ok=True)
        local_copy.write_text(current, encoding="utf-8")
        prepared.append(
            {
                "relative": relative,
                "path": path,
                "current": current,
                "new": new_content,
                "existed": path.exists(),
            }
        )
    backup = SupervisorClient().backup(f"AI Supervisor V5 before {proposal_id[:8]}")
    try:
        for item in prepared:
            atomic_write(item["path"], item["new"])
        check = HAClient().check_config()
        valid = check.get("result") == "valid" or check.get("result") is None and not check.get("errors")
        if not valid:
            raise APIError(f"Home Assistant configuration check failed: {check}")
    except Exception as exc:
        for item in prepared:
            if item["existed"]:
                atomic_write(item["path"], item["current"])
            else:
                item["path"].unlink(missing_ok=True)
        rollback_check = HAClient().check_config()
        record = {
            "transaction_id": transaction_id,
            "proposal_id": proposal_id,
            "status": "rolled_back",
            "created_at": utc_now(),
            "error": str(exc),
            "backup": backup,
            "rollback_check": rollback_check,
        }
        add_history(record)
        update_proposal(proposal_id, {"last_apply_error": str(exc), "last_apply_at": utc_now()})
        raise ValueError("Change failed and files were restored. " + str(exc)) from exc
    result = {
        "transaction_id": transaction_id,
        "proposal_id": proposal_id,
        "status": "applied",
        "applied_at": utc_now(),
        "backup": backup,
        "configuration_check": check,
        "files": [item["relative"] for item in prepared],
        "restart_performed": False,
        "message": "Files were written and configuration is valid. Home Assistant was not restarted.",
    }
    add_history(result)
    update_proposal(proposal_id, {"applied_at": result["applied_at"], "transaction_id": transaction_id})
    return result


def add_history(record: dict[str, Any]) -> None:
    with LOCK:
        items = read_json(APPLY_HISTORY_PATH, [])
        if not isinstance(items, list):
            items = []
        items.insert(0, record)
        write_json(APPLY_HISTORY_PATH, items[:MAX_HISTORY])


def status() -> dict[str, Any]:
    snapshot = read_json(LAST_SNAPSHOT_PATH, {})
    proposals = read_json(PROPOSALS_PATH, [])
    health = engine_health() if load_settings()["engine_url"] else {"ok": False, "error": "not_configured"}
    return {
        "ok": True,
        "connector_version": APP_VERSION,
        "settings": public_settings(),
        "engine": health,
        "last_snapshot": {
            "snapshot_id": snapshot.get("snapshot_id"),
            "created_at": snapshot.get("created_at"),
            "file_count": snapshot.get("file_count", 0),
            "state_count": snapshot.get("state_count", 0),
            "entity_registry_count": snapshot.get("entity_registry_count", 0),
            "device_registry_count": snapshot.get("device_registry_count", 0),
            "area_registry_count": snapshot.get("area_registry_count", 0),
            "entity_validation": snapshot.get("entity_validation", "unavailable"),
            "inventory_status": snapshot.get("inventory_status", {}),
            "truncated": snapshot.get("truncated", False),
            "api_warnings": snapshot.get("api_warnings", []),
        },
        "proposal_count": len(proposals) if isinstance(proposals, list) else 0,
        "write_policy": {
            "enabled": load_options()["allow_package_writes"],
            "scope": "packages/*.yaml",
            "backup_required": True,
            "confirmation_required": True,
            "configuration_check_required": True,
            "automatic_restart": False,
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AISupervisorV5Connector/" + APP_VERSION

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)

    def json_response(self, value: Any, status_code: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def file_response(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("Request is too large")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/health":
                self.json_response({"ok": True, "version": APP_VERSION})
            elif path in {"/", "/index.html"}:
                self.file_response(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            elif path == "/api/status":
                self.json_response(status())
            elif path == "/api/settings":
                self.json_response(public_settings())
            elif path == "/api/proposals":
                self.json_response(read_json(PROPOSALS_PATH, []))
            elif path == "/api/history":
                self.json_response(read_json(APPLY_HISTORY_PATH, []))
            else:
                self.send_error(404)
        except Exception as exc:
            LOGGER.error("GET %s failed: %s\n%s", path, exc, traceback.format_exc())
            self.json_response({"ok": False, "error": str(exc)}, 500)

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        try:
            incoming = self.body()
            if path == "/api/pair":
                result = pair_engine(incoming)
            elif path == "/api/sync":
                result = sync_snapshot()
            elif path == "/api/analyse":
                result = analyse_process(str(incoming.get("query", "")))
            elif path == "/api/apply":
                result = apply_proposal(incoming)
            elif path == "/api/check-config":
                result = HAClient().check_config()
            else:
                self.send_error(404)
                return
            self.json_response({"ok": True, "result": result})
        except (ValueError, APIError, json.JSONDecodeError) as exc:
            LOGGER.warning("POST %s rejected: %s", path, exc)
            self.json_response({"ok": False, "error": str(exc)}, 400)
        except Exception as exc:
            LOGGER.error("POST %s failed: %s\n%s", path, exc, traceback.format_exc())
            self.json_response({"ok": False, "error": str(exc)}, 500)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    LOGGER.info("AI Supervisor V5 Connector %s listening on port %s", APP_VERSION, PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
