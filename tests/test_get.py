"""Tests for the reference tier (askill get) and clone failure hints."""

from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

import agent_skill_manager.services.get as get_mod
from agent_skill_manager.services.get import get_skill
from agent_skill_manager.services.sync.install import install_skill


def _fake_repo(repo_url, branch, dest):
    """Pretend to clone: build a repo with two skills at dest."""
    from pathlib import Path

    d = Path(dest)
    for name, body in (("alpha", "alpha body"), ("beta", "beta body")):
        s = d / name
        s.mkdir(parents=True)
        (s / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {body}\n---\n# {name}\n",
            encoding="utf-8",
        )
    return True, ""


def test_get_prints_skill_md_to_stdout(tmp_path, capsys):
    with patch.object(get_mod, "_shallow_clone", _fake_repo):
        code = get_skill("acme/skills@alpha")
    assert code == 0
    out = capsys.readouterr().out
    assert "alpha body" in out


def test_get_without_hint_uses_single_skill(tmp_path, capsys):
    with patch.object(get_mod, "_shallow_clone", _fake_repo):
        # two skills, no hint -> ambiguity message, exit 1
        code = get_skill("acme/skills")
    assert code == 1
    assert "alpha" in capsys.readouterr().out


def test_get_list(tmp_path, capsys):
    with patch.object(get_mod, "_shallow_clone", _fake_repo):
        code = get_skill("acme/skills", list_only=True)
    assert code == 0
    out = capsys.readouterr().out
    assert "alpha" in out and "beta" in out and "2 skill(s)" in out


def test_get_dir_borrows_full_folder(tmp_path, capsys):
    with patch.object(get_mod, "_shallow_clone", _fake_repo):
        code = get_skill("acme/skills@beta", to_dir=True)
    assert code == 0
    out = capsys.readouterr().out
    assert "Borrowed to:" in out
    borrowed = out.split("Borrowed to: ")[1].splitlines()[0].strip()
    assert (path_import(borrowed) / "SKILL.md").exists()


def path_import(p):
    from pathlib import Path

    return Path(p)


def test_get_unknown_hint(tmp_path, capsys):
    with patch.object(get_mod, "_shallow_clone", _fake_repo):
        code = get_skill("acme/skills@missing")
    assert code == 1
    assert "not found" in capsys.readouterr().out


def test_get_unsupported_source(capsys):
    code = get_skill("not-a-source")
    assert code == 2


def test_get_local_dir_prints_skill_md(tmp_path, capsys):
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: my-skill\n---\nlocal body", encoding="utf-8")
    code = get_skill(str(src))
    assert code == 0
    assert "local body" in capsys.readouterr().out


def test_get_local_list(tmp_path, capsys):
    src = tmp_path / "skills"
    for n in ("alpha", "beta"):
        d = src / n
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {n}\n---\n", encoding="utf-8")
    code = get_skill(str(src), list_only=True)
    assert code == 0
    out = capsys.readouterr().out
    assert "alpha" in out and "beta" in out


def test_get_local_to_dir_borrows(tmp_path, capsys):
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: my-skill\n---\n", encoding="utf-8")
    (src / "helper.txt").write_text("support", encoding="utf-8")
    code = get_skill(str(src), to_dir=True)
    assert code == 0
    out = capsys.readouterr().out
    borrowed = Path(out.split("Borrowed to: ")[1].splitlines()[0].strip())
    assert (borrowed / "helper.txt").exists()


def test_get_clone_failure_names_proxy(tmp_path, capsys):
    err = (
        "fatal: unable to access 'https://github.com/acme/skills/': "
        "Failed to connect to github.com:443 over proxy 127.0.0.1:7897"
    )
    with patch("subprocess.run", side_effect=CalledProcessError(128, "git", stderr=err)):
        code = get_skill("acme/skills@alpha")
    assert code == 1
    out = capsys.readouterr().out
    assert "proxy client" in out  # actionable hint, not raw stderr only


def test_install_clone_failure_also_names_proxy(tmp_path, capsys):
    err = (
        "fatal: unable to access 'https://github.com/acme/skills/': "
        "Failed to connect to github.com:443 over proxy 127.0.0.1:7897"
    )
    with patch("subprocess.run", side_effect=CalledProcessError(128, "git", stderr=err)), \
         patch("agent_skill_manager.services.sync.CENTRAL_DIR", tmp_path):
        ok = install_skill("https://github.com/acme/skills", no_audit=True, verbose=True)
    assert ok is False
    assert "git config --global --unset http.proxy" in capsys.readouterr().out
