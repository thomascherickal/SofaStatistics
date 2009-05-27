
import wx

import util

if util.in_windows():
    
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
            self.SetPageSource(strHTML)

    