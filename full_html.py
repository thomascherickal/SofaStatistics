#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import traceback
import wx

import my_globals as mg
import lib
import my_exceptions
import output
use_renderer = True # False if renderer not available and other testing required

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
        except Exception, e:
            mytraceback = traceback.format_exc()
            if "Typelib newer than module" in mytraceback:
                raise my_exceptions.InconsistentFileDate()
            elif "comtypes" in mytraceback or "IUnknown" in mytraceback:
                # No module named comtypes, 
                # 'module' object has no attribute 'IUnknown' etc
                raise my_exceptions.ComtypesException()
            else:
                raise Exception(_(u"Problem importing wx.lib.iewin.") +
                            u"\nCaused by errors:\n\n%s" % lib.ue(e))
        
        class FullHTML(ie.IEHtmlWindow): #@UndefinedVariable
        
            def __init__(self, panel, parent, size):
                ie.IEHtmlWindow.__init__(self, panel, -1, #@UndefinedVariable 
                    size=wx.Size(size[0], size[1]))
            
            def back2forwards_slashes(self, mystr):
                """
                But not LBL_LINE_BREAK_JS. Don't turn \n in JS to /n!
                """
                debug = False
                safe_str = mystr.replace(mg.LBL_LINE_BREAK_JS, 
                                         u"<label_line_break>")
                new_str = safe_str.replace(u"\\", u"/")
                final_str = new_str.replace(u"<label_line_break>", 
                                            mg.LBL_LINE_BREAK_JS)
                if debug: print(final_str)
                return final_str
            
            def show_html(self, str_html, url_load=False):
                """
                If first time, will have delay while initialising comtypes.
                url_load -- so internal links like footnotes will work.
                """
                debug = False
                if url_load:
                    url_fil = os.path.join(mg.INT_PATH, u"ready2load.htm")
                    if debug: print(url_fil)
                    f = codecs.open(url_fil, "w", encoding="utf-8")
                    html2write = output.fix_perc_encodings_for_win(
                        self.back2forwards_slashes(
                            output.rel2abs_css_links(str_html)))
                    f.write(html2write)
                    f.close()
                    html2load = u"%s%s" % (mg.FILE_URL_START_WIN, 
                                           self.back2forwards_slashes(url_fil))
                    self.LoadUrl(html2load)
                else:
                    html2load = self.back2forwards_slashes(str_html)
                    self.LoadString(html2load)
                    
            def load_url(self, url):
                self.LoadUrl(url)
                
    elif mg.PLATFORM == mg.LINUX:
        # http://wiki.wxpython.org/wxGTKWebKit
        import gobject
        gobject.threads_init() #@UndefinedVariable
        import pygtk
        pygtk.require('2.0')
        import gtk.gdk
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
                window = gtk.gdk.window_lookup(whdl) #@UndefinedVariable
                self.pizza = pizza = window.get_user_data()
                self.scrolled_window = scrolled_window = pizza.parent
                scrolled_window.remove(pizza)
                self.ctrl = ctrl = webkit.WebView()
                scrolled_window.add(ctrl)
                scrolled_window.show_all()
            
            def show_html(self, str_html, url_load=False):
                debug = False
                verbose = True
                if debug: print(self.ctrl.get_encoding())
                if debug: 
                    if verbose:
                        print(u"str_html is: %s" % str_html)
                    else:
                        print(u"str_html is: %s ... %s" % (str_html[:60], 
                                                           str_html[-60:]))
                # NB no issue with backslashes because not in Windows ;-)
                """
                http://webkitgtk.org/reference/webkitgtk/stable/webkitgtk-webkitwebview.html
                webkit_web_view_load_string         (WebKitWebView *web_view,
                                                     const gchar *content,
                                                     const gchar *mime_type,
                                                     const gchar *encoding,
                                                     const gchar *base_uri);
                """
                content = str_html
                mime_type = "text/html"
                encoding = "utf-8"
                base_uri = "%s%s/" % (mg.FILE_URL_START_GEN, mg.INT_PATH)
                self.ctrl.load_string(content, mime_type, encoding, base_uri)
            
            def load_url(self, url):
                self.ctrl.load_uri(url)
                
    elif mg.PLATFORM == mg.MAC:
        import wx.webkit        
        
        class FullHTML(wx.webkit.WebKitCtrl):
        
            def __init__(self, panel, parent, size):
                wx.webkit.WebKitCtrl.__init__(self, panel, -1, size=size)
            
            def show_html(self, str_html, url_load=False):
                debug = False
                if debug: print("str_html is: %s" % str_html)
                # NB no issue with backslashes because not used in Windows ;-)
                self.SetPageSource(str_html, "%s%s/" % (mg.FILE_URL_START_GEN,
                                                        mg.INT_PATH))
            
            def load_url(self, url):
                self.LoadURL(url)
                