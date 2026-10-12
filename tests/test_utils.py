"""Tests for agent_skill_manager.utils module."""


import shutil

import pytest
from agent_skill_manager.utils.filesystem import (
    copy_skill,
    create_link,
    is_symlink_or_junction,
    read_skill_metadata,
    remove_path,
)


class TestIsSymlinkOrJunction:
    def test_nonexistent_path(self, tmp_path):
        assert not is_symlink_or_junction(tmp_path / "nonexistent")

    def test_regular_directory(self, tmp_path):
        d = tmp_path / "regular"
        d.mkdir()
        assert not is_symlink_or_junction(d)

    def test_regular_file(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        assert not is_symlink_or_junction(f)

    def test_dead_link_still_detected(self, tmp_path):
        """A link whose target was deleted must still read as a link.

        Regression: the old implementation gated on ``path.exists()``, which
        follows the link and reports ``False`` once the target is gone - so a
        dangling Windows junction was treated as a plain (missing) path and
        never cleaned up. See ``clean_deleted_skill``.
        """
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("x", encoding="utf-8")
        dst = tmp_path / "dst"
        ok, method, _ = create_link(src, dst)
        assert ok and method in ("symlink", "junction", "copy")

        if method == "copy":
            pytest.skip("link creation fell back to copy on this platform")
        assert is_symlink_or_junction(dst)

        # delete the target -> dst is now a dead link
        shutil.rmtree(src)
        assert not dst.exists()          # resolves through the dead link
        assert is_symlink_or_junction(dst)  # ...but it is still a link


class TestRemovePath:
    def test_removes_dead_link_without_touching_target(self, tmp_path):
        """``remove_path`` must drop a dead link, not its (gone) target."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("x", encoding="utf-8")
        dst = tmp_path / "dst"
        ok, method, _ = create_link(src, dst)
        assert ok
        if method == "copy":
            pytest.skip("link creation fell back to copy on this platform")

        shutil.rmtree(src)
        remove_path(dst)
        assert not dst.exists()
        assert not is_symlink_or_junction(dst)

    def test_removes_live_link_keeps_target(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("keep me", encoding="utf-8")
        dst = tmp_path / "dst"
        ok, method, _ = create_link(src, dst)
        assert ok
        if method == "copy":
            pytest.skip("link creation fell back to copy on this platform")

        remove_path(dst)
        assert not dst.exists()
        assert (src / "SKILL.md").read_text(encoding="utf-8") == "keep me"

    def test_removes_plain_file_and_dir(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x", encoding="utf-8")
        remove_path(f)
        assert not f.exists()

        d = tmp_path / "d"
        d.mkdir()
        (d / "inner.txt").write_text("x", encoding="utf-8")
        remove_path(d)
        assert not d.exists()

    def test_nonexistent_path_is_a_noop(self, tmp_path):
        remove_path(tmp_path / "never-existed")  # must not raise


class TestCreateLink:
    def test_creates_link_to_directory(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("content")
        dst = tmp_path / "dst"

        success, method, msg = create_link(src, dst)
        assert success
        assert method in ("symlink", "junction", "copy")
        assert (dst / "SKILL.md").exists()

    def test_replaces_identical_existing(self, tmp_path):
        """Same content as central -> safe to swap the real dir for a link."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("new")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "SKILL.md").write_text("new")

        success, method, msg = create_link(src, dst)
        assert success
        assert (dst / "SKILL.md").exists()

    def test_conflicting_real_dir_is_protected(self, tmp_path):
        """v0.13.0: a differing real dir is never silently destroyed."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("new")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "old.txt").write_text("user edits")

        success, method, msg = create_link(src, dst)
        assert not success
        assert method == "conflict"
        assert (dst / "old.txt").exists()          # untouched
        assert not (dst / "SKILL.md").exists()

    def test_force_overwrites_conflicting_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("new")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "old.txt").write_text("old")

        success, method, msg = create_link(src, dst, force=True)
        assert success
        assert method in ("symlink", "junction", "copy")
        assert (dst / "SKILL.md").exists()
        assert not (dst / "old.txt").exists()

    def test_source_not_found(self, tmp_path):
        success, method, msg = create_link(tmp_path / "noexist", tmp_path / "dst")
        assert not success
        assert method == "error"


class TestCopySkill:
    def test_copies_directory(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("content")
        (src / "scripts").mkdir()
        (src / "scripts" / "run.py").write_text("# script")

        dst = tmp_path / "dst"
        copy_skill(src, dst)
        assert (dst / "SKILL.md").exists()
        assert (dst / "scripts" / "run.py").exists()

    def test_replaces_existing(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "SKILL.md").write_text("new")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "old.txt").write_text("old")

        copy_skill(src, dst)
        assert (dst / "SKILL.md").exists()
        assert not (dst / "old.txt").exists()


class TestReadSkillMetadata:
    def test_reads_name_and_description(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n# Body\n"
        )
        meta = read_skill_metadata(skill_dir)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "A test skill"

    def test_returns_empty_for_no_skill_md(self, tmp_path):
        meta = read_skill_metadata(tmp_path)
        assert meta["name"] == ""
        assert meta["description"] == ""

    def test_handles_multiline_description(self, tmp_path):
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\ndescription: >\n  Multi-line description here\n---\n"
        )
        meta = read_skill_metadata(skill_dir)
        assert meta["name"] == "test"
