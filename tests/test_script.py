"""Lua escape hatch (script.py)."""
import sys

from conftest import ok, run

from aseprite_mcp.core.commands import AsepriteCommand, validate_lua_script
from aseprite_mcp.tools import script


def test_run_lua_script_returns_printed_output(sprite):
    out = ok(run(script.run_lua_script(
        'local spr = app.activeSprite print("size=" .. spr.width .. "x" .. spr.height)',
        sprite)))
    assert "size=32x32" in out


def test_run_lua_script_rejects_empty():
    assert run(script.run_lua_script("  ")) == "Script cannot be empty"


def test_lua_validation_blocks_common_host_apis():
    assert validate_lua_script('os.execute("echo unsafe")') is not None
    assert validate_lua_script('io.open("secret.txt")') is not None
    assert validate_lua_script('print("sprite work")') is None


def test_lua_validation_allows_unsafe_apis_with_opt_in(monkeypatch):
    monkeypatch.delenv("ASEPRITE_MCP_ALLOW_UNSAFE_LUA", raising=False)
    assert validate_lua_script(
        'os.execute("echo trusted")',
        allow_unsafe_lua=True,
    ) is None


def test_lua_validation_respects_server_and_per_call_size_caps(monkeypatch):
    import aseprite_mcp.core.commands as commands

    monkeypatch.setattr(commands, "_MAX_LUA_SCRIPT_BYTES", 8)
    assert validate_lua_script("123456789", max_bytes=100) == (
        "Script exceeds the maximum size of 8 bytes"
    )
    assert validate_lua_script("1234", max_bytes=3) == (
        "Script exceeds the maximum size of 3 bytes"
    )


def test_run_lua_script_rejects_path_traversal():
    assert run(script.run_lua_script("print('ok')", "../outside.aseprite")).startswith(
        "Invalid filename"
    )


def test_run_command_times_out(monkeypatch):
    monkeypatch.setenv("ASEPRITE_PATH", sys.executable)
    success, output = AsepriteCommand.run_command(
        ["-c", "import time; time.sleep(5)"],
        timeout=0.05,
        max_output_bytes=1024,
    )
    assert not success
    assert "timed out" in output


def test_run_command_caps_combined_output(monkeypatch):
    monkeypatch.setenv("ASEPRITE_PATH", sys.executable)
    success, output = AsepriteCommand.run_command(
        ["-c", "import sys; print('x' * 100); print('y' * 100, file=sys.stderr)"],
        timeout=5,
        max_output_bytes=32,
    )
    assert success
    assert "[output truncated]" in output
    assert len(output.encode("utf-8")) <= 32 + len("\n[output truncated]") * 2
