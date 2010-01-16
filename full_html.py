
import wx

import my_globals

use_renderer = True # False if renderer not available and other testing required
debug = False

if not use_renderer:
    class FullHTML(wx.Window):

        def __init__(self, panel, size):
            wx.Window.__init__(self, panel, -1, size=wx.Size(size[0], size[1]))
        
        def ShowHTML(self, strHTML):
            pass
else:
    if my_globals.IN_WINDOWS:
        
        import wx.lib.iewin as ie
        
        class FullHTML(ie.IEHtmlWindow):
        
            def __init__(self, panel, size):
                ie.IEHtmlWindow.__init__(self, panel, -1, 
                                         size=wx.Size(size[0], size[1]))
            
            def ShowHTML(self, strHTML):
                """If first time, will have delay while initialising comtypes"""
                self.LoadString(strHTML)
        
    else:
        import wx.webview
        
        class FullHTML(wx.webview.WebView):
        
            def __init__(self, panel, size):
                wx.webview.WebView.__init__(self, panel, -1, size=size)
            
            def ShowHTML(self, strHTML):
                if debug: print("strHTML is: %s" % strHTML)
                # NB no issue with backslashes because not used in Windows ;-)
                self.SetPageSource(strHTML, "file://%s/" % my_globals.INT_PATH)
