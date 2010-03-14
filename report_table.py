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

def replace_titles_subtitles(orig, titles, subtitles):
    """
    Have original html
        <span class='tbltitle0'><tag>Title<tag></span> # or other n
        <span class='tblsubtitle0'><tag>Subtitle<tag></span> # or other n
    Have list of titles and subtitles (both or either could be empty).
    Use specific tags to slice it up and reassemble it. Easiest to do with crude 
        slicing and inserting.  Best to leave the table-making processes code 
        alone. 
    Will have TBL_TITLE_START and TBL_TITLE_END. We only change what is between.
    Subtitles follows the same approach.
    NB if either or both of the titles and subtitles are empty, the row should 
        be of minimal height (using span instead of block display).
    pre_title = everything before the actual content of the title
    titles_html = just the inner html (words with lines sep by <br>)
    post_title = everything after the actual content of the title
    between_title_and_sub = everything between the title content and the 
        subtitle content.
    post_subtitle = everything after the subtitle content e.g. 2010 data
    """
    debug = False
    if debug: print("orig: %s\n\ntitles: %s\n\nsubtitles: %s\n\n" % (orig, 
                                                            titles, subtitles))
    titles_inner_html = u""
    titles_inner_html = lib.get_titles_inner_html(titles_inner_html, titles)
    subtitles_inner_html = u""
    subtitles_inner_html = \
            lib.get_subtitles_inner_html(subtitles_inner_html, subtitles)
    # need break between titles and subtitles if both present
    if titles_inner_html and subtitles_inner_html:
        subtitles_inner_html = u"<br>" + subtitles_inner_html
    title_start_idx = orig.index(my_globals.TBL_TITLE_START) + \
        len(my_globals.TBL_TITLE_START)
    pre_title = orig[ : title_start_idx]
    title_end_idx = orig.index(my_globals.TBL_TITLE_END)
    post_title = orig[title_end_idx :] # everything after title inc subtitles
    # use shorter post_title instead or orig from here on
    subtitle_start_idx = post_title.index(my_globals.TBL_SUBTITLE_START) + \
        len(my_globals.TBL_SUBTITLE_START)
    between_title_and_sub = post_title[ : subtitle_start_idx]
    post_subtitle = post_title[post_title.index(my_globals.TBL_SUBTITLE_END):]
    # put it all back together
    demo_tbl_html = pre_title + titles_inner_html + between_title_and_sub \
        + subtitles_inner_html + post_subtitle
    if debug: 
        print(("pre_title: %s\n\ntitles_inner_html: %s\n\n"
               "between_title_and_sub: %s\n\nsubtitles_inner_html: %s\n\n"
               "post_subtitle: %s") % (pre_title, titles_inner_html,
               between_title_and_sub, subtitles_inner_html, post_subtitle))
        print("\n\n" + "*"*50 + "\n\n")
    return demo_tbl_html  
    
