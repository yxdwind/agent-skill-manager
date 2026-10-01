"""Tests for agent_skill_manager.products module."""

from pathlib import Path

from agent_skill_manager.config import products as prod_mod
from agent_skill_manager.config.products import (
    CENTRAL_DIR,
    PRODUCTS,
    get_all_product_dirs,
    get_product_by_short,
    get_product_path,
)


class TestProducts:
    def test_products_not_empty(self):
        assert len(PRODUCTS) >= 9

    def test_all_have_required_fields(self):
        required = {"name", "short", "macos_path", "windows_path", "linux_path", "sync_method"}
        for p in PRODUCTS:
            assert required.issubset(p.keys()), f"Missing fields in {p.get('name')}"

    def test_short_names_unique(self):
        shorts = [p["short"] for p in PRODUCTS]
        assert len(shorts) == len(set(shorts)), "Short names must be unique"

    def test_central_dir_is_under_home(self):
        assert str(CENTRAL_DIR).startswith(str(Path.home()))

    def test_get_product_by_short(self):
        p = get_product_by_short("dumate")
        assert p is not None
        assert p["name"].startswith("DuMate")

    def test_get_product_by_short_not_found(self):
        assert get_product_by_short("nonexistent") is None

    def _assert_platform_path(self, short: str, expect_fragment: str):
        """On Linux desktop/IDE products without a build have linux_path=None."""
        from agent_skill_manager.config import products as prod_mod
        p = get_product_by_short(short)
        assert p is not None
        path = get_product_path(p)
        if prod_mod.IS_LINUX:
            assert path is None, f"{short} should have no Linux path"
            return
        assert path is not None
        assert expect_fragment in str(path)

    def test_get_product_path_returns_path_or_none(self):
        """Non-pack products expose a path on every platform they ship for.

        On Linux only the CLI-based products carry a linux_path - desktop /
        IDE apps without a Linux build stay None (v0.10.0).
        """
        linux_products = {
            "autoclaw2", "kimi", "minimax", "codebuddy", "comate", "zcode",
        }
        for p in PRODUCTS:
            path = get_product_path(p)
            if p["sync_method"] == "pack":
                assert path is None
            elif prod_mod.IS_LINUX:
                if p["short"] in linux_products:
                    assert isinstance(path, Path), p["short"]
                else:
                    assert path is None, p["short"]
            else:
                assert isinstance(path, Path), p["short"]

    def test_linux_paths_declared(self):
        """v0.10.0: exactly the CLI-based products support Linux."""
        declared = {
            p["short"] for p in PRODUCTS if p.get("linux_path") is not None
        }
        assert declared == {
            "autoclaw2", "kimi", "minimax", "codebuddy", "comate", "zcode",
        }

    def test_linux_platform_dispatch(self, monkeypatch):
        """get_product_path picks linux_path on Linux, incl. None products."""
        monkeypatch.setattr(prod_mod, "IS_WINDOWS", False)
        monkeypatch.setattr(prod_mod, "IS_MACOS", False)
        traecn = get_product_by_short("traecn")
        assert get_product_path(traecn) is None           # no Linux build
        zcode = get_product_by_short("zcode")
        assert get_product_path(zcode) == Path.home() / ".zcode" / "skills"
        kimi = get_product_by_short("kimi")
        dirs = get_all_product_dirs(kimi)
        assert Path.home() / ".kimi-code" / "skills" in dirs

    def test_windows_platform_dispatch(self, monkeypatch):
        monkeypatch.setattr(prod_mod, "IS_WINDOWS", True)
        monkeypatch.setattr(prod_mod, "IS_MACOS", False)
        p = get_product_by_short("doubaowork")
        assert "DoubaoWork" in str(get_product_path(p))

    def test_macos_platform_dispatch(self, monkeypatch):
        monkeypatch.setattr(prod_mod, "IS_WINDOWS", False)
        monkeypatch.setattr(prod_mod, "IS_MACOS", True)
        p = get_product_by_short("doubaowork")
        assert ".super_doubao" in str(get_product_path(p))

    def test_get_all_product_dirs_returns_list(self):
        for p in PRODUCTS:
            dirs = get_all_product_dirs(p)
            assert isinstance(dirs, list)

    def test_minimax_uses_central_dir(self):
        minimax = get_product_by_short("minimax")
        assert minimax["sync_method"] == "native"
        assert get_product_path(minimax) == CENTRAL_DIR

    def test_codebuddy_has_settings_file(self):
        cb = get_product_by_short("codebuddy")
        assert cb is not None
        assert "settings_file" in cb
        assert cb["settings_file"].name == "settings.json"

    def test_comate_path(self):
        comate = get_product_by_short("comate")
        assert comate is not None
        assert comate["sync_method"] == "symlink"
        path = get_product_path(comate)
        assert path is not None
        assert ".comate" in str(path)

    def test_qodercn_path(self):
        """v0.9.0: qoder entry was reworked to Qoder CN (~/.qoder-cn)."""
        qodercn = get_product_by_short("qodercn")
        assert qodercn is not None
        assert qodercn["sync_method"] == "symlink"
        self._assert_platform_path("qodercn", ".qoder-cn")
        assert get_product_by_short("qoder") is None

    def test_new_products_count(self):
        """Verify 3 new products were added."""
        shorts = {p["short"] for p in PRODUCTS}
        assert "codebuddy" in shorts
        assert "comate" in shorts
        assert "qodercn" in shorts


    def test_qwenwork_path(self):
        qwenwork = get_product_by_short("qwenwork")
        assert qwenwork is not None
        assert qwenwork["sync_method"] == "symlink"
        self._assert_platform_path("qwenwork", ".qwenworkcn")

    def test_doubaowork_path(self):
        dbw = get_product_by_short("doubaowork")
        assert dbw is not None
        assert dbw["sync_method"] == "symlink"
        self._assert_platform_path("doubaowork", ".user_skills")

    def test_newest_products_count(self):
        """Verify qwenwork + doubaowork were added."""
        shorts = {p["short"] for p in PRODUCTS}
        assert "qwenwork" in shorts
        assert "doubaowork" in shorts

    def test_v090_products_count(self):
        """v0.9.0: 15 products after adding Trae CN, TRAE SOLO CN, Qoder CN IDE, ZCode and reworking qoder/autoclaw."""
        assert len(PRODUCTS) == 15

    def test_traecn_path(self):
        self._assert_platform_path("traecn", ".trae-cn")

    def test_traesolo_shares_dir_with_traecn(self):
        traecn = get_product_path(get_product_by_short("traecn"))
        traesolo = get_product_path(get_product_by_short("traesolo"))
        assert traesolo == traecn

    def test_qodercnide_shares_dir_with_qodercn(self):
        qodercn = get_product_path(get_product_by_short("qodercn"))
        qodercnide = get_product_path(get_product_by_short("qodercnide"))
        assert qodercnide == qodercn

    def test_zcode_path(self):
        zcode = get_product_by_short("zcode")
        assert zcode is not None
        path = get_product_path(zcode)
        assert path is not None
        assert ".zcode" in str(path)

    def test_autoclaw2_path(self):
        """v0.9.0: autoclaw entry reworked to AutoClaw2 (~/.openclaw-autoclaw)."""
        autoclaw2 = get_product_by_short("autoclaw2")
        assert autoclaw2 is not None
        path = get_product_path(autoclaw2)
        assert path is not None
        assert ".openclaw-autoclaw" in str(path)
        assert get_product_by_short("autoclaw") is None
