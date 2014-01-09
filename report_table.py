#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import locale
import wx #@UnusedImport
import wx.gizmos

import my_globals as mg
import lib
import my_exceptions
import getdata
import config_output
import demotables
import dimtree
import full_html
import output
import projects

def replace_titles_subtitles(orig, titles, subtitles):
    """
    Have original html.
    Have list of titles and subtitles (both or either could be empty).
    Use specific tags to slice it up and reassemble it. Easiest to do with crude 
        slicing and inserting.  Best to leave the table-making processes code 
        alone. 
    Will have TBL_TITLE_START and TBL_TITLE_END. We only change what is between.
    Subtitles follows the same approach.
    NB if either or both of the titles and subtitles are empty, the row should 
        be of minimal height.
    pre_title = everything before the actual content of the title
    titles_html = just the inner html (words with lines sep by <br>)
    post_title = everything after the actual content of the title
    between_title_and_sub = everything between the title content and the 
        subtitle content.
    post_subtitle = everything after the subtitle content e.g. 2010 data
    """
    debug = False
    if debug: print(u"orig: %s\n\ntitles: %s\n\nsubtitles: %s\n\n" % (orig, 
                                                            titles, subtitles))
    titles_inner_html = output.get_titles_inner_html(titles)
    subtitles_inner_html = output.get_subtitles_inner_html(subtitles)
    # need break between titles and subtitles if both present
    if titles_inner_html and subtitles_inner_html:
        subtitles_inner_html = u"<br>" + subtitles_inner_html
    title_start_idx = orig.index(mg.TBL_TITLE_START) + len(mg.TBL_TITLE_START)
    pre_title = orig[ : title_start_idx]
    title_end_idx = orig.index(mg.TBL_TITLE_END)
    post_title = orig[title_end_idx :] # everything after title inc subtitles
    # use shorter post_title instead or orig from here on
    subtitle_start_idx = (post_title.index(mg.TBL_SUBTITLE_START) +
                          len(mg.TBL_SUBTITLE_START))
    between_title_and_sub = post_title[ : subtitle_start_idx]
    post_subtitle = post_title[post_title.index(mg.TBL_SUBTITLE_END):]
    # put it all back together
    demo_tbl_html = (pre_title + titles_inner_html + between_title_and_sub
                     + subtitles_inner_html + post_subtitle)
    if debug: 
        print((u"pre_title: %s\n\ntitles_inner_html: %s\n\n"
               u"between_title_and_sub: %s\n\nsubtitles_inner_html: %s\n\n"
               u"post_subtitle: %s") % (pre_title, titles_inner_html,
               between_title_and_sub, subtitles_inner_html, post_subtitle))
        print(u"\n\n" + u"*"*50 + u"\n\n")
    return demo_tbl_html  

def get_missing_dets_msg(tab_type, has_rows, has_cols):
    """
    No css - just directly fed into web renderer as is.
    29221c -- dark brown
    """
    html = [u"<div style=\"color: 29221c; font-size: 20px;"
        u"font-family: Arial; font-weight: bold\">"]
    if tab_type == mg.FREQS:
        html.append(_("Add and configure rows"))
    elif tab_type == mg.CROSSTAB:
        if not has_rows and not has_cols:
            html.append(_("Add and configure rows and columns"))
        elif not has_rows:
            html.append(_("Add and configure rows"))
        elif not has_cols:
            html.append(_("Add and configure columns"))
        else:
            html.append(_("Waiting for enough settings ..."))
    elif tab_type == mg.ROW_STATS:
        html.append(_("Add and configure columns"))
        if not has_rows:
            html.append(_(u" (and optionally rows)"))
        html.append(u"<p style=\"font-size: 13px; font-weight: normal\">E.g. "
                u"if you want the average age per country select age as the "
                u"<u>column</u> variable (configure mean, median etc) and "
                u"country as the <u>row</u> variable.</p>")
    elif tab_type == mg.DATA_LIST:
        html.append(_("Add and configure columns"))
    else:
        raise Exception(u"Unknown table type")
    html.append(u"</div>")
    return u"\n".join(html)


