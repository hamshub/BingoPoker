"""Tests for crash-safe JSON writes."""

import asyncio
import json

from utils.file_io import write_json_atomic, write_text_atomic


async def test_write_json_atomic_replaces_content(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"old": true}', encoding="utf-8")

    await write_json_atomic(str(path), {"new": True})

    assert json.loads(path.read_text(encoding="utf-8")) == {"new": True}
    assert not (tmp_path / "data.json.tmp").exists()


async def test_concurrent_writes_end_with_latest_state(tmp_path):
    path = str(tmp_path / "data.json")
    state = {"n": 0}

    async def bump_and_save():
        state["n"] += 1
        await write_json_atomic(path, state)

    await asyncio.gather(*(bump_and_save() for _ in range(20)))

    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8")) == {"n": 20}


async def test_write_creates_missing_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "data.json"

    await write_json_atomic(str(path), [1, 2, 3])

    assert json.loads(path.read_text(encoding="utf-8")) == [1, 2, 3]


def test_write_text_atomic(tmp_path):
    path = tmp_path / "secret.txt"

    write_text_atomic(str(path), "abc")

    assert path.read_text(encoding="utf-8") == "abc"
    assert not (tmp_path / "secret.txt.tmp").exists()
