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
import googleapi.gdata.spreadsheet.service as gdata_spreadsheet_service
import googleapi.gdata.spreadsheet as gdata_spreadsheet
import googleapi.gdata.docs.service as gdata_docs_service
import googleapi.gdata.service as gdata_service
import lib

debug = True

GAUGE_STEPS = 50
SPREADSHEET_NAME = u"spreadsheet name"
SPREADSHEET_KEY = u"spreadsheet key"


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
        self.spreadsheet_dets_lst = [] # populated whenever signing in
        bx_spreadsheets = wx.StaticBox(self.panel, -1, 
                                       _("Select a spreadsheet"))
        szr_spreadsheets = wx.StaticBoxSizer(bx_spreadsheets, wx.VERTICAL)
        bx_worksheets = wx.StaticBox(self.panel, -1, 
                                       _("Select a worksheet"))
        szr_worksheets = wx.StaticBoxSizer(bx_worksheets, wx.VERTICAL)
        szr_download = wx.BoxSizer(wx.HORIZONTAL)
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
        self.lst_spreadsheets.Bind(wx.EVT_LIST_ITEM_ACTIVATED, 
                                   self.on_select_spreadsheet)
        self.btn_select_spreadsheet.Bind(wx.EVT_BUTTON, 
                                         self.on_select_spreadsheet)
        self.btn_select_spreadsheet.SetToolTipString(_("Select spreadsheet"))
        self.btn_select_spreadsheet.Enable(False)
        # worksheets
        self.lst_worksheets = wx.ListBox(self.panel, -1)
        self.lst_worksheets.SetSelection(0)
        # download
        self.lbl_download = wx.StaticText(self.panel, -1)
        self.btn_download = wx.Button(self.panel, -1, _("DOWNLOAD"))
        self.btn_download.Bind(wx.EVT_BUTTON, self.on_btn_download)
        self.btn_download.SetToolTipString(_("Download copy to local machine"))
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
        szr_download.Add(self.lbl_download, 1)
        szr_download.Add(self.btn_download, 0)
        szr_bottom_btns.Add(self.btn_restart, 0)
        szr_bottom_btns.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_sign_in, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_spreadsheets, 1, 
                     wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(szr_worksheets, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(szr_download, 0, wx.GROW|wx.LEFT|wx.RIGHT, 15)
        szr_main.Add(szr_bottom_btns, 0, wx.GROW|wx.TOP|wx.RIGHT|wx.LEFT, 15)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.init_enablement()
        self.Layout()
        lib.safe_end_cursor()
    
    def init_enablement(self):
        self.gd_client = None
        self.gs_client = None
        self.spreadsheet_key = None
        self.wksheet_idx = None
        self.txt_email.Enable(True)
        self.txt_email.SetValue(u"")
        self.txt_email.SetFocus()
        self.txt_pwd.Enable(True)
        self.txt_pwd.SetValue(u"")
        self.btn_sign_in.SetDefault()
        self.btn_sign_in.Enable(False)
        self.lst_spreadsheets.SetItems([_("Waiting for sign in")])
        #self.lst_spreadsheets.SetSelection(0)
        self.lst_spreadsheets.Enable(False)
        self.btn_select_spreadsheet.Enable(False)
        self.lst_worksheets.SetItems([_("Waiting for a spreadsheet to be "
                                                 "selected")])
        self.lst_worksheets.Enable(False)
        self.lbl_download.SetLabel(u"")
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
            self.gd_client = self.get_gd_client(email, pwd)
            self.gs_client = self.get_gs_client(email, pwd)
        except Exception, e:
            lib.safe_end_cursor()
            wx.MessageBox(_("Problem signing in. Orig error: %s") % e)
            return
        try:    
            self.spreadsheet_dets_lst = \
                                self.get_spreadsheet_dets_lst(self.gs_client)
        except Exception, e:
            lib.safe_end_cursor()
            wx.MessageBox(_("Problem getting spreadsheet details. "
                            "Orig error: %s") % e)
            return
        spreadsheets = [x[SPREADSHEET_NAME] for x in self.spreadsheet_dets_lst]
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
        if len(self.spreadsheet_dets_lst) == 1:
            spreadsheet_name = self.spreadsheet_dets_lst[0][SPREADSHEET_NAME]
            self.spreadsheet_key = self.spreadsheet_dets_lst[0][SPREADSHEET_KEY]
            self.lst_spreadsheets.Enable(False)
            self.btn_select_spreadsheet.Enable(False)
            self.process_worksheets()
            self.btn_download.Enable(True)
        lib.safe_end_cursor()

    def get_gd_client(self, email, pwd):
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
        return gd_client
    
    def get_gs_client(self, email, pwd):
        # setup a spreadsheets service for downloading spreadsheets
        debug = False
        gs_client = gdata_spreadsheet_service.SpreadsheetsService()
        try:
            gs_client.ClientLogin(email, pwd)
        except gdata_service.BadAuthentication, e:
            if debug:
                print("Orig error: %s" % e)
            raise Exception, (u"Problem signing into Google account with email "
                            "and password details supplied.")
        return gs_client
    
    def get_spreadsheet_dets_lst(self, gs_client):
        feed = gs_client.GetSpreadsheetsFeed()
        spreadsheet_dets_lst = []
        for entry in feed.entry:
            spreadsheet_name = entry.title.text
            spreadsheet_key = entry.id.text.rsplit('/', 1)[1]
            spreadsheet_dets = {SPREADSHEET_NAME: spreadsheet_name, 
                                SPREADSHEET_KEY: spreadsheet_key}
            spreadsheet_dets_lst.append(spreadsheet_dets)
        return spreadsheet_dets_lst
    
    def process_worksheets(self):
        # get worksheets for that spreadsheet
        worksheet_names = self.get_worksheet_names(self.spreadsheet_key)
        n_worksheets = len(worksheet_names)
        if n_worksheets == 0:
            lib.safe_end_cursor()
            wx.MessageBox(_("No worksheets available in %s") % spreadsheet_name)
            return
        elif n_worksheets == 1:
            self.wksheet_idx = 0
            worksheet_name = worksheet_names[self.wksheet_idx]
            self.lst_worksheets.SetItems(worksheet_names)
            self.lst_worksheets.SetSelection(self.wksheet_idx)
            self.lbl_download.SetLabel(_("Ready to download %s" % 
                                         worksheet_name))
        elif n_worksheets > 0:
            self.wksheet_idx = 0
            self.lst_worksheets.Enable(True)
            self.lst_worksheets.SetItems(worksheet_names)
            self.lst_worksheets.SetSelection(self.wksheet_idx)
    
    def get_worksheet_names(self, spreadsheet_key):
        feed = self.gs_client.GetWorksheetsFeed(spreadsheet_key)
        worksheet_names = []
        for entry in feed.entry:
            worksheet_names.append(entry.title.text)
        return worksheet_names
    
    def on_select_spreadsheet(self, event):
        idx = self.lst_spreadsheets.GetFirstSelected()
        try:
            sel_spreadsheet_dets = self.spreadsheet_dets_lst[idx]
        except Exception:
            wx.MessageBox(_("Please select a spreadsheet"))
            event.Skip()
            return
        self.spreadsheet_key = sel_spreadsheet_dets[SPREADSHEET_KEY]
        self.process_worksheets()
    
    def on_btn_download(self, event):
        wx.BeginBusyCursor()
        url = (
            u"http://spreadsheets.google.com/feeds/download/spreadsheets/Export"
            u"?key=%s&exportFormat=%s") % (self.spreadsheet_key, 
                                           mg.GOOGLE_DOWNLOAD_EXT)
        file_path = os.path.join(mg.INT_PATH, mg.GOOGLE_DOWNLOAD)
        docs_token = self.gd_client.GetClientLoginToken()
        self.gd_client.SetClientLoginToken(self.gs_client.GetClientLoginToken())
        self.gd_client.Export(url, file_path, gid=self.wksheet_idx)
        self.gd_client.SetClientLoginToken(docs_token)
        lib.safe_end_cursor()
        wx.MessageBox(_("Successfully downloaded worksheet ready for import."))
        self.Destroy()
    
    def on_btn_restart(self, event):
        self.init_enablement()
        
    def on_close(self, event):
        self.Destroy()
