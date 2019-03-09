from pathlib import Path
import wx  #@UnusedImport
import wx.html2
import os

from . import my_globals as mg
from . import lib

def display_report(parent, str_content, url_load=False):
    ## display results
    wx.BeginBusyCursor()
    dlg = DlgHTML(parent=parent, title=_("Report"), url=None, 
        content=str_content, url_load=url_load)
    dlg.ShowModal()
    lib.GuiLib.safe_end_cursor() # again to be sure

def get_html(title, content, template, root='', file_name='', print_folder=''):
    """
    Returns HTML with embedded CSS.
    %title% is replaced with title
    %content% is replaced with the content
    """
    ## get html content
    with open(template, "r") as f:
        html = f.read()
    html = html.replace('%title%', title)
    html = html.replace('%content%', content)
    html = html.replace('%root%', mg.FILE_URL_START_GEN + root)
    ## save copy of html content (for printing)
    if print_folder:
        fpath = print_folder / file_name
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(html)
    return html

def get_html_header(title, header_template):
    "Get the HTML down as far as (and including) <body>"
    with open(header_template, "r") as f:
        hdr = f.read()
    hdr = hdr.replace('%title%', title)
    return hdr


class DlgHTML(wx.Dialog):
    "Show HTML window with content displayed"    

    def __init__(self, parent, title, *,
            url=None, content=None, url_load=False,
            file_name=mg.INT_REPORT_FILE, print_folder=mg.INT_FOLDER,
            width_reduction=80, height_reduction=40):
        """
        :param str url: url to display (either this or content).
        :param str content: html ready to display.
        :param str file_name: excludes any path information. Needed for printing
        :param str title: dialog title.
        :param str print_folder: needs to be a subfolder of the current folder
        :param int width_reduction: reduce dialog width by this much
        :param int height_reduction: reduce dialog height by this much
        """
        wx.Dialog.__init__(self, parent=parent, id=-1, title=title,
            style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.file_name = file_name
        self.print_folder = print_folder
        self.url = url
        self.content = content
        self.url_load = url_load
        self.html = wx.html2.WebView.New(self, -1, size=wx.DefaultSize)
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        btn_close = wx.Button(self, wx.ID_CLOSE, _("Close"))
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_main.Add(self.html,1,wx.GROW|wx.ALL, 5)
        if mg.PLATFORM == mg.WINDOWS:
            szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
            szr_btns.AddGrowableCol(1,2)
            btn_print = wx.Button(self, -1, _("Print"))
            btn_print.Bind(wx.EVT_BUTTON, self.on_print)        
            szr_btns.Add(btn_print, 0, wx.ALL, 5)
            szr_btns.Add(btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        else:
            szr_btns = wx.FlexGridSizer(rows=1, cols=1, hgap=5, vgap=5)
            szr_btns.AddGrowableCol(0,2)
            szr_btns.Add(btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        szr_main.Add(szr_btns, 0, wx.GROW)
        self.SetSizer(szr_main)
        self.Layout()
        height_adj = 60 if mg.PLATFORM != mg.WINDOWS else 0
        pos_y = 40 if mg.PLATFORM != mg.WINDOWS else 5
        self.SetSize(
            (mg.MAX_WIDTH - width_reduction, 
             mg.MAX_HEIGHT - (height_reduction+height_adj)))
        self.SetPosition((10, pos_y))
        self.Restore()
        lib.GuiLib.safe_end_cursor()

    def on_show(self, _event):
        self.show(self.url, self.content)
  
    def show(self, url=None, str_content=None):
        if str_content is None and url is None:
            raise Exception("Need whether string content or a url")
        if str_content:
            lib.OutputLib.update_html_ctrl(self.html, str_content)
        else:
            self.html.LoadURL(url)

    def show_str_content(self, content):
        self.html.SetPage(content, mg.BASE_URL)
        if mg.PLATFORM == mg.WINDOWS:
            self.html.Reload()  ## reload seems required to allow JS scripts to be loaded and Dojo charts to become visible

    def on_print(self, _event):
        "Print page"
        #printer = wx.html.HtmlEasyPrinting("Printing output", None)
        #printer.PrintFile(self.file_name) #horrible printing - large H1s, no CSS etc
        full_file = Path.cwd() / self.print_folder / self.file_name
        os.system(f'rundll32.exe MSHTML.DLL,PrintHTML "{full_file}"')

    def on_close(self, _event):
        "Close Viewer"        
        self.Destroy()    
