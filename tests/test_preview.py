"""Unit tests for preview-server startup handling."""
import asyncio

from aseprite_mcp.tools import preview


class FakeProcess:
    pid = 4321

    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode


def test_start_preview_server_rejects_invalid_port(tmp_path):
    result = asyncio.run(preview.start_preview_server(str(tmp_path), port=65536))
    assert result == "Port must be an integer between 1 and 65535"


def test_start_preview_server_cleans_up_when_not_ready(monkeypatch, tmp_path):
    proc = FakeProcess()
    pid_file = tmp_path / "preview.pid"
    monkeypatch.setattr(preview, "_pid_path", lambda port, host: str(pid_file))
    monkeypatch.setattr(preview.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(preview, "_wait_for_server", lambda *args: (False, "address in use"))

    result = asyncio.run(preview.start_preview_server(str(tmp_path), port=8123))

    assert result.startswith("Failed to start preview server")
    assert proc.terminated
    assert not pid_file.exists()


def test_start_preview_server_records_pid_only_after_ready(monkeypatch, tmp_path):
    proc = FakeProcess()
    pid_file = tmp_path / "preview.pid"
    monkeypatch.setattr(preview, "_pid_path", lambda port, host: str(pid_file))
    monkeypatch.setattr(preview.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(preview, "_wait_for_server", lambda *args: (True, ""))

    result = asyncio.run(preview.start_preview_server(str(tmp_path), port=8123))

    assert result == "Preview server started: http://127.0.0.1:8123/"
    assert pid_file.read_text(encoding="utf-8") == str(proc.pid)
