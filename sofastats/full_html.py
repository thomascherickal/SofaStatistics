#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import traceback
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import my_exceptions
from sofastats import output
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
                    u"\nCaused by errors:\n\n%s" % b.ue(e))
        
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
        ## Relies on sudo apt install python-wxgtk-webview3.0 libwxgtk-webview3.0-0v5
        import wx.html2  ## BUG if older Ubuntu than about 17.04 Zesty Zapus - https://bugs.launchpad.net/ubuntu/+source/wxwidgets3.0/+bug/1388847. Must LD_PRELOAD=/usr/lib/i386-linux-gnu/libwx_gtk2u_webview-3.0.so.0.2.0  ## i386 not x86_64 and 0.2.0 not 0.1.0

        class FullHTML(wx.html2.WebView):

            def __init__(self, panel, parent, size):
                pre = wx.html2.WebView.New(panel, -1, size=wx.Size(size[0], size[1]))
                self.PostCreate(pre)  ## http://wiki.wxpython.org/TwoStageCreation

            def show_html(self, str_html, url_load=False):
                base_uri = "%s%s/" % (mg.FILE_URL_START_GEN, mg.INT_PATH)
                self.SetPage(str_html, base_uri)

            def load_url(self, url):
                self.LoadURL(url)

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
