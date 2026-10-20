# -*- coding: utf-8 -*-
"""Win32 yardımcıları: Evrim penceresi, DPI, monitör parmak izi, göreli koordinat."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
SM_CXSCREEN = 0
SM_CYSCREEN = 1

EVRIM_EXES = (
    "ithalsql.exe",
    "ihrsql.exe",
    "antsql.exe",
    "evrimhaber.exe",
    "evrimrpa.exe",
    "evrim.exe",
    "gumruk.exe",
    "ithalat.exe",
    "ihracat.exe",
)

TITLE_KEYWORDS = (
    "EVRİM", "EVRIM", "İTHALAT", "ITHALAT", "İHRACAT", "IHRACAT",
    "ANTREPO", "TRANSİT", "TRANSIT", "BEYANNAME", "GÜMRÜK", "GUMRUK",
)

EXCLUDE_TITLES = (
    "MASTER SUITE",
    "SMARTCLEARANCE",
    "VISUAL STUDIO",
    "CHROME",
    "MSEDGE",
    "TEAMS",
    "OUTLOOK",
    "CURSOR",
    "ANTIGRAVITY",
)

EXCLUDE_EXES = (
    "python.exe",
    "pythonw.exe",
    "code.exe",
    "cursor.exe",
    "chrome.exe",
    "msedge.exe",
    "teams.exe",
    "outlook.exe",
    "excel.exe",
    "winword.exe",
)


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
# Callback nesnesini GC'den koru (aksi halde EnumWindows pencereleri kaçırır)
_KEEP = []


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def virtual_screen() -> Tuple[int, int, int, int]:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return left, top, w, h


def display_fingerprint() -> str:
    vx, vy, vw, vh = virtual_screen()
    n = user32.GetSystemMetrics(SM_CMONITORS)
    pw = user32.GetSystemMetrics(SM_CXSCREEN)
    ph = user32.GetSystemMetrics(SM_CYSCREEN)
    dpi = 96
    try:
        dpi = int(user32.GetDpiForSystem())
    except Exception:
        pass
    return f"mon={n}|virt={vw}x{vh}@{vx},{vy}|primary={pw}x{ph}|dpi={dpi}"


def window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def window_title(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value.strip()


def process_image(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value.lower()
    finally:
        kernel32.CloseHandle(h)
    return ""


def pid_of(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def evrim_pids() -> List[int]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
        return []
    pids = []
    try:
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        first = getattr(kernel32, "Process32FirstW", kernel32.Process32First)
        nxt = getattr(kernel32, "Process32NextW", kernel32.Process32Next)
        if not first(snap, ctypes.byref(pe)):
            return []
        while True:
            name = (pe.szExeFile or "").lower()
            if name in EVRIM_EXES:
                pids.append(int(pe.th32ProcessID))
            if not nxt(snap, ctypes.byref(pe)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return pids


def _score_window(hwnd: int, title: str, exe_path: str, pid_ok: bool) -> int:
    tu = title.upper()
    score = 0
    w, h = window_rect(hwnd)[2:]
    if w < 80 or h < 80:
        return 0
    if pid_ok:
        score += 40
    if any(exe in exe_path for exe in EVRIM_EXES):
        score += 40
    if "ithalsql.exe" in exe_path or "ihrsql.exe" in exe_path:
        score += 25
    if "\\evrgrfktmp\\" in exe_path or "\\evrim\\" in exe_path:
        score += 20
    if any(k in tu for k in TITLE_KEYWORDS):
        score += 15
    if any(k in tu for k in ("İTHALAT SİSTEMİ", "ITHALAT SISTEMI", "İHRACAT SİSTEMİ", "IHRACAT SISTEMI")):
        score += 35
    if user32.IsIconic(hwnd):
        score += 5
    if w >= 600 and h >= 400:
        score += 8
    return score


def find_evrim_hwnd() -> Tuple[Optional[int], str, List[str]]:
    """(hwnd, title, debug_notes)."""
    notes: List[str] = []
    pids = set(evrim_pids())
    if pids:
        notes.append(f"Evrim süreçleri: {sorted(pids)}")
    else:
        notes.append("Bilinen Evrim .exe süreci yok (ithalsql/ihrsql/antsql).")

    candidates: List[Tuple[int, int, str]] = []

    def consider(hwnd):
        if not user32.IsWindow(hwnd):
            return
        visible = user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd)
        if not visible:
            return
        title = window_title(hwnd)
        tu = title.upper()
        if any(ex in tu for ex in EXCLUDE_TITLES):
            return
        pid = pid_of(hwnd)
        exe = process_image(pid)
        if any(ex in exe for ex in EXCLUDE_EXES):
            return
        pid_ok = pid in pids
        score = _score_window(hwnd, title, exe, pid_ok)
        if score <= 0:
            return
        if pid_ok or any(k in tu for k in TITLE_KEYWORDS) or any(e in exe for e in EVRIM_EXES):
            candidates.append((score, hwnd, title or exe or f"hwnd={hwnd}"))

    def enum_cb(hwnd, _lp):
        consider(hwnd)
        return True

    proc = _WNDENUMPROC(enum_cb)
    _KEEP.append(proc)
    user32.EnumWindows(proc, 0)

    if not candidates:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            try:
                user32.EnumDesktopWindows(hdesk, proc, 0)
            finally:
                user32.CloseDesktop(hdesk)

    if not candidates:
        notes.append("Uygun üst pencere bulunamadı. Evrim simge durumunda veya farklı kullanıcı oturumunda olabilir.")
        return None, "", notes

    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]
    notes.append(f"Seçilen: [{best[2]}] skor={best[0]} (aday={len(candidates)})")
    return best[1], best[2], notes


def focus_window(hwnd: int, maximize: bool = False) -> bool:
    if not hwnd:
        return False
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        if maximize:
            user32.ShowWindow(hwnd, 3)
        user32.AllowSetForegroundWindow(-1)
        fg = user32.GetForegroundWindow()
        dummy = wintypes.DWORD()
        fg_tid = user32.GetWindowThreadProcessId(fg, ctypes.byref(dummy))
        cur_tid = kernel32.GetCurrentThreadId()
        if fg_tid and fg_tid != cur_tid:
            user32.AttachThreadInput(cur_tid, fg_tid, True)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(cur_tid, fg_tid, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        user32.SetForegroundWindow(hwnd)
        return True


def capture_point(hwnd: Optional[int], x: int, y: int) -> Dict:
    rec: Dict = {"x": int(x), "y": int(y)}
    if hwnd:
        left, top, w, h = window_rect(hwnd)
        if w > 0 and h > 0:
            rec["rx"] = round((x - left) / float(w), 6)
            rec["ry"] = round((y - top) / float(h), 6)
            rec["win_w"] = int(w)
            rec["win_h"] = int(h)
    rec["fp"] = display_fingerprint()
    return rec


def resolve_point(hwnd: Optional[int], pt: Dict) -> Optional[Tuple[int, int]]:
    if not isinstance(pt, dict):
        return None
    if hwnd and "rx" in pt and "ry" in pt:
        left, top, w, h = window_rect(hwnd)
        if w > 80 and h > 80:
            x = left + int(float(pt["rx"]) * w)
            y = top + int(float(pt["ry"]) * h)
            return x, y
    if "x" in pt and "y" in pt:
        return int(pt["x"]), int(pt["y"])
    return None


def point_inside_window(hwnd: int, x: int, y: int, margin: int = 8) -> bool:
    left, top, w, h = window_rect(hwnd)
    return (left - margin) <= x <= (left + w + margin) and (top - margin) <= y <= (top + h + margin)
