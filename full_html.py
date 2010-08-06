import codecs
import os
import traceback
import wx

import my_globals as mg

use_renderer = True # False if renderer not available and other testing required
debug = False

# url_load only needed for Windows

if not use_renderer:    
    
    class FullHTML(wx.Window):

        def __init__(self, panel, parent, size):
            wx.Window.__init__(self, panel, -1, size=wx.Size(size[0], size[1]))
        
        def show_html(self, strHTML, url_load=False):
            pass
        
        def load_url(self, url):
            pass
        
else:
    if mg.PLATFORM == mg.WINDOWS:
        try:
            import wx.lib.iewin as ie
        except ImportError, e: # using traceback because can be fiendish
            raise Exception(_("Problem importing wx.lib.iewin."
                              "\nCaused by errors:\n\n%s" % 
                              traceback.format_exc()))        
        
        class FullHTML(ie.IEHtmlWindow):
        
            def __init__(self, panel, parent, size):
                ie.IEHtmlWindow.__init__(self, panel, -1, 
                                         size=wx.Size(size[0], size[1]))
            
            def show_html(self, strHTML, url_load=False):
                """
                If first time, will have delay while initialising comtypes.
                url_load -- so internal links like footnotes will work.
                """
                if url_load:
                    url_fil = os.path.join(mg.INT_PATH, u"ready2load.htm")
                    if debug: print(url_fil)
                    f = codecs.open(url_fil, "w", encoding="utf-8")
                    f.write(strHTML)
                    f.close()
                    self.LoadUrl(u"file:///%s" % url_fil)
                else:
                    self.LoadString(strHTML)
                    
            def load_url(self, url):
                self.LoadUrl(url)
                
    elif mg.PLATFORM == mg.LINUX:
        use_gtk = True
        if not use_gtk:
            try:
                import wx.webview
            except ImportError, e:
                raise Exception(_("Problem importing wx.webview.  Did you " 
                    "follow the instructions at http://www.sofastatistics.com/"
                    "predeb.php before installing the deb file (especially the "
                    "step installing python-webkitwx)?"))                
            
            class FullHTML(wx.webview.WebView):
        
                def __init__(self, panel, parent, size):
                    wx.webview.WebView.__init__(self, panel, -1, size=size)
                
                def show_html(self, strHTML, url_load=False):
                    if debug: print("strHTML is: %s" % strHTML)
                    # NB no issue with backslashes because not in Windows ;-)
                    self.SetPageSource(strHTML, "file://%s/" % mg.INT_PATH)
                
                def load_url(self, url):
                    self.LoadURL(url)
                    
        else:
            # http://wiki.wxpython.org/wxGTKWebKit
            import gobject
            gobject.threads_init()
            import pygtk
            pygtk.require('2.0')
            import gtk, gtk.gdk
            # pywebkitgtk (http://code.google.com/p/pywebkitgtk/)
            import webkit
        
            class FullHTML(wx.Panel):
        
                def __init__(self, panel, parent, size):
                    wx.Panel.__init__(self, panel, size=size)
                
                def pizza_magic(self):
                    """
                    Do pizza_magic when parent is shown (EVT_SHOW).  If not 
                        shown, can't get handle and can't make magic work. 
                    """
                    debug = False
                    whdl = self.GetHandle() # only works if parent is shown
                    if debug: print(whdl) # 0 if not shown so will fail
                    window = gtk.gdk.window_lookup(whdl)
                    self.pizza = pizza = window.get_user_data()
                    self.scrolled_window = scrolled_window = pizza.parent
                    scrolled_window.remove(pizza)
                    self.ctrl = ctrl = webkit.WebView()
                    scrolled_window.add(ctrl)
                    scrolled_window.show_all()
                
                def show_html(self, strHTML, url_load=False):
                    if debug: print("strHTML is: %s" % strHTML)
                    # NB no issue with backslashes because not in Windows ;-)
                    self.ctrl.load_string(strHTML, "text/html", "utf-8",
                                          "file://%s/" % mg.INT_PATH)
                
                def load_url(self, url):
                    self.ctrl.load_uri(url)
                
    elif mg.PLATFORM == mg.MAC:
        import wx.webkit        
        
        class FullHTML(wx.webkit.WebKitCtrl):
        
            def __init__(self, panel, parent, size):
                wx.webkit.WebKitCtrl.__init__(self, panel, -1, size=size)
            
            def show_html(self, strHTML, url_load=False):
                if debug: print("strHTML is: %s" % strHTML)
                # NB no issue with backslashes because not used in Windows ;-)
                self.SetPageSource(strHTML, "file://%s/" % mg.INT_PATH)
            
            def load_url(self, url):
                self.LoadURL(url)
                