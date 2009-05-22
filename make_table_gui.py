#! /usr/bin/env python
# -*- coding: utf-8 -*-

#leave one of these out and it might fail silently!
import sys
import os
import pprint
import wx
import wx.gizmos

import demotables
import dimtables
import dimtree
import full_html
import getdata
import make_table
import projects
import util

SCRIPT_PATH = util.get_script_path()

             
class DlgMakeTable(wx.Dialog, make_table.MakeTable, dimtree.DimTree):
    
    def __init__(self, title, dbe, conn_dets, default_dbs=None, 
                 default_tbls=None, fil_labels="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None, pos=wx.DefaultPosition, size=wx.DefaultSize):
         
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, pos=pos,
                          style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                          wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                          wx.CAPTION | wx.CLOSE_BOX | \
                          wx.CLIP_CHILDREN)
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
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, 
                                        "images", 
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)   
        self.SetIcons(ib)
        # Data details
        # Databases
        lblDatabases = wx.StaticText(self.panel, -1, "Database:")
        lblDatabases.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        # set up self.dropDatabases and self.dropTables
        getdata.setupDataDropdowns(self, self.panel, dbe, conn_dets, 
                                   default_dbs, default_tbls)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        # Tables
        lblTables = wx.StaticText(self.panel, -1, "Table:")
        lblTables.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.dropTables.Bind(wx.EVT_CHOICE, self.OnTableSel)
        # Data config details
        lblLabelPath = wx.StaticText(self.panel, -1, "Labels:")
        lblLabelPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtLabelsFile = wx.TextCtrl(self.panel, -1, self.fil_labels, 
                                         size=(250,-1))
        self.txtLabelsFile.Bind(wx.EVT_KILL_FOCUS, self.OnLabelFileLostFocus)
        btnLabelPath = wx.Button(self.panel, -1, "Browse ...")
        btnLabelPath.Bind(wx.EVT_BUTTON, self.OnButtonLabelPath)
        #btnLabelPath.Bind(wx.EVT_ENTER_WINDOW, self.LabelPathEnterWindow)
        #btnLabelPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # CSS style config details
        lblCssPath = wx.StaticText(self.panel, -1, "CSS file:")
        lblCssPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtCssFile = wx.TextCtrl(self.panel, -1, self.fil_css, 
                                      size=(250,-1))
        self.txtCssFile.Bind(wx.EVT_KILL_FOCUS, self.OnCssFileLostFocus)
        btnCssPath = wx.Button(self.panel, -1, "Browse ...")
        btnCssPath.Bind(wx.EVT_BUTTON, self.OnButtonCssPath)
        #btnCssPath.Bind(wx.EVT_ENTER_WINDOW, self.CssPathEnterWindow)
        #btnCssPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # Output details
        # report 
        lblReportPath = wx.StaticText(self.panel, -1, "Report:")
        lblReportPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtReportFile = wx.TextCtrl(self.panel, -1, self.fil_report, 
                                         size=(250,-1))
        self.txtReportFile.Bind(wx.EVT_KILL_FOCUS, self.OnReportFileLostFocus)
        btnReportPath = wx.Button(self.panel, -1, "Browse ...")
        btnReportPath.Bind(wx.EVT_BUTTON, self.OnButtonReportPath)
        #btnReportPath.Bind(wx.EVT_ENTER_WINDOW, self.ReportPathEnterWindow)
        #btnReportPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # script
        lblScriptPath = wx.StaticText(self.panel, -1, "Script:")
        lblScriptPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtScriptFile = wx.TextCtrl(self.panel, -1, self.fil_script, 
                                   size=(250,-1))
        self.txtScriptFile.Bind(wx.EVT_KILL_FOCUS, self.OnScriptFileLostFocus)
        btnScriptPath = wx.Button(self.panel, -1, "Browse ...")
        btnScriptPath.Bind(wx.EVT_BUTTON, self.OnButtonScriptPath)
        #btnScriptPath.Bind(wx.EVT_ENTER_WINDOW, self.ScriptPathEnterWindow)
        #btnScriptPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
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
        #main
        btnRun = wx.Button(self.panel, -1, "RUN")
        btnRun.Bind(wx.EVT_BUTTON, self.OnButtonRun)
        #btnRun.Bind(wx.EVT_ENTER_WINDOW, self.OnRunEnterWindow)
        #btnRun.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)        
        btnExport = wx.Button(self.panel, -1, "EXPORT")
        btnExport.Bind(wx.EVT_BUTTON, self.OnButtonExport)
        #btnExport.Bind(wx.EVT_ENTER_WINDOW, self.OnExportEnterWindow)
        #btnExport.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        btnHelp = wx.Button(self.panel, -1, "HELP")
        #btnHelp.Bind(wx.EVT_BUTTON, self.OnButtonView)
        #btnHelp.Bind(wx.EVT_ENTER_WINDOW, self.OnHelpEnterWindow)
        #btnHelp.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        btnClear = wx.Button(self.panel, -1, "CLEAR")
        btnClear.Bind(wx.EVT_BUTTON, self.OnButtonClear)
        #btnClear.Bind(wx.EVT_ENTER_WINDOW, self.OnClearEnterWindow)
        #btnClear.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        btnClose = wx.Button(self.panel, -1, "CLOSE")
        btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        #btnClose.Bind(wx.EVT_ENTER_WINDOW, self.OnCloseEnterWindow)
        #btnClose.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
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
        
        #self.html = wx.webview.WebView(self.panel, -1, size=(200,250))
        
        lbldemo_tbls = wx.StaticText(self.panel, -1, "Demonstration Table:")
        lbldemo_tbls.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        # main section SIZERS **************************************************************
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxData = wx.StaticBox(self.panel, -1, "Data Source")
        szrData = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        szrConfig = wx.BoxSizer(wx.HORIZONTAL)
        bxOutput = wx.StaticBox(self.panel, -1, "Output")
        szrOutput = wx.StaticBoxSizer(bxOutput, wx.HORIZONTAL)
        szrMid = wx.BoxSizer(wx.HORIZONTAL)
        szrDims = wx.BoxSizer(wx.HORIZONTAL)
        #1 MAIN
        #2 DATA
        #3 DATA INNER
        szrDataInner = wx.BoxSizer(wx.HORIZONTAL)
        szrDataInner.Add(lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        szrDataInner.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        szrDataInner.Add(lblTables, 0, wx.RIGHT, 5)
        szrDataInner.Add(self.dropTables, 0)
        szrData.Add(szrDataInner)
        #2 CONFIG
        #3 DATA CONFIG
        bxDataConfig = wx.StaticBox(self.panel, -1, "Data Config")
        szrDataConfig = wx.StaticBoxSizer(bxDataConfig, wx.HORIZONTAL)
        #3 DATA CONFIG INNER
        szrDataConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrDataConfigInner.Add(lblLabelPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrDataConfigInner.Add(self.txtLabelsFile, 1, wx.GROW|wx.RIGHT, 10)
        szrDataConfigInner.Add(btnLabelPath, 0)
        szrDataConfig.Add(szrDataConfigInner, 1)
        szrConfig.Add(szrDataConfig, 1, wx.RIGHT, 10)
        #3 CSS CONFIG
        bxCssConfig = wx.StaticBox(self.panel, -1, "Table Style")
        szrCssConfig = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        #3 CSS CONFIG INNER
        szrCssConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrCssConfigInner.Add(lblCssPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrCssConfigInner.Add(self.txtCssFile, 1, wx.GROW|wx.RIGHT, 10)
        szrCssConfigInner.Add(btnCssPath, 0)
        szrCssConfig.Add(szrCssConfigInner, 1)
        szrConfig.Add(szrCssConfig, 1)
        #2 OUTPUT
        #3 OUTPUT INNER
        szrOutputInner = wx.BoxSizer(wx.HORIZONTAL)
        # report 
        szrOutputInner.Add(lblReportPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtReportFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(btnReportPath, 0, wx.RIGHT, 10)
        # script
        szrOutputInner.Add(lblScriptPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtScriptFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(btnScriptPath, 0)
        szrOutput.Add(szrOutputInner, 1)
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
        #3 BUTTONS
        szrButtons = wx.FlexGridSizer(rows=3, cols=1, hgap=5, vgap=5)
        szrButtons.AddGrowableRow(2,2) #only relevant if surrounding sizer 
        #  stretched vertically enough by its content
        szrButtons.Add(btnRun, 0, wx.TOP, 0)
        szrButtons.Add(btnExport, 0)
        szrButtons.Add(btnHelp, 0)
        szrButtons.Add(btnClear, 0)
        szrButtons.Add(btnClose, 1, wx.ALIGN_BOTTOM)
        #2 MID assemble
        szrDims.Add(szrTrees, 1, wx.GROW|wx.RIGHT, 5)
        szrDims.Add(szrButtons, 0, wx.GROW)
        #2 HTML
        szrHtml = wx.BoxSizer(wx.VERTICAL)
        szrHtml.Add(lbldemo_tbls, 0)
        szrHtml.Add(self.html, 1, wx.GROW)
        #1 MAIN assemble
        szrMain.Add(szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrConfig, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrOutput, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrMid, 0, wx.GROW|wx.ALL, 10)
        szrMain.Add(szrDims, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrMain.Add(szrHtml, 2, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        #status bar
        #self.statusbar = self.CreateStatusBar()
        #attach main sizer to panel>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Fit() #needed, otherwise initial display problem with 
        #  status bar
