"""
MMCSS (Multimedia Class Scheduler Service) integration for Windows.

Registers audio threads with the "Pro Audio" task for real-time priority,
ensuring consistent low-latency performance even under system load.
"""

import ctypes
from ctypes import wintypes
import platform
import threading
from core.logger import log

# MMCSS priority levels
AVRT_PRIORITY_CRITICAL = 2
AVRT_PRIORITY_HIGH = 1
AVRT_PRIORITY_NORMAL = 0
AVRT_PRIORITY_LOW = -1


class MMCSSManager:
    """
    Manages MMCSS registration for real-time audio threads on Windows.
    Safe no-op on non-Windows platforms.
    """

    def __init__(self):
        self._task_handles = {}  # thread_id -> task_handle
        self._lock = threading.Lock()
        self._avrt = None

        if platform.system() != 'Windows':
            log("MMCSS: Not on Windows, skipping initialization", "info")
            return

        try:
            self._avrt = ctypes.windll.avrt

            # AvSetMmThreadCharacteristicsW
            self._avrt.AvSetMmThreadCharacteristicsW.argtypes = [
                wintypes.LPCWSTR,
                ctypes.POINTER(wintypes.DWORD)
            ]
            self._avrt.AvSetMmThreadCharacteristicsW.restype = wintypes.HANDLE

            # AvRevertMmThreadCharacteristics
            self._avrt.AvRevertMmThreadCharacteristics.argtypes = [wintypes.HANDLE]
            self._avrt.AvRevertMmThreadCharacteristics.restype = wintypes.BOOL

            # AvSetMmThreadPriority
            self._avrt.AvSetMmThreadPriority.argtypes = [wintypes.HANDLE, ctypes.c_int]
            self._avrt.AvSetMmThreadPriority.restype = wintypes.BOOL

            log("MMCSS: Initialized successfully", "info")
        except Exception as e:
            log(f"MMCSS: Failed to initialize - {e}", "warning")
            self._avrt = None

    def register_audio_thread(self, task_name: str = "Pro Audio") -> bool:
        """
        Register the current thread with MMCSS for real-time audio priority.

        Args:
            task_name: MMCSS task name. Options:
                - "Pro Audio" - Lowest latency, highest priority
                - "Audio" - Standard audio
                - "Games" - Game audio

        Returns:
            True if registration succeeded.
        """
        if self._avrt is None:
            return False

        thread_id = threading.current_thread().ident

        with self._lock:
            if thread_id in self._task_handles:
                return True  # Already registered

            try:
                task_index = wintypes.DWORD(0)
                handle = self._avrt.AvSetMmThreadCharacteristicsW(
                    task_name,
                    ctypes.byref(task_index)
                )

                if handle:
                    # Boost to high priority within the MMCSS task
                    self._avrt.AvSetMmThreadPriority(handle, AVRT_PRIORITY_HIGH)
                    self._task_handles[thread_id] = handle
                    log(f"MMCSS: Registered thread {thread_id} with '{task_name}' (index={task_index.value})", "info")
                    return True
                else:
                    error = ctypes.get_last_error()
                    log(f"MMCSS: Registration failed with error {error}", "warning")
                    return False

            except Exception as e:
                log(f"MMCSS: Registration exception - {e}", "warning")
                return False

    def unregister_audio_thread(self) -> bool:
        """
        Unregister the current thread from MMCSS.
        Call this when the audio thread is stopping.
        """
        if self._avrt is None:
            return False

        thread_id = threading.current_thread().ident

        with self._lock:
            handle = self._task_handles.pop(thread_id, None)
            if handle:
                try:
                    result = self._avrt.AvRevertMmThreadCharacteristics(handle)
                    log(f"MMCSS: Unregistered thread {thread_id}", "info")
                    return bool(result)
                except Exception as e:
                    log(f"MMCSS: Unregister exception - {e}", "warning")
                    return False
        return False

    def cleanup_all(self):
        """Unregister all threads. Call on application shutdown."""
        if self._avrt is None:
            return

        with self._lock:
            for thread_id, handle in list(self._task_handles.items()):
                try:
                    self._avrt.AvRevertMmThreadCharacteristics(handle)
                    log(f"MMCSS: Cleanup - unregistered thread {thread_id}", "info")
                except Exception:
                    pass
            self._task_handles.clear()


# Global singleton
_mmcss_manager = None

def get_mmcss_manager() -> MMCSSManager:
    """Get the global MMCSS manager instance."""
    global _mmcss_manager
    if _mmcss_manager is None:
        _mmcss_manager = MMCSSManager()
    return _mmcss_manager
