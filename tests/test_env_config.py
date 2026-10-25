"""Tests for the small .env reader used by command configuration."""
import os

from aseprite_mcp.core.commands import _load_env_file


def test_load_env_file_reads_simple_values_and_comments(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "ASEPRITE_PATH=/opt/aseprite\n"
        "QUOTED='with spaces'\n"
        "INLINE=value # comment\n"
        "export EXPORTED=yes\n"
        "not a setting\n",
        encoding="utf-8",
    )
    for key in ("ASEPRITE_PATH", "QUOTED", "INLINE", "EXPORTED"):
        monkeypatch.delenv(key, raising=False)

    _load_env_file(str(env_file))

    assert os.environ["ASEPRITE_PATH"] == "/opt/aseprite"
    assert os.environ["QUOTED"] == "with spaces"
    assert os.environ["INLINE"] == "value"
    assert os.environ["EXPORTED"] == "yes"


def test_load_env_file_does_not_override_process_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ASEPRITE_PATH=from-file\n", encoding="utf-8")
    monkeypatch.setenv("ASEPRITE_PATH", "from-environment")

    _load_env_file(str(env_file))

    assert os.environ["ASEPRITE_PATH"] == "from-environment"


def test_load_env_file_ignores_missing_file(tmp_path):
    _load_env_file(str(tmp_path / "missing.env"))
