"""
Local filesystem storage backend.

Implements a minimal `StorageBackend` interface so we can later drop in an
S3-compatible backend (see PRD 5.3) for a hosted deployment without changing
any calling code. For the hackathon, everything lives under `storage_dir`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageBackend(Protocol):
    def job_dir(self, job_id: str) -> Path: ...

    def save_upload(self, job_id: str, filename: str, contents: bytes) -> Path: ...

    def path_for(self, job_id: str, filename: str) -> Path: ...

    def url_for(self, job_id: str, filename: str) -> str: ...


class LocalStorageBackend:
    def __init__(self) -> None:
        self._settings = get_settings()

    def job_dir(self, job_id: str) -> Path:
        directory = self._settings.storage_dir / job_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def save_upload(self, job_id: str, filename: str, contents: bytes) -> Path:
        destination = self.job_dir(job_id) / filename
        destination.write_bytes(contents)
        return destination

    def path_for(self, job_id: str, filename: str) -> Path:
        return self.job_dir(job_id) / filename

    def url_for(self, job_id: str, filename: str) -> str:
        # Served via the /media static mount registered in app.main.
        return f"/media/{job_id}/{filename}"


_storage_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _storage_backend
    if _storage_backend is None:
        _storage_backend = LocalStorageBackend()
    return _storage_backend
