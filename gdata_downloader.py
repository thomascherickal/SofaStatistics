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
import googleapi.gdata.docs.service as gservice
import googleapi.gdata.spreadsheet.service as sservice
import googleapi.gdata.spreadsheet as gdata_spreadsheet
import lib
import string

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
        szr_close = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_close.AddGrowableCol(0,2) # idx, propn
        
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # connection details
        self.lbl_email = wx.StaticText(self.panel, -1, _("Email login:"))
        self.lbl_email.SetFont(lblfont)
        self.txt_email = wx.TextCtrl(self.panel, -1, u"", size=(320,-1))
        self.txt_email.SetFocus()
        
        img_ctrl_gdata = wx.StaticBitmap(self.panel)
        img_gdata = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                u"google_spreadsheet.xpm"), wx.BITMAP_TYPE_XPM)
        bmp_gdata = wx.BitmapFromImage(img_gdata)
        img_ctrl_gdata.SetBitmap(bmp_gdata)
        
        self.lbl_pwd = wx.StaticText(self.panel, -1, _("Password:"))
        self.lbl_pwd.SetFont(lblfont)
        self.txt_pwd = wx.TextCtrl(self.panel, -1, u"", size=(320,-1))
        self.btn_sign_in.Bind(wx.EVT_BUTTON, self.on_btn_sign_in)
        self.btn_sign_in.SetToolTipString(_("Sign into Google Account"))
        # spreadsheets
        self.lst_spreadsheets = wx.ListBox(self.panel, -1, 
                                           choices=[_("Waiting for sign in")])
        self.lst_spreadsheets.SetSelection(0)
        self.lst_spreadsheets.Enable(False)
        self.btn_select_spreadsheet.Bind(wx.EVT_BUTTON, 
                                         self.on_btn_select_spreadsheet)
        self.btn_select_spreadsheet.SetToolTipString(_("Select spreadsheet"))
        self.btn_select_spreadsheet.Enable(False)
        # worksheets
        self.lst_worksheets = wx.ListBox(self.panel, -1, 
                                       choices=[_("Waiting for a spreadsheet to"
                                                 " be selected")])
        self.lst_worksheets.SetSelection(0)
        self.lst_worksheets.Enable(False)
        # download
        self.btn_download = wx.Button(self.panel, -1, _("DOWNLOAD"))
        self.btn_download.Bind(wx.EVT_BUTTON, self.on_btn_download)
        self.btn_download.SetToolTipString(_("Download copy to local machine"))
        self.btn_download.Enable(False)
        # progress
        self.progbar = wx.Gauge(self.panel, -1, GAUGE_STEPS, size=(-1, 20),
                                style=wx.GA_PROGRESSBAR)
        # close
        self.lbl_feedback = wx.StaticText(self.panel)
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
                              
        szr_spreadsheets.Add(self.lst_spreadsheets, 1, wx.GROW|wx.ALL, 10)
        szr_spreadsheets.Add(self.btn_select_spreadsheet, 0, wx.ALIGN_RIGHT)
        szr_worksheets.Add(self.lst_worksheets, 1, wx.GROW|wx.ALL, 10)
        
        szr_close.Add(self.lbl_feedback)
        szr_close.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        
        szr_main.Add(szr_sign_in, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_spreadsheets, 1, 
                     wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(szr_worksheets, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_main.Add(self.btn_download, 0, wx.ALIGN_RIGHT|wx.RIGHT, 15)
        szr_main.Add(self.progbar, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_close, 0, wx.GROW|wx.TOP|wx.RIGHT, 15)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        self.ctrl_enablement()
        lib.safe_end_cursor()

    def ctrl_enablement(self):
        pass

    def download_as_csv(self):
        # get a docs client
        gd_client = gservice.DocsService()
        gd_client.ClientLogin('grant@p-s.co.nz', 'beatmss00n')
        
        # setup a spreadsheets service for downloading spreadsheets
        gs_client = sservice.SpreadsheetsService()
        gs_client.ClientLogin('grant@p-s.co.nz', 'beatmss00n')
        feed = gs_client.GetSpreadsheetsFeed()
        
        def PrintFeed(feed):
            for i, entry in enumerate(feed.entry):
                if isinstance(feed, gdata_spreadsheet.SpreadsheetsCellsFeed):
                    print('%s %s\n' % (entry.title.text, entry.content.text))
                elif isinstance(feed, gdata_spreadsheet.SpreadsheetsListFeed):
                    print('%s %s %s' % (i, entry.title.text, entry.content.text))
                    # Print this row's value for each column (the custom dictionary is
                    # built from the gsx: elements in the entry.) See the description of
                    # gsx elements in the protocol guide.
                    print('Contents:')
                    for key in entry.custom:
                        print('  %s: %s' % (key, entry.custom[key].text))
                        print('\n')
                else:
                    print('%s %s\n' % (i, entry.title.text))

        PrintFeed(feed)
        input = raw_input('\nSelection: ')
        key = feed.entry[string.atoi(input)].id.text.rsplit('/', 1)[1]
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
    
    def on_btn_sign_in(self, event):
        pass
    
    def on_btn_select_spreadsheet(self, event):
        pass
    
    def on_btn_select_worksheet(self, event):
        pass
    
    def on_btn_download(self, event):
        pass
    
    def on_close(self, event):
        self.Destroy()
