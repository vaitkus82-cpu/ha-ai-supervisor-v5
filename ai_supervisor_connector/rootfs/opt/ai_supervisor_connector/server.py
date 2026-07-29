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

APP_VERSION = "5.0.0-alpha10"
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
CONTROL_DOMAINS = {
    "alarm_control_panel", "climate", "cover", "fan", "light", "lock",
    "media_player", "select", "switch", "vacuum", "valve", "water_heater",
}
HELPER_DOMAINS = {
    "counter", "group", "input_boolean", "input_button", "input_datetime",
    "input_number", "input_select", "input_text", "schedule", "timer",
}
COMPONENT_DOMAINS = HELPER_DOMAINS | {"automation", "script", "scene", "template"}

TOP_LEVEL_DOMAIN_RE = re.compile(r"^(?P<key>[a-z_][a-z0-9_]*)\s*:\s*(?:#.*)?$")
MAPPING_CHILD_RE = re.compile(r"^(?P<indent>\s+)(?P<key>[A-Za-z0-9_\-]+)\s*:\s*(?:#.*)?$")
RAW_ID_RE = re.compile(r"(?m)^\s*(?:-\s*)?id\s*:\s*['\"]?([^'\"#\n]+)")
RAW_ALIAS_RE = re.compile(r"(?m)^\s*(?:-\s*)?(?:alias|name|friendly_name)\s*:\s*['\"]?([^'\"#\n]+)")
RAW_SERVICE_RE = re.compile(r"(?m)^\s*(?:-\s*)?(?:service|action)\s*:\s*['\"]?([a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*)")
RAW_DEVICE_ID_RE = re.compile(r"(?m)^\s*device_id\s*:\s*['\"]?([A-Za-z0-9_-]+)")
RAW_AREA_ID_RE = re.compile(r"(?m)^\s*area_id\s*:\s*['\"]?([A-Za-z0-9_-]+)")


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



def _iter_entity_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(ENTITY_RE.findall(value))
    elif isinstance(value, dict):
        for child in value.values():
            refs.update(_iter_entity_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_iter_entity_refs(child))
    return refs


def _component_entity_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(ENTITY_RE.findall(value))
    elif isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in {"service", "action"} and isinstance(child, str):
                # Direct script/scene service calls identify a real component.
                if re.fullmatch(r"(?:script|scene)\.[a-z0-9_]+", child) and child not in {
                    "script.turn_on", "script.turn_off", "script.toggle", "script.reload",
                    "scene.turn_on", "scene.reload", "scene.apply", "scene.create",
                }:
                    refs.add(child)
                continue
            refs.update(_component_entity_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_component_entity_refs(child))
    return refs


def _iter_named_ids(value: Any, key_name: str) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) == key_name:
                if isinstance(child, str):
                    found.add(child)
                elif isinstance(child, list):
                    found.update(str(item) for item in child if isinstance(item, (str, int)))
            found.update(_iter_named_ids(child, key_name))
    elif isinstance(value, list):
        for child in value:
            found.update(_iter_named_ids(child, key_name))
    return found


def _service_actions(value: Any) -> set[str]:
    actions: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in {"service", "action"} and isinstance(child, str) and re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*", child):
                actions.add(child)
            actions.update(_service_actions(child))
    elif isinstance(value, list):
        for child in value:
            actions.update(_service_actions(child))
    return actions


def _control_targets(value: Any) -> set[str]:
    targets: set[str] = set()
    if isinstance(value, dict):
        service_value = value.get("service") or value.get("action")
        service_domain = str(service_value).split(".", 1)[0] if isinstance(service_value, str) and "." in service_value else ""
        if service_domain in CONTROL_DOMAINS:
            candidate = value.get("target")
            if candidate is not None:
                targets.update(entity for entity in _iter_entity_refs(candidate) if entity.split(".", 1)[0] in CONTROL_DOMAINS)
            candidate = value.get("entity_id")
            if candidate is not None:
                targets.update(entity for entity in _iter_entity_refs(candidate) if entity.split(".", 1)[0] in CONTROL_DOMAINS)
            data = value.get("data")
            if data is not None:
                targets.update(entity for entity in _iter_entity_refs(data) if entity.split(".", 1)[0] in CONTROL_DOMAINS)
        for child in value.values():
            targets.update(_control_targets(child))
    elif isinstance(value, list):
        for child in value:
            targets.update(_control_targets(child))
    return targets



