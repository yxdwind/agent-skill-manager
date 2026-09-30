"""Tests for the native fs-event watcher backends (v0.10.0).

The integration tests run against the real filesystem with the platform's
native backend (inotify on Linux CI, kqueue on macOS, ReadDirectoryChangesW
on Windows), so all three code paths are exercised by the CI matrix.  When
no native backend can be established the strict tests skip - the poll
fallback is covered separately.
"""
from __future__ import annotations

import shutil
import threading
import time

import pytest

from agent_skill_manager.utils import watcher as wmod
from agent_skill_manager.utils.watcher import PollingWatcher, create_watcher


# ---------------------------------------------------------------- factory

class TestFactory:
    def test_backend_has_shared_interface(self, tmp_path):
        w = create_watcher(tmp_path)
        assert w.describe() in {
            "inotify", "kqueue", "ReadDirectoryChangesW", "poll",
        }
        w.close()

    def test_unsupported_platform_falls_back_to_poll(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wmod.platform, "system", lambda: "SunOS")
        w = create_watcher(tmp_path)
        assert isinstance(w, PollingWatcher)
        assert w.describe() == "poll"
        w.close()


# ---------------------------------------------------------------- polling

class TestPolling:
    def test_wait_ticks_and_returns_true(self):
        w = PollingWatcher(interval=0.05)
        t0 = time.monotonic()
        assert w.wait(5.0) is True
        assert time.monotonic() - t0 >= 0.04
        w.close()

    def test_close_is_idempotent(self):
        w = PollingWatcher()
        w.close()
        w.close()


# ---------------------------------------------------------------- native

def _skip_if_poll(w):
    if w.describe() == "poll":
        pytest.skip("no native fs-event backend available on this host")


@pytest.fixture()
def central(tmp_path):
    d = tmp_path / "central"
    d.mkdir()
    return d


class TestNativeWatch:
    def test_quiet_timeout_returns_false(self, central):
        w = create_watcher(central)
        _skip_if_poll(w)
        assert w.wait(0.5) is False
        w.close()

    def test_file_write_detected(self, central):
        w = create_watcher(central)
        _skip_if_poll(w)

        def touch():
            time.sleep(0.2)
            (central / "a.txt").write_text("x", encoding="utf-8")

        threading.Thread(target=touch, daemon=True).start()
        assert w.wait(5.0) is True
        w.close()

    def test_file_delete_detected(self, central):
        w = create_watcher(central)
        _skip_if_poll(w)
        f = central / "gone.txt"
        f.write_text("x", encoding="utf-8")
        time.sleep(0.3)
        assert w.wait(2.0) is True          # create event
        time.sleep(0.5)
        f.unlink()
        assert w.wait(5.0) is True          # delete event
        w.close()

    def test_new_subtree_change_detected(self, central):
        """Mkdir, settle, then write INSIDE the new dir.

        Only a watch covering the new subdirectory can see the inner write:
        the parent dir is untouched.  Proves inotify's dynamic subtree add,
        kqueue's post-event sweep and Windows' native recursion.
        """
        w = create_watcher(central)
        _skip_if_poll(w)
        sub = central / "new-skill"
        sub.mkdir()
        assert w.wait(5.0) is True          # mkdir event; sub gets registered
        time.sleep(0.2)
        (sub / "SKILL.md").write_text("hello", encoding="utf-8")
        assert w.wait(5.0) is True          # visible only via the subtree watch
        w.close()

    def test_root_recreate_detected(self, central):
        """Root deleted -> one True; recreated -> watches re-established."""
        w = create_watcher(central)
        _skip_if_poll(w)
        shutil.rmtree(central)
        assert w.wait(5.0) is True          # deletion surfaced
        time.sleep(0.2)
        central.mkdir()
        assert w.wait(5.0) is True          # recreation re-arms the backend
        (central / "back.txt").write_text("x", encoding="utf-8")
        assert w.wait(5.0) is True          # events work after recovery
        w.close()

    def test_close_is_idempotent(self, central):
        w = create_watcher(central)
        w.close()
        w.close()
