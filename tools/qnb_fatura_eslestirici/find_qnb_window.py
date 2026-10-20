import os
import sys
import time
import win32gui
import win32con
import subprocess

def find_qnb_window():
    found = []
    def enum_cb(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "QNB" in title or "eSolutions" in title:
                found.append((hwnd, title))
    win32gui.EnumWindows(enum_cb, None)
    return found

print("FOUND QNB WINDOWS:", find_qnb_window())
