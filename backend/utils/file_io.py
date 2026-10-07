"""Crash-safe JSON persistence helpers.

Files are written to a temporary sibling and atomically swapped into place with
os.replace, so a crash mid-write never leaves a truncated JSON file behind.
"""

import asyncio
import json
import os
from typing import Any, Dict

import aiofiles

# One lock per target path so concurrent saves of the same file are serialized
_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(path: str) -> asyncio.Lock:
    key = os.path.abspath(path)
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


async def write_json_atomic(path: str, data: Any) -> None:
    """
    Serialize data to JSON and atomically replace the file at path.

    Serialization happens inside the per-file lock, so the last caller to
    acquire it always writes the newest in-memory state.

    Args:
        path: Destination file path
        data: JSON-serializable object
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    async with _lock_for(path):
        content = json.dumps(data, indent=2)
        tmp_path = f"{path}.tmp"
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(content)
            await f.flush()
            await asyncio.to_thread(os.fsync, f.fileno())
        os.replace(tmp_path, path)


def write_text_atomic(path: str, content: str) -> None:
    """
    Synchronously and atomically replace a small text file.

    Args:
        path: Destination file path
        content: Text to write
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