def _raw_component_record(kind: str, key: str, block: str, path: str, line_start: int, line_end: int, index: int = 0) -> dict[str, Any]:
    """Create a component from raw YAML text.

    This is intentionally conservative: it records exact entity IDs and basic
    component metadata without trying to execute or fully interpret Jinja.
    It is used both as a supplement to parsed YAML and as a fallback when a
    valid Home Assistant package contains tags or syntax PyYAML cannot model.
    """
    clean_key = str(key or index)
    alias_match = RAW_ALIAS_RE.search(block)
    automation_match = RAW_ID_RE.search(block)
    alias = alias_match.group(1).strip() if alias_match else clean_key
    component_entity = f"{kind}.{clean_key}" if kind in HELPER_DOMAINS | {"script", "scene"} and clean_key else ""
    services = sorted(set(RAW_SERVICE_RE.findall(block)))[:300]
    reference_set = set(ENTITY_RE.findall(block)) - set(services)
    for service in services:
        if re.fullmatch(r"(?:script|scene)\.[a-z0-9_]+", service) and service not in {
            "script.turn_on", "script.turn_off", "script.toggle", "script.reload",
            "scene.turn_on", "scene.reload", "scene.apply", "scene.create",
        }:
            reference_set.add(service)
    references = sorted(reference_set)[:2000]
    control_service_domains = {
        action.split(".", 1)[0]
        for action in services
        if "." in action and action.split(".", 1)[0] in CONTROL_DOMAINS
    }
    control_targets: set[str] = set()
    if control_service_domains:
        for line in block.splitlines():
            lowered = line.lower()
            if any(token in lowered for token in ("entity_id:", "target:", "cover_entity:")):
                for entity in ENTITY_RE.findall(line):
                    if entity.split(".", 1)[0] in CONTROL_DOMAINS:
                        control_targets.add(entity)
    return {
        "component_id": f"{path}:{kind}:{clean_key or index}",
        "kind": kind,
        "key": clean_key,
        "entity_id": component_entity,
        "automation_id": automation_match.group(1).strip() if kind == "automation" and automation_match else "",
        "name": str(alias or clean_key)[:240],
        "file": path,
        "references": references,
        "control_targets": sorted(control_targets)[:500],
        "services": services,
        "device_ids": sorted(set(RAW_DEVICE_ID_RE.findall(block)))[:200],
        "area_ids": sorted(set(RAW_AREA_ID_RE.findall(block)))[:100],
        "line_start": line_start,
        "line_end": line_end,
        "catalog_source": "raw_yaml_text",
    }


def _section_child_blocks(lines: list[str], section_start: int, section_end: int, kind: str) -> list[tuple[str, int, int, str]]:
    """Split a top-level package domain into named/list child blocks."""
    body_indices = [
        index for index in range(section_start + 1, section_end)
        if lines[index].strip() and not lines[index].lstrip().startswith("#")
    ]
    if not body_indices:
        return []
    base_indent = min(len(lines[index]) - len(lines[index].lstrip(" ")) for index in body_indices)
    starts: list[tuple[int, str]] = []
    for index in body_indices:
        raw = lines[index]
        indent = len(raw) - len(raw.lstrip(" "))
        if indent != base_indent:
            continue
        stripped = raw.strip()
        if stripped.startswith("-"):
            if kind not in {"automation", "scene", "template"}:
                continue
            inline_id = re.search(r"\bid\s*:\s*['\"]?([^'\"#]+)", stripped)
            inline_alias = re.search(r"\b(?:alias|name)\s*:\s*['\"]?([^'\"#]+)", stripped)
            key = (inline_id or inline_alias).group(1).strip() if (inline_id or inline_alias) else str(len(starts))
            starts.append((index, key))
            continue
        match = MAPPING_CHILD_RE.match(raw)
        if match:
            starts.append((index, match.group("key")))
    blocks: list[tuple[str, int, int, str]] = []
    for pos, (start, key) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else section_end
        block = "\n".join(lines[start:end])
        if kind == "automation":
            id_match = RAW_ID_RE.search(block)
            alias_match = RAW_ALIAS_RE.search(block)
            if id_match:
                key = id_match.group(1).strip()
            elif key.isdigit() and alias_match:
                key = alias_match.group(1).strip()
        elif kind == "scene":
            id_match = RAW_ID_RE.search(block)
            alias_match = RAW_ALIAS_RE.search(block)
            if id_match:
                key = id_match.group(1).strip()
            elif key.isdigit() and alias_match:
                key = alias_match.group(1).strip()
        blocks.append((key, start + 1, end, block))
    return blocks