class RptTypeOpts(object):
    """
    Required because of a bug in Mac when displaying radio button groups with a 
        font size smaller than the system font. Have to build a collection of 
        individual widgets myself.
    """
    
    def __init__(self, parent, panel):
        group_lbl = _("Table Type")
        tab_type_choices = (mg.FREQS_LBL, mg.CROSSTAB_LBL, mg.ROW_STATS_LBL, 
                            mg.DATA_LIST_LBL)
        if not config_output.IS_MAC:
            self.rad_opts = wx.RadioBox(panel, -1, group_lbl, 
                                            choices=tab_type_choices,
                                            style=wx.RA_SPECIFY_COLS)
            self.rad_opts.SetFont(mg.GEN_FONT)
            self.rad_opts.Bind(wx.EVT_RADIOBOX, parent.on_tab_type_change)
        else:
            bx_rpt_type = wx.StaticBox(panel, -1, group_lbl)
            szr_rad_rpt_type = wx.StaticBoxSizer(bx_rpt_type, wx.HORIZONTAL)
            self.rad_freq = wx.RadioButton(panel, -1, mg.FREQS_LBL, 
                                           style=wx.RB_GROUP) # leads
            self.rad_freq.SetFont(mg.GEN_FONT)
            self.rad_freq.Bind(wx.EVT_RADIOBUTTON, parent.on_tab_type_change)
            self.rad_freq.SetValue(True) # init (required by Mac)
            szr_rad_rpt_type.Add(self.rad_freq)
            self.rad_cross = wx.RadioButton(panel, -1, mg.CROSSTAB_LBL)
            self.rad_cross.SetFont(mg.GEN_FONT)
            self.rad_cross.Bind(wx.EVT_RADIOBUTTON, parent.on_tab_type_change)
            szr_rad_rpt_type.Add(self.rad_cross, 0, wx.LEFT, 5)
            self.rad_row_stats = wx.RadioButton(panel, -1, mg.ROW_STATS_LBL)
            self.rad_row_stats.SetFont(mg.GEN_FONT)
            self.rad_row_stats.Bind(wx.EVT_RADIOBUTTON, 
                                    parent.on_tab_type_change)
            szr_rad_rpt_type.Add(self.rad_row_stats, 0, wx.LEFT, 5)
            self.rad_data_list = wx.RadioButton(panel, -1, mg.DATA_LIST_LBL)
            self.rad_data_list.SetFont(mg.GEN_FONT)
            self.rad_data_list.Bind(wx.EVT_RADIOBUTTON, 
                                    parent.on_tab_type_change)
            szr_rad_rpt_type.Add(self.rad_data_list, 0, wx.LEFT, 5)
            self.rad_opts = szr_rad_rpt_type

    def GetSelection(self):
        debug = False
        try:
            return self.rad_opts.GetSelection()
        except AttributeError:
            for idx, szr_item in enumerate(self.rad_opts.GetChildren()):
                rad = szr_item.GetWindow()
                if debug: print(u"Item %s with value of %s" % (idx, 
                                                               rad.GetValue()))
                if rad.GetValue():
                    return idx
            return None
        
    def SetSelection(self, idx):
        try:
            return self.rad_opts.SetSelection(idx)
        except AttributeError:
            self.rad_opts.GetChildren()[idx].GetWindow().SetValue(True)
            
    def Enable(self, enable=True):
        """
        If the object can be enabled/disabled do that. If not, assume it is a 
            sizer containing widgets needing to be individually enabled etc.
        """
        try:
            self.rad_opts.Enable(enable)
        except AttributeError:
            for szr_item in self.rad_opts.GetChildren():
                szr_item.GetWindow().Enable(enable)
            
    def get_szr(self):
        """
        Use this when inserting into a sizer (expects a sizer or widget not this 
            object.
        """
        return self.rad_opts
    

