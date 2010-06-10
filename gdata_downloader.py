#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
http://code.google.com/apis/documents/docs/1.0/developers_guide_python.html...
    ...#DownloadingSpreadsheets
http://code.google.com/apis/documents/docs/2.0/developers_guide_protocol.html...
    ...#DownloadingSpreadsheets
"""
from __future__ import print_function
import os
import wx

import my_globals as mg
import googleapi.gdata.docs.service as gdata_docs_service
import googleapi.gdata.spreadsheet.service as gdata_spreadsheet_service
import googleapi.gdata.spreadsheet as gdata_spreadsheet
import googleapi.gdata.service as gdata_service
import lib

debug = True

GAUGE_STEPS = 50


class GdataDownloadDlg(wx.Dialog):
    def __init__(self, parent):
        debug = False
        wx.BeginBusyCursor()
        title = _("Download Google Spreadsheet")
        wx.Dialog.__init__(self, parent=parent, title=title, 
                       style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|\
                       wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN, 
                       pos=(mg.HORIZ_OFFSET+100,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        self.btn_sign_in = wx.Button(self.panel, -1, _("Sign In"))
        self.btn_select_spreadsheet = wx.Button(self.panel, 1, _("Select"))
        bx_sign_in = wx.StaticBox(self.panel, -1, 
                                  _("Sign into your Google Account"))
        szr_sign_in = wx.StaticBoxSizer(bx_sign_in, wx.VERTICAL)
        szr_sign_in_inner = wx.FlexGridSizer(rows=2, cols=3, hgap=5, vgap=5)
        szr_sign_in.Add(szr_sign_in_inner, 0, wx.GROW|wx.TOP, 10)
        bx_spreadsheets = wx.StaticBox(self.panel, -1, 
                                       _("Select a spreadsheet"))
        szr_spreadsheets = wx.StaticBoxSizer(bx_spreadsheets, wx.VERTICAL)
        bx_worksheets = wx.StaticBox(self.panel, -1, 
                                       _("Select a worksheet"))
        szr_worksheets = wx.StaticBoxSizer(bx_worksheets, wx.VERTICAL)
        szr_bottom_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_bottom_btns.AddGrowableCol(0,2) # idx, propn
        
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # sign in details
        self.lbl_email = wx.StaticText(self.panel, -1, _("Email login:"))
        self.lbl_email.SetFont(lblfont)
        self.txt_email = wx.TextCtrl(self.panel, -1, u"", size=(320,-1))
        self.txt_email.Bind(wx.EVT_CHAR, self.on_sign_in_char)
        
        img_ctrl_gdata = wx.StaticBitmap(self.panel)
        img_gdata = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                u"google_spreadsheet.xpm"), wx.BITMAP_TYPE_XPM)
        bmp_gdata = wx.BitmapFromImage(img_gdata)
        img_ctrl_gdata.SetBitmap(bmp_gdata)
        
        self.lbl_pwd = wx.StaticText(self.panel, -1, _("Password:"))
        self.lbl_pwd.SetFont(lblfont)
        self.txt_pwd = wx.TextCtrl(self.panel, -1, u"", style=wx.TE_PASSWORD, 
                                   size=(320,-1))
        self.txt_pwd.Bind(wx.EVT_CHAR, self.on_sign_in_char)
        self.btn_sign_in.Bind(wx.EVT_BUTTON, self.on_btn_sign_in)
        self.btn_sign_in.SetToolTipString(_("Sign into Google Account"))
        # spreadsheets
        self.lst_spreadsheets = wx.ListBox(self.panel, -1)
        self.btn_select_spreadsheet.Bind(wx.EVT_BUTTON, 
                                         self.on_btn_select_spreadsheet)
        self.btn_select_spreadsheet.SetToolTipString(_("Select spreadsheet"))
        self.btn_select_spreadsheet.Enable(False)
        # worksheets
        self.lst_worksheets = wx.ListBox(self.panel, -1, 
                                       choices=[_("Waiting for a spreadsheet to"
                                                 " be selected")])
        self.lst_worksheets.SetSelection(0)
        # download
        self.btn_download = wx.Button(self.panel, -1, _("DOWNLOAD"))
        self.btn_download.Bind(wx.EVT_BUTTON, self.on_btn_download)
        self.btn_download.SetToolTipString(_("Download copy to local machine"))
        # progress
        self.progbar = wx.Gauge(self.panel, -1, GAUGE_STEPS, size=(-1, 20),
                                style=wx.GA_PROGRESSBAR)
        # bottom buttons
        self.btn_restart = wx.Button(self.panel, -1, _("Restart"))
        self.btn_restart.Bind(wx.EVT_BUTTON, self.on_btn_restart)
        self.btn_restart.SetToolTipString(_("Start again with a fresh sign in"))
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        self.btn_close.SetToolTipString(_("Close"))
        # assembly
        szr_sign_in_inner.Add(self.lbl_email, 0)
        szr_sign_in_inner.Add(self.txt_email, 0, wx.LEFT|wx.ALIGN_RIGHT, 10)
        szr_sign_in_inner.Add(img_ctrl_gdata, 0, 
                              wx.ALIGN_RIGHT|wx.BOTTOM|wx.RIGHT, 5)
        szr_sign_in_inner.Add(self.lbl_pwd, 0)
        szr_sign_in_inner.Add(self.txt_pwd, 0, wx.LEFT|wx.ALIGN_RIGHT, 10)
        szr_sign_in_inner.Add(self.btn_sign_in)
        szr_spreadsheets.Add(self.lst_spreadsheets, 1, 
                             wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szr_spreadsheets.Add(self.btn_select_spreadsheet, 0, wx.ALIGN_RIGHT)
        szr_worksheets.Add(self.lst_worksheets, 1, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        
        szr_bottom_btns.Add(self.btn_restart, 0)
        szr_bottom_btns.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        
        szr_main.Add(szr_sign_in, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_spreadsheets, 1, 
                     wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(szr_worksheets, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(self.btn_download, 0, wx.ALIGN_RIGHT|wx.RIGHT, 15)
        szr_main.Add(self.progbar, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_main.Add(szr_bottom_btns, 0, wx.GROW|wx.TOP|wx.RIGHT|wx.LEFT, 15)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.init_enablement()
        self.Layout()
        lib.safe_end_cursor()
    
    def init_enablement(self):
        self.txt_email.Enable(True)
        self.txt_email.SetValue(u"")
        self.txt_email.SetFocus()
        self.txt_pwd.Enable(True)
        self.txt_pwd.SetValue(u"")
        self.btn_sign_in.SetDefault()
        self.btn_sign_in.Enable(False)
        self.lst_spreadsheets.SetItems([_("Waiting for sign in")])
        self.lst_spreadsheets.SetSelection(0)
        self.lst_spreadsheets.Enable(False)
        self.btn_select_spreadsheet.Enable(False)
        self.lst_worksheets.Enable(False)
        self.btn_download.Enable(False)
        self.btn_restart.Enable(False)
        
    def on_sign_in_char(self, event):
        # NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.align_btn_to_completeness)
        event.Skip()
        
    def align_btn_to_completeness(self):
        debug = False
        email = self.txt_email.GetValue()
        pwd = self.txt_pwd.GetValue()
        complete = (email != u"" and pwd != u"")
        if debug: print("email: \"%s\" pwd: \"%s\" complete: %s" % \
                        (email, pwd, complete))
        self.btn_sign_in.Enable(complete)
    
    def on_btn_sign_in(self, event):
        # both filled in?
        wx.BeginBusyCursor()
        self.progbar.SetValue(0)
        email = self.txt_email.GetValue()
        pwd = self.txt_pwd.GetValue()
        complete = (email != u"" and pwd != u"")
        if not complete:
            lib.safe_end_cursor()
            wx.MessageBox(_("Please complete both email and password and try "
                            "again"))
            self.txt_email.SetFocus()
            return
        try:
            spreadsheet_dets_lst = self.get_spreadsheet_dets_lst(email, pwd)
        except Exception, e:
            lib.safe_end_cursor()
            wx.MessageBox(_("Problem signing in. Orig error: %s") % e)
            return
        spreadsheets = [x[0] for x in spreadsheet_dets_lst]
        if not spreadsheets:
            lib.safe_end_cursor()
            wx.MessageBox(_("No spreadsheets available under this Google "
                            "account"))
            return
        self.lst_spreadsheets.SetItems(spreadsheets)
        self.lst_spreadsheets.SetSelection(0)
        self.txt_email.Enable(False)
        self.txt_pwd.Enable(False)
        self.btn_sign_in.Enable(False)
        self.lst_spreadsheets.Enable(True)
        self.btn_select_spreadsheet.Enable(True)
        self.btn_restart.Enable(True)
        lib.safe_end_cursor()
    
    def get_spreadsheet_dets_lst(self, email, pwd):
        # get a docs client
        debug = False
        gd_client = gdata_docs_service.DocsService()
        try:
            gd_client.ClientLogin(email, pwd)
        except gdata_service.Error, e:
            if debug:
                print("Orig error: %s" % e)
            raise Exception, (u"Problem signing into Google account with email "
                            "and password details supplied.")        
        # setup a spreadsheets service for downloading spreadsheets
        gs_client = gdata_spreadsheet_service.SpreadsheetsService()
        gs_client.ClientLogin(email, pwd)
        feed = gs_client.GetSpreadsheetsFeed()
        spreadsheet_dets_lst = []
        for entry in feed.entry:
            spreadsheet_dets = (entry.title.text, 
                                entry.id.text.rsplit('/', 1)[1])
            spreadsheet_dets_lst.append(spreadsheet_dets)
        return spreadsheet_dets_lst
    
    
    def download_as_csv(self, feed):
        url = (u"http://spreadsheets.google.com/feeds/download/spreadsheets/Export?"
               u"key=%(example_spreadsheet_id)s&exportFormat=%(example_format)s") % \
               {"example_spreadsheet_id": key,
                "example_format": "csv"}
        file_path = '/home/g/Desktop/your_spreadsheets.csv'
        docs_token = gd_client.GetClientLoginToken()
        gd_client.SetClientLoginToken(gs_client.GetClientLoginToken())
        wksheet_idx = 0
        gd_client.Export(url, file_path, gid=wksheet_idx)
        gd_client.SetClientLoginToken(docs_token)
        
    
    def on_btn_select_spreadsheet(self, event):
        pass
    
    def on_btn_select_worksheet(self, event):
        pass
    
    def on_btn_download(self, event):
        pass
    
    def on_btn_restart(self, event):
        self.init_enablement()
        
    def on_close(self, event):
        self.Destroy()
