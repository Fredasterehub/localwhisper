import time
import sys
import os
import ctypes
from ctypes import wintypes
from pynput.keyboard import Controller, Key
from core.settings import manager as settings
from core.logger import log

class Injector:
    def __init__(self):
        self.keyboard = Controller()
        self._terminal_processes = set()
        self._paste_hotkey_order = []
        self._refresh_config()

    def _refresh_config(self):
        processes = settings.get("terminal_processes")
        if isinstance(processes, list) and processes:
            self._terminal_processes = {str(p).lower() for p in processes if str(p).strip()}
        else:
            self._terminal_processes = {"windowsterminal.exe", "wt.exe", "conhost.exe"}

        order = settings.get("paste_hotkey_order")
        if isinstance(order, list) and order:
            self._paste_hotkey_order = [str(x).lower() for x in order if str(x).strip()]
        else:
            self._paste_hotkey_order = ["ctrl+shift+v", "shift+insert", "ctrl+v"]

    @staticmethod
    def _get_foreground_process_name() -> str | None:
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            GetForegroundWindow = user32.GetForegroundWindow
            GetForegroundWindow.restype = wintypes.HWND

            GetWindowThreadProcessId = user32.GetWindowThreadProcessId
            GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            GetWindowThreadProcessId.restype = wintypes.DWORD

            QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
            QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
            QueryFullProcessImageNameW.restype = wintypes.BOOL

            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            hwnd = GetForegroundWindow()
            if not hwnd:
                return None

            pid = wintypes.DWORD(0)
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return None

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            hproc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not hproc:
                return None

            try:
                buf_len = wintypes.DWORD(260)
                buf = ctypes.create_unicode_buffer(buf_len.value)
                if not QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(buf_len)):
                    return None
                exe = os.path.basename(buf.value).lower()
                return exe or None
            finally:
                CloseHandle(hproc)
        except Exception:
            return None

    def _is_terminal(self, process_name: str | None) -> bool:
        if not process_name:
            return False
        return process_name.lower() in self._terminal_processes

    def _press_combo(self, combo: str) -> bool:
        """
        combo examples: 'ctrl+v', 'ctrl+shift+v', 'shift+insert'
        Returns True if we attempted to send it without throwing.
        """
        try:
            parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
            if not parts:
                return False

            mods = []
            key = parts[-1]
            for p in parts[:-1]:
                if p in {"ctrl", "control"}:
                    mods.append(Key.ctrl)
                elif p == "shift":
                    mods.append(Key.shift)
                elif p == "alt":
                    mods.append(Key.alt)

            def press_key(k: str):
                if k == "insert":
                    self.keyboard.press(Key.insert)
                    self.keyboard.release(Key.insert)
                else:
                    self.keyboard.type(k)

            ctx = None
            # Nest pressed() contexts for modifiers.
            if mods:
                ctx = self.keyboard.pressed(mods[0])
                ctx.__enter__()
                entered = [ctx]
                for m in mods[1:]:
                    c = self.keyboard.pressed(m)
                    c.__enter__()
                    entered.append(c)
                try:
                    press_key(key)
                finally:
                    for c in reversed(entered):
                        c.__exit__(None, None, None)
            else:
                press_key(key)
            return True
        except Exception:
            return False

    def _send_paste_hotkey(self, is_terminal: bool):
        if not is_terminal:
            self._press_combo("ctrl+v")
            return

        # Configurable ordering; we only fall back if sending the combo throws.
        for combo in self._paste_hotkey_order:
            if self._press_combo(combo):
                return
        # Last resort
        self._press_combo("ctrl+v")

    # --- Clipboard (Win32) ---
    _CF_UNICODETEXT = 13
    _GMEM_MOVEABLE = 0x0002
    
    # Formats that are GDI handles or otherwise unsafe/pointless to GlobalLock() as memory.
    # 2=Bitmap, 3=MetafilePict, 9=Palette, 14=EnhMetaFile, 17=DIB, 8=DIBv5
    _UNSAFE_FORMATS = {2, 3, 9, 14, 17, 8}

    def _clipboard_open_retry(self) -> bool:
        tries = int(settings.get("inject_clipboard_retry_count"))
        backoff_ms = int(settings.get("inject_clipboard_retry_backoff_ms"))
        delay = max(0.0, backoff_ms / 1000.0)

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        OpenClipboard = user32.OpenClipboard
        OpenClipboard.argtypes = [wintypes.HWND]
        OpenClipboard.restype = wintypes.BOOL

        for _ in range(max(1, tries)):
            if OpenClipboard(None):
                return True
            time.sleep(delay)
            delay = min(0.25, delay * 2.0 if delay else 0.02)
        return False

    @staticmethod
    def _clipboard_close():
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.CloseClipboard()

    @staticmethod
    def _clipboard_get_sequence() -> int:
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            GetClipboardSequenceNumber = user32.GetClipboardSequenceNumber
            GetClipboardSequenceNumber.restype = wintypes.DWORD
            return int(GetClipboardSequenceNumber())
        except Exception:
            return -1

    def _clipboard_get_unicode_text_unsafe(self) -> str | None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        GetClipboardData = user32.GetClipboardData
        GetClipboardData.argtypes = [wintypes.UINT]
        GetClipboardData.restype = wintypes.HANDLE

        GlobalLock = kernel32.GlobalLock
        GlobalLock.argtypes = [wintypes.HGLOBAL]
        GlobalLock.restype = wintypes.LPVOID

        GlobalUnlock = kernel32.GlobalUnlock
        GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        GlobalUnlock.restype = wintypes.BOOL

        h = GetClipboardData(self._CF_UNICODETEXT)
        if not h:
            return None
        p = GlobalLock(h)
        if not p:
            return None
        try:
            return ctypes.wstring_at(p)
        finally:
            GlobalUnlock(h)

    def _clipboard_snapshot_unsafe(self) -> tuple[int, bool, list[tuple[int, bytes]]]:
        """
        Returns (sequence_number, formats_bytes) for all GlobalAlloc-able formats.
        Skip GDI handle formats that cause GlobalLock to crash/fail.
        """
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        EnumClipboardFormats = user32.EnumClipboardFormats
        EnumClipboardFormats.argtypes = [wintypes.UINT]
        EnumClipboardFormats.restype = wintypes.UINT

        GetClipboardData = user32.GetClipboardData
        GetClipboardData.argtypes = [wintypes.UINT]
        GetClipboardData.restype = wintypes.HANDLE

        GlobalSize = kernel32.GlobalSize
        GlobalSize.argtypes = [wintypes.HGLOBAL]
        GlobalSize.restype = ctypes.c_size_t

        GlobalLock = kernel32.GlobalLock
        GlobalLock.argtypes = [wintypes.HGLOBAL]
        GlobalLock.restype = wintypes.LPVOID

        GlobalUnlock = kernel32.GlobalUnlock
        GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        GlobalUnlock.restype = wintypes.BOOL

        seq = self._clipboard_get_sequence()
        out: list[tuple[int, bytes]] = []
        had_any = False

        fmt = 0
        while True:
            fmt = int(EnumClipboardFormats(fmt))
            if fmt == 0:
                break
            had_any = True
            
            # CRITICAL: Skip bitmap/GDI formats because GetClipboardData returns a GDI handle,
            # NOT a global memory handle. GlobalLocking it can crash or return junk.
            if fmt in self._UNSAFE_FORMATS:
                continue

            h = GetClipboardData(fmt)
            if not h:
                continue
            try:
                size = int(GlobalSize(h))
                if size <= 0:
                    continue
                p = GlobalLock(h)
                if not p:
                    continue
                try:
                    data = ctypes.string_at(p, size)
                    out.append((fmt, data))
                finally:
                    GlobalUnlock(h)
            except Exception:
                # Likely a non-global handle format we missed; skip.
                continue

        return seq, had_any, out
    
    def _is_clipboard_safe_to_restore(self) -> bool:
        """
        Returns False if clipboard contains data we cannot backup/restore safely (like images).
        """
        if not self._clipboard_open_retry():
            return False # Assume unsafe if we can't open it
        
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            EnumClipboardFormats = user32.EnumClipboardFormats
            EnumClipboardFormats.argtypes = [wintypes.UINT]
            EnumClipboardFormats.restype = wintypes.UINT
            
            fmt = 0
            while True:
                fmt = int(EnumClipboardFormats(fmt))
                if fmt == 0:
                    break
                if fmt in self._UNSAFE_FORMATS:
                    return False
            return True
        finally:
            self._clipboard_close()

    def _clipboard_set_formats_unsafe(self, formats: list[tuple[int, bytes]]) -> bool:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        EmptyClipboard = user32.EmptyClipboard
        EmptyClipboard.restype = wintypes.BOOL

        SetClipboardData = user32.SetClipboardData
        SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        SetClipboardData.restype = wintypes.HANDLE

        GlobalAlloc = kernel32.GlobalAlloc
        GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        GlobalAlloc.restype = wintypes.HGLOBAL

        GlobalLock = kernel32.GlobalLock
        GlobalLock.argtypes = [wintypes.HGLOBAL]
        GlobalLock.restype = wintypes.LPVOID

        GlobalUnlock = kernel32.GlobalUnlock
        GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        GlobalUnlock.restype = wintypes.BOOL

        if not EmptyClipboard():
            return False

        # Restore in stable order.
        for fmt, data in sorted(formats, key=lambda x: x[0]):
            try:
                h = GlobalAlloc(self._GMEM_MOVEABLE, len(data))
                if not h:
                    continue
                p = GlobalLock(h)
                if not p:
                    continue
                try:
                    ctypes.memmove(p, data, len(data))
                finally:
                    GlobalUnlock(h)
                if not SetClipboardData(int(fmt), h):
                    # If SetClipboardData fails, the system does not own h; leak avoidance is non-trivial here.
                    continue
            except Exception:
                continue
        return True

    def _clipboard_set_unicode_text_unsafe(self, text: str) -> bool:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        EmptyClipboard = user32.EmptyClipboard
        EmptyClipboard.restype = wintypes.BOOL

        SetClipboardData = user32.SetClipboardData
        SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        SetClipboardData.restype = wintypes.HANDLE

        GlobalAlloc = kernel32.GlobalAlloc
        GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        GlobalAlloc.restype = wintypes.HGLOBAL

        GlobalLock = kernel32.GlobalLock
        GlobalLock.argtypes = [wintypes.HGLOBAL]
        GlobalLock.restype = wintypes.LPVOID

        GlobalUnlock = kernel32.GlobalUnlock
        GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        GlobalUnlock.restype = wintypes.BOOL

        if not EmptyClipboard():
            return False

        # Windows expects UTF-16LE including null terminator.
        raw = (text + "\x00").encode("utf-16le")
        h = GlobalAlloc(self._GMEM_MOVEABLE, len(raw))
        if not h:
            return False
        p = GlobalLock(h)
        if not p:
            return False
        try:
            ctypes.memmove(p, raw, len(raw))
        finally:
            GlobalUnlock(h)
        return bool(SetClipboardData(self._CF_UNICODETEXT, h))

    def _paste_via_clipboard(self, text: str, is_terminal: bool):
        clipboard_settle_ms = int(settings.get("inject_clipboard_settle_ms"))
        restore_delay_ms = int(settings.get("inject_clipboard_restore_delay_ms"))

        if not self._clipboard_open_retry():
            raise RuntimeError("clipboard_busy_open")
        try:
            before_seq, had_any, snapshot = self._clipboard_snapshot_unsafe()
            if had_any and not snapshot:
                # If we detected content but failed to snapshot ANY of it suitable for restore,
                # we technically risk losing data.
                # However, with _UNSAFE_FORMATS ignored, this is expected behavior for image-only clipboards.
                pass

            if not self._clipboard_set_unicode_text_unsafe(text):
                raise RuntimeError("clipboard_busy_set")
            after_seq = self._clipboard_get_sequence()
        finally:
            self._clipboard_close()

        time.sleep(max(0.01, clipboard_settle_ms / 1000.0))
        self._send_paste_hotkey(is_terminal=is_terminal)

        # Restore previous clipboard ONLY if unchanged (prevents clobbering user copies).
        time.sleep(max(0.30, restore_delay_ms / 1000.0))
        if not self._clipboard_open_retry():
            return
        try:
            now_seq = self._clipboard_get_sequence()
            current = self._clipboard_get_unicode_text_unsafe()
            if (now_seq == after_seq) and (current == text):
                if snapshot:
                    self._clipboard_set_formats_unsafe(snapshot)
                elif not had_any:
                    # Clipboard was explicitly empty before; restore empty.
                    # If it had formats but we filtered them all out (images), 
                    # DO NOT clear the clipboard, or we lose the user's image! 
                    # But wait, if we are here, we successfully pasted TEXT. 
                    # So the clipboard currently contains TEXT.
                    # We need to restore the IMAGE. 
                    # But we consciously chose NOT to snapshot the image data.
                    # THIS IS A PROBLEM. We cannot restore what we didn't save.
                    # This confirms why we must check _is_clipboard_safe_to_restore() BEFORE this method 
                    # and abort pasting if unsafe.
                    self._clipboard_set_formats_unsafe([])
        finally:
            self._clipboard_close()

    def type_text(self, text):
        """
        Inject text into active window.
        Terminal-safe: paste in terminals (SSH/tmux friendly), type only very short text elsewhere.
        Clipboard-safe: "borrow and restore" without clobbering user clipboard changes.
        """
        if not text:
            return

        self._refresh_config()
        process_name = self._get_foreground_process_name()
        is_terminal = self._is_terminal(process_name) and bool(settings.get("inject_terminal_always_paste"))
        typing_max = int(settings.get("inject_typing_max_chars"))

        # Safety check: if clipboard has stuff we can't backup (images), DO NOT touch it.
        # This will force fallback to typing below.
        clipboard_safe = True
        if is_terminal or (len(text) > typing_max):
            # Only check if we are actually considering using paste
            if not self._is_clipboard_safe_to_restore():
                clipboard_safe = False
                log("Clipboard contains unsafe/binary data; falling back to typing to preserve it.", "info")

        use_paste = clipboard_safe and (is_terminal or (len(text) > typing_max))
        log(f"Injecting ({'paste' if use_paste else 'type'}) into {process_name or 'unknown'}: {text}", "debug")

        if use_paste:
            try:
                self._paste_via_clipboard(text, is_terminal=is_terminal)
                return
            except Exception as e:
                log(f"Clipboard Injection Failed: {e}", "warning")
                # Fallback to typing (non-terminal only).
                if is_terminal:
                    return

        try:
            self.keyboard.type(text)
        except Exception as e:
            log(f"Injection Failed: {e}", "error")

if __name__ == "__main__":
    time.sleep(2)
    inj = Injector()
    inj.type_text("Short text types.")