class DlgMakeTable(wx.Dialog, config_output.ConfigUI, dimtree.DimTree):
    """
    ConfigUI -- provides reusable interface for data selection, setting labels 
        etc. Sets values for db, default_tbl etc and responds to selections etc.
    self.col_no_vars_item -- the column item when there are no column variables,
        only columns related to the row variables e.g. total, row and col %s.
    """
    
    def __init__(self, var_labels=None, var_notes=None, val_dics=None):
        debug = False
        self.exiting = False
        cc = config_output.get_cc()
        self.title = _("Make Report Table")
        wx.Dialog.__init__(self, parent=None, id=-1, title=self.title, 
                       pos=(mg.HORIZ_OFFSET, 0), # -1 positions too low on 768v
                       style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|
                       wx.CLOSE_BOX|wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
        config_output.ConfigUI.__init__(self, autoupdate=True)
        self.SetFont(mg.GEN_FONT)
        dimtree.DimTree.__init__(self)
        self.output_modules = ["my_globals as mg", "dimtables", "rawtables", 
                               "output", "getdata"]
        self.Bind(wx.EVT_CLOSE, self.on_btn_close)
        self.url_load = True # btn_expand    
        (self.var_labels, self.var_notes, 
         self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.col_no_vars_item = None #  needed if no variable in columns.  Must
            # reset to None if deleted all vars
        # set up panel for frame
        self.panel = wx.Panel(self)
        config_output.add_icon(frame=self)
        # sizers
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_top = wx.BoxSizer(wx.HORIZONTAL)
        # key settings
        self.drop_tbls_panel = self.panel
        self.drop_tbls_system_font_size = False
        self.drop_tbls_sel_evt = self.on_table_sel
        hide_db = projects.get_hide_db()
        self.drop_tbls_idx_in_szr = 3 if not hide_db else 1 # the 2 database items are missing)
        self.drop_tbls_rmargin = 10
        self.drop_tbls_can_grow = False
        (self.szr_data, 
         self.szr_output_config) = self.get_gen_config_szrs(self.panel, 
                                                            hide_db=hide_db) # mixin
        self.drop_tbls_szr = self.szr_data
        getdata.data_dropdown_settings_correct(parent=self)
        szr_tab_type = wx.BoxSizer(wx.HORIZONTAL)
        szr_opts = wx.BoxSizer(wx.HORIZONTAL)
        szr_raw_display_opts = wx.BoxSizer(wx.VERTICAL)
        szr_titles = wx.BoxSizer(wx.HORIZONTAL)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_trees = wx.BoxSizer(wx.HORIZONTAL)
        szr_rows = wx.BoxSizer(wx.VERTICAL)
        szr_cols = wx.BoxSizer(wx.VERTICAL)
        szr_col_btns = wx.BoxSizer(wx.HORIZONTAL)
        szr_html = wx.BoxSizer(wx.VERTICAL)
        self.szr_output_display = self.get_szr_output_display(self.panel, 
            idx_style=2) # mixin
        self.btn_help = wx.Button(self.panel, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        # title details
        lbl_titles = wx.StaticText(self.panel, -1, _("Title:"))
        lbl_titles.SetFont(mg.LABEL_FONT)
        title_height = 40 if mg.PLATFORM == mg.MAC else 20
        self.txt_titles = wx.TextCtrl(self.panel, -1, size=(250,title_height), 
            style=wx.TE_MULTILINE)
        self.txt_titles.Bind(wx.EVT_TEXT, self.on_title_change)
        lbl_subtitles = wx.StaticText(self.panel, -1, _("Subtitle:"))
        lbl_subtitles.SetFont(mg.LABEL_FONT)
        self.txt_subtitles = wx.TextCtrl(self.panel, -1,size=(250,title_height), 
            style=wx.TE_MULTILINE)
        self.txt_subtitles.Bind(wx.EVT_TEXT, self.on_subtitle_change)
        # table type. NB max indiv width sets width for all items in Win or OSX
        self.rad_opts = RptTypeOpts(parent=self, panel=self.panel)
        self.tab_type = self.rad_opts.GetSelection()
        # option checkboxs
        self.chk_totals_row = wx.CheckBox(self.panel, -1, _("Totals Row?"))
        self.chk_totals_row.SetFont(mg.GEN_FONT)
        self.chk_totals_row.Bind(wx.EVT_CHECKBOX, self.on_chk_totals_row)
        self.chk_first_as_label = wx.CheckBox(self.panel, -1, 
            _("First col as label?"))
        self.chk_first_as_label.SetFont(mg.GEN_FONT)
        self.chk_first_as_label.Bind(wx.EVT_CHECKBOX, 
            self.on_chk_first_as_label)
        self.enable_raw_display_opts(enable=False)
        self.chk_show_perc_symbol = wx.CheckBox(self.panel, -1, 
            _("Show percent symbol?"))
        self.chk_show_perc_symbol.SetFont(mg.GEN_FONT)
        self.chk_show_perc_symbol.Bind(wx.EVT_CHECKBOX, 
            self.on_chk_show_perc_symbol)
        has_perc = not mg.RPT_CONFIG[self.tab_type][mg.VAR_SUMMARISED_KEY]
        self.enable_show_perc_symbol_opt(enable=has_perc)
        self.chk_show_perc_symbol.SetValue(True) # True is default
        #text labels
        lbl_rows = wx.StaticText(self.panel, -1, _("Rows:"))
        lbl_rows.SetFont(mg.LABEL_FONT)
        lbl_cols = wx.StaticText(self.panel, -1, _("Columns:"))
        lbl_cols.SetFont(mg.LABEL_FONT)
        #buttons
        #rows
        self.btn_row_add = wx.Button(self.panel, -1, _("Add"))
        self.btn_row_add.SetFont(mg.BTN_FONT)
        self.btn_row_add.Bind(wx.EVT_BUTTON, self.on_row_add)
        self.btn_row_add_under = wx.Button(self.panel, -1, _("Add Under"))
        self.btn_row_add_under.SetFont(mg.BTN_FONT)
        self.btn_row_add_under.Bind(wx.EVT_BUTTON, self.on_row_add_under)
        self.btn_row_del = wx.Button(self.panel, -1, _("Delete"))
        self.btn_row_del.SetFont(mg.BTN_FONT)
        self.btn_row_del.Bind(wx.EVT_BUTTON, self.on_row_delete)
        self.btn_row_conf = wx.Button(self.panel, -1, _("Config"))
        self.btn_row_conf.SetFont(mg.BTN_FONT)
        self.btn_row_conf.Bind(wx.EVT_BUTTON, self.on_row_config)
        #cols
        self.btn_col_add = wx.Button(self.panel, -1, _("Add"))
        self.btn_col_add.SetFont(mg.BTN_FONT)
        self.btn_col_add.Bind(wx.EVT_BUTTON, self.on_col_add)
        self.btn_col_add_under = wx.Button(self.panel, -1, _("Add Under"))
        self.btn_col_add_under.SetFont(mg.BTN_FONT)
        self.btn_col_add_under.Bind(wx.EVT_BUTTON, self.on_col_add_under)
        self.btn_col_del = wx.Button(self.panel, -1, _("Delete"))
        self.btn_col_del.SetFont(mg.BTN_FONT)
        self.btn_col_del.Bind(wx.EVT_BUTTON, self.on_col_delete)
        self.btn_col_conf = wx.Button(self.panel, -1, _("Config"))
        self.btn_col_conf.SetFont(mg.BTN_FONT)
        self.btn_col_conf.Bind(wx.EVT_BUTTON, self.on_col_config)
        #trees
        self.rowtree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, 
            self.on_row_item_activated)
        self.rowtree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_row_item_rclick)
        self.rowtree.SetToolTipString(_("Right click variables to view/edit "
            "details"))
        self.rowroot = self.setup_dim_tree(self.rowtree)
        self.coltree = wx.gizmos.TreeListCtrl(self.panel, -1, 
              style=wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT|wx.TR_MULTIPLE)
        self.coltree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, 
                          self.on_col_item_activated)
        self.coltree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_col_item_rclick)
        self.coltree.SetToolTipString(_("Right click variables to view/edit "
            "details"))
        self.colroot = self.setup_dim_tree(self.coltree)
        # setup demo table type
        if debug: print(cc[mg.CURRENT_CSS_PATH])
        self.prev_demo = None
        self.demo_tab = demotables.DemoDimTable(txt_titles=self.txt_titles, 
            txt_subtitles=self.txt_subtitles, tab_type=mg.FREQS, # the default
            colroot=self.colroot, rowroot=self.rowroot, rowtree=self.rowtree, 
            coltree=self.coltree, col_no_vars_item=self.col_no_vars_item, 
            var_labels=self.var_labels, val_dics=self.val_dics)
        # freqs tbl is default
        self.setup_row_btns()
        self.setup_col_btns()
        self.add_default_column_config() # must set up after coltree and demo
        # html (esp height)
        if mg.PLATFORM == mg.MAC:
            min_height = 80
            grow_from = 768
        else:
            min_height = 150
            grow_from = 600
        if mg.MAX_HEIGHT <= grow_from:
            myheight = min_height
        else:
            myheight = min_height + ((mg.MAX_HEIGHT-grow_from)*0.2)
        myheight = 350 if myheight > 350 else myheight
        self.html = full_html.FullHTML(panel=self.panel, parent=self, 
            size=(200,myheight))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        self.btn_run.Enable(False)
        self.chk_add_to_report.Enable(False)
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_top.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_top.Add(self.szr_data, 1, wx.LEFT, 5)
        try:
            szr_tab_type.Add(self.rad_opts, 0, wx.LEFT|wx.RIGHT, 10)
        except TypeError:
            szr_tab_type.Add(self.rad_opts.get_szr(), 0, 
                wx.LEFT|wx.RIGHT, 10)
        szr_titles.Add(lbl_titles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_titles, 1, wx.RIGHT, 10)
        szr_titles.Add(lbl_subtitles, 0, wx.RIGHT, 5)
        szr_titles.Add(self.txt_subtitles, 1)
        szr_raw_display_opts.Add(self.chk_totals_row, 0)        
        szr_raw_display_opts.Add(self.chk_first_as_label, 0)
        szr_opts.Add(szr_raw_display_opts, 0) 
        szr_opts.Add(self.chk_show_perc_symbol, 0)
        szr_tab_type.Add(szr_opts, 0)
        szr_rows.Add(lbl_rows, 0)
        szr_row_btns = wx.BoxSizer(wx.HORIZONTAL)
        szr_row_btns.Add(self.btn_row_add, 0, wx.RIGHT, 2)
        szr_row_btns.Add(self.btn_row_add_under, 0, wx.RIGHT, 2)
        szr_row_btns.Add(self.btn_row_del, 0, wx.RIGHT, 2)
        szr_row_btns.Add(self.btn_row_conf)
        szr_rows.Add(szr_row_btns, 0)
        szr_rows.Add(self.rowtree, 1, wx.GROW)
        szr_cols.Add(lbl_cols, 0)
        szr_col_btns.Add(self.btn_col_add, 0, wx.RIGHT, 2)
        szr_col_btns.Add(self.btn_col_add_under, 0, wx.RIGHT, 2)
        szr_col_btns.Add(self.btn_col_del, 0, wx.RIGHT, 2)
        szr_col_btns.Add(self.btn_col_conf)
        szr_cols.Add(szr_col_btns)
        szr_cols.Add(self.coltree, 1, wx.GROW)
        szr_trees.Add(szr_rows, 1, wx.GROW|wx.RIGHT, 2)
        szr_trees.Add(szr_cols, 1, wx.GROW|wx.LEFT, 2)
        szr_html.Add(self.html, 1, wx.GROW)
        szr_bottom.Add(szr_html, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_bottom.Add(self.szr_output_display, 0, wx.GROW|wx.RIGHT, 5)
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 5
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(szr_top, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(szr_tab_type, 0, wx.BOTTOM, 5)
        szr_main.Add(szr_trees, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_titles, 0, wx.GROW|wx.LEFT|wx.TOP|wx.RIGHT|
            wx.BOTTOM, 10)
        szr_main.Add(self.szr_output_config, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_bottom, 2, wx.GROW|wx.TOP|wx.BOTTOM, 5)
        self.panel.SetSizer(szr_main)
        szr_lst = [szr_top, szr_tab_type, szr_trees, szr_titles, 
            self.szr_output_config, szr_bottom]
        lib.set_size(window=self, szr_lst=szr_lst, width_init=1024)

    def on_show(self, event):
        if self.exiting:
            return
        try:
            self.html.pizza_magic() # must happen after Show
        except Exception:
            pass # need on Mac or exceptn survives
        finally: # any initial content
            has_rows, has_cols = self.get_row_col_status()
            waiting_msg = get_missing_dets_msg(self.tab_type, has_rows, 
                                               has_cols)
            self.html.show_html(waiting_msg)

    def update_css(self):
        "Update css, including for demo table"
        cc = config_output.get_cc()
        config_output.ConfigUI.update_css(self)
        self.demo_tab.fil_css = cc[mg.CURRENT_CSS_PATH]
        self.update_demo_display()
    
    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        Clear dim areas.
        """
        if config_output.ConfigUI.on_database_sel(self, event):
            self.data_changed()
        
    def on_table_sel(self, event):
        """
        Reset table, fields, has_unique, and idxs.
        Clear dim areas.
        """       
        config_output.ConfigUI.on_table_sel(self, event)
        self.data_changed()
    
    def data_changed(self):
        """
        Things to do after the data source has changed.
        Note - real tables always run a script supplied fresh db details. Demo 
            tables either don't use real data (dim tables use labels and items 
            stored in variable trees) or take the data details they need at the 
            moment they generate the html. 
        """
        self.delete_all_dim_children()
        self.col_no_vars_item = None
        if self.tab_type == mg.FREQS:
            self.add_default_column_config()
        self.setup_row_btns()
        self.setup_col_btns()
        live_demo = self.update_demo_display()
        self.align_action_btns(live_demo)
        
    def update_var_dets(self, update_display=True):
        "Update all labels, including those already displayed"
        config_output.update_var_dets(dlg=self)
        # update dim trees
        rowdescendants = lib.get_tree_ctrl_descendants(self.rowtree, 
                                                       self.rowroot)
        self.refresh_descendants(self.rowtree, rowdescendants)
        coldescendants = lib.get_tree_ctrl_descendants(self.coltree, 
                                                       self.colroot)
        self.refresh_descendants(self.coltree, coldescendants)
        # update demo area
        self.demo_tab.var_labels = self.var_labels
        self.demo_tab.val_dics = self.val_dics
        if update_display:
            self.update_demo_display()    
    
    def refresh_vars(self):
        self.update_var_dets()
           
    def refresh_descendants(self, tree, descendants):
        for descendant in descendants:
            # descendant -- NB GUI tree items, not my Dim Node obj
            if descendant == self.col_no_vars_item:
                continue
            item_conf = tree.GetItemPyData(descendant)
            var_name = item_conf.var_name
            fresh_label = lib.get_choice_item(self.var_labels, var_name)
            tree.SetItemText(descendant, fresh_label)

    # table type
    def on_tab_type_change(self, event):
        "Respond to change of table type"
        self.update_by_tab_type()
    
    def update_by_tab_type(self):
        """
        Delete all col vars. May add back the default col config if a FREQS TBL
        If changed to row summ or raw display, delete all row vars.
        If changing to freq or crosstab, leave row vars alone but wipe their 
            measures (if any set).
        Don't set show_perc when instantiating here as needs to be checked every 
            time get_demo_html_if_ok() is called.
        """
        self.tab_type = self.rad_opts.GetSelection() # for convenience
        self.coltree.DeleteChildren(self.colroot)
        self.col_no_vars_item = None
        if self.tab_type != mg.DATA_LIST:
            rowdescendants = lib.get_tree_ctrl_descendants(tree=self.rowtree, 
                                                           parent=self.rowroot)
            for tree_dims_item in rowdescendants:
                item_conf = self.rowtree.GetItemPyData(tree_dims_item)
                if item_conf is not None:
                    item_conf.measures_lst = []
                    self.rowtree.SetItemText(tree_dims_item, 
                                             item_conf.get_summary(), 1)    
        else:
            self.rowtree.DeleteChildren(self.rowroot)
        # link to appropriate demo table type
        if self.tab_type != mg.DATA_LIST:
            self.enable_raw_display_opts(enable=False)
            rpt_config = mg.RPT_CONFIG[self.tab_type]
            has_perc = not rpt_config[mg.VAR_SUMMARISED_KEY]
            self.enable_show_perc_symbol_opt(enable=has_perc)
            self.demo_tab = demotables.DemoDimTable(txt_titles=self.txt_titles, 
                         txt_subtitles=self.txt_subtitles, 
                         tab_type=self.tab_type,
                         colroot=self.colroot, rowroot=self.rowroot, 
                         rowtree=self.rowtree, coltree=self.coltree, 
                         col_no_vars_item=self.col_no_vars_item, 
                         var_labels=self.var_labels, val_dics=self.val_dics)
            if self.tab_type == mg.FREQS:
                self.add_default_column_config()
        else:
            self.enable_raw_display_opts(enable=True)
            self.enable_show_perc_symbol_opt(enable=False)
            self.demo_tab = demotables.DemoRawTable(txt_titles=self.txt_titles, 
                         txt_subtitles=self.txt_subtitles, 
                         colroot=self.colroot, coltree=self.coltree, 
                         var_labels=self.var_labels, val_dics=self.val_dics,
                         add_total_row=self.chk_totals_row.IsChecked(),
                         first_col_as_label=self.chk_first_as_label.IsChecked())
        # in case they were disabled and then we changed tab type
        self.setup_row_btns()
        self.setup_col_btns()
        live_demo = self.update_demo_display()
        self.align_action_btns(live_demo)
        self.txt_titles.SetFocus()
        
    def enable_raw_display_opts(self, enable=True):
        "Enable (or disable) raw display options"
        self.chk_totals_row.Enable(enable)
        self.chk_first_as_label.Enable(enable)
        
    def enable_show_perc_symbol_opt(self, enable=True):
        "Enable (or disable) Show Percentage Symbol option"
        self.chk_show_perc_symbol.Enable(enable)
        
    def on_chk_totals_row(self, event):
        "Update display as total rows checkbox changes"
        self.update_demo_display()

    def on_chk_first_as_label(self, event):
        "Update display as first column as label checkbox changes"
        self.update_demo_display()
    
    def on_chk_show_perc_symbol(self, event):
        "Update display as show percentage symbol checkbox changes"
        self.update_demo_display()
    
    # titles/subtitles
    def on_title_change(self, event):
        """
        Update display as titles change
        Need to SetFocus back to titles because in Windows, IEHTMLWindow steals
            the focus if you have previously clicked it at some point.
        """
        self.update_demo_display(titles_only=True)
        self.txt_titles.SetFocus()

    def on_subtitle_change(self, event):
        """
        Update display as subtitles change.  See on_title_change comment.
        """
        self.update_demo_display(titles_only=True)
        self.txt_subtitles.SetFocus()
        
    # run
    def too_long(self):
        # check not a massive report table. Overrides default
        too_long = False
        if self.tab_type == mg.DATA_LIST:
            rows_n = config_output.ConfigUI.get_rows_n(self)
            if rows_n > 500:
                strn = locale.format('%d', rows_n, True)
                if (wx.MessageBox(_("This report has %s rows. Do you wish to "
                                   "run it?") % strn, caption=_("LONG REPORT"), 
                                   style=wx.YES_NO) == wx.NO):
                    too_long = True
        return too_long
    
    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location (INT_REPORT_PATH) 
            and into report file, and finally, display html output.
        """
        run_ok, has_cols = self.table_config_ok()
        if run_ok:
            config_output.ConfigUI.on_btn_run(self, event, 
                                              get_script_args=[has_cols,])
    
    # export script
    def on_btn_script(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        export_ok, has_cols = self.table_config_ok()
        if export_ok:
            try:
                css_fils, css_idx = output.get_css_dets()
            except my_exceptions.MissingCss, e:
                lib.update_local_display(self.html, 
                        _(u"Please check the CSS file exists or set another."
                          u"\nCaused by error: %s") % lib.ue(e), wrap_text=True)
                lib.safe_end_cursor()
                event.Skip()
                return
            script = self.get_script(css_idx, has_cols)
            output.export_script(script, css_fils)
    
    def get_script(self, css_idx, has_cols):
        """
        Build script from inputs.
        Unlike the stats test output, no need to link to images etc, so no need
            to know what this report will be called (so we can know where any
            images are to link to).
        """
        dd = mg.DATADETS_OBJ
        self.g = self.get_next_node_name()
        script_lst = []
        # set up variables required for passing into main table instantiation
        if self.tab_type in [mg.FREQS, mg.CROSSTAB, mg.ROW_STATS]:
            script_lst.append(u"# Rows" + 60*u"*")
            script_lst.append(u"tree_rows = dimtables.DimNodeTree()")
            for child in lib.get_tree_ctrl_children(tree=self.rowtree, 
                                                    item=self.rowroot):
                # child -- NB GUI tree items, not my Dim Node obj
                item_conf = self.rowtree.GetItemPyData(child)
                child_fldname = item_conf.var_name
                self.add_to_parent(script_lst=script_lst, tree=self.rowtree, 
                            parent=self.rowtree, parent_node_label=u"tree_rows",
                            parent_name=u"row",
                            child=child, child_fldname=child_fldname)
            script_lst.append(u"# Columns" + 57*u"*")
            script_lst.append(u"tree_cols = dimtables.DimNodeTree()")
            if has_cols:
                for child in lib.get_tree_ctrl_children(tree=self.coltree, 
                                                        item=self.colroot):
                    item_conf = self.coltree.GetItemPyData(child)
                    child_fldname = item_conf.var_name
                    self.add_to_parent(script_lst=script_lst, tree=self.coltree, 
                            parent=self.coltree, parent_node_label=u"tree_cols",
                            parent_name=u"column",
                            child=child, child_fldname=child_fldname)
            script_lst.append(u"# Misc" + 60*u"*")
        elif self.tab_type == mg.DATA_LIST:
            (col_names, col_labels, 
             col_sorting) = lib.get_col_dets(self.coltree, self.colroot, 
                                             self.var_labels)
            # pprint.pformat() fails on non-ascii - a shame
            script_lst.append(u"col_names = " + unicode(col_names))
            script_lst.append(u"col_labels = " + unicode(col_labels))
            script_lst.append(u"col_sorting = " + unicode(col_sorting))
            script_lst.append(u"flds = " + lib.dic2unicode(dd.flds))
            script_lst.append(u"var_labels = " +
                              lib.dic2unicode(self.var_labels))
            script_lst.append(u"val_dics = " + lib.dic2unicode(self.val_dics))
        # process title dets
        titles, subtitles = self.get_titles()
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        # NB the following text is all going to be run
        if self.tab_type in (mg.FREQS, mg.CROSSTAB):
            show_perc = (u"True" if self.chk_show_perc_symbol.IsChecked() 
                         else u"False")
            script_lst.append(u"tab_test = dimtables.GenTable(" +
                            u"titles=%s," % unicode(titles) +
                            u"\n    subtitles=%s," % unicode(subtitles) +
                            u"\n    tab_type=%s," % self.tab_type +
                            u"\n    dbe=u\"%s\", " % dd.dbe +
                            u"tbl=u\"%s\", " % dd.tbl +
                            u"tbl_filt=tbl_filt," +
                            u"\n    cur=cur, flds=flds, tree_rows=tree_rows, " +
                            u"tree_cols=tree_cols, show_perc=%s)" % show_perc)
        elif self.tab_type == mg.ROW_STATS:
            script_lst.append(u"tab_test = dimtables.SummTable(" +
                            u"titles=%s," % unicode(titles) +
                            u"\n    subtitles=%s," % unicode(subtitles) +
                            u"\n    tab_type=%s," % self.tab_type +
                            u"\n    dbe=u\"%s\", " % dd.dbe +
                            u"tbl=u\"%s\", " % dd.tbl +
                            u"tbl_filt=tbl_filt," +
                            u"\n    cur=cur, flds=flds, tree_rows=tree_rows, " +
                            u"tree_cols=tree_cols)")
        elif self.tab_type == mg.DATA_LIST:
            tot_rows = u"True" if self.chk_totals_row.IsChecked() else u"False"
            first_label = (u"True" if self.chk_first_as_label.IsChecked()
                           else u"False")
            script_lst.append(u"""
tab_test = rawtables.RawTable(titles=%(titles)s, 
    subtitles=%(subtitles)s, dbe=u\"%(dbe)s\", col_names=col_names, 
    col_labels=col_labels, col_sorting=col_sorting, flds=flds, 
    var_labels=var_labels, val_dics=val_dics, tbl=u\"%(tbl)s\",
    tbl_filt=tbl_filt, cur=cur, add_total_row=%(tot_rows)s,
    first_col_as_label=%(first_label)s)""" % {u"titles": unicode(titles), 
                u"subtitles": unicode(subtitles), u"dbe": dd.dbe, 
                u"tbl": dd.tbl, u"tot_rows": tot_rows, 
                u"first_label": first_label})
        if self.tab_type in [mg.FREQS, mg.CROSSTAB, mg.ROW_STATS]:
            script_lst.append(u"tab_test.prep_table(%s)" % css_idx)
            script_lst.append(u"max_cells = %s" % mg.MAX_CELLS_IN_REPORT_TABLE)
            script_lst.append(u"if tab_test.get_cell_n_ok("
                              u"max_cells=max_cells):")
            script_lst.append(u"    "
                              u"fil.write(tab_test.get_html(%s, " % css_idx +
                              u"page_break_after=False))")
            script_lst.append(u"else:")
            script_lst.append(u"    "
                      u"raise my_exceptions.ExcessReportTableCells(max_cells)")
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
                      parent_name, child, child_fldname):
        """
        Add script code for adding child nodes to parent nodes.
        tree -- TreeListCtrl tree
        parent, child -- TreeListCtrl items
        parent_node_label -- for parent_node_label.add_child(...)
        child_fldname -- used to get variable label, and value labels
            from relevant dicts; plus as the field name
        """
        debug = False
        # add child to parent
        if child == self.col_no_vars_item:
            fld_arg = u""
            var_label = _("Frequency column")
        else:
            fld_arg = u"fld=u\"%s\", " % child_fldname
            if debug: 
                print(self.var_labels)
                print(self.val_dics)
            var_label = self.var_labels.get(child_fldname, 
                                            child_fldname.title())
        labels_dic = self.val_dics.get(child_fldname, {})
        child_node_label = self.g.next()
        item_conf = tree.GetItemPyData(child)
        measures_lst = item_conf.measures_lst
        measures = u", ".join([(u"mg." +
                               mg.script_export_measures_dic[x]) for
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
        fldname = (_("Column configuration") if child_fldname is None
                   else child_fldname)
        script_lst.append(u"# Defining %s (\"%s\")" % (child_node_label, 
                                                       fldname))
        script_lst.append(child_node_label +
                          u" = dimtables.DimNode(" + fld_arg +
                          u"\n    label=u\"%s\"," % unicode(var_label) +
                          u"\n    labels=" + unicode(labels_dic) +
                          measures_arg + tot_arg + sort_order_arg +
                          numeric_arg + u")")
        if parent_node_label in (u"tree_rows", u"tree_cols"):
            parent_name = (u"rows" if parent_node_label == u"tree_rows"
                           else u"columns")          
            script_lst.append(u"# Adding \"%s\" to %s" % (fldname, 
                                                          parent_name))
        else:
            script_lst.append(u"# Adding \"%s\" under \"%s\"" % (fldname, 
                                                                 parent_name))
        script_lst.append(u"%s.add_child(%s)" % (parent_node_label, 
                                                 child_node_label))
        # send child through for each grandchild
        for grandchild in lib.get_tree_ctrl_children(tree=tree, item=child):
            # grandchild -- NB GUI tree items, not my Dim Node obj
            item_conf = tree.GetItemPyData(grandchild)
            grandchild_fldname = item_conf.var_name
            self.add_to_parent(script_lst=script_lst, tree=tree, parent=child,
                               parent_node_label=child_node_label, 
                               parent_name=child_fldname, child=grandchild, 
                               child_fldname=grandchild_fldname)
    
    def on_btn_help(self, event):
        """
        Export script if enough data to create table.
        """
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:report_tables"
        webbrowser.open_new_tab(url)
        event.Skip()
    
    def delete_all_dim_children(self):
        """
        If wiping columns, must always reset col_no_vars_item to None.
        """
        self.rowtree.DeleteChildren(self.rowroot)
        self.coltree.DeleteChildren(self.colroot)
        self.col_no_vars_item = None
          
    def on_btn_clear(self, event):
        "Clear all settings"
        self.txt_titles.SetValue("")        
        self.txt_subtitles.SetValue("")
        self.rad_opts.SetSelection(mg.FREQS)
        self.tab_type = mg.FREQS
        self.delete_all_dim_children()
        self.update_by_tab_type()

    def update_titles_subtitles(self, orig):
        titles, subtitles = self.get_titles()
        return replace_titles_subtitles(orig, titles, subtitles)
    
    # demo table display
    def get_live_html(self):
        run_ok, has_cols = self.table_config_ok(silent=True)
        if not run_ok:
            return False, u""
        new_has_dojo = False
        get_script_args = [has_cols,]
        (bolran_report, 
         str_content) = config_output.ConfigUI.get_script_output(self, 
                                                  get_script_args, new_has_dojo,
                                                  allow_add2rpt=False)
        return bolran_report, str_content
    
    def update_demo_display(self, titles_only=False):
        """
        Update demo table display. If small data volume, use real data. 
            Otherwise use random data.
        Always use one css only (the current one).
        If only changing titles or subtitles, keep the rest constant to avoid 
            random twitching as we add letters to the title.
        """
        debug = False
        demo_html = u""
        self.btn_expand.Enable(False)
        demo_was_live = False
        if titles_only:
            if self.prev_demo:
                # replace titles and subtitles
                demo_tbl_html = self.update_titles_subtitles(self.prev_demo)
                self.prev_demo = demo_tbl_html
            else:
                has_rows, has_cols = self.get_row_col_status()
                waiting_msg = get_missing_dets_msg(self.tab_type, has_rows, 
                                                   has_cols)
                demo_tbl_html = waiting_msg
        else:
            try: # need to reset here otherwise stays as was set when instantiated
                self.demo_tab.show_perc = self.chk_show_perc_symbol.IsChecked()
                rpt_config = mg.RPT_CONFIG[self.tab_type]
                quick_enough = (self.rows_n < rpt_config[mg.QUICK_IF_BELOW_KEY])
                if quick_enough:
                    bolran_report, demo_html = self.get_live_html()
                    self.btn_expand.Enable(bolran_report)
                    self.content2expand = demo_html
                    demo_was_live = bolran_report
                else:
                    demo_html = self.demo_tab.get_demo_html_if_ok(css_idx=0)
            except my_exceptions.MissingCss, e:
                lib.update_local_display(self.html, _("Please check the CSS "
                                        "file exists or set another. "
                                        "Caused by error: %s") % lib.ue(e), 
                                        wrap_text=True)
                lib.safe_end_cursor()
                return demo_was_live
            except my_exceptions.TooFewValsForDisplay:
                lib.update_local_display(self.html,
                                   _("Not enough data to display.  "
                                   "Please check variables and any filtering."),
                                   wrap_text=True)
                lib.safe_end_cursor()
                return demo_was_live
            if demo_html == u"":
                has_rows, has_cols = self.get_row_col_status()
                waiting_msg = get_missing_dets_msg(self.tab_type, has_rows, 
                                                   has_cols)
                demo_tbl_html = waiting_msg
                self.prev_demo = None
            else:
                if demo_was_live:
                    demo_tbl_html = demo_html
                else:
                    demo_only_msg = (_(u"<p class='gui-msg-medium'>Example data"
                       u" only because of size of table - click '%s' for actual"
                       u" results<br>&nbsp;&nbsp;or keep configuring</p>") % 
                                     config_output.RUN_LBL)
                    try:
                        idx_body_start = (demo_html.index(mg.BODY_START) + 
                                          len(mg.BODY_START))
                        demo_tbl_html = (demo_html[:idx_body_start] 
                                         + demo_only_msg 
                                         + u"\n\n" + demo_html[idx_body_start:])
                    except ValueError:
                        demo_tbl_html = demo_html
                self.prev_demo = demo_tbl_html
        if debug: print(u"\n" + demo_tbl_html + "\n")
        self.html.show_html(demo_tbl_html)
        return demo_was_live

    def get_row_col_status(self):
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              item=self.rowroot)
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              item=self.colroot)
        return has_rows, has_cols

    def table_config_ok(self, silent=False):
        """
        Is the table configuration sufficient to export as script or HTML?
        """
        has_rows, has_cols = self.get_row_col_status()
        export_ok = False
        if self.tab_type == mg.FREQS:
            if has_rows:
                export_ok = True
            elif not has_rows and not silent:
                wx.MessageBox(_("Missing row(s)"))
        elif self.tab_type == mg.CROSSTAB:
            if has_rows and has_cols:
                export_ok = True
            elif not has_rows and not silent:
                wx.MessageBox(_("Missing row(s)"))
            elif not has_cols and not silent:
                wx.MessageBox(_("Missing column(s)"))
        elif self.tab_type == mg.ROW_STATS:
            if has_cols:
                export_ok = True
            elif not silent:
                wx.MessageBox(_("Missing column(s)"))
        elif self.tab_type == mg.DATA_LIST:
            if has_cols:
                export_ok = True
            elif not silent:
                wx.MessageBox(_("Missing column(s)"))
        else:
            raise Exception(u"Not an expected table type")
        return (export_ok, has_cols)

    def align_action_btns(self, live_demo=False):
        """
        Enable or disable the action buttons (Run and Export) according to 
            completeness of configuration data.
        Also align the export buttons.
        """
        ready2run, unused = self.table_config_ok(silent=True)
        if live_demo:
            runlbl2use = config_output.ADD2_RPT_LBL
            mg.ADD2RPT = True
            self.chk_add_to_report.Show(False) # The button itself can handle this
        else:
            runlbl2use = config_output.RUN_LBL
            self.chk_add_to_report.Show(True)
            self.panel_with_add2report.Layout()
            if self.chk_add_to_report.Enabled:
                mg.ADD2RPT = self.chk_add_to_report.IsChecked()
        if not self.btn_run.IsEnabled():
            self.btn_run.Enable()
        self.btn_run.SetLabel(runlbl2use)
        self.btn_run.Enable(ready2run)
        self.chk_add_to_report.Enable(ready2run)
        self.align_export_btns(live_demo)
        
    def on_btn_var_config(self, event):
        """
        Variable details may have changed e.g. variable and value labels.
        """
        ret = config_output.ConfigUI.on_btn_var_config(self, event)
        update_display = (ret != wx.ID_CANCEL)
        self.update_var_dets(update_display)
