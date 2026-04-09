"""Figma source (text-only extraction).

Walks a Figma node tree via the REST API and emits a structured text
representation: frame/component names become headings, text layers become
body text. Screenshots and visual fidelity are out of scope for v1 — this
source gives the LLM enough structural + copy context to write test cases
about a design.

Authentication (env var):
    FIGMA_API_TOKEN   personal access token from figma.com/settings

Supported URL shapes:
    https://figma.com/design/<fileKey>/<name>?node-id=<id>
    https://figma.com/file/<fileKey>/<name>?node-id=<id>     (legacy)
    https://figma.com/design/<fileKey>/<name>                (whole file)
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .base import LoadedDoc, SourceError

_HOST_RE = re.compile(r"(^|\.)figma\.com$", re.IGNORECASE)
_FILE_KEY_RE = re.compile(r"/(?:design|file|proto)/([A-Za-z0-9]+)")

# Node types whose names should become headings in the text dump.
_CONTAINER_TYPES = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE", "SECTION"}
# Node types to skip entirely (purely visual, no structural value).
_SKIP_TYPES = {"VECTOR", "LINE", "ELLIPSE", "RECTANGLE", "STAR", "POLYGON", "BOOLEAN_OPERATION"}
# Heading depth cap so deeply nested designs don't explode into h7+.
_MAX_HEADING_DEPTH = 4


class FigmaSource:
    name = "figma"

    def matches(self, ref: str) -> bool:
        if "://" not in ref:
            return False
        try:
            host = urlparse(ref).hostname or ""
        except ValueError:
            return False
        return bool(_HOST_RE.search(host))

    def load(self, ref: str) -> LoadedDoc:
        client = _FigmaClient.from_env()
        file_key, node_id = _parse_figma_url(ref)
        if not file_key:
            raise SourceError(f"Could not extract Figma file key from URL: {ref}")

        if node_id:
            data = client.fetch_nodes(file_key, [node_id])
            nodes = data.get("nodes", {}) or {}
            entry = nodes.get(node_id) or {}
            root = entry.get("document")
            if not root:
                raise SourceError(f"Figma node {node_id} not found in file {file_key}")
            file_name = entry.get("name") or data.get("name") or file_key
        else:
            data = client.fetch_file(file_key)
            root = data.get("document")
            if not root:
                raise SourceError(f"Figma file {file_key} returned no document")
            file_name = data.get("name") or file_key

        text = _render_node(root, depth=1).strip()
        if not text:
            raise SourceError(f"Figma node produced empty text for {ref}")
        title = f"Figma: {file_name}"
        return LoadedDoc(title=title, text=text, origin=ref)


# --------------------------------------------------------------------------
# URL parsing
# --------------------------------------------------------------------------


def _parse_figma_url(url: str) -> tuple[str | None, str | None]:
    """Return (file_key, node_id_or_none). Converts '-' to ':' in the node id."""
    parsed = urlparse(url)
    match = _FILE_KEY_RE.search(parsed.path)
    file_key = match.group(1) if match else None

    node_id: str | None = None
    qs = parse_qs(parsed.query)
    if "node-id" in qs and qs["node-id"]:
        raw = qs["node-id"][0]
        # Figma URLs encode node ids like "1-23"; API expects "1:23".
        node_id = raw.replace("-", ":")
    return file_key, node_id


# --------------------------------------------------------------------------
# REST client
# --------------------------------------------------------------------------


class _FigmaClient:
    _BASE = "https://api.figma.com/v1"

    def __init__(self, token: str):
        self.token = token

    @classmethod
    def from_env(cls) -> "_FigmaClient":
        token = os.environ.get("FIGMA_API_TOKEN")
        if not token:
            raise SourceError("FIGMA_API_TOKEN is not set.")
        return cls(token)

    def fetch_file(self, file_key: str) -> dict:
        return self._get_json(f"/files/{file_key}")

    def fetch_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        ids = ",".join(node_ids)
        return self._get_json(f"/files/{file_key}/nodes?ids={ids}")

    def _get_json(self, path: str) -> dict:
        url = f"{self._BASE}{path}"
        req = Request(url, headers={"X-Figma-Token": self.token, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
        except HTTPError as e:
            raise SourceError(f"Figma API {e.code} for {path}: {e.reason}") from e
        except URLError as e:
            raise SourceError(f"Figma API unreachable: {e.reason}") from e
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise SourceError(f"Invalid JSON from Figma: {e}") from e


# --------------------------------------------------------------------------
# Node tree → text
# --------------------------------------------------------------------------


def _render_node(node: dict, depth: int) -> str:
    """Recursively render a Figma node into a markdown-ish text block."""
    node_type = node.get("type", "")
    if node_type in _SKIP_TYPES:
        return ""

    parts: list[str] = []
    name = (node.get("name") or "").strip()

    if node_type == "TEXT":
        chars = (node.get("characters") or "").strip()
        if chars:
            parts.append(chars)

    elif node_type in _CONTAINER_TYPES or node_type in {"DOCUMENT", "CANVAS"}:
        if name and node_type not in {"DOCUMENT"}:
            heading_level = min(depth, _MAX_HEADING_DEPTH)
            parts.append(f"{'#' * heading_level} {name}")
            # Include component description if present (great for design-system docs).
            desc = (node.get("description") or "").strip()
            if desc:
                parts.append(desc)

    elif name:
        # GROUP or other container: include the name as a light bullet so
        # hierarchy is visible without polluting heading structure.
        parts.append(f"- {name}")

    for child in node.get("children", []) or []:
        child_text = _render_node(child, depth=depth + 1)
        if child_text:
            parts.append(child_text)

    return "\n\n".join(p for p in parts if p)
