#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import pprint
import os
import random
import sys
import wx
import wx.gizmos

import my_globals
import lib
import config_dlg
import demotables
import dimtables
import dimtree
import getdata
import full_html
import output
import projects
import rawtables

OUTPUT_MODULES = ["my_globals", "dimtables", "rawtables", "output", "getdata"]
WAITING_MSG = _("<p>Waiting for enough settings.</p>")


class DlgMakeTable(wx.Dialog, config_dlg.ConfigDlg, dimtree.DimTree):
    """
    ConfigDlg - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    """
    
    def __init__(self, dbe, con_dets, default_dbs=None, 
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None):
        debug = False
        wx.Dialog.__init__(self, parent=None, id=-1, 
                           title=_("Make Report Table"), 
                           pos=(200, 0),
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_var_dets = fil_var_dets
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script        
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(fil_var_dets)
        self.col_no_vars_item = None # needed if no variable in columns
        # set up panel for frame
        self.panel = wx.Panel(self)
        config_dlg.add_icon(frame=self)
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel) # mixin
        # title details
        lblTitles = wx.StaticText(self.panel, -1, _("Title:"))
        lblTitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                     style=wx.TE_MULTILINE)
        self.txtTitles.Bind(wx.EVT_TEXT, self.OnTitleChange)
        lblSubtitles = wx.StaticText(self.panel, -1, _("Subtitle:"))
        lblSubtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txtSubtitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                        style=wx.TE_MULTILINE)
        self.txtSubtitles.Bind(wx.EVT_TEXT, self.OnSubtitleChange)
        #radio
        self.radTabType = wx.RadioBox(self.panel, -1, _("Table Type"), 
                         choices=(_("Column measures e.g. FREQ, row % etc"),
                                  _("Summarise rows e.g. MEAN, MEDIAN etc"),
                                  _("Display table data as is")),
                         style=wx.RA_SPECIFY_ROWS)
        self.radTabType.Bind(wx.EVT_RADIOBOX, self.OnTabTypeChange)
        self.tab_type = self.radTabType.GetSelection()
        # option checkboxs
        self.chkTotalsRow = wx.CheckBox(self.panel, -1, _("Totals Row?"))
        self.chkTotalsRow.Bind(wx.EVT_CHECKBOX, self.OnChkTotalsRow)
        self.chkFirstAsLabel = wx.CheckBox(self.panel, -1, 
                                           _("First col as label?"))
        self.chkFirstAsLabel.Bind(wx.EVT_CHECKBOX, self.OnChkFirstAsLabel)
        self.EnableOpts(enable=False)
        #text labels
        lblRows = wx.StaticText(self.panel, -1, _("Rows:"))
        lblRows.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        lblCols = wx.StaticText(self.panel, -1, _("Columns:"))
        lblCols.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        #buttons
        #rows
        self.btnRowAdd = wx.Button(self.panel, -1, _("Add"))
        self.btnRowAdd.Bind(wx.EVT_BUTTON, self.OnRowAdd)
        self.btnRowAddUnder = wx.Button(self.panel, -1, _("Add Under"))
        self.btnRowAddUnder.Bind(wx.EVT_BUTTON, self.OnRowAddUnder)
        self.btnRowDel = wx.Button(self.panel, -1, _("Delete"))
        self.btnRowDel.Bind(wx.EVT_BUTTON, self.OnRowDelete)
        self.btnRowConf = wx.Button(self.panel, -1, _("Config"))
        self.btnRowConf.Bind(wx.EVT_BUTTON, self.OnRowConfig)
        #cols
        self.btnColAdd = wx.Button(self.panel, -1, _("Add"))
        self.btnColAdd.Bind(wx.EVT_BUTTON, self.OnColAdd)
        self.btnColAddUnder = wx.Button(self.panel, -1, _("Add Under"))
        self.btnColAddUnder.Bind(wx.EVT_BUTTON, self.OnColAddUnder)
        self.btnColDel = wx.Button(self.panel, -1, _("Delete"))
        self.btnColDel.Bind(wx.EVT_BUTTON, self.OnColDelete)
        self.btnColConf = wx.Button(self.panel, -1, _("Config"))
        self.btnColConf.Bind(wx.EVT_BUTTON, self.OnColConfig)
        #trees
        self.rowtree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnRowItemActivated)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, 
                          self.OnRowItemRightClick)
        self.rowtree.SetToolTipString(_("Right click variables to view/edit "
                                        "details"))
        self.rowRoot = self.setupDimTree(self.rowtree)
        self.coltree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.coltree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnColItemActivated)
        self.coltree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, 
                          self.OnColItemRightClick)
        self.coltree.SetToolTipString(_("Right click variables to view/edit "
                                        "details"))
        self.colRoot = self.setupDimTree(self.coltree)
        #setup demo table type
        if debug: print(self.fil_css)
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
        self.html = full_html.FullHTML(self.panel, size=(200, 150))
        self.html.show_html(WAITING_MSG)
        lbldemo_tbls = wx.StaticText(self.panel, -1, _("Output Table:"))
        lbldemo_tbls.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        # main section SIZERS **************************************************
        szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrData, self.szrConfigBottom, self.szrConfigTop = \
            self.get_gen_config_szrs(self.panel) # mixin
        szrMid = wx.BoxSizer(wx.HORIZONTAL)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
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
        #2 BOTTOM assemble
        #3 BOTTOM LEFT        
        #3 HTML
        szrHtml = wx.BoxSizer(wx.VERTICAL)
        szrHtml.Add(lbldemo_tbls, 0)
        szrHtml.Add(self.html, 1, wx.GROW)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        szrBottomLeft.Add(szrHtml, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrBottomLeft.Add(self.szrConfigBottom, 0, 
                          wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        #3 BUTTONS
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrOutputButtons, 0, wx.GROW|wx.BOTTOM|wx.RIGHT, 10)
        #1 MAIN assemble
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrMid, 0, wx.GROW|wx.ALL, 10)
        szrMain.Add(szrTrees, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrMain.Add(szrBottom, 2, wx.GROW)
        # attach main sizer to panel
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)

    def UpdateCss(self):
        "Update css, including for demo table"
        config_dlg.ConfigDlg.UpdateCss(self)
        self.demo_tab.fil_css = self.fil_css
        self.update_demo_display()
    
    # database/ tables (and views)
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        Clear dim areas.
        """
        config_dlg.ConfigDlg.OnDatabaseSel(self, event)
        self.enable_col_btns()
        self.ClearDims()
        
    def OnTableSel(self, event):
        """
        Reset table, fields, has_unique, and idxs.
        Clear dim areas.
        """       
        config_dlg.ConfigDlg.OnTableSel(self, event)
        self.enable_col_btns()
        self.ClearDims()
    
    def update_var_dets(self):
        "Update all labels, including those already displayed"
        config_dlg.ConfigDlg.update_var_dets(self)
        # update dim trees
        rowdescendants = lib.get_tree_ctrl_descendants(self.rowtree, 
                                                       self.rowRoot)
        self.RefreshDescendants(self.rowtree, rowdescendants)
        coldescendants = lib.get_tree_ctrl_descendants(self.coltree, 
                                                       self.colRoot)
        self.RefreshDescendants(self.coltree, coldescendants)
        # update demo area
        self.demo_tab.var_labels = self.var_labels
        self.demo_tab.val_dics = self.val_dics
        self.update_demo_display()    
    
    def refresh_vars(self):
        self.update_var_dets()
        
           
    def RefreshDescendants(self, tree, descendants):
        ""
        for descendant in descendants:
            var_name, unused = \
                lib.extract_var_choice_dets(tree.GetItemText(descendant))
            fresh_label = lib.get_choice_item(self.var_labels, var_name)
            tree.SetItemText(descendant, fresh_label)

    # table type
    def OnTabTypeChange(self, event):
        "Respond to change of table type"
        self.UpdateByTabType()
    
    def UpdateByTabType(self):
        self.tab_type = self.radTabType.GetSelection() #for convenience
        #delete all row and col vars
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        #link to appropriate demo table type
        titles = [u"\"%s\"" % x for x \
                  in self.txtTitles.GetValue().split(u"\n")]
        Subtitles = [u"\"%s\"" % x for x \
                     in self.txtSubtitles.GetValue().split(u"\n")]
        if self.tab_type == my_globals.COL_MEASURES:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.EnableOpts(enable=False)
            self.EnableRowSel(enable=True)
            self.enable_col_btns()
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
        elif self.tab_type == my_globals.ROW_SUMM:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.EnableOpts(enable=False)
            self.EnableRowSel(enable=True)
            self.enable_col_btns()
            self.demo_tab = demotables.SummDemoTable(txtTitles=self.txtTitles, 
                             txtSubtitles=self.txtSubtitles,
                             colRoot=self.colRoot,                                  
                             rowRoot=self.rowRoot, 
                             rowtree=self.rowtree, 
                             coltree=self.coltree, 
                             col_no_vars_item=self.col_no_vars_item, 
                             var_labels=self.var_labels, 
                             val_dics=self.val_dics,
                             fil_css=self.fil_css)
        elif self.tab_type == my_globals.RAW_DISPLAY:
            self.EnableOpts(enable=True)
            self.EnableRowSel(enable=False)
            self.btnColConf.Disable()
            self.btnColAddUnder.Disable()
            self.demo_tab = demotables.DemoRawTable(txtTitles=self.txtTitles, 
                     txtSubtitles=self.txtSubtitles,                                 
                     colRoot=self.colRoot, 
                     coltree=self.coltree, 
                     flds=self.flds,
                     var_labels=self.var_labels,
                     val_dics=self.val_dics,
                     fil_css=self.fil_css,
                     chkTotalsRow=self.chkTotalsRow,
                     chkFirstAsLabel=self.chkFirstAsLabel)
        #in case they were disabled and then we changed tab type
        self.update_demo_display()
        
    def EnableOpts(self, enable=True):
        "Enable (or disable) options"
        self.chkTotalsRow.Enable(enable)
        self.chkFirstAsLabel.Enable(enable)
        
    def OnChkTotalsRow(self, event):
        "Update display as total rows checkbox changes"
        self.update_demo_display()

    def OnChkFirstAsLabel(self, event):
        "Update display as first column as label checkbox changes"
        self.update_demo_display()
                
    # titles/subtitles
    def OnTitleChange(self, event):
        """
        Update display as titles change
        Need to SetFocus back to titles because in Windows, IEHTMLWindow steals
            the focus if you have previously clicked it at some point.
        """
        self.update_demo_display(titles_only=True)
        self.txtTitles.SetFocus()

    def OnSubtitleChange(self, event):
        """
        Update display as subtitles change.  See OnTitleChange comment.
        """
        self.update_demo_display(titles_only=True)
        self.txtSubtitles.SetFocus()
        
    # run 
    def too_long(self):
        # check not a massive report table
        too_long = False
        if self.tab_type == my_globals.RAW_DISPLAY:
            # count records in table
            quoter = getdata.get_obj_quoter_func(self.dbe)
            unused, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
            where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
            s = u"SELECT COUNT(*) FROM %s %s" % (quoter(self.tbl), 
                                                 where_tbl_filt)
            self.cur.execute(s)
            n_rows = self.cur.fetchone()[0]
            if n_rows > 500:
                if wx.MessageBox(_("This report has %s rows. "
                                   "Do you wish to run it?") % n_rows, 
                                   caption=_("LONG REPORT"), 
                                   style=wx.YES_NO) == wx.NO:
                    too_long = True
        return too_long
    
    def update_local_display(self, strContent):
        self.html.show_html(strContent)
    
    def OnButtonRun(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH) and into report file, and finally, 
            display html output.
        """
        debug = False
        run_ok, missing_dim, has_rows, has_cols = self.table_config_ok()
        if run_ok:
            if self.too_long():
                return
            wx.BeginBusyCursor()
            add_to_report = self.chkAddToReport.IsChecked()
            if debug: print(self.fil_css)
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.get_script(has_rows, has_cols, css_idx)
            str_content = output.run_report(OUTPUT_MODULES, add_to_report, 
                    self.fil_report, css_fils, script, self.con_dets, self.dbe, 
                    self.db, self.tbl, self.default_dbs, self.default_tbls)
            wx.EndBusyCursor()
            self.update_local_display(str_content)
            self.str_content = str_content
            self.btnExpand.Enable(True)
        else:
            wx.MessageBox(_("Missing %s data") % missing_dim)
    
    # export script
    def OnButtonExport(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        export_ok, missing_dim, has_rows, has_cols = self.table_config_ok()
        if export_ok:
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.get_script(has_rows, has_cols, css_idx)
            output.export_script(script, self.fil_script, 
                                 self.fil_report, css_fils, self.con_dets, 
                                 self.dbe, self.db, self.tbl, self.default_dbs, 
                                 self.default_tbls)
        else:
            wx.MessageBox(_("Missing %s data") % missing_dim) 
    
    def get_titles(self):
        """
        Get titles list and subtitles list from GUI.
        """
        titles = [u"%s" % x for x \
                  in self.txtTitles.GetValue().split(u"\n")]
        subtitles = [u"%s" % x for x \
                     in self.txtSubtitles.GetValue().split(u"\n")]
        return titles, subtitles
    
    def get_script(self, has_rows, has_cols, css_idx):
        """
        Build script from inputs.
        Unlike the stats test output, no need to link to images etc, so no need
            to know what this report will be called (so we can know where any
            images are to link to).
        """
        script_lst = []
        # set up variables required for passing into main table instantiation
        if self.tab_type in [my_globals.COL_MEASURES, my_globals.ROW_SUMM]:
            script_lst.append(u"tree_rows = dimtables.DimNodeTree()")
            for child in lib.get_tree_ctrl_children(tree=self.rowtree, 
                                                    parent=self.rowRoot):
                child_fld_name, unused = lib.extract_var_choice_dets(
                                            self.rowtree.GetItemText(child))
                self.addToParent(script_lst=script_lst, tree=self.rowtree, 
                             parent=self.rowtree, 
                             parent_node_label=u"tree_rows",
                             child=child, child_fld_name=child_fld_name)
            script_lst.append(u"tree_cols = dimtables.DimNodeTree()")
            if has_cols:
                for child in lib.get_tree_ctrl_children(tree=self.coltree, 
                                                        parent=self.colRoot):
                    child_fld_name, unused = lib.extract_var_choice_dets(
                                            self.coltree.GetItemText(child))
                    self.addToParent(script_lst=script_lst, tree=self.coltree, 
                                 parent=self.coltree, 
                                 parent_node_label=u"tree_cols",
                                 child=child, child_fld_name=child_fld_name)
        elif self.tab_type == my_globals.RAW_DISPLAY:
            col_names, col_labels = lib.get_col_dets(self.coltree, self.colRoot, 
                                                     self.var_labels)
            script_lst.append(u"col_names = " + pprint.pformat(col_names))
            script_lst.append(u"col_labels = " + pprint.pformat(col_labels))
            script_lst.append(u"flds = " + pprint.pformat(self.flds))
            script_lst.append(u"var_labels = " + \
                              pprint.pformat(self.var_labels))
            script_lst.append(u"val_dics = " + pprint.pformat(self.val_dics))
        # process title dets
        titles, subtitles = self.get_titles()
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        # NB the following text is all going to be run
        if self.tab_type == my_globals.COL_MEASURES:
            script_lst.append(u"tab_test = dimtables.GenTable(" + \
                u"titles=%s," % unicode(titles) + \
                u"\n    subtitles=%s," % unicode(subtitles) + \
                u"\n    dbe=\"%s\", " % self.dbe + \
                u"tbl=\"%s\", " % self.tbl + \
                u"tbl_filt=tbl_filt," + \
                u"\n    cur=cur, flds=flds, tree_rows=tree_rows, " + \
                u"tree_cols=tree_cols)")
        elif self.tab_type == my_globals.ROW_SUMM:
            script_lst.append(u"tab_test = dimtables.SummTable(" + \
                u"titles=%s," % unicode(titles) + \
                u"\n    subtitles=%s," % unicode(subtitles) + \
                u"\n    dbe=\"%s\", " % self.dbe + \
                u"tbl=\"%s\", " % self.tbl + \
                u"tbl_filt=tbl_filt," + \
                u"\n    cur=cur, flds=flds, tree_rows=tree_rows, " + \
                u"tree_cols=tree_cols)")
        elif self.tab_type == my_globals.RAW_DISPLAY:
            tot_rows = u"True" if self.chkTotalsRow.IsChecked() else u"False"
            first_label = u"True" if self.chkFirstAsLabel.IsChecked() \
                else u"False"
            script_lst.append(u"tab_test = rawtables.RawTable(" + \
                u"titles=%s, " % unicode(titles) + \
                u"\n    subtitles=%s, " % unicode(subtitles) + \
                u"\n    dbe=\"%s\", " % self.dbe + \
                u"col_names=col_names, col_labels=col_labels, flds=flds," + \
                u"\n    var_labels=var_labels, val_dics=val_dics, " + \
                u"tbl=\"%s\"," % self.tbl + \
                u"\n    tbl_filt=tbl_filt, cur=cur, add_total_row=%s, " % \
                    tot_rows + \
                u"\n    first_col_as_label=%s)" % first_label)
        if self.tab_type in [my_globals.COL_MEASURES, my_globals.ROW_SUMM]:
            script_lst.append(u"tab_test.prepTable(%s)" % css_idx)
            script_lst.append(u"max_cells = 5000")
            script_lst.append(u"if tab_test.getCellNOk(max_cells=max_cells):")
            script_lst.append(u"    " + \
                        u"fil.write(tab_test.getHTML(%s, " % css_idx + \
                        u"page_break_after=False))")
            script_lst.append(u"else:")
            script_lst.append(u"    " + \
                              u"fil.write(\"Table not made.  Number \" + \\" + \
                              u"\n        \"of cells exceeded limit \" + \\" + \
                              u"\n        \"of %s\" % max_cells)")
        else:
            script_lst.append(u"fil.write(tab_test.getHTML(%s, " % css_idx + \
                              u"page_break_after=False))")
        return u"\n".join(script_lst)

    def addToParent(self, script_lst, tree, parent, parent_node_label, 
                    child, child_fld_name):
        """
        Add script code for adding child nodes to parent nodes.
        tree - TreeListCtrl tree
        parent, child - TreeListCtrl items
        parent_node_label - for parent_node_label.addChild(...)
        child_fld_name - used to get variable label, and value labels
            from relevant dics; plus as the field name
        """
        # add child to parent
        if child == self.col_no_vars_item:
            fld_arg = u""
        else:
            fld_arg = u"fld=\"%s\", " % child_fld_name
        #print(self.var_labels) #debug
        #print(self.val_dics) #debug
        var_label = self.var_labels.get(child_fld_name, 
                                        child_fld_name.title())
        labels_dic = self.val_dics.get(child_fld_name, {})
        child_node_label = u"node_" + u"_".join(child_fld_name.split(u" "))
        item_conf = tree.GetItemPyData(child)
        measures_lst = item_conf.measures_lst
        measures = u", ".join([(u"my_globals." + \
                               my_globals.script_export_measures_dic[x]) for \
                               x in measures_lst])
        if measures:
            measures_arg = u", \n    measures=[%s]" % measures
        else:
            measures_arg = u""
        if item_conf.has_tot:
            tot_arg = u", \n    has_tot=True"
        else:
            tot_arg = u""
        sort_order_arg = u", \n    sort_order=\"%s\"" % \
            item_conf.sort_order
        numeric_arg = u", \n    bolnumeric=%s" % item_conf.bolnumeric
        script_lst.append(child_node_label + \
                          u" = dimtables.DimNode(" + fld_arg + \
                          u"\n    label=\"" + unicode(var_label) + \
                          u"\", \n    labels=" + unicode(labels_dic) + \
                          measures_arg + tot_arg + sort_order_arg + \
                          numeric_arg + ")")
        script_lst.append(u"%s.addChild(%s)" % (parent_node_label, 
                                                child_node_label))
        # send child through for each grandchild
        for grandchild in lib.get_tree_ctrl_children(tree=tree, parent=child):
            grandchild_fld_name, unused = lib.extract_var_choice_dets(
                                                tree.GetItemText(grandchild))
            self.addToParent(script_lst=script_lst, tree=tree, 
                             parent=child, 
                             parent_node_label=child_node_label,
                             child=grandchild, 
                             child_fld_name=grandchild_fld_name)
    
    def OnButtonHelp(self, event):
        """
        Export script if enough data to create table.
        """
        wx.MessageBox("Not available yet in this version")
        
    # clear button
    def ClearDims(self):
        "Clear dim trees"
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.update_demo_display()

    #def OnClearEnterWindow(self, event):
    #    "Hover over CLEAR button"
    #    self.statusbar.SetStatusText("Clear settings")

    def OnButtonClear(self, event):
        "Clear all settings"
        self.txtTitles.SetValue("")        
        self.txtSubtitles.SetValue("")
        self.radTabType.SetSelection(my_globals.COL_MEASURES)
        self.tab_type = my_globals.COL_MEASURES
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.UpdateByTabType()
        self.update_demo_display()

    def OnClose(self, event):
        "Close app"
        try:
            self.con.close()
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = open(fil_script, "a")
                output.AddClosingScriptCode(f)
                f.close()
        except Exception:
            pass
        finally:
            self.Destroy()
            event.Skip()
    
    def replace_titles_only(self, orig):
        """
        Have original html
            <p class='tbltitle0'></p> # or other n
            <p class='tblsubtitle0'></p> # ditto
        Have list of titles and subtitles (both or either could be empty).
        Use specific tags to slice it up and reassemble it.  
        Will always have TBL_TITLE_START and TBL_TITLE_END.
        Will either have TBL_SUBTITLE_START and TBL_SUBTITLE_END
            OR TBL_SUBTITLE_LEVEL_START and TBL_SUBTITLE_LEVEL_END.  If the 
            latter, need to build entire subtitle html into gap, not just the 
            subtitle.  Use the level to do it in a way which matches what was 
            there.
        """
        debug = False
        titles, subtitles = self.get_titles()
        titles_inner_html = ""
        titles_inner_html = lib.get_titles_inner_html(titles_inner_html, titles)
        subtitles_inner_html = ""
        subtitles_inner_html = \
                lib.get_subtitles_inner_html(subtitles_inner_html, subtitles)
        pre_title_idx = orig.index(my_globals.TBL_TITLE_START) + \
            len(my_globals.TBL_TITLE_START)
        pre_title = orig[: pre_title_idx]
        post_title = orig[orig.index(my_globals.TBL_TITLE_END):]
        # a placeholder only or a proper subtitle?
        try:
            orig.index(my_globals.TBL_SUBTITLE_LEVEL_START)
            has_placeholder = True
        except ValueError:
            has_placeholder = False
        if has_placeholder:
            # get level and build own subtitle
            level_start_idx = orig.index(my_globals.TBL_SUBTITLE_LEVEL_START) \
                + len(my_globals.TBL_SUBTITLE_LEVEL_START)
            level_end_idx = orig.index(my_globals.TBL_SUBTITLE_LEVEL_END)
            css_idx = orig[level_start_idx, level_end_idx]
            if debug: print("css_idx: %s" % css_idx)
            CSS_SUBTITLE = my_globals.CSS_SUFFIX_TEMPLATE % \
                (my_globals.CSS_SUBTITLE, css_idx)
            subtitles_html = u"\n<p class='%s'>%s" % (CSS_SUBTITLE, 
                                                my_globals.TBL_SUBTITLE_START)
            subtitles_html += subtitles_inner_html
            subtitles_html += u"%s</p>" % my_globals.TBL_SUBTITLE_END
            between_title_and_sub = ""
            post_subtitle = orig[orig.index(my_globals.TBL_SUBTITLE_LEVEL_END):]
        else: # proper subtitle
            sub_start_idx = post_title.index(my_globals.TBL_SUBTITLE_START) + \
                len(my_globals.TBL_SUBTITLE_START)
            between_title_and_sub = post_title[: sub_start_idx]
            subtitles_html = subtitles_inner_html
            post_sub_start_idx = post_title.index(my_globals.TBL_SUBTITLE_END)
            post_subtitle = post_title[post_sub_start_idx :]
        # put it all back together
        demo_tbl_html = pre_title + titles_inner_html + between_title_and_sub \
            + subtitles_html + post_subtitle
        if debug: print(("pre_title: %s\n\ntitles_inner_html: %s\n\n"
                     "between_title_and_sub: %s\n\nsubtitles_html: %s\n\n"
                     "post_subtitle: %s") % (pre_title, titles_inner_html,
                     between_title_and_sub, subtitles_html, post_subtitle))
        return demo_tbl_html
    
    # demo table display
    def update_demo_display(self, titles_only=False):
        """
        Update demo table display with random data.
        Always use one css only (the current one).
        If titles_only, and the last demo was a table, change the title and 
            subtitle text only.
        Easiest to do with crude slicing and inserting.  Best to leave the 
            table-making processes code alone.
        """
        debug = False
        self.btnExpand.Enable(False)
        if titles_only:
            if self.prev_demo:
                # replace titles and subtitles
                demo_tbl_html = self.replace_titles_only(self.prev_demo)
                self.prev_demo = demo_tbl_html
        else:
            demo_html = self.demo_tab.get_demo_html_if_ok(css_idx=0)
            if demo_html == "":
                demo_tbl_html = WAITING_MSG
                self.prev_demo = None
            else:
                demo_tbl_html = ("<h1>%s</h1>\n" % 
                     _("Example data - click 'Run' for actual results") + demo_html)
                self.prev_demo = demo_tbl_html
        if debug: print(u"\n" + demo_tbl_html + "\n")
        self.html.show_html(demo_tbl_html)

    def table_config_ok(self):
        """
        Is the table configuration sufficient to export as script or HTML?
        Summary only requires rows (can have both)
        Raw only requires cols (and cannot have rows)
        And gen requires both        
        """
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              parent=self.rowRoot)
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              parent=self.colRoot)
        export_ok = False
        missing_dim = None
        if self.tab_type == my_globals.ROW_SUMM:
            if has_rows:
                export_ok = True
            else:
                missing_dim = _("row")
        elif self.tab_type == my_globals.RAW_DISPLAY:
            if has_cols:
                export_ok = True
            else:
                missing_dim = _("column")
        elif self.tab_type == my_globals.COL_MEASURES:
            if has_rows and has_cols:
                export_ok = True
            else:
                missing_dim = _("row and column")
        return (export_ok, missing_dim, has_rows, has_cols)