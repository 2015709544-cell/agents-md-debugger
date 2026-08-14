import json
from pathlib import Path

import pytest

from agents_md_debugger import discovery
from agents_md_debugger.cli import main
from agents_md_debugger.config import load_settings
from agents_md_debugger.discovery import explain_path, find_project_root, scan_tree
from agents_md_debugger.doctor import diagnose


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_explain_selects_one_file_per_directory_in_precedence_order(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.md", "root")
    write(tmp_path / "src" / "AGENTS.md", "shadowed")
    write(tmp_path / "src" / "AGENTS.override.md", "override")
    write(tmp_path / "src" / "api" / "TEAM_GUIDE.md", "fallback")
    write(tmp_path / "src" / "api" / "user.py", "pass")
    settings = load_settings(
        tmp_path / "missing.toml", fallbacks=["TEAM_GUIDE.md"], codex_home=tmp_path / "home"
    )

    result = explain_path(tmp_path / "src" / "api" / "user.py", settings)

    assert [Path(item.path).name for item in result.project_files] == [
        "AGENTS.md",
        "AGENTS.override.md",
        "TEAM_GUIDE.md",
    ]
    assert result.root_marker == ".git"


def test_empty_override_falls_through_to_agents(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.override.md", "  \n")
    write(tmp_path / "AGENTS.md", "use me")
    result = explain_path(tmp_path, load_settings(codex_home=tmp_path / "home"))
    assert Path(result.project_files[0].path).name == "AGENTS.md"


def test_budget_reports_truncation(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.md", "12345678")
    write(tmp_path / "src" / "AGENTS.md", "abcdefgh")
    settings = load_settings(max_bytes=10, codex_home=tmp_path / "home")
    result = explain_path(tmp_path / "src", settings)
    assert result.total_project_bytes == 10
    assert result.truncated is True
    assert result.project_files[-1].loaded_bytes == 2


def test_config_file_controls_fallbacks_and_markers(tmp_path):
    config = tmp_path / "config.toml"
    write(
        config,
        'project_doc_max_bytes = 99\nproject_doc_fallback_filenames = ["TEAM.md"]\nproject_root_markers = [".hg"]\n',
    )
    settings = load_settings(config, codex_home=tmp_path)
    assert settings.max_bytes == 99
    assert settings.fallbacks == ("TEAM.md",)
    assert settings.root_markers == (".hg",)


def test_scan_and_doctor_report_shadow_empty_scope_and_duplicate(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.md", "Always run the complete test suite before merging.")
    write(
        tmp_path / "src" / "AGENTS.override.md",
        "Always run the complete test suite before merging.",
    )
    write(tmp_path / "src" / "AGENTS.md", "shadowed")
    write(tmp_path / "empty" / "AGENTS.md", "")
    settings = load_settings(codex_home=tmp_path / "home")
    assert any(item.status == "shadowed" for item in scan_tree(tmp_path, settings))
    codes = {item.code for item in diagnose(tmp_path, settings)}
    assert {"AMD001", "AMD002", "AMD004", "AMD005"} <= codes


def test_cli_json_and_failure_threshold(tmp_path, capsys):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.override.md", "chosen")
    write(tmp_path / "AGENTS.md", "shadowed")
    assert main(["scan", str(tmp_path), "--json", "--codex-home", str(tmp_path / "home")]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1
    assert (
        main(
            [
                "doctor",
                str(tmp_path),
                "--fail-on",
                "warning",
                "--codex-home",
                str(tmp_path / "home"),
            ]
        )
        == 1
    )


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "agents-md-debugger 0.1.1"


def test_unicode_and_spaces_in_paths(tmp_path):
    root = tmp_path / "项目 with spaces"
    (root / ".git").mkdir(parents=True)
    write(root / "AGENTS.md", "repository")
    write(root / "源 代码" / "AGENTS.md", "source")
    write(root / "源 代码" / "模块" / "文件.py", "pass")

    result = explain_path(
        root / "源 代码" / "模块" / "文件.py",
        load_settings(codex_home=tmp_path / "home"),
    )

    assert Path(result.project_root) == root.resolve()
    assert [Path(item.path).name for item in result.project_files] == ["AGENTS.md", "AGENTS.md"]


def test_git_file_is_a_project_root_marker(tmp_path):
    root = tmp_path / "worktree"
    write(root / ".git", "gitdir: ../main/.git/worktrees/worktree\n")
    (root / "nested").mkdir()

    project_root, marker = find_project_root(root / "nested", (".git",))

    assert project_root == root.resolve()
    assert marker == ".git"


def test_no_marker_uses_target_directory_as_root(tmp_path):
    target = tmp_path / "standalone" / "nested"
    target.mkdir(parents=True)

    project_root, marker = find_project_root(target, (".git",))

    assert project_root == target.resolve()
    assert marker is None


def test_utf8_budget_is_counted_in_bytes(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.md", "规则")

    result = explain_path(
        tmp_path,
        load_settings(max_bytes=4, codex_home=tmp_path / "home"),
    )

    assert result.project_files[0].size_bytes == 6
    assert result.project_files[0].loaded_bytes == 4
    assert result.truncated is True


def test_override_shadows_configured_fallback(tmp_path):
    write(tmp_path / "AGENTS.override.md", "override")
    write(tmp_path / "TEAM_GUIDE.md", "fallback")
    settings = load_settings(
        tmp_path / "missing.toml",
        fallbacks=["TEAM_GUIDE.md"],
        codex_home=tmp_path / "home",
    )

    items = {Path(item.path).name: item for item in scan_tree(tmp_path, settings)}

    assert items["AGENTS.override.md"].status == "candidate"
    assert items["TEAM_GUIDE.md"].status == "shadowed"


def test_read_failure_is_reported_by_cli(tmp_path, monkeypatch, capsys):
    write(tmp_path / "AGENTS.md", "private")

    def deny_read(_path):
        raise PermissionError("permission denied")

    monkeypatch.setattr(discovery, "_content", deny_read)

    assert main(["scan", str(tmp_path), "--codex-home", str(tmp_path / "home")]) == 2
    assert "permission denied" in capsys.readouterr().err


def test_committed_demo_resolves_three_scopes():
    root = Path(__file__).parents[1] / "examples" / "demo-repo"

    result = explain_path(
        root / "src" / "api" / "user.py",
        load_settings(codex_home=root / ".empty-codex-home"),
        root,
    )

    assert [item.scope for item in result.project_files] == [".", "src", "src/api"]
    assert [Path(item.path).name for item in result.project_files] == [
        "AGENTS.md",
        "AGENTS.md",
        "AGENTS.override.md",
    ]
