import os, unittest
from unittest.mock import patch

@unittest.skipUnless(os.name=='nt','Windows desktop required')
class WindowsCaptureTests(unittest.TestCase):
    def test_visible_window_and_capture_modes(self):
        import tkinter as tk
        from capture import windows, window_rect, grab
        root=tk.Tk();root.title('OCR Capture Fixture');root.geometry('400x240+80+80');root.update()
        try:
            matches=[hwnd for hwnd,title in windows() if title=='OCR Capture Fixture']
            self.assertTrue(matches)
            rect=window_rect(matches[0]);self.assertGreater(rect[2]-rect[0],300)
            self.assertGreater(grab('window',hwnd=matches[0]).width,300)
            self.assertEqual(grab('region',region=(80,80,280,200)).size,(200,120))
            self.assertGreater(grab('screen').width,300)
        finally:root.destroy()
    def test_compact_ui_constructs(self):
        import tkinter as tk
        from app import App
        root=tk.Tk()
        with patch('app.Engine.start',return_value=None):
            app=App(root);root.update()
            try:
                self.assertEqual(root.winfo_width(),640)
                self.assertEqual(app.mode.get(),'region')
                self.assertTrue(app.footer.winfo_ismapped())
                self.assertLessEqual(app.footer.winfo_y()+app.footer.winfo_height(),root.winfo_height())
                root.geometry('520x740');root.update()
                for widget in (app.footer,app.question,app.answer,app.history_list):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertGreater(widget.winfo_height(),20)
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),root.winfo_rooty()+root.winfo_height())
                app.capture_options();root.update()
                self.assertTrue(root.winfo_exists())
                app.busy=False;app.options();root.update()
                settings=[c for c in root.winfo_children() if isinstance(c,tk.Toplevel) and c.title()=='BORO • Settings']
                self.assertEqual(len(settings),1)
            finally:app.close()
