import json
from pathlib import Path

from agents_md_debugger.cli import main
from agents_md_debugger.config import load_settings
from agents_md_debugger.discovery import explain_path, scan_tree
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
    settings = load_settings(tmp_path / "missing.toml", fallbacks=["TEAM_GUIDE.md"], codex_home=tmp_path / "home")

    result = explain_path(tmp_path / "src" / "api" / "user.py", settings)

    assert [Path(item.path).name for item in result.project_files] == ["AGENTS.md", "AGENTS.override.md", "TEAM_GUIDE.md"]
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
    write(config, 'project_doc_max_bytes = 99\nproject_doc_fallback_filenames = ["TEAM.md"]\nproject_root_markers = [".hg"]\n')
    settings = load_settings(config, codex_home=tmp_path)
    assert settings.max_bytes == 99
    assert settings.fallbacks == ("TEAM.md",)
    assert settings.root_markers == (".hg",)


def test_scan_and_doctor_report_shadow_empty_scope_and_duplicate(tmp_path):
    (tmp_path / ".git").mkdir()
    write(tmp_path / "AGENTS.md", "Always run the complete test suite before merging.")
    write(tmp_path / "src" / "AGENTS.override.md", "Always run the complete test suite before merging.")
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
    assert main(["doctor", str(tmp_path), "--fail-on", "warning", "--codex-home", str(tmp_path / "home")]) == 1
