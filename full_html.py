import codecs
import os
import traceback
import wx

import my_globals as mg
import lib
import output
use_renderer = True # False if renderer not available and other testing required
debug = False

# url_load only needed for Windows

if not use_renderer:    
    
    class FullHTML(wx.Window):

        def __init__(self, panel, parent, size):
            wx.Window.__init__(self, panel, -1, size=wx.Size(size[0], size[1]))
        
        def show_html(self, str_html, url_load=False):
            pass
        
        def load_url(self, url):
            pass
        
else:
    if mg.PLATFORM == mg.WINDOWS:
        try:
            import wx.lib.iewin as ie
        except ImportError, e: # can be fiendish - traceback shown in start.py
            mytraceback = traceback.format_exc()
            if "Typelib newer than module" in mytraceback:
                extra_msg = _("SOFA has detected an inconsistent file date. "
                              "Is your system date/time set correctly?\n")
            elif "comtypes" in mytraceback: # No module named comtypes
                extra_msg = (u"Problem with comtypes: look at help in "
                             u"http://www.sofastatistics.com/wiki/doku.php?"
                             u"id=help:will_not_start#no_module_named_comtypes")
            else:
                extra_msg = u""
            raise Exception(extra_msg + _("Problem importing wx.lib.iewin.") +
                            u"\nCaused by errors:\n\n%s" % lib.ue(e))
        
        class FullHTML(ie.IEHtmlWindow):
        
            def __init__(self, panel, parent, size):
                ie.IEHtmlWindow.__init__(self, panel, -1, 
                                         size=wx.Size(size[0], size[1]))
            
            def back2forwards_slashes(self, mystr):
                """
                But not LABEL_LINE_BREAK_JS.  Don't turn \n in JS to /n!
                """
                debug = False
                safe_str = mystr.replace(mg.LABEL_LINE_BREAK_JS, 
                                         u"<label_line_break>")
                new_str = safe_str.replace("\\", "/")
                final_str = new_str.replace(u"<label_line_break>", 
                                            mg.LABEL_LINE_BREAK_JS)
                if debug: print(final_str)
                return final_str
            
            def show_html(self, str_html, url_load=False):
                """
                If first time, will have delay while initialising comtypes.
                url_load -- so internal links like footnotes will work.
                """
                if url_load:
                    url_fil = os.path.join(mg.INT_PATH, u"ready2load.htm")
                    if debug: print(url_fil)
                    f = codecs.open(url_fil, "w", encoding="utf-8")
                    html2write = self.back2forwards_slashes(\
                                    output.rel2abs_css_links(\
                                    str_html))
                    f.write(html2write)
                    f.close()
                    self.LoadUrl(u"file:///%s" % url_fil)
                else:
                    html2load = self.back2forwards_slashes(str_html)
                    self.LoadString(html2load)
                    
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
                
                def show_html(self, str_html, url_load=False):
                    if debug: print("str_html is: %s" % str_html)
                    # NB no issue with backslashes because not in Windows ;-)
                    self.SetPageSource(str_html, "file://%s/" % mg.INT_PATH)
                
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
                    Do pizza_magic when parent is created (EVT_WINDOW_CREATE).
                    EVT_SHOW worked on Windows and Linux but not on Macs. If not 
                        shown/created, can't get handle and can't make magic 
                        work. See http://groups.google.com/group/...
                        ...wxpython-users/t/ac193c36b9fafe48 
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
                
                def show_html(self, str_html, url_load=False):
                    if debug: print("str_html is: %s" % str_html)
                    # NB no issue with backslashes because not in Windows ;-)
                    self.ctrl.load_string(str_html, "text/html", "utf-8",
                                          "file://%s/" % mg.INT_PATH)
                
                def load_url(self, url):
                    self.ctrl.load_uri(url)
                
    elif mg.PLATFORM == mg.MAC:
        import wx.webkit        
        
        class FullHTML(wx.webkit.WebKitCtrl):
        
            def __init__(self, panel, parent, size):
                wx.webkit.WebKitCtrl.__init__(self, panel, -1, size=size)
            
            def show_html(self, str_html, url_load=False):
                if debug: print("str_html is: %s" % str_html)
                # NB no issue with backslashes because not used in Windows ;-)
                self.SetPageSource(str_html, "file://%s/" % mg.INT_PATH)
            
            def load_url(self, url):
                self.LoadURL(url)
                