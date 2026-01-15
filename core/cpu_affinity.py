"""
CPU affinity and power throttling control for Intel hybrid CPUs (i9-14900K).

On hybrid architectures (P-cores + E-cores), Windows may schedule latency-critical
audio threads to slower E-cores. This module provides utilities to:
1. Pin processes/threads to P-cores only
2. Disable power throttling (EcoQoS) to prevent E-core scheduling
"""

import ctypes
from ctypes import wintypes
import platform
import os
from core.logger import log

# Windows API constants
THREAD_POWER_THROTTLING_CURRENT_VERSION = 1
THREAD_POWER_THROTTLING_EXECUTION_SPEED = 0x1
ThreadPowerThrottling = 4  # THREAD_INFORMATION_CLASS


class THREAD_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_ulong),
        ("ControlMask", ctypes.c_ulong),
        ("StateMask", ctypes.c_ulong),
    ]


# Set up kernel32 with proper error handling
_kernel32 = None

def _get_kernel32():
    global _kernel32
    if _kernel32 is None and platform.system() == 'Windows':
        _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

        # SetProcessAffinityMask
        _kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        _kernel32.SetProcessAffinityMask.restype = wintypes.BOOL

        # GetCurrentProcess
        _kernel32.GetCurrentProcess.argtypes = []
        _kernel32.GetCurrentProcess.restype = wintypes.HANDLE

        # SetPriorityClass
        _kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        _kernel32.SetPriorityClass.restype = wintypes.BOOL

        # GetCurrentThread
        _kernel32.GetCurrentThread.argtypes = []
        _kernel32.GetCurrentThread.restype = wintypes.HANDLE

        # SetThreadInformation
        _kernel32.SetThreadInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
        ]
        _kernel32.SetThreadInformation.restype = wintypes.BOOL

    return _kernel32


def get_cpu_info() -> dict:
    """
    Get CPU topology information.
    Returns dict with core counts and affinity masks.
    """
    cpu_count = os.cpu_count() or 4

    # For i9-14900K: 8 P-cores (16 threads with HT) + 16 E-cores = 32 logical processors
    # P-cores are typically the first 16 logical processors (0-15)
    # This is a heuristic - actual topology can vary

    return {
        'logical_processors': cpu_count,
        # Conservative: assume first half are P-cores (with hyperthreading)
        'p_core_mask': (1 << (cpu_count // 2)) - 1 if cpu_count > 4 else (1 << cpu_count) - 1,
        'all_cores_mask': (1 << cpu_count) - 1
    }


def set_process_affinity_to_p_cores() -> bool:
    """
    Set the current process affinity to P-cores only.
    Call this early in main() for latency-critical applications.

    Returns:
        True if affinity was set successfully.
    """
    if platform.system() != 'Windows':
        log("CPU Affinity: Not on Windows, skipping", "info")
        return False

    try:
        kernel32 = _get_kernel32()
        if kernel32 is None:
            return False

        info = get_cpu_info()
        handle = kernel32.GetCurrentProcess()
        mask = info['p_core_mask']

        # SetProcessAffinityMask returns non-zero on success
        result = kernel32.SetProcessAffinityMask(handle, mask)

        if result:
            log(f"CPU Affinity: Process pinned to P-cores (mask=0x{mask:X})", "info")
            return True
        else:
            error = ctypes.get_last_error()
            log(f"CPU Affinity: SetProcessAffinityMask failed with error {error}", "warning")
            return False

    except Exception as e:
        log(f"CPU Affinity: Exception - {e}", "warning")
        return False


def disable_power_throttling() -> bool:
    """
    Disable EcoQoS/power throttling for the current thread.
    This prevents Windows from scheduling the thread to E-cores.

    Call this at the start of latency-critical threads (audio capture, etc.).

    Returns:
        True if power throttling was disabled successfully.
    """
    if platform.system() != 'Windows':
        return False

    try:
        kernel32 = _get_kernel32()
        if kernel32 is None:
            return False

        # Get current thread handle
        thread_handle = kernel32.GetCurrentThread()

        # Set up the throttling state structure
        state = THREAD_POWER_THROTTLING_STATE()
        state.Version = THREAD_POWER_THROTTLING_CURRENT_VERSION
        state.ControlMask = THREAD_POWER_THROTTLING_EXECUTION_SPEED
        state.StateMask = 0  # 0 = disable throttling (request high performance)

        # SetThreadInformation
        result = kernel32.SetThreadInformation(
            thread_handle,
            ThreadPowerThrottling,
            ctypes.byref(state),
            ctypes.sizeof(state)
        )

        if result:
            log("CPU Affinity: Power throttling disabled for current thread", "info")
            return True
        else:
            # This can fail on older Windows versions - not critical
            return False

    except Exception as e:
        log(f"CPU Affinity: disable_power_throttling exception - {e}", "warning")
        return False


def set_high_process_priority() -> bool:
    """
    Set the current process to HIGH priority class.

    Returns:
        True if priority was set successfully.
    """
    if platform.system() != 'Windows':
        return False

    try:
        kernel32 = _get_kernel32()
        if kernel32 is None:
            return False

        HIGH_PRIORITY_CLASS = 0x00000080

        handle = kernel32.GetCurrentProcess()
        result = kernel32.SetPriorityClass(handle, HIGH_PRIORITY_CLASS)

        if result:
            log("CPU Affinity: Process priority set to HIGH", "info")
            return True
        else:
            return False

    except Exception as e:
        log(f"CPU Affinity: set_high_process_priority exception - {e}", "warning")
        return False


def apply_all_cpu_optimizations() -> dict:
    """
    Apply all CPU optimizations for real-time audio.
    Call this once at application startup.

    Returns:
        Dict with results of each optimization.
    """
    results = {
        'p_core_affinity': set_process_affinity_to_p_cores(),
        'high_priority': set_high_process_priority(),
        'power_throttling_disabled': disable_power_throttling(),
    }

    success_count = sum(1 for v in results.values() if v)
    log(f"CPU Affinity: Applied {success_count}/3 optimizations", "info")

    return results
