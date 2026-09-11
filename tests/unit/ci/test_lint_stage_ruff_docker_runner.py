"""Fail-closed contract for the Windows-orchestrated Docker Ruff runner (#4487)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.stages.lint import (
    _black_runner_command,
    RUFF_DOCKER_IMAGE_MISSING,
    RUFF_RUNNER_INVALID,
    RuffResolutionError,
    _ruff_command,
    pinned_ruff_version,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_native_ruff_runner_preserves_canonical_python_module_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("CDB_RUFF_RUNNER", raising=False)
    assert _ruff_command(python="python.exe", repo_root=tmp_path) == [
        "python.exe",
        "-m",
        "ruff",
        "check",
        ".",
    ]


def test_docker_ruff_runner_is_networkless_readonly_and_pinned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "requirements-dev.txt").write_text("ruff==0.16.5\n", encoding="utf-8")
    monkeypatch.setenv("CDB_RUFF_RUNNER", "docker")
    monkeypatch.setenv("CDB_RUFF_DOCKER_IMAGE", "cdb-ci-runner:prepared")

    command = _ruff_command(python="python.exe", repo_root=tmp_path)

    assert command[:5] == ["docker", "run", "--rm", "--pull=never", "--network"]
    assert "none" in command
    assert "--read-only" in command
    assert "HOME=/tmp" in command
    assert "RUFF_CACHE_DIR=/tmp/ruff-cache" in command
    assert not any("docker.sock" in part.lower() for part in command)
    assert "_version=" in command[-1]
    assert "0.16.5" in command[-1]


def test_native_black_runner_preserves_the_existing_python_module_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "requirements-dev.txt").write_text("black==26.5.1\n", encoding="utf-8")
    monkeypatch.delenv("CDB_BLACK_RUNNER", raising=False)
    monkeypatch.delenv("CDB_BLACK_EXECUTABLE", raising=False)
    monkeypatch.setattr(
        "ci.stages.lint.ensure_black_version", lambda *_args, **_kwargs: "26.5.1"
    )

    command, version, is_docker = _black_runner_command(
        python="python.exe", repo_root=tmp_path, files=["ci/stages/lint.py"]
    )

    assert command == ["python.exe", "-m", "black"]
    assert version == "26.5.1"
    assert is_docker is False


def test_docker_black_runner_is_allowlisted_and_pinned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "requirements-dev.txt").write_text("black==26.5.1\n", encoding="utf-8")
    monkeypatch.setenv("CDB_BLACK_RUNNER", "docker")
    monkeypatch.setenv("CDB_RUFF_DOCKER_IMAGE", "cdb-ci-runner:prepared")

    command, version, is_docker = _black_runner_command(
        python="python.exe", repo_root=tmp_path, files=["ci/stages/lint.py"]
    )

    assert is_docker is True
    assert version == "26.5.1"
    assert "--network" in command and "none" in command
    assert "--read-only" in command
    assert not any("docker.sock" in part.lower() for part in command)
    assert "_version=" in command[-1]
    assert "ci/stages/lint.py" in command[-1]


def test_docker_ruff_runner_rejects_missing_image(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CDB_RUFF_RUNNER", "docker")
    monkeypatch.delenv("CDB_RUFF_DOCKER_IMAGE", raising=False)
    with pytest.raises(RuffResolutionError, match=RUFF_DOCKER_IMAGE_MISSING):
        _ruff_command(python="python.exe", repo_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_image",
    [
        "cdb-ci-runner:prepared;calc.exe",
        "cdb-ci-runner:prepared|whoami",
        "cdb-ci-runner:prepared&whoami",
        "cdb-ci-runner:$(whoami)",
        "cdb-ci-runner:`whoami`",
    ],
)
def test_docker_ruff_runner_rejects_unsafe_image_characters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unsafe_image: str
) -> None:
    """#4488 residual: image argv must fail closed like CDB_BLACK_EXECUTABLE."""
    (tmp_path / "requirements-dev.txt").write_text("ruff==0.16.5\n", encoding="utf-8")
    monkeypatch.setenv("CDB_RUFF_RUNNER", "docker")
    monkeypatch.setenv("CDB_RUFF_DOCKER_IMAGE", unsafe_image)
    with pytest.raises(RuffResolutionError, match=RUFF_RUNNER_INVALID):
        _ruff_command(python="python.exe", repo_root=tmp_path)


def test_ruff_runner_rejects_unknown_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CDB_RUFF_RUNNER", "remote")
    with pytest.raises(RuffResolutionError, match=RUFF_RUNNER_INVALID):
        _ruff_command(python="python.exe", repo_root=tmp_path)


def test_pinned_ruff_version_is_repo_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    assert pinned_ruff_version(repo_root) == "0.16.6"
