from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class JobSourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class GreenhouseAdapter(JobSourceAdapter):
    name = "greenhouse"

    def __init__(self, board: str, source_url: str | None = None):
        self.board = board
        self.source_url = source_url or f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    def fetch(self) -> list[dict[str, Any]]:
        response = httpx.get(self.source_url, timeout=20, follow_redirects=True)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload.get("jobs", [])]

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        location = (item.get("location") or {}).get("name")
        offices = item.get("offices") or []
        if not location and offices:
            location = ", ".join(o.get("location") or o.get("name", "") for o in offices if o.get("location") or o.get("name"))
        return {
            "source": self.name,
            "external_id": str(item.get("id")) if item.get("id") is not None else None,
            "title": item.get("title") or "Untitled role",
            "company": self.board,
            "location": location,
            "description": _strip_html(item.get("content") or ""),
            "apply_url": item.get("absolute_url"),
            "source_url": self.source_url,
            "raw_data": item,
        }


class LeverAdapter(JobSourceAdapter):
    name = "lever"

    def __init__(self, board: str, source_url: str | None = None):
        self.board = board
        self.source_url = source_url or f"https://api.lever.co/v0/postings/{board}?mode=json"

    def fetch(self) -> list[dict[str, Any]]:
        response = httpx.get(self.source_url, timeout=20, follow_redirects=True)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(item) for item in payload]

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        categories = item.get("categories") or {}
        location = categories.get("location")
        if isinstance(location, list):
            location = ", ".join(str(x) for x in location)
        description = item.get("descriptionPlain") or _strip_html(item.get("description") or "")
        return {
            "source": self.name,
            "external_id": item.get("id"),
            "title": item.get("text") or "Untitled role",
            "company": self.board,
            "location": location,
            "work_mode": "remote" if "remote" in description.lower() else "unknown",
            "employment_type": categories.get("commitment"),
            "description": description,
            "apply_url": item.get("hostedUrl") or item.get("applyUrl"),
            "source_url": self.source_url,
            "raw_data": item,
        }


def _strip_html(value: str) -> str:
    import re

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_adapter(source_type: str, board: str, source_url: str | None = None) -> JobSourceAdapter:
    source_type = source_type.lower()
    if source_type == "greenhouse":
        return GreenhouseAdapter(board, source_url)
    if source_type == "lever":
        return LeverAdapter(board, source_url)
    raise ValueError(f"Unsupported job source: {source_type}")


class ManualImportAdapter(JobSourceAdapter):
    """Adapter used by the REST manual-import endpoint and tests."""

    name = "manual"

    def __init__(self, jobs: list[dict[str, Any]]):
        self.jobs = jobs

    def fetch(self) -> list[dict[str, Any]]:
        return self.jobs


class ApiAdapter(JobSourceAdapter):
    """Generic JSON API adapter for providers that return a top-level jobs list."""

    name = "api"

    def __init__(self, url: str, headers: dict[str, str] | None = None):
        self.url = url
        self.headers = headers or {}

    def fetch(self) -> list[dict[str, Any]]:
        response = httpx.get(self.url, headers=self.headers, timeout=20, follow_redirects=True)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("API response must be a list or contain a 'jobs' list")
        return jobs