def collect_text_component_catalog(path: str, text: str) -> list[dict[str, Any]]:
    """Extract package components directly from YAML text and Jinja strings."""
    lines = text.splitlines()
    top_sections: list[tuple[int, str]] = []
    for index, raw in enumerate(lines):
        if raw.startswith((" ", "\t")) or not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = TOP_LEVEL_DOMAIN_RE.match(raw.strip())
        if match and match.group("key") in COMPONENT_DOMAINS:
            top_sections.append((index, match.group("key")))
    components: list[dict[str, Any]] = []
    for pos, (start, kind) in enumerate(top_sections):
        end = top_sections[pos + 1][0] if pos + 1 < len(top_sections) else len(lines)
        for index, (key, line_start, line_end, block) in enumerate(_section_child_blocks(lines, start, end, kind)):
            components.append(_raw_component_record(kind, key, block, path, line_start, line_end, index))
    return components


def _merge_component(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key in ("references", "control_targets", "services", "device_ids", "area_ids"):
        merged[key] = sorted(set(existing.get(key, []) or []) | set(incoming.get(key, []) or []))
    for key in ("automation_id", "entity_id", "name"):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]
    if incoming.get("line_start"):
        merged.setdefault("line_start", incoming.get("line_start"))
        merged.setdefault("line_end", incoming.get("line_end"))
    merged["catalog_source"] = "parsed_plus_raw" if existing.get("catalog_source") != "raw_yaml_text" else incoming.get("catalog_source", "raw_yaml_text")
    return merged


def _component_record(kind: str, key: str, payload: Any, path: str, index: int = 0) -> dict[str, Any]:
    mapping = payload if isinstance(payload, dict) else {}
    alias = mapping.get("alias") or mapping.get("name") or mapping.get("friendly_name") or key
    component_entity = ""
    if kind in HELPER_DOMAINS | {"script", "scene"} and key:
        component_entity = f"{kind}.{key}"
    component_id = f"{path}:{kind}:{key or index}"
    return {
        "component_id": component_id,
        "kind": kind,
        "key": key,
        "entity_id": component_entity,
        "automation_id": str(mapping.get("id", "")) if kind == "automation" else "",
        "name": str(alias or component_id)[:240],
        "file": path,
        "references": sorted(_component_entity_refs(payload))[:1000],
        "control_targets": sorted(_control_targets(payload))[:500],
        "services": sorted(_service_actions(payload))[:300],
        "device_ids": sorted(_iter_named_ids(payload, "device_id"))[:200],
        "area_ids": sorted(_iter_named_ids(payload, "area_id"))[:100],
        "catalog_source": "parsed_yaml",
    }


