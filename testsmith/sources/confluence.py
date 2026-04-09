"""Confluence Cloud source.

Fetches a Confluence page by URL using the REST API and converts its
storage-format XHTML body to plain text.

Authentication (env vars):
    CONFLUENCE_BASE_URL   e.g. https://acme.atlassian.net
    CONFLUENCE_EMAIL      your Atlassian account email
    CONFLUENCE_API_TOKEN  API token from id.atlassian.com

Supported URL shapes:
    https://acme.atlassian.net/wiki/spaces/<SPACE>/pages/<ID>/<slug>
    https://acme.atlassian.net/wiki/spaces/<SPACE>/pages/<ID>
    https://acme.atlassian.net/wiki/display/<SPACE>/<title>      (tinyurl)
    https://acme.atlassian.net/wiki/x/<tinyId>
"""

from __future__ import annotations

import base64
import json
import os
import re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .base import LoadedDoc, SourceError

_CONFLUENCE_HOST_HINT = re.compile(r"\.atlassian\.net$", re.IGNORECASE)
_PAGE_ID_RE = re.compile(r"/pages/(\d+)")
_TINY_ID_RE = re.compile(r"/x/([A-Za-z0-9_-]+)")


class ConfluenceSource:
    name = "confluence"

    def matches(self, ref: str) -> bool:
        if "://" not in ref:
            return False
        try:
            host = urlparse(ref).hostname or ""
        except ValueError:
            return False
        return bool(_CONFLUENCE_HOST_HINT.search(host)) and "/wiki/" in ref

    def load(self, ref: str) -> LoadedDoc:
        client = _ConfluenceClient.from_env()
        page_id = client.resolve_page_id(ref)
        page = client.fetch_page(page_id)

        title = page.get("title") or f"Confluence page {page_id}"
        storage_html = page.get("body", {}).get("storage", {}).get("value", "") or ""
        text = _html_to_text(storage_html).strip()
        if not text:
            raise SourceError(f"Confluence page {page_id} returned empty content")
        return LoadedDoc(title=title, text=text, origin=ref)


# --------------------------------------------------------------------------
# REST client
# --------------------------------------------------------------------------


class _ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{email}:{api_token}".encode("utf-8")).decode("ascii")
        self.auth_header = f"Basic {token}"

    @classmethod
    def from_env(cls) -> "_ConfluenceClient":
        base = os.environ.get("CONFLUENCE_BASE_URL")
        email = os.environ.get("CONFLUENCE_EMAIL")
        token = os.environ.get("CONFLUENCE_API_TOKEN")
        missing = [
            name
            for name, val in (
                ("CONFLUENCE_BASE_URL", base),
                ("CONFLUENCE_EMAIL", email),
                ("CONFLUENCE_API_TOKEN", token),
            )
            if not val
        ]
        if missing:
            raise SourceError(
                "Confluence credentials missing. Set: " + ", ".join(missing)
            )
        return cls(base, email, token)  # type: ignore[arg-type]

    def resolve_page_id(self, url: str) -> str:
        """Extract a numeric page ID from a Confluence URL.

        For /pages/<id>/... URLs, the ID is in the path.
        For /x/<tinyId> tinyurls, we follow the redirect to discover the ID.
        """
        match = _PAGE_ID_RE.search(url)
        if match:
            return match.group(1)

        tiny = _TINY_ID_RE.search(url)
        if tiny:
            # Follow redirect with HEAD to get the canonical URL.
            location = self._follow_redirect(url)
            match = _PAGE_ID_RE.search(location or "")
            if match:
                return match.group(1)

        raise SourceError(f"Could not extract page ID from URL: {url}")

    def fetch_page(self, page_id: str) -> dict:
        path = f"/wiki/rest/api/content/{page_id}?expand=body.storage,title"
        return self._get_json(path)

    # --- HTTP helpers --------------------------------------------------------

    def _get_json(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = Request(
            url,
            headers={"Authorization": self.auth_header, "Accept": "application/json"},
        )
        try:
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
        except HTTPError as e:
            raise SourceError(f"Confluence API {e.code} for {path}: {e.reason}") from e
        except URLError as e:
            raise SourceError(f"Confluence API unreachable: {e.reason}") from e
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise SourceError(f"Invalid JSON from Confluence: {e}") from e

    def _follow_redirect(self, url: str) -> str | None:
        req = Request(url, headers={"Authorization": self.auth_header})
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.geturl()
        except (HTTPError, URLError):
            return None


# --------------------------------------------------------------------------
# HTML → text conversion
# --------------------------------------------------------------------------


class _StorageFormatParser(HTMLParser):
    """Minimal XHTML → text converter for Confluence storage format.

    Strips tags, preserves headings/lists/paragraphs as line breaks, and
    skips Confluence macros (`ac:*` tags) that don't contribute reading text.
    """

    _BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "li",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }
    _SKIP_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._list_markers: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in self._SKIP_TAGS or tag.startswith("ac:"):
            self._skip_depth += 1
            return
        if tag in ("ul", "ol"):
            self._list_markers.append("- " if tag == "ul" else "1. ")
        elif tag == "li":
            marker = self._list_markers[-1] if self._list_markers else "- "
            self._parts.append(f"\n{marker}")
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in self._SKIP_TAGS or tag.startswith("ac:"):
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if tag in ("ul", "ol") and self._list_markers:
            self._list_markers.pop()
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._skip_depth:
            return
        self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse 3+ newlines to 2 and trim trailing whitespace per line.
        lines = [line.rstrip() for line in raw.splitlines()]
        cleaned: list[str] = []
        blank = 0
        for line in lines:
            if not line.strip():
                blank += 1
                if blank <= 1:
                    cleaned.append("")
            else:
                blank = 0
                cleaned.append(line)
        return "\n".join(cleaned).strip()


def _html_to_text(html: str) -> str:
    parser = _StorageFormatParser()
    parser.feed(html)
    parser.close()
    return parser.get_text()
