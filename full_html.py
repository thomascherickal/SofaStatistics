import os
import wx

import my_globals

use_renderer = True # False if renderer not available and other testing required
debug = False

# url_load only needed for Windows

if not use_renderer:
    class FullHTML(wx.Window):

        def __init__(self, panel, size):
            wx.Window.__init__(self, panel, -1, size=wx.Size(size[0], size[1]))
        
        def ShowHTML(self, strHTML, url_load=False):
            pass
else:
    if my_globals.IN_WINDOWS:
        
        import wx.lib.iewin as ie
        
        class FullHTML(ie.IEHtmlWindow):
        
            def __init__(self, panel, size):
                ie.IEHtmlWindow.__init__(self, panel, -1, 
                                         size=wx.Size(size[0], size[1]))
            
            def ShowHTML(self, strHTML, url_load=False):
                """
                If first time, will have delay while initialising comtypes.
                url_load -- so internal links like footnotes will work.
                """
                if url_load:
                    url_fil = os.path.join(my_globals.INT_PATH, u"my_url.htm")
                    print(url_fil)
                    f = open(url_fil, "w")
                    f.write(strHTML)
                    f.close()
                    self.LoadUrl("file:///%s" % url_fil)
                else:
                    self.LoadString(strHTML)
    else:
        import wx.webview
        
        class FullHTML(wx.webview.WebView):
        
            def __init__(self, panel, size):
                wx.webview.WebView.__init__(self, panel, -1, size=size)
            
            def ShowHTML(self, strHTML, url_load=False):
                if debug: print("strHTML is: %s" % strHTML)
                # NB no issue with backslashes because not used in Windows ;-)
                self.SetPageSource(strHTML, "file://%s/" % my_globals.INT_PATH)
