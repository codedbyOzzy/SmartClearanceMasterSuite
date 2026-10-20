# -*- coding: utf-8 -*-
"""Tek MasterSuite örneği — ikinci kopya Excel/JSON/COM'u ezmesin."""
from __future__ import annotations

import ctypes
import sys

MUTEX_NAME = "Local\\DogruerMasterSuite_v4_SingleInstance"
ERROR_ALREADY_EXISTS = 183

_handle = None


def acquire_single_instance():
    """True = bu süreç sahibi. False = başka kopya zaten açık."""
    global _handle
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if not handle:
        return False
    err = kernel32.GetLastError()
    if err == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _handle = handle
    return True


def release_single_instance():
    global _handle
    if sys.platform != "win32" or not _handle:
        _handle = None
        return
    ctypes.windll.kernel32.CloseHandle(_handle)
    _handle = None
