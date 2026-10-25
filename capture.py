"""Visible Windows surfaces only; no browser profile, hidden tab or account access."""
import ctypes, os
from ctypes import wintypes

def windows():
    if os.name!='nt':return []
    user=ctypes.windll.user32;result=[]
    @ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def callback(hwnd,_):
        if user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd):
            length=user.GetWindowTextLengthW(hwnd)
            if length:
                title=ctypes.create_unicode_buffer(length+1);user.GetWindowTextW(hwnd,title,length+1)
                if title.value and not title.value.startswith('TeamsAI'):result.append((int(hwnd),title.value))
        return True
    user.EnumWindows(callback,0);return result

def window_rect(hwnd):
    user=ctypes.windll.user32
    user.IsWindow.argtypes=[wintypes.HWND];user.IsIconic.argtypes=[wintypes.HWND]
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    if not user.IsWindow(hwnd) or user.IsIconic(hwnd):raise RuntimeError('Сонгосон цонх хаагдсан эсвэл жижигрүүлсэн байна.')
    rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
    if rect.right<=rect.left or rect.bottom<=rect.top:raise RuntimeError('Цонхны хэмжээ буруу')
    return (rect.left,rect.top,rect.right,rect.bottom)

def exclude_window(root):
    if os.name!='nt':return False
    user=ctypes.windll.user32;root.update_idletasks()
    user.GetParent.argtypes=[wintypes.HWND];user.GetParent.restype=wintypes.HWND
    user.SetWindowDisplayAffinity.argtypes=[wintypes.HWND,wintypes.DWORD]
    hwnd=user.GetParent(root.winfo_id()) or root.winfo_id()
    return bool(user.SetWindowDisplayAffinity(hwnd,0x11))

def grab(mode, region=None, hwnd=None):
    from PIL import ImageGrab
    box=window_rect(hwnd) if mode=='window' else region if mode=='region' else None
    if mode=='region' and not box:raise RuntimeError('Хэсгээ сонгоно уу')
    # Window mode reads visible pixels. Foreground occlusion changes the captured content.
    return ImageGrab.grab(bbox=box,all_screens=True)
