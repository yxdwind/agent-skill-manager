"""Tests for local .zip / .skill archive installation (v0.22.0)."""

import zipfile
from unittest.mock import patch

from agent_skill_manager.services.sync.install import install_skill

FRONT = "---\nname: {}\ndescription: packed skill\n---\n# body\n"


def _zip(tmp_path, name, entries):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w") as z:
        for fn, content in entries.items():
            z.writestr(fn, content)
    return p


def test_install_zip_root_layout_uses_frontmatter_name(tmp_path):
    central = tmp_path / "central"
    archive = _zip(tmp_path, "tool.zip", {"SKILL.md": FRONT.format("zipped-skill")})
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is True
    assert (central / "zipped-skill" / "SKILL.md").exists()


def test_install_zip_wrapped_layout_falls_back_to_folder_name(tmp_path):
    central = tmp_path / "central"
    archive = _zip(tmp_path, "tool.zip", {
        "wrapped/SKILL.md": "---\ndescription: no name field\n---\nbody",
        "wrapped/helper.txt": "support file",
    })
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is True
    assert (central / "wrapped" / "helper.txt").exists()


def test_install_zip_rejects_zip_slip(tmp_path, capsys):
    central = tmp_path / "central"
    archive = _zip(tmp_path, "evil.zip", {"../outside.txt": "payload"})
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is False
    assert "zip-slip" in capsys.readouterr().out
    assert not central.exists() or not list(central.iterdir())


def test_install_zip_name_field_cannot_escape(tmp_path):
    central = tmp_path / "central"
    archive = _zip(tmp_path, "tool.zip", {"SKILL.md": FRONT.format("../../escape")})
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is True
    # fell back to the archive stem, nothing escaped the central repo
    assert (central / "tool" / "SKILL.md").exists()
    assert not (tmp_path / "escape").exists()


def test_install_zip_bad_archive(tmp_path, capsys):
    central = tmp_path / "central"
    p = tmp_path / "broken.zip"
    p.write_bytes(b"not a zip at all")
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(p), no_audit=True)
    assert ok is False
    assert "Not a valid zip archive" in capsys.readouterr().out


def test_install_zip_collision(tmp_path, capsys):
    central = tmp_path / "central"
    (central / "zipped-skill").mkdir(parents=True)
    archive = _zip(tmp_path, "tool.zip", {"SKILL.md": FRONT.format("zipped-skill")})
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is False
    assert "already exists" in capsys.readouterr().out


def test_install_zip_multi_skill_refused(tmp_path, capsys):
    central = tmp_path / "central"
    archive = _zip(tmp_path, "tool.zip", {
        "a/SKILL.md": FRONT.format("a"),
        "b/SKILL.md": FRONT.format("b"),
    })
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(archive), no_audit=True)
    assert ok is False
    out = capsys.readouterr().out
    assert "multiple skills" in out and "a" in out and "b" in out


def test_install_zip_missing_file(tmp_path, capsys):
    central = tmp_path / "central"
    with patch("agent_skill_manager.services.sync.CENTRAL_DIR", central):
        ok = install_skill(str(tmp_path / "nope.zip"), no_audit=True)
    assert ok is False
    assert "Archive not found" in capsys.readouterr().out