def _looks_like_automation(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    keys = {str(key) for key in value}
    has_trigger = bool(keys & {"trigger", "triggers"})
    has_action = bool(keys & {"action", "actions"})
    return (has_trigger and has_action) or (has_action and bool(keys & {"condition", "conditions", "mode", "id"}))


def _looks_like_script(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    keys = {str(key) for key in value}
    return "sequence" in keys and not bool(keys & {"trigger", "triggers"})


def _looks_like_scene(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    keys = {str(key) for key in value}
    return "entities" in keys and bool(keys & {"name", "id"}) and not _looks_like_automation(value)


def _path_component_hint(path: str) -> str:
    lowered = path.lower().replace("\\", "/")
    parts = set(Path(lowered).parts)
    name = Path(lowered).name
    if "automation" in parts or "automations" in parts or "automation" in name:
        return "automation"
    if "script" in parts or "scripts" in parts or "script" in name:
        return "script"
    if "scene" in parts or "scenes" in parts or "scene" in name:
        return "scene"
    return ""


def _append_inferred_component(
    components: list[dict[str, Any]],
    payload: Any,
    path: str,
    key: str,
    index: int,
    hint: str = "",
) -> bool:
    kind = ""
    if _looks_like_automation(payload):
        kind = "automation"
    elif _looks_like_script(payload):
        kind = "script"
    elif _looks_like_scene(payload):
        kind = "scene"
    elif hint in {"automation", "script", "scene"} and isinstance(payload, dict):
        # Included files often omit the domain wrapper. Only accept a path hint
        # when the entry is a mapping; the shape checks above remain preferred.
        kind = hint
    if not kind:
        return False
    key_text = str(key or "")
    if key_text and not key_text.isdigit():
        inferred_key = key_text
    elif isinstance(payload, dict):
        inferred_key = str(payload.get("id") or payload.get("alias") or payload.get("name") or key or index)
    else:
        inferred_key = str(key or index)
    components.append(_component_record(kind, inferred_key, payload, path, index))
    return True


def collect_component_catalog(files: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Build a component catalogue from package and include-style YAML files.

    Home Assistant allows automations and scripts to be split into arbitrary
    files via !include / !include_dir_* directives. Those included files often
    have a root list or a root mapping without an ``automation:`` / ``script:``
    wrapper. Alpha10 recognises those shapes and supplements them with exact raw-text Jinja references instead of only relying on standard
    filenames such as automations.yaml and scripts.yaml.
    """
    components: list[dict[str, Any]] = []
    warnings: list[str] = []
    for item in files:
        if item.get("kind") != "home_assistant_yaml" or not isinstance(item.get("content"), str):
            continue
        path = str(item.get("path", ""))
        text = str(item.get("content", ""))
        raw_components = collect_text_component_catalog(path, text)
        file_components: list[dict[str, Any]] = []
        try:
            data = yaml.load(text, Loader=StrictLoader)
        except Exception as exc:
            warnings.append(f"Component catalog used raw-text fallback for {path}: {exc}")
            data = None

        lower_name = Path(path).name.lower()
        hint = _path_component_hint(path)

        # Root lists are common in automations include directories.
        if isinstance(data, list):
            for index, entry in enumerate(data):
                if not isinstance(entry, dict):
                    continue
                if lower_name == "scenes.yaml":
                    key = str(entry.get("id") or entry.get("name") or index)
                    file_components.append(_component_record("scene", key, entry, path, index))
                elif lower_name == "automations.yaml":
                    key = str(entry.get("id") or entry.get("alias") or index)
                    file_components.append(_component_record("automation", key, entry, path, index))
                else:
                    _append_inferred_component(file_components, entry, path, str(index), index, hint)
            merged_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
            for component in file_components + raw_components:
                key = (str(component.get("file")), str(component.get("kind")), str(component.get("key")))
                merged_by_key[key] = _merge_component(merged_by_key[key], component) if key in merged_by_key else component
            components.extend(merged_by_key.values())
            continue

        if not isinstance(data, dict):
            components.extend(raw_components)
            continue

        # A single included automation/script may itself be the root mapping.
        # Do not use the path hint here: a scripts directory commonly contains
        # a mapping of multiple named scripts rather than one script body.
        if _append_inferred_component(file_components, data, path, Path(path).stem, 0, ""):
            merged_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
            for component in file_components + raw_components:
                key = (str(component.get("file")), str(component.get("kind")), str(component.get("key")))
                merged_by_key[key] = _merge_component(merged_by_key[key], component) if key in merged_by_key else component
            components.extend(merged_by_key.values())
            continue

        handled_keys: set[str] = set()
        for raw_domain, payload in data.items():
            domain = str(raw_domain)
            if domain == "automation":
                handled_keys.add(domain)
                if isinstance(payload, list):
                    entries = [(str(index), entry, index) for index, entry in enumerate(payload)]
                elif isinstance(payload, dict):
                    entries = [(str(key), entry, index) for index, (key, entry) in enumerate(payload.items())]
                else:
                    entries = []
                for key, entry, index in entries:
                    if isinstance(entry, dict):
                        component_key = str(entry.get("id") or entry.get("alias") or key or index)
                        file_components.append(_component_record("automation", component_key, entry, path, index))
            elif domain == "script":
                handled_keys.add(domain)
                if isinstance(payload, dict):
                    for index, (key, entry) in enumerate(payload.items()):
                        file_components.append(_component_record("script", str(key), entry, path, index))
            elif domain in HELPER_DOMAINS:
                handled_keys.add(domain)
                if isinstance(payload, dict):
                    for index, (key, entry) in enumerate(payload.items()):
                        file_components.append(_component_record(domain, str(key), entry, path, index))
            elif domain == "scene":
                handled_keys.add(domain)
                if isinstance(payload, list):
                    entries = [(str(index), entry, index) for index, entry in enumerate(payload)]
                elif isinstance(payload, dict):
                    entries = [(str(key), entry, index) for index, (key, entry) in enumerate(payload.items())]
                else:
                    entries = []
                for key, entry, index in entries:
                    if isinstance(entry, dict):
                        component_key = str(entry.get("id") or entry.get("name") or key or index)
                        file_components.append(_component_record("scene", component_key, entry, path, index))
            elif domain == "template" and isinstance(payload, list):
                handled_keys.add(domain)
                for index, entry in enumerate(payload):
                    if isinstance(entry, dict):
                        file_components.append(_component_record("template", str(index), entry, path, index))

        # Generic include files may be mappings keyed by an automation/script ID.
        for index, (key, entry) in enumerate(data.items()):
            if str(key) in handled_keys or not isinstance(entry, dict):
                continue
            _append_inferred_component(file_components, entry, path, str(key), index, hint)

        merged_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        for component in file_components + raw_components:
            key = (str(component.get("file")), str(component.get("kind")), str(component.get("key")))
            merged_by_key[key] = _merge_component(merged_by_key[key], component) if key in merged_by_key else component
        components.extend(merged_by_key.values())

    unique: dict[str, dict[str, Any]] = {}
    for component in components:
        unique[str(component["component_id"])] = component
    return list(unique.values()), list(dict.fromkeys(warnings))


def _count_dashboard_cards(value: Any) -> int:
    count = 0
    if isinstance(value, dict):
        if "type" in value and any(key in value for key in ("entity", "entities", "card", "cards", "content", "title", "name")):
            count += 1
        for child in value.values():
            count += _count_dashboard_cards(child)
    elif isinstance(value, list):
        for child in value:
            count += _count_dashboard_cards(child)
    return count


def summarize_dashboard(url_path: str, title: str, config: Any) -> dict[str, Any]:
    views: list[dict[str, Any]] = []
    raw_views = config.get("views") if isinstance(config, dict) else []
    for index, view in enumerate(raw_views if isinstance(raw_views, list) else []):
        if not isinstance(view, dict):
            continue
        refs = sorted(_iter_entity_refs(view))
        views.append({
            "title": str(view.get("title") or f"View {index + 1}"),
            "path": str(view.get("path") or ""),
            "entity_ids": refs[:1000],
            "card_count": _count_dashboard_cards(view),
        })
    all_refs = sorted({entity for view in views for entity in view["entity_ids"]})
    return {
        "url_path": url_path,
        "title": title,
        "entity_ids": all_refs[:3000],
        "view_count": len(views),
        "card_count": sum(int(view["card_count"]) for view in views),
        "views": views[:100],
    }


def collect_lovelace_inventory() -> tuple[list[dict[str, Any]], list[str]]:
    dashboards: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        listing, list_warnings = HAWebSocketClient().call_many([
            ("dashboards", {"type": "lovelace/dashboards/list"}),
        ])
        warnings.extend(list_warnings)
        rows = listing.get("dashboards") if isinstance(listing.get("dashboards"), list) else []
        definitions: list[tuple[str, str]] = [("", "Overview")]
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            url_path = str(row.get("url_path") or "")
            title = str(row.get("title") or url_path or "Dashboard")
            if (url_path, title) not in definitions:
                definitions.append((url_path, title))
        commands: list[tuple[str, dict[str, Any]]] = []
        for index, (url_path, _title) in enumerate(definitions):
            command: dict[str, Any] = {"type": "lovelace/config"}
            if url_path:
                command["url_path"] = url_path
            commands.append((f"dashboard_{index}", command))
        configs, config_warnings = HAWebSocketClient().call_many(commands)
        warnings.extend(config_warnings)
        for index, (url_path, title) in enumerate(definitions):
            config = configs.get(f"dashboard_{index}")
            if isinstance(config, dict):
                dashboards.append(summarize_dashboard(url_path, title, config))
    except APIError as exc:
        warnings.append(f"Lovelace inventory unavailable: {exc}")
    return dashboards, list(dict.fromkeys(warnings))


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




def _snapshot_priority(path: Path) -> tuple[int, str]:
    """Prioritise Home Assistant YAML before optional source and documentation.

    The old alphabetical walk could spend the snapshot byte budget on HACS or
    custom-component source files before reaching packages/. Process mapping
    requires the actual HA YAML, so root YAML and packages are always visited
    first.
    """
    relative = safe_relative(path)
    suffix = path.suffix.lower()
    parts = Path(relative).parts
    if suffix in {".yaml", ".yml"}:
        if len(parts) == 1 or (parts and parts[0] in {"packages", "automations", "scripts", "scenes"}):
            return (0, relative)
        return (1, relative)
    if suffix == ".json":
        return (2, relative)
    if suffix in {".py", ".js"}:
        return (3, relative)
    return (4, relative)

def build_snapshot() -> dict[str, Any]:
    options = load_options()
    limit = options["max_snapshot_mb"] * 1024 * 1024
    files: list[dict[str, Any]] = []
    total = 0
    omitted_budget = 0
    omitted_large = 0
    candidate_paths = [
        path for path in HA_CONFIG_DIR.rglob("*")
        if path.is_file() and include_file(path)
    ]
    candidate_paths.sort(key=_snapshot_priority)

    for path in candidate_paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            omitted_large += 1
            continue
        if len(files) >= MAX_FILES or total + size > limit:
            omitted_budget += 1
            continue
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
                "snapshot_priority": _snapshot_priority(path)[0],
            }
        )
        total += len(clean.encode("utf-8"))

    package_yaml_count = sum(
        1 for item in files
        if item.get("kind") == "home_assistant_yaml"
        and str(item.get("path", "")).replace("\\", "/").startswith("packages/")
    )
    yaml_count = sum(1 for item in files if item.get("kind") == "home_assistant_yaml")
    truncated = bool(omitted_budget or omitted_large)
    snapshot_scope = {
        "candidate_files": len(candidate_paths),
        "included_files": len(files),
        "included_yaml_files": yaml_count,
        "included_package_yaml_files": package_yaml_count,
        "omitted_by_budget": omitted_budget,
        "omitted_too_large": omitted_large,
        "content_bytes": total,
        "limit_bytes": limit,
        "priority_policy": "root-and-packages-yaml-first",
    }

    inventory = collect_home_assistant_inventory()
    components, component_warnings = collect_component_catalog(files)
    dashboards, dashboard_warnings = collect_lovelace_inventory()
    states = inventory["states"]
    config = inventory["config"]
    api_warnings = list(dict.fromkeys(inventory["warnings"] + component_warnings + dashboard_warnings))
    snapshot = {
        "schema_version": 3,
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
        "snapshot_scope": snapshot_scope,
        "states": states,
        "state_count": len(states),
        "entity_registry": inventory["entity_registry"],
        "entity_registry_count": len(inventory["entity_registry"]),
        "device_registry": inventory["device_registry"],
        "device_registry_count": len(inventory["device_registry"]),
        "area_registry": inventory["area_registry"],
        "area_registry_count": len(inventory["area_registry"]),
        "components": components,
        "component_count": len(components),
        "dashboards": dashboards,
        "dashboard_count": len(dashboards),
        "entity_validation": inventory["entity_validation"],
        "inventory_status": inventory["inventory_status"],
        "api_warnings": api_warnings,
        "privacy": {
            "secrets_excluded": True,
            "storage_excluded": True,
            "database_excluded": True,
            "device_identifiers_excluded": True,
            "device_connections_excluded": True,
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
        {
            "code": code,
            "connector_name": "Home Assistant AI Supervisor V5",
            "connector_version": APP_VERSION,
        },
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
    if isinstance(result, dict):
        result["snapshot_scope"] = snapshot.get("snapshot_scope", {})
        result["snapshot_truncated"] = bool(snapshot.get("truncated", False))
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


def get_process_map(query: str) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("Describe the process to find")
    if len(query) > 4000:
        raise ValueError("Query is too long")
    snapshot = read_json(LAST_SNAPSHOT_PATH, None)
    if not isinstance(snapshot, dict):
        sync_snapshot()
    return EngineClient().request(
        "POST", "/v1/process/map", {"query": query, "language": load_options()["language"]}, timeout=120
    )


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
            "component_count": snapshot.get("component_count", 0),
            "dashboard_count": snapshot.get("dashboard_count", 0),
            "entity_validation": snapshot.get("entity_validation", "unavailable"),
            "inventory_status": snapshot.get("inventory_status", {}),
            "truncated": snapshot.get("truncated", False),
            "api_warnings": snapshot.get("api_warnings", []),
            "snapshot_scope": snapshot.get("snapshot_scope", {}),
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
            elif path == "/api/process-map":
                result = get_process_map(str(incoming.get("query", "")))
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
