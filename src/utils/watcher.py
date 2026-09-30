"""Native filesystem event watchers - stdlib only.

"fsnotify-grade" backends for ``askill watch``: instead of blindly polling,
the watch loop sleeps on real OS file events and rescans only when something
actually happened.  Three native backends, all built on the Python standard
library so the zero-dependency guarantee holds:

- Linux     inotify                via ctypes on libc
- macOS     kqueue (KQ_FILTER_VNODE) via select.kqueue()
- Windows   ReadDirectoryChangesW  via ctypes on kernel32 (recursive natively)

Shared interface::

    w = create_watcher(root, poll_interval=3.0)
    w.describe() -> str      # backend name for status output
    w.wait(timeout) -> bool  # True = filesystem may have changed
    w.close()                # release handles; idempotent

``wait()`` returns False only when nothing was observed for ``timeout``
seconds; the periodic timeout therefore doubles as the watch loop's
reconciliation tick (protection against missed events, queue overflow and
root-directory recreation).  True may be spurious - callers re-diff cheap
snapshots to decide what actually changed.

If a native backend is unavailable at start-up (restricted kernel, exotic
libc) or dies at run-time, callers fall back to :class:`PollingWatcher`,
which simply ticks every ``poll_interval`` seconds - the pre-v0.10 behavior.
"""
from __future__ import annotations

import ctypes
import os
import platform
import select
import struct
import threading
import time
from pathlib import Path

# Quiet period an event burst must settle into before ``wait`` reports
# True.  Editors usually save via several syscalls (tmp file + rename);
# without debounce a single save would wake the sync loop repeatedly.
DEBOUNCE_S = 0.4

_DEFAULT_POLL_INTERVAL = 3.0


# ---------------------------------------------------------------- fallback

class PollingWatcher:
    """Timer-based watcher - the universal fallback.

    ``wait(timeout)`` sleeps ``min(interval, timeout)`` and returns True, so
    a watch loop driven by it rescans on exactly the old polling cadence.
    """

    def __init__(self, root=None, interval: float = _DEFAULT_POLL_INTERVAL):
        self._interval = max(float(interval), 0.05)

    def describe(self) -> str:
        return "poll"

    def wait(self, timeout: float) -> bool:
        time.sleep(min(self._interval, max(float(timeout), 0.0)))
        return True

    def close(self) -> None:
        pass


# ---------------------------------------------------------------- Linux

# inotify event masks (linux/inotify.h)
_IN_MODIFY = 0x02
_IN_ATTRIB = 0x04
_IN_CLOSE_WRITE = 0x08
_IN_MOVED_FROM = 0x40
_IN_MOVED_TO = 0x80
_IN_CREATE = 0x100
_IN_DELETE = 0x200
_IN_DELETE_SELF = 0x400
_IN_MOVE_SELF = 0x800
_IN_IGNORED = 0x8000
_IN_Q_OVERFLOW = 0x4000
_IN_ISDIR = 0x40000000

_IN_FLAGS = (
    _IN_MODIFY | _IN_ATTRIB | _IN_CLOSE_WRITE | _IN_MOVED_FROM | _IN_MOVED_TO
    | _IN_CREATE | _IN_DELETE | _IN_DELETE_SELF | _IN_MOVE_SELF
)

_IN_EVENT_HEADER = struct.Struct("=iIII")   # wd, mask, cookie, name_len


