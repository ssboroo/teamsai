"""Visible Windows surfaces only; no browser profile, hidden tab or account access."""
import ctypes, os, sys
from ctypes import wintypes

def windows():
    if sys.platform=='darwin':
        import Quartz
        return [(int(w[Quartz.kCGWindowNumber]),str(w.get(Quartz.kCGWindowOwnerName,''))+' — '+str(w.get(Quartz.kCGWindowName,''))) for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly,Quartz.kCGNullWindowID) if w.get(Quartz.kCGWindowLayer,0)==0 and w.get(Quartz.kCGWindowOwnerPID)!=os.getpid()]
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
    if sys.platform=='darwin':
        import Quartz
        rows=Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionIncludingWindow,int(hwnd))
        if not rows:raise RuntimeError('Сонгосон цонх хаагдсан байна.')
        b=rows[0][Quartz.kCGWindowBounds]
        return (int(b['X']),int(b['Y']),int(b['X']+b['Width']),int(b['Y']+b['Height']))
    user=ctypes.windll.user32
    user.IsWindow.argtypes=[wintypes.HWND];user.IsIconic.argtypes=[wintypes.HWND]
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    if not user.IsWindow(hwnd) or user.IsIconic(hwnd):raise RuntimeError('Сонгосон цонх хаагдсан эсвэл жижигрүүлсэн байна.')
    rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
    if rect.right<=rect.left or rect.bottom<=rect.top:raise RuntimeError('Цонхны хэмжээ буруу')
    return (rect.left,rect.top,rect.right,rect.bottom)

def exclude_window(root):
    if sys.platform=='darwin':return True # App hides itself briefly during full-screen capture.
    if os.name!='nt':return False
    user=ctypes.windll.user32;root.update_idletasks()
    user.GetParent.argtypes=[wintypes.HWND];user.GetParent.restype=wintypes.HWND
    user.SetWindowDisplayAffinity.argtypes=[wintypes.HWND,wintypes.DWORD]
    hwnd=user.GetParent(root.winfo_id()) or root.winfo_id()
    return bool(user.SetWindowDisplayAffinity(hwnd,0x11))

def grab(mode, region=None, hwnd=None):
    if sys.platform=='darwin':return mac_grab(mode,region,hwnd)
    from PIL import ImageGrab
    box=window_rect(hwnd) if mode=='window' else region if mode=='region' else None
    if mode=='region' and not box:raise RuntimeError('Хэсгээ сонгоно уу')
    # Window mode reads visible pixels. Foreground occlusion changes the captured content.
    return ImageGrab.grab(bbox=box,all_screens=True)


def screen_permission(request=False):
    if sys.platform!='darwin':return True
    import Quartz
    if Quartz.CGPreflightScreenCaptureAccess():return True
    if request:Quartz.CGRequestScreenCaptureAccess()
    return False

def mac_grab(mode,region=None,hwnd=None):
    import subprocess,tempfile
    from pathlib import Path
    from PIL import Image
    if not screen_permission():raise RuntimeError('System Settings → Privacy & Security → Screen Recording хэсэгт TeamsAI-г зөвшөөрөөд дахин нээнэ үү.')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'capture.png';args=['/usr/sbin/screencapture','-x']
        if mode=='window':args+=['-o','-l',str(int(hwnd))]
        elif mode=='region':
            if not region:raise RuntimeError('Хэсгээ сонгоно уу')
            x,y,r,b=region;args+=['-R',f'{x},{y},{r-x},{b-y}']
        else:args+=['-m'] # Main monitor, in macOS display coordinates.
        subprocess.run(args+[str(path)],check=True,timeout=8,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with Image.open(path) as im:return im.convert('RGB')
