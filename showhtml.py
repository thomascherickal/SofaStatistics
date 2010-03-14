import wx
import os

import my_globals as mg
import full_html

def get_html(title, content, template, root="", file_name="", print_folder=""):
    """
    Returns HTML with embedded CSS.
    %title% is replaced with title
    %content% is replaced with the content
    """
    #get html content
    fil = file(template, "r")
    html = fil.read()
    html = html.replace("%title%", title)
    html = html.replace("%content%", content)
    html = html.replace("%root%", "file://" + root)
    fil.close()
    #save copy of html content (for printing)
    if print_folder:
        fil = file(os.path.join(print_folder, file_name), "w")
        fil.write(html)
        fil.close()
    return html

def get_html_header(title, header_template):
    "Get the HTML down as far as (and including) <body>"
    fil = file(header_template, "r")
    hdr = fil.read()
    hdr = hdr.replace("%title%", title)
    fil.close()
    return hdr

class ShowHTML(wx.Dialog):
    "Show HTML window with content displayed"    
    
    def __init__(self, parent, content, file_name, title, print_folder, 
                 url_load=False):
        """
        content - html ready to display.
        file_name - excludes any path information. Needed for printing.
        title - dialog title.
        print_folder - needs to be a subfolder of the current folder.
        """
        wx.Dialog.__init__(self, parent=parent, id=-1, title=title, 
                        pos=(0,0), size=(900,700), style=wx.RESIZE_BORDER|\
                        wx.DEFAULT_DIALOG_STYLE|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX)
        self.file_name = file_name
        self.print_folder = print_folder
        html = full_html.FullHTML(self, size=wx.DefaultSize)
        html.show_html(content, url_load)
        btnClose = wx.Button(self, wx.ID_CLOSE, _("Close"))
        btnClose.Bind(wx.EVT_BUTTON, self.on_close)
        szrMain = wx.BoxSizer(wx.VERTICAL)
        szrMain.Add(html,1,wx.GROW|wx.ALL, 5)
        if mg.IN_WINDOWS:
            szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
            szr_btns.AddGrowableCol(1,2)
            btnPrint = wx.Button(self, -1, _("Print"))
            btnPrint.Bind(wx.EVT_BUTTON, self.on_print)        
            szr_btns.Add(btnPrint, 0, wx.ALL, 5)
            szr_btns.Add(btnClose, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        else:
            szr_btns = wx.FlexGridSizer(rows=1, cols=1, hgap=5, vgap=5)
            szr_btns.AddGrowableCol(0,2)
            szr_btns.Add(btnClose, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        szrMain.Add(szr_btns, 0, wx.GROW)
        self.SetSizer(szrMain)
        self.Layout()
        wx.EndBusyCursor()
        
    def on_print(self, event):
        "Print page"
        #printer = wx.html.HtmlEasyPrinting("Printing output", None)
        #printer.PrintFile(self.file_name) #horrible printing - large H1s, no CSS etc
        
        full_file = os.path.join(os.getcwd(), self.print_folder, self.file_name)
        os.system("rundll32.exe MSHTML.DLL,PrintHTML \"%s\"" % full_file)
    
    def on_close(self, event):
        "Close Viewer"        
        self.Destroy()    