class _InotifyWatcher:
    """Linux backend: inotify via ctypes, single-threaded select() loop."""

    def __init__(self, root):
        self._root = Path(root)
        self._libc = ctypes.CDLL(None, use_errno=True)
        self._libc.inotify_init1.argtypes = (ctypes.c_int,)
        self._libc.inotify_init1.restype = ctypes.c_int
        self._libc.inotify_add_watch.argtypes = (
            ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32,
        )
        self._libc.inotify_add_watch.restype = ctypes.c_int
        self._fd = None
        self._wd_path: dict[int, Path] = {}
        self._setup()
        if not self._wd_path:
            raise OSError("inotify: no watches could be established")

    def describe(self) -> str:
        return "inotify"

    # -- setup / teardown ------------------------------------------------

    def _setup(self) -> None:
        fd = self._libc.inotify_init1(os.O_NONBLOCK)
        if fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1 failed")
        self._fd = fd
        self._wd_path.clear()
        self._add_tree(self._root)

    def _teardown(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        self._wd_path.clear()

    def _add_tree(self, top: Path) -> None:
        """Register every (real) directory under *top*, including top itself."""
        for dirpath, dirnames, _files in os.walk(top):
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            self._register(Path(dirpath), strict=False)

    def _register(self, path: Path, strict: bool) -> None:
        if self._fd is None:
            return
        wd = self._libc.inotify_add_watch(
            self._fd, os.fsencode(str(path)), _IN_FLAGS,
        )
        if wd >= 0:
            self._wd_path[wd] = path
        elif strict:
            err = ctypes.get_errno()
            raise OSError(err, f"inotify_add_watch failed: {path}")

    # -- event handling --------------------------------------------------

    def _read_events(self) -> None:
        """Drain the inotify fd once, updating watch state."""
        try:
            chunk = os.read(self._fd, 1 << 20)
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            self._teardown()
            return
        off = 0
        while off + _IN_EVENT_HEADER.size <= len(chunk):
            wd, mask, _cookie, name_len = _IN_EVENT_HEADER.unpack_from(chunk, off)
            name = chunk[off + _IN_EVENT_HEADER.size:off + _IN_EVENT_HEADER.size + name_len]
            name = name.split(b"\0", 1)[0]
            off += _IN_EVENT_HEADER.size + name_len

            if mask & _IN_IGNORED:
                self._wd_path.pop(wd, None)
                continue
            if mask & _IN_Q_OVERFLOW:
                continue    # wait() already reports True; reconcile covers it

            path = self._wd_path.get(wd)
            if path is None:
                continue
            if mask & (_IN_DELETE_SELF | _IN_MOVE_SELF):
                if path == self._root:
                    self._teardown()    # root gone; recover on next wait()
                    return
                self._wd_path.pop(wd, None)
                continue
            # a directory appeared inside a watched dir -> watch its subtree
            if mask & _IN_ISDIR and mask & _IN_CREATE and name:
                child = path / os.fsdecode(name)
                if child.is_dir() and not child.is_symlink():
                    try:
                        self._add_tree(child)
                    except OSError:
                        pass    # parent watch still reports dir-level changes

    # -- interface -------------------------------------------------------

    def wait(self, timeout: float) -> bool:
        if self._fd is None:
            return self._recover_or_sleep(timeout)
        ready, _, _ = select.select([self._fd], [], [], float(timeout))
        if not ready:
            return False
        self._read_events()
        self._debounce()
        return True

    def _debounce(self) -> None:
        """Keep consuming until the stream is quiet for DEBOUNCE_S."""
        deadline = time.monotonic() + DEBOUNCE_S
        while True:
            if self._fd is None:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            ready, _, _ = select.select([self._fd], [], [], remaining)
            if not ready:
                return
            self._read_events()
            deadline = time.monotonic() + DEBOUNCE_S

    def _recover_or_sleep(self, timeout: float) -> bool:
        """Root was deleted/moved: re-arm when it reappears, else idle."""
        if self._root.is_dir():
            try:
                self._setup()
                return True     # force a diff of whatever reappeared
            except OSError:
                pass
        time.sleep(min(float(timeout), 1.0))
        return False

    def close(self) -> None:
        self._teardown()


# ---------------------------------------------------------------- macOS

# KQ_NOTE_* attributes exist only in Darwin builds of the select module;
# other platforms import this module, so the constant is set up lazily.
_KQ_NOTES = 0
if platform.system() == "Darwin":
    _KQ_NOTES = (
        select.KQ_NOTE_WRITE | select.KQ_NOTE_EXTEND | select.KQ_NOTE_DELETE
        | select.KQ_NOTE_RENAME | select.KQ_NOTE_REVOKE
    )


class _KqueueWatcher:
    """macOS backend: kqueue vnode notes via select.kqueue().

    Each directory is watched through an O_EVTONLY fd; NOTE_WRITE on a
    directory fires for create/delete/rename of its direct children, and a
    sweep after every event batch registers directories that appeared.
    """

    def __init__(self, root):
        if not hasattr(select, "kqueue"):
            raise OSError("kqueue not available")
        self._root = Path(root)
        self._kq = select.kqueue()
        self._fds: dict[int, Path] = {}
        self._root_gone = False
        self._register_tree(self._root)
        if not self._fds:
            self._kq.close()
            raise OSError("kqueue: no watches could be established")

    def describe(self) -> str:
        return "kqueue"

    # -- setup / teardown ------------------------------------------------

    def _register(self, path: Path) -> None:
        fd = os.open(path, os.O_RDONLY | os.O_EVTONLY)
        try:
            kev = select.kevent(
                fd, select.KQ_FILTER_VNODE,
                select.KQ_EV_ADD | select.KQ_EV_CLEAR, _KQ_NOTES,
            )
            self._kq.control([kev], 0, 0)
        except Exception:
            os.close(fd)
            raise
        self._fds[fd] = path

    def _register_tree(self, top: Path) -> None:
        for dirpath, dirnames, _files in os.walk(top):
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            self._register(Path(dirpath))

    def _register_new_dirs(self) -> None:
        watched = set(self._fds.values())
        for dirpath, dirnames, _files in os.walk(self._root):
            dirnames[:] = [
                d for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            for d in dirnames:
                p = Path(dirpath) / d
                if p not in watched:
                    try:
                        self._register(p)
                    except OSError:
                        pass

    def _drop_fd(self, fd: int) -> None:
        self._fds.pop(fd, None)
        try:
            os.close(fd)
        except OSError:
            pass

    # -- event handling --------------------------------------------------

    def _process(self, events) -> None:
        for ev in events:
            fflags = ev.fflags
            if fflags & (select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME
                         | select.KQ_NOTE_REVOKE):
                path = self._fds.get(ev.ident)
                self._drop_fd(ev.ident)
                if path == self._root:
                    self._root_gone = True
        if not self._root_gone:
            self._register_new_dirs()

    # -- interface -------------------------------------------------------

    def wait(self, timeout: float) -> bool:
        if self._root_gone:
            return self._recover_or_sleep(timeout)
        events = self._kq.control(None, 32, float(timeout))
        if not events:
            return False
        self._process(events)
        self._debounce()
        return True

    def _debounce(self) -> None:
        deadline = time.monotonic() + DEBOUNCE_S
        while True:
            if self._root_gone:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            events = self._kq.control(None, 32, remaining)
            if not events:
                return
            self._process(events)
            deadline = time.monotonic() + DEBOUNCE_S

    def _recover_or_sleep(self, timeout: float) -> bool:
        if self._root.is_dir():
            for fd in list(self._fds):
                self._drop_fd(fd)
            try:
                self._register_tree(self._root)
                self._root_gone = False
                return True
            except OSError:
                pass
        time.sleep(min(float(timeout), 1.0))
        return False

    def close(self) -> None:
        for fd in list(self._fds):
            self._drop_fd(fd)
        try:
            self._kq.close()
        except OSError:
            pass


# ---------------------------------------------------------------- Windows

if platform.system() == "Windows":
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateFileW.restype = wintypes.HANDLE
    _k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    _k32.ReadDirectoryChangesW.restype = wintypes.BOOL
    _k32.ReadDirectoryChangesW.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, wintypes.BOOL,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    _k32.CancelIoEx.restype = wintypes.BOOL
    _k32.CancelIoEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    _k32.CloseHandle.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]

    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _WinDirChangeWatcher:
    """Windows backend: ReadDirectoryChangesW on a background thread.

    The kernel call is blocking and watches the whole subtree natively
    (bWatchSubtree=TRUE); a daemon thread turns each delivered buffer into
    an event so the main thread can ``wait()`` with a timeout.
    """

    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_SHARE_RWX = 1 | 2 | 4
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _NOTIFY = (0x1 | 0x2 | 0x8 | 0x10)  # FILE_NAME|DIR_NAME|SIZE|LAST_WRITE

    def __init__(self, root):
        self._root = Path(root)
        self._event = threading.Event()
        self._closed = False
        self._thread = None
        self._absent_reported = False
        self._open()
        self._thread = threading.Thread(
            target=self._read_loop, name="askill-watch", daemon=True,
        )
        self._thread.start()

    def describe(self) -> str:
        return "ReadDirectoryChangesW"

    # -- setup / teardown ------------------------------------------------

    def _open(self) -> None:
        handle = _k32.CreateFileW(
            str(self._root), self._FILE_LIST_DIRECTORY, self._FILE_SHARE_RWX,
            None, self._OPEN_EXISTING, self._FILE_FLAG_BACKUP_SEMANTICS, None,
        )
        if not handle or handle == _INVALID_HANDLE_VALUE:
            raise OSError(
                ctypes.get_last_error(), "CreateFileW failed", str(self._root),
            )
        self._handle = handle

    def _close_handle(self) -> None:
        handle = getattr(self, "_handle", None)
        self._handle = None
        if handle:
            _k32.CancelIoEx(handle, None)
            _k32.CloseHandle(handle)

    # -- reader thread ---------------------------------------------------

    def _read_loop(self) -> None:
        buf = ctypes.create_string_buffer(65536)
        returned = wintypes.DWORD(0)
        handle = self._handle
        while not self._closed and handle:
            ok = _k32.ReadDirectoryChangesW(
                handle, buf, len(buf), True, self._NOTIFY,
                ctypes.byref(returned), None, None,
            )
            if not ok:
                break   # closed/cancelled, or root vanished
            if returned.value == 0:
                self._event.set()   # buffer overflow - treat as change
                continue
            off = 0
            while off + 12 <= returned.value:
                next_off, _action, _name_len = struct.unpack_from("<III", buf, off)
                if next_off == 0:
                    break
                off += next_off
            self._event.set()

    # -- interface -------------------------------------------------------

    def wait(self, timeout: float) -> bool:
        if self._closed:
            return False
        if self._handle is None or (
            self._thread is not None and not self._thread.is_alive()
        ):
            return self._recover_or_sleep(timeout)
        if not self._event.wait(float(timeout)):
            return False
        time.sleep(DEBOUNCE_S)  # let an editor's multi-syscall save finish
        self._event.clear()
        return True

    def _recover_or_sleep(self, timeout: float) -> bool:
        """Reader thread died: reopen if the root is back, else idle.

        A vanished root must still surface as one True (it is a change the
        watch loop needs, so dead links get cleaned) - hence the one-shot
        ``_absent_reported`` flag instead of a busy-looping always-True.
        """
        if self._closed:
            return False
        if self._root.is_dir():
            try:
                self._close_handle()
                self._open()
                if self._thread is None or not self._thread.is_alive():
                    self._thread = threading.Thread(
                        target=self._read_loop, name="askill-watch", daemon=True,
                    )
                    self._thread.start()
                self._absent_reported = False
                return True
            except OSError:
                pass
        if not self._absent_reported:
            self._absent_reported = True
            return True
        time.sleep(min(float(timeout), 1.0))
        return False

    def close(self) -> None:
        self._closed = True
        self._close_handle()
        self._event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)


# ---------------------------------------------------------------- factory

_BACKENDS = {
    "Linux": (_InotifyWatcher,),
    "Darwin": (_KqueueWatcher,),
    "Windows": (_WinDirChangeWatcher,),
}


def create_watcher(root, poll_interval: float = _DEFAULT_POLL_INTERVAL):
    """Create the best available watcher for *root* on this platform.

    Native backends are tried first; if none can be established the
    universal :class:`PollingWatcher` is returned, so the result always
    offers the full interface.
    """
    system = platform.system()
    for cls in _BACKENDS.get(system, ()):
        try:
            return cls(Path(root))
        except (OSError, AttributeError, ValueError):
            continue
    return PollingWatcher(root, interval=poll_interval)
