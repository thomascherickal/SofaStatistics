#! /usr/bin/env python
# -*- coding: utf-8 -*-

#leave one of these out and it might fail silently!
import sys
import os
import pprint
import wx
import wx.gizmos

import my_globals
import demotables
import dimtables
import dimtree
import full_html
import gen_config
import getdata
import make_table
import output_buttons
import projects

             
class DlgMakeTable(wx.Dialog, 
                   gen_config.GenConfig, output_buttons.OutputButtons,
                   make_table.MakeTable, dimtree.DimTree):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
    """
    
    def __init__(self, dbe, conn_dets, default_dbs=None, 
                 default_tbls=None, fil_labels="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None):
         
        wx.Dialog.__init__(self, parent=None, id=-1, title="Make Report Table", 
                           pos=(200, 0), 
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.conn_dets = conn_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_labels = fil_labels
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script        
        self.var_labels, self.var_notes, self.val_dics = \
            projects.GetLabels(fil_labels)            
        self.open_html = []
        self.open_scripts = []
        self.col_no_vars_item = None # needed if no variable in columns
        # set up panel for frame
        self.panel = wx.Panel(self)
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, "images",
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)   
        self.SetIcons(ib)
        self.GenConfigSetup()
        self.SetupOutputButtons()
        # title details
        lblTitles = wx.StaticText(self.panel, -1, "Title:")
        lblTitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                     style=wx.TE_MULTILINE)
        self.txtTitles.Bind(wx.EVT_TEXT, self.OnTitleChange)
        lblSubtitles = wx.StaticText(self.panel, -1, "Subtitle:")
        lblSubtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txtSubtitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                        style=wx.TE_MULTILINE)
        self.txtSubtitles.Bind(wx.EVT_TEXT, self.OnSubtitleChange)
        #radio
        self.radTabType = wx.RadioBox(self.panel, -1, "Table Type", 
                         choices=("Column measures e.g. FREQ, row % etc",
                                  "Summarise rows e.g. MEAN, MEDIAN etc",
                                  "Display table data as is"),
                         style=wx.RA_SPECIFY_ROWS)
        self.radTabType.Bind(wx.EVT_RADIOBOX, self.OnTabTypeChange)
        self.tab_type = self.radTabType.GetSelection()
        # option checkboxs
        self.chkTotalsRow = wx.CheckBox(self.panel, -1, "Totals Row?")
        self.chkTotalsRow.Bind(wx.EVT_CHECKBOX, self.OnChkTotalsRow)
        self.chkFirstAsLabel = wx.CheckBox(self.panel, -1, 
                                           "First col as label?")
        self.chkFirstAsLabel.Bind(wx.EVT_CHECKBOX, self.OnChkFirstAsLabel)
        self.EnableOpts(enable=False)
        #text labels
        lblRows = wx.StaticText(self.panel, -1, "Rows:")
        lblRows.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        lblCols = wx.StaticText(self.panel, -1, "Columns:")
        lblCols.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        #buttons
        #rows
        self.btnRowAdd = wx.Button(self.panel, -1, "Add")
        self.btnRowAdd.Bind(wx.EVT_BUTTON, self.OnRowAdd)
        #self.btnRowAdd.Bind(wx.EVT_ENTER_WINDOW, self.OnAddRowEnterWindow)
        #self.btnRowAdd.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnRowAddUnder = wx.Button(self.panel, -1, "Add Under")
        self.btnRowAddUnder.Bind(wx.EVT_BUTTON, self.OnRowAddUnder)
        #self.btnRowAddUnder.Bind(wx.EVT_ENTER_WINDOW, self.OnAddRowUnderEnterWindow)
        #self.btnRowAddUnder.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnRowDel = wx.Button(self.panel, -1, "Delete")
        self.btnRowDel.Bind(wx.EVT_BUTTON, self.OnRowDelete)
        #self.btnRowDel.Bind(wx.EVT_ENTER_WINDOW, self.OnDeleteRowEnterWindow)
        #self.btnRowDel.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnRowConf = wx.Button(self.panel, -1, "Config")
        self.btnRowConf.Bind(wx.EVT_BUTTON, self.OnRowConfig)
        #self.btnRowConf.Bind(wx.EVT_ENTER_WINDOW, self.OnConfigRowEnterWindow)
        #self.btnRowConf.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        #cols
        self.btnColAdd = wx.Button(self.panel, -1, "Add")
        self.btnColAdd.Bind(wx.EVT_BUTTON, self.OnColAdd)
        #self.btnColAdd.Bind(wx.EVT_ENTER_WINDOW, self.OnAddColEnterWindow)
        #self.btnColAdd.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnColAddUnder = wx.Button(self.panel, -1, "Add Under")
        self.btnColAddUnder.Bind(wx.EVT_BUTTON, self.OnColAddUnder)
        #self.btnColAddUnder.Bind(wx.EVT_ENTER_WINDOW, 
        #                    self.OnAddColUnderEnterWindow)
        #self.btnColAddUnder.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnColDel = wx.Button(self.panel, -1, "Delete")
        self.btnColDel.Bind(wx.EVT_BUTTON, self.OnColDelete)
        #self.btnColDel.Bind(wx.EVT_ENTER_WINDOW, 
        #               self.OnDeleteColEnterWindow)
        #self.btnColDel.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        self.btnColConf = wx.Button(self.panel, -1, "Config")
        self.btnColConf.Bind(wx.EVT_BUTTON, self.OnColConfig)
        #self.btnColConf.Bind(wx.EVT_ENTER_WINDOW, 
        #                self.OnConfigColEnterWindow)
        #self.btnColConf.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)       
        #trees
        self.rowtree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnRowItemActivated)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRowItemRightClick)
        self.rowRoot = self.setupDimTree(self.rowtree)
        self.coltree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.coltree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnColItemActivated)
        self.coltree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnColItemRightClick)
        self.colRoot = self.setupDimTree(self.coltree)
        #setup demo table type
        self.demo_tab = demotables.GenDemoTable(txtTitles=self.txtTitles, 
                                 txtSubtitles=self.txtSubtitles,
                                 colRoot=self.colRoot, 
                                 rowRoot=self.rowRoot, 
                                 rowtree=self.rowtree, 
                                 coltree=self.coltree, 
                                 col_no_vars_item=self.col_no_vars_item, 
                                 var_labels=self.var_labels, 
                                 val_dics=self.val_dics,
                                 fil_css=self.fil_css)
        self.html = full_html.FullHTML(self.panel, size=(200,250))        
        lbldemo_tbls = wx.StaticText(self.panel, -1, "Demonstration Table:")
        lbldemo_tbls.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        # main section SIZERS **************************************************************
        szrMain = wx.BoxSizer(wx.VERTICAL)
        self.SetupGenConfigSizer()
        szrMid = wx.BoxSizer(wx.HORIZONTAL)
        szrDims = wx.BoxSizer(wx.HORIZONTAL)
        #2 MID
        #3 TABTYPE
        szrTabType = wx.BoxSizer(wx.HORIZONTAL)
        szrTabType.Add(self.radTabType, 0)
        #3 TITLES/OPTIONS
        szrTitlesOptions = wx.BoxSizer(wx.VERTICAL)
        #4 TITLE DETS
        szrTitleDets = wx.BoxSizer(wx.HORIZONTAL)
        #5 TITLES
        szrTitles = wx.BoxSizer(wx.VERTICAL)
        szrTitles.Add(lblTitles, 0)
        szrTitles.Add(self.txtTitles, 0, wx.GROW)
        #5 Subtitles
        szrSubtitles = wx.BoxSizer(wx.VERTICAL)
        szrSubtitles.Add(lblSubtitles, 0)
        szrSubtitles.Add(self.txtSubtitles, 0, wx.GROW)
        #4 TITLE assembly
        szrTitleDets.Add(szrTitles, 1, wx.GROW|wx.LEFT, 5)
        szrTitleDets.Add(szrSubtitles, 1, wx.GROW|wx.LEFT, 5)
        #4 totals row
        szrOpts = wx.BoxSizer(wx.HORIZONTAL)
        szrOpts.Add(self.chkTotalsRow, 0, wx.LEFT|wx.TOP, 5)        
        szrOpts.Add(self.chkFirstAsLabel, 0, wx.LEFT|wx.TOP, 5)
        #3 TITLES/OPTIONS assembly      
        szrTitlesOptions.Add(szrTitleDets, 1, wx.GROW|wx.LEFT, 5)
        szrTitlesOptions.Add(szrOpts, 0, wx.LEFT, 5)
        #3 MID assembly
        szrMid.Add(szrTabType, 0)
        szrMid.Add(szrTitlesOptions, 1, wx.GROW)
        #2 DIMS
        #3 TREES
        szrTrees = wx.BoxSizer(wx.HORIZONTAL)
        #4 ROWS
        szrRows = wx.BoxSizer(wx.VERTICAL)
        szrRows.Add(lblRows, 0)
        szrRowButtons = wx.BoxSizer(wx.HORIZONTAL)
        szrRowButtons.Add(self.btnRowAdd, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowAddUnder, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowDel, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowConf)
        szrRows.Add(szrRowButtons, 0)
        szrRows.Add(self.rowtree, 1, wx.GROW)
        #4 COLS
        szrCols = wx.BoxSizer(wx.VERTICAL)
        szrCols.Add(lblCols, 0)
        szrColButtons = wx.BoxSizer(wx.HORIZONTAL)
        szrColButtons.Add(self.btnColAdd, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColAddUnder, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColDel, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColConf)
        szrCols.Add(szrColButtons)
        szrCols.Add(self.coltree, 1, wx.GROW)
        #3 TREES assemble
        szrTrees.Add(szrRows, 1, wx.GROW|wx.RIGHT, 2)
        szrTrees.Add(szrCols, 1, wx.GROW|wx.LEFT, 2)
        # standard output buttons handled in output_buttons
        #2 MID assemble
        szrDims.Add(szrTrees, 1, wx.GROW|wx.RIGHT, 5)
        szrDims.Add(self.szrButtons, 0, wx.GROW)
        #2 HTML
        szrHtml = wx.BoxSizer(wx.VERTICAL)
        szrHtml.Add(lbldemo_tbls, 0)
        szrHtml.Add(self.html, 1, wx.GROW)
        #1 MAIN assemble
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrMid, 0, wx.GROW|wx.ALL, 10)
        szrMain.Add(szrDims, 5, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrMain.Add(szrHtml, 8, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(self.szrConfig, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(self.szrOutput, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        #status bar
        #self.statusbar = self.CreateStatusBar()
        #attach main sizer to panel>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Fit() #needed, otherwise initial display problem with 
        #  status bar
        
    # database/ tables (and views)
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        Clear dim areas.
        """
        gen_config.GenConfig.OnDatabaseSel(self, event)
        self.ClearDims()
        
    def OnTableSel(self, event):
        """
        Reset table, fields, has_unique, and idxs.
        Clear dim areas.
        """       
        gen_config.GenConfig.OnTableSel(self, event)
        self.ClearDims()