class DlgMakeTable(wx.Dialog, config_dlg.ConfigDlg, dimtree.DimTree):
    """
    ConfigDlg - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    self.col_no_vars_item -- the column item when there are no column variables,
        only columns related to the row variables e.g. total, row and col %s.
    """
    
    def __init__(self, dbe, con_dets, default_dbs=None, 
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None):
        debug = False
        wx.Dialog.__init__(self, parent=None, id=-1, 
               title=_("Make Report Table"), pos=(200, 0),
               style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|\
               wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_var_dets = fil_var_dets
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script
        self.url_load = True # btnExpand    
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(fil_var_dets)
        self.col_no_vars_item = None # needed if no variable in columns
        # set up panel for frame
        self.panel = wx.Panel(self)
        config_dlg.add_icon(frame=self)
        # sizers
        szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrData, self.szrConfigBottom, self.szrConfigTop = \
            self.get_gen_config_szrs(self.panel) # mixin
        szrMid = wx.BoxSizer(wx.VERTICAL)
        szrTabType = wx.BoxSizer(wx.HORIZONTAL)
        szrOpts = wx.BoxSizer(wx.VERTICAL)
        szrTitles = wx.BoxSizer(wx.HORIZONTAL)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrTrees = wx.BoxSizer(wx.HORIZONTAL)
        szrRows = wx.BoxSizer(wx.VERTICAL)
        szrCols = wx.BoxSizer(wx.VERTICAL)
        szrColButtons = wx.BoxSizer(wx.HORIZONTAL)
        szrHtml = wx.BoxSizer(wx.VERTICAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel) # mixin
        # title details
        lblTitles = wx.StaticText(self.panel, -1, _("Title:"))
        lblTitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtTitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                     style=wx.TE_MULTILINE)
        self.txtTitles.Bind(wx.EVT_TEXT, self.on_title_change)
        lblSubtitles = wx.StaticText(self.panel, -1, _("Subtitle:"))
        lblSubtitles.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                          wx.BOLD))
        self.txtSubtitles = wx.TextCtrl(self.panel, -1, size=(50,40), 
                                        style=wx.TE_MULTILINE)
        self.txtSubtitles.Bind(wx.EVT_TEXT, self.on_subtitle_change)
        # table type
        self.radTabType = wx.RadioBox(self.panel, -1, _("Table Type"), 
                         choices=(_("Frequencies"),
                                  _("Crosstabs"),
                                  _("Row summaries (mean etc)"),
                                  _("Data List")),
                         style=wx.RA_SPECIFY_COLS)
        self.radTabType.Bind(wx.EVT_RADIOBOX, self.on_tab_type_change)
        self.tab_type = self.radTabType.GetSelection()
        # option checkboxs
        self.chkTotalsRow = wx.CheckBox(self.panel, -1, _("Totals Row?"))
        self.chkTotalsRow.Bind(wx.EVT_CHECKBOX, self.on_chk_totals_row)
        self.chkFirstAsLabel = wx.CheckBox(self.panel, -1, 
                                           _("First col as label?"))
        self.chkFirstAsLabel.Bind(wx.EVT_CHECKBOX, self.on_chk_first_as_label)
        self.enable_opts(enable=False)
        #text labels
        lblRows = wx.StaticText(self.panel, -1, _("Rows:"))
        lblRows.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        lblCols = wx.StaticText(self.panel, -1, _("Columns:"))
        lblCols.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        #buttons
        #rows
        self.btnRowAdd = wx.Button(self.panel, -1, _("Add"))
        self.btnRowAdd.Bind(wx.EVT_BUTTON, self.on_row_add)
        self.btnRowAddUnder = wx.Button(self.panel, -1, _("Add Under"))
        self.btnRowAddUnder.Bind(wx.EVT_BUTTON, self.on_row_add_under)
        self.btnRowDel = wx.Button(self.panel, -1, _("Delete"))
        self.btnRowDel.Bind(wx.EVT_BUTTON, self.on_row_delete)
        self.btnRowConf = wx.Button(self.panel, -1, _("Config"))
        self.btnRowConf.Bind(wx.EVT_BUTTON, self.on_row_config)
        #cols
        self.btnColAdd = wx.Button(self.panel, -1, _("Add"))
        self.btnColAdd.Bind(wx.EVT_BUTTON, self.on_col_add)
        self.btnColAddUnder = wx.Button(self.panel, -1, _("Add Under"))
        self.btnColAddUnder.Bind(wx.EVT_BUTTON, self.on_col_add_under)
        self.btnColDel = wx.Button(self.panel, -1, _("Delete"))
        self.btnColDel.Bind(wx.EVT_BUTTON, self.on_col_delete)
        self.btnColConf = wx.Button(self.panel, -1, _("Config"))
        self.btnColConf.Bind(wx.EVT_BUTTON, self.on_col_config)
        #trees
        self.rowtree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, 
                          self.on_row_item_activated)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, 
                          self.on_row_item_right_click)
        self.rowtree.SetToolTipString(_("Right click variables to view/edit "
                                        "details"))
        self.rowRoot = self.setup_dim_tree(self.rowtree)
        self.coltree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.coltree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, 
                          self.on_col_item_activated)
        self.coltree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, 
                          self.on_col_item_right_click)
        self.coltree.SetToolTipString(_("Right click variables to view/edit "
                                        "details"))
        self.colRoot = self.setup_dim_tree(self.coltree)
        # setup demo table type
        if debug: print(self.fil_css)
        self.prev_demo = None
        self.demo_tab = demotables.GenDemoTable(txtTitles=self.txtTitles, 
                                 txtSubtitles=self.txtSubtitles,
                                 colRoot=self.colRoot, rowRoot=self.rowRoot, 
                                 rowtree=self.rowtree, coltree=self.coltree, 
                                 col_no_vars_item=self.col_no_vars_item, 
                                 var_labels=self.var_labels, 
                                 val_dics=self.val_dics, fil_css=self.fil_css)
        # freqs tbl is default
        self.setup_col_btns()
        self.add_default_column_config() # must set up after coltree and demo 
        # tabs defined
        if my_globals.IN_WINDOWS:
            mid_height = 820
            height_drop = 20
        else:
            mid_height = 850
            height_drop = 50
        if my_globals.MAX_HEIGHT <= 620:
            myheight = 130
        elif my_globals.MAX_HEIGHT <= mid_height:
            myheight = ((my_globals.MAX_HEIGHT/1024.0)*350) - height_drop
        else:
            myheight = 350
        self.html = full_html.FullHTML(self.panel, size=(200, myheight))
        self.html.show_html(WAITING_MSG)
        lbldemo_tbls = wx.StaticText(self.panel, -1, _("Output Table:"))
        lbldemo_tbls.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        szrTabType.Add(self.radTabType, 0, wx.RIGHT, 10)
        szrTitles.Add(lblTitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtTitles, 1, wx.GROW|wx.RIGHT, 10)
        szrTitles.Add(lblSubtitles, 0, wx.RIGHT, 5)
        szrTitles.Add(self.txtSubtitles, 1, wx.GROW)
        szrOpts.Add(self.chkTotalsRow, 0)        
        szrOpts.Add(self.chkFirstAsLabel)
        szrTabType.Add(szrOpts, 0)
        szrMid.Add(szrTabType, 0, wx.BOTTOM|wx.TOP, 5)
        szrMid.Add(szrTitles, 1, wx.GROW|wx.TOP, 5)
        szrRows.Add(lblRows, 0)
        szrRowButtons = wx.BoxSizer(wx.HORIZONTAL)
        szrRowButtons.Add(self.btnRowAdd, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowAddUnder, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowDel, 0, wx.RIGHT, 2)
        szrRowButtons.Add(self.btnRowConf)
        szrRows.Add(szrRowButtons, 0)
        szrRows.Add(self.rowtree, 1, wx.GROW)
        szrCols.Add(lblCols, 0)
        szrColButtons.Add(self.btnColAdd, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColAddUnder, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColDel, 0, wx.RIGHT, 2)
        szrColButtons.Add(self.btnColConf)
        szrCols.Add(szrColButtons)
        szrCols.Add(self.coltree, 1, wx.GROW)
        szrTrees.Add(szrRows, 1, wx.GROW|wx.RIGHT, 2)
        szrTrees.Add(szrCols, 1, wx.GROW|wx.LEFT, 2)
        szrHtml.Add(lbldemo_tbls, 0)
        szrHtml.Add(self.html, 1, wx.GROW)
        szrBottomLeft.Add(szrHtml, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrBottomLeft.Add(self.szrConfigBottom, 0, wx.GROW|wx.LEFT|wx.RIGHT|\
                          wx.BOTTOM, 10)
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrOutputButtons, 0, wx.GROW|wx.BOTTOM|wx.RIGHT, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrMid, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrTrees, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrMain.Add(szrBottom, 2, wx.GROW)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()

    def update_css(self):
        "Update css, including for demo table"
        config_dlg.ConfigDlg.update_css(self)
        self.demo_tab.fil_css = self.fil_css
        self.update_demo_display()
    
    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        Clear dim areas.
        """
        config_dlg.ConfigDlg.on_database_sel(self, event)
        self.data_changed()
        
    def on_table_sel(self, event):
        """
        Reset table, fields, has_unique, and idxs.
        Clear dim areas.
        """       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        self.data_changed()
    
    def data_changed(self):
        """
        Things to do after the data source has changed.
        """
        self.setup_col_btns()
        if self.tab_type == my_globals.RAW_DISPLAY:
            self.demo_tab.update_flds(self.flds)
        self.clear_dims()
        
    def update_var_dets(self):
        "Update all labels, including those already displayed"
        config_dlg.ConfigDlg.update_var_dets(self)
        # update dim trees
        rowdescendants = lib.get_tree_ctrl_descendants(self.rowtree, 
                                                       self.rowRoot)
        self.refresh_descendants(self.rowtree, rowdescendants)
        coldescendants = lib.get_tree_ctrl_descendants(self.coltree, 
                                                       self.colRoot)
        self.refresh_descendants(self.coltree, coldescendants)
        # update demo area
        self.demo_tab.var_labels = self.var_labels
        self.demo_tab.val_dics = self.val_dics
        self.update_demo_display()    
    
    def refresh_vars(self):
        self.update_var_dets()
           
    def refresh_descendants(self, tree, descendants):
        for descendant in descendants:
            # descendant -- NB GUI tree items, not my Dim Node obj
            item_conf = tree.GetItemPyData(descendant)
            var_name = item_conf.var_name
            fresh_label = lib.get_choice_item(self.var_labels, var_name)
            tree.SetItemText(descendant, fresh_label)

    # table type
    def on_tab_type_change(self, event):
        "Respond to change of table type"
        self.update_by_tab_type()
    
    def update_by_tab_type(self):
        self.tab_type = self.radTabType.GetSelection() #for convenience
        # delete all row and col vars
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        # link to appropriate demo table type
        if self.tab_type == my_globals.FREQS_TBL:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.enable_opts(enable=False)
            self.enable_row_sel(enable=True)
            self.demo_tab = demotables.GenDemoTable(txtTitles=self.txtTitles, 
                                 txtSubtitles=self.txtSubtitles,
                                 colRoot=self.colRoot, rowRoot=self.rowRoot, 
                                 rowtree=self.rowtree, coltree=self.coltree, 
                                 col_no_vars_item=self.col_no_vars_item, 
                                 var_labels=self.var_labels, 
                                 val_dics=self.val_dics, fil_css=self.fil_css)
            self.add_default_column_config()
        if self.tab_type == my_globals.CROSSTAB:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.enable_opts(enable=False)
            self.enable_row_sel(enable=True)
            self.demo_tab = demotables.GenDemoTable(txtTitles=self.txtTitles, 
                                 txtSubtitles=self.txtSubtitles,
                                 colRoot=self.colRoot,  rowRoot=self.rowRoot, 
                                 rowtree=self.rowtree,  coltree=self.coltree, 
                                 col_no_vars_item=self.col_no_vars_item, 
                                 var_labels=self.var_labels, 
                                 val_dics=self.val_dics, fil_css=self.fil_css)
        elif self.tab_type == my_globals.ROW_SUMM:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.enable_opts(enable=False)
            self.enable_row_sel(enable=True)
            self.demo_tab = demotables.SummDemoTable(txtTitles=self.txtTitles, 
                                 txtSubtitles=self.txtSubtitles,
                                 colRoot=self.colRoot, rowRoot=self.rowRoot, 
                                 rowtree=self.rowtree, coltree=self.coltree, 
                                 col_no_vars_item=self.col_no_vars_item, 
                                 var_labels=self.var_labels, 
                                 val_dics=self.val_dics, fil_css=self.fil_css)
        elif self.tab_type == my_globals.RAW_DISPLAY:
            self.enable_opts(enable=True)
            self.enable_row_sel(enable=False)
            self.btnColConf.Disable()
            self.btnColAddUnder.Disable()
            self.demo_tab = demotables.DemoRawTable(txtTitles=self.txtTitles, 
                         txtSubtitles=self.txtSubtitles,                                 
                         colRoot=self.colRoot, coltree=self.coltree, 
                         flds=self.flds, # needs to be reset if table changes
                         var_labels=self.var_labels, val_dics=self.val_dics,
                         fil_css=self.fil_css, chkTotalsRow=self.chkTotalsRow,
                         chkFirstAsLabel=self.chkFirstAsLabel)
        #in case they were disabled and then we changed tab type
        self.setup_col_btns()
        self.update_demo_display()
        self.txtTitles.SetFocus()
        
    def enable_opts(self, enable=True):
        "Enable (or disable) options"
        self.chkTotalsRow.Enable(enable)
        self.chkFirstAsLabel.Enable(enable)
        
    def on_chk_totals_row(self, event):
        "Update display as total rows checkbox changes"
        self.update_demo_display()

    def on_chk_first_as_label(self, event):
        "Update display as first column as label checkbox changes"
        self.update_demo_display()
                
    # titles/subtitles
    def on_title_change(self, event):
        """
        Update display as titles change
        Need to SetFocus back to titles because in Windows, IEHTMLWindow steals
            the focus if you have previously clicked it at some point.
        """
        self.update_demo_display(titles_only=True)
        self.txtTitles.SetFocus()

    def on_subtitle_change(self, event):
        """
        Update display as subtitles change.  See on_title_change comment.
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
    
    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location (INT_REPORT_PATH) 
            and into report file, and finally, display html output.
        """
        debug = False
        run_ok, has_cols = self.table_config_ok()
        if run_ok:
            if self.too_long():
                return
            wx.BeginBusyCursor()
            add_to_report = self.chkAddToReport.IsChecked()
            if debug: print(self.fil_css)
            css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                    self.fil_css)
            script = self.get_script(has_cols, css_idx)
            bolran_report, str_content = output.run_report(OUTPUT_MODULES, 
                    add_to_report, self.fil_report, css_fils, script, 
                    self.con_dets, self.dbe, self.db, self.tbl, 
                    self.default_dbs, self.default_tbls)
            wx.EndBusyCursor()
            # test JS charting
            """f = open("/home/g/Desktop/testrob1.htm", "r")
            str_content = f.read()
            f.close()"""
            self.update_local_display(str_content)
            self.str_content = str_content
            self.btnExpand.Enable(bolran_report)
    
    # export script
    def on_btn_export(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        export_ok, has_cols = self.table_config_ok()
        if export_ok:
            css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                    self.fil_css)
            script = self.get_script(has_cols, css_idx)
            output.export_script(script, self.fil_script, self.fil_report, 
                                 css_fils, self.con_dets, self.dbe, self.db, 
                                 self.tbl, self.default_dbs, self.default_tbls)
    
    def get_titles(self):
        """
        Get titles list and subtitles list from GUI.
        """
        debug = False
        raw_titles = self.txtTitles.GetValue()
        if raw_titles:
            titles = [u"%s" % x for x in raw_titles.split(u"\n")]
        else:
            titles = []
        raw_subtitles = self.txtSubtitles.GetValue()
        if raw_subtitles:
            subtitles = [u"%s" % x for x in raw_subtitles.split(u"\n")]
        else:
            subtitles = []
        if debug: print("%s %s" % (titles, subtitles))
        return titles, subtitles
    
    def get_script(self, has_cols, css_idx):
        """
        Build script from inputs.
        Unlike the stats test output, no need to link to images etc, so no need
            to know what this report will be called (so we can know where any
            images are to link to).
        """
        self.g = self.get_next_node_name()
        script_lst = []
        # set up variables required for passing into main table instantiation
        if self.tab_type in [my_globals.FREQS_TBL, my_globals.CROSSTAB, 
                             my_globals.ROW_SUMM]:
            script_lst.append(u"# Rows" + 60*u"*")
            script_lst.append(u"tree_rows = dimtables.DimNodeTree()")
            for child in lib.get_tree_ctrl_children(tree=self.rowtree, 
                                                    parent=self.rowRoot):
                # child -- NB GUI tree items, not my Dim Node obj
                item_conf = self.rowtree.GetItemPyData(child)
                child_fld_name = item_conf.var_name
                self.add_to_parent(script_lst=script_lst, tree=self.rowtree, 
                            parent=self.rowtree, parent_node_label=u"tree_rows",
                            parent_name=u"row",
                            child=child, child_fld_name=child_fld_name)
            script_lst.append(u"# Columns" + 57*u"*")
            script_lst.append(u"tree_cols = dimtables.DimNodeTree()")
            if has_cols:
                for child in lib.get_tree_ctrl_children(tree=self.coltree, 
                                                        parent=self.colRoot):
                    item_conf = self.coltree.GetItemPyData(child)
                    child_fld_name = item_conf.var_name
                    self.add_to_parent(script_lst=script_lst, tree=self.coltree, 
                            parent=self.coltree, parent_node_label=u"tree_cols",
                            parent_name=u"column",
                            child=child, child_fld_name=child_fld_name)
            script_lst.append(u"# Misc" + 60*u"*")
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
        if self.tab_type in (my_globals.FREQS_TBL, my_globals.CROSSTAB):
            script_lst.append(u"tab_test = dimtables.GenTable(" + \
                u"titles=%s," % unicode(titles) + \
                u"\n    subtitles=%s," % unicode(subtitles) + \
                u"\n    dbe=u\"%s\", " % self.dbe + \
                u"tbl=u\"%s\", " % self.tbl + \
                u"tbl_filt=tbl_filt," + \
                u"\n    cur=cur, flds=flds, tree_rows=tree_rows, " + \
                u"tree_cols=tree_cols)")
        elif self.tab_type == my_globals.ROW_SUMM:
            script_lst.append(u"tab_test = dimtables.SummTable(" + \
                u"titles=%s," % unicode(titles) + \
                u"\n    subtitles=%s," % unicode(subtitles) + \
                u"\n    dbe=u\"%s\", " % self.dbe + \
                u"tbl=u\"%s\", " % self.tbl + \
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
                u"\n    dbe=u\"%s\", " % self.dbe + \
                u"col_names=col_names, col_labels=col_labels, flds=flds," + \
                u"\n    var_labels=var_labels, val_dics=val_dics, " + \
                u"tbl=u\"%s\"," % self.tbl + \
                u"\n    tbl_filt=tbl_filt, cur=cur, add_total_row=%s, " % \
                    tot_rows + \
                u"\n    first_col_as_label=%s)" % first_label)
        if self.tab_type in [my_globals.FREQS_TBL, my_globals.CROSSTAB, 
                             my_globals.ROW_SUMM]:
            script_lst.append(u"tab_test.prep_table(%s)" % css_idx)
            script_lst.append(u"max_cells = 5000")
            script_lst.append(u"if tab_test.get_cell_n_ok("
                              u"max_cells=max_cells):")
            script_lst.append(u"    "
                        u"fil.write(tab_test.get_html(%s, " % css_idx + \
                        u"page_break_after=False))")
            script_lst.append(u"else:")
            script_lst.append(u"    "
                  u"raise my_exceptions.ExcessReportTableCellsException("
                  u"max_cells)")
        else:
            script_lst.append(u"fil.write(tab_test.get_html(%s, " % css_idx + \
                              u"page_break_after=False))")
        return u"\n".join(script_lst)

    def get_next_node_name(self):
        i = 0
        while True:
            yield u"node_%s" % i # guaranteed collision free
            i += 1
 
    def add_to_parent(self, script_lst, tree, parent, parent_node_label, 
                      parent_name, child, child_fld_name):
        """
        Add script code for adding child nodes to parent nodes.
        tree -- TreeListCtrl tree
        parent, child -- TreeListCtrl items
        parent_node_label -- for parent_node_label.add_child(...)
        child_fld_name -- used to get variable label, and value labels
            from relevant dicts; plus as the field name
        """
        debug = False
        # add child to parent
        if child == self.col_no_vars_item:
            fld_arg = u""
            var_label = _("Frequency column")
        else:
            fld_arg = u"fld=u\"%s\", " % child_fld_name
            if debug: 
                print(self.var_labels)
                print(self.val_dics)
            var_label = self.var_labels.get(child_fld_name, 
                                            child_fld_name.title())
        labels_dic = self.val_dics.get(child_fld_name, {})
        child_node_label = self.g.next()
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
        sort_order_arg = u", \n    sort_order=u\"%s\"" % \
            item_conf.sort_order
        numeric_arg = u", \n    bolnumeric=%s" % item_conf.bolnumeric
        script_lst.append(u"# Defining %s (\"%s\")" % (child_node_label, 
                                                       child_fld_name))
        script_lst.append(child_node_label + \
                          u" = dimtables.DimNode(" + fld_arg + \
                          u"\n    label=u\"%s\"," % unicode(var_label) + \
                          u"\n    labels=" + unicode(labels_dic) + \
                          measures_arg + tot_arg + sort_order_arg + \
                          numeric_arg + u")")
        if parent_node_label in (u"tree_rows", u"tree_cols"):
            parent_name = u"rows" if parent_node_label == u"tree_rows" \
                else u"columns"          
            script_lst.append(u"# Adding \"%s\" to %s" % (child_fld_name, 
                                                          parent_name))
        else:
            script_lst.append(u"# Adding \"%s\" under \"%s\"" % (child_fld_name, 
                                                                 parent_name))
        script_lst.append(u"%s.add_child(%s)" % (parent_node_label, 
                                                 child_node_label))
        # send child through for each grandchild
        for grandchild in lib.get_tree_ctrl_children(tree=tree, parent=child):
            # grandchild -- NB GUI tree items, not my Dim Node obj
            item_conf = tree.GetItemPyData(grandchild)
            grandchild_fld_name = item_conf.var_name
            self.add_to_parent(script_lst=script_lst, tree=tree, parent=child,
                               parent_node_label=child_node_label, 
                               parent_name=child_fld_name, child=grandchild, 
                               child_fld_name=grandchild_fld_name)
    
    def on_btn_help(self, event):
        """
        Export script if enough data to create table.
        """
        wx.MessageBox("Not available yet in this version")
        
    # clear button
    def clear_dims(self):
        "Clear dim trees"
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.update_demo_display()

    def on_btn_clear(self, event):
        "Clear all settings"
        self.txtTitles.SetValue("")        
        self.txtSubtitles.SetValue("")
        self.radTabType.SetSelection(my_globals.FREQS_TBL)
        self.tab_type = my_globals.FREQS_TBL
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.update_by_tab_type()
        self.update_demo_display()

    def on_close(self, event):
        "Close app"
        try:
            self.con.close()
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = open(fil_script, "a")
                output.add_end_script_code(f)
                f.close()
        except Exception:
            pass
        finally:
            my_globals.DBE_DEFAULT = self.dbe
            my_globals.DB_DEFAULTS[self.dbe] = self.db
            my_globals.TBL_DEFAULTS[self.dbe] = self.tbl
            self.Destroy()
            event.Skip()
    
    def update_titles_subtitles(self, orig):
        titles, subtitles = self.get_titles()
        return replace_titles_subtitles(orig, titles, subtitles)
    
    # demo table display
    def update_demo_display(self, titles_only=False):
        """
        Update demo table display with random data.
        Always use one css only (the current one).
        If only changing titles or subtitles, keep the rest constant.
        """
        debug = False
        self.btnExpand.Enable(False)
        if titles_only:
            if self.prev_demo:
                # replace titles and subtitles
                demo_tbl_html = self.update_titles_subtitles(self.prev_demo)
                self.prev_demo = demo_tbl_html
            else:
                demo_tbl_html = WAITING_MSG
        else:
            demo_html = self.demo_tab.get_demo_html_if_ok(css_idx=0)
            if demo_html == "":
                demo_tbl_html = WAITING_MSG
                self.prev_demo = None
            else:
                demo_tbl_html = ("<h1>%s</h1>\n" % 
                     _("Example data - click 'Run' for actual results") +
                     demo_html)
                self.prev_demo = demo_tbl_html
        if debug: print(u"\n" + demo_tbl_html + "\n")
        self.html.show_html(demo_tbl_html)

    def table_config_ok(self):
        """
        Is the table configuration sufficient to export as script or HTML?
        """
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              parent=self.rowRoot)
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              parent=self.colRoot)
        export_ok = False
        if self.tab_type == my_globals.FREQS_TBL:
            if has_rows:
                export_ok = True
            elif not has_rows:
                wx.MessageBox(_("Missing row(s)"))
        elif self.tab_type == my_globals.CROSSTAB:
            if has_rows and has_cols:
                export_ok = True
            elif not has_rows:
                wx.MessageBox(_("Missing row(s)"))
            elif not has_cols:
                wx.MessageBox(_("Missing column(s)"))
        elif self.tab_type == my_globals.ROW_SUMM:
            if has_rows:
                export_ok = True
            else:
                wx.MessageBox(_("Missing row(s)"))
        elif self.tab_type == my_globals.RAW_DISPLAY:
            if has_cols:
                export_ok = True
            else:
                wx.MessageBox(_("Missing column(s)"))
        else:
            raise Exception, "Not an expected table type"
        return (export_ok, has_cols)
    