from __future__ import print_function
import pprint
import sys
import wx

import my_globals as mg
import config_globals
import lib
import config_dlg
import db_grid
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import table_config

sqlite_quoter = getdata.get_obj_quoter_func(mg.DBE_SQLITE)
dd = getdata.get_dd()
cc = config_dlg.get_cc()


class DataSelectDlg(wx.Dialog):
    def __init__(self, parent, proj_name):
        debug = False
        title = _("Data in \"%s\" Project") % proj_name
        wx.Dialog.__init__(self, parent=parent, title=title, 
                           style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        bx_existing = wx.StaticBox(self.panel, -1, _("Existing data tables"))
        bx_new = wx.StaticBox(self.panel, -1, "")
        wx.BeginBusyCursor()
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        lbl_choose = wx.StaticText(self.panel, -1, 
                                  _("Choose an existing data table ..."), 
                                  size=(480,20))
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=proj_name)
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        # set up self.drop_dbs and self.drop_tbls
        self.drop_dbs, self.drop_tbls = getdata.get_data_dropdowns(self, 
                                            self.panel, proj_dic["default_dbs"])
        self.chk_readonly = wx.CheckBox(self.panel, -1, _("Read Only"))
        self.chk_readonly.SetValue(True)
        self.btn_delete = wx.Button(self.panel, -1, _("Delete"))
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_design = wx.Button(self.panel, -1, _("Design"))
        self.btn_design.Bind(wx.EVT_BUTTON, self.on_design)
        btn_open = wx.Button(self.panel, wx.ID_OPEN)
        btn_open.Bind(wx.EVT_BUTTON, self.on_open)
        szr_data = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=5)  
        szr_data.AddGrowableCol(1, 1)      
        lbl_dbs = wx.StaticText(self.panel, -1, _("Databases:"))
        lbl_dbs.SetFont(lblfont)        
        szr_data.Add(lbl_dbs, 0, wx.RIGHT, 5)
        szr_data.Add(self.drop_dbs, 1, wx.GROW)     
        lbl_tbls = wx.StaticText(self.panel, -1, _("Data tables:"))
        lbl_tbls.SetFont(lblfont)
        szr_data.Add(lbl_tbls, 0, wx.RIGHT, 5)
        szr_data.Add(self.drop_tbls, 1, wx.GROW)        
        szr_existing_bottom = wx.FlexGridSizer(rows=1, cols=4, hgap=5, vgap=50)
        szr_existing_bottom.AddGrowableCol(2,2) # idx, propn
        szr_existing_bottom.Add(self.btn_delete, 0, wx.RIGHT, 10)
        szr_existing_bottom.Add(self.btn_design, 0)
        szr_existing_bottom.Add(self.chk_readonly, 0, wx.ALIGN_RIGHT)
        szr_existing_bottom.Add(btn_open, 0, wx.ALIGN_RIGHT)
        szr_existing = wx.StaticBoxSizer(bx_existing, wx.VERTICAL)
        szr_existing.Add(szr_data, 0, wx.GROW|wx.ALL, 10)
        szr_existing.Add(szr_existing_bottom, 0, wx.GROW|wx.ALL, 10)
        szr_new = wx.StaticBoxSizer(bx_new, wx.HORIZONTAL)
        lbl_new = wx.StaticText(self.panel, -1, _("... or add a new data table "
                                                "to the default SOFA database"))
        btn_new = wx.Button(self.panel, wx.ID_NEW)
        btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        szr_new.Add(lbl_new, 1, wx.GROW|wx.ALL, 10)
        szr_new.Add(btn_new, 0, wx.ALL, 10)
        self.lbl_feedback = wx.StaticText(self.panel, -1, u"")
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns.Add(self.lbl_feedback, 1, wx.GROW|wx.ALL, 10)
        self.szr_btns.Add(btn_close, 0)
        szr_bottom.Add(self.szr_btns, 1, wx.GROW|wx.RIGHT, 15) # align with New        
        self.szr_main.Add(lbl_choose, 0, wx.ALL, 10)
        self.szr_main.Add(szr_existing, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 
                          10)
        self.szr_main.Add(szr_new, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr_main.Add(szr_bottom, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.ctrl_enablement()
        lib.safe_end_cursor()

    def add_feedback(self, feedback):
        self.lbl_feedback.SetLabel(feedback)
        wx.Yield()
    
    def ctrl_enablement(self):
        """
        Can only design tables in the default SOFA database.
        Only need read only option if outside the default sofa database.
        """
        sofa_db = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB)
        self.btn_design.Enable(sofa_db)
        delete_enable = (sofa_db and dd.tbl != mg.DEMO_TBL)
        self.btn_delete.Enable(delete_enable)
        self.chk_readonly.Enable(not sofa_db)
        
    def on_database_sel(self, event):
        getdata.refresh_db_dets(self)
        self.reset_tbl_dropdown()
        self.ctrl_enablement()
        
    def reset_tbl_dropdown(self):
        "Set tables dropdown items and select item according to dd.tbl"
        getdata.setup_drop_tbls(self.drop_tbls)
    
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        getdata.refresh_tbl_dets(self)
        self.ctrl_enablement()

    def on_open(self, event):
        ""
        if not dd.has_unique:
            msg = _("Table \"%s\" cannot be opened because it lacks a unique "
                    "index")
            wx.MessageBox(msg % dd.tbl) # needed for caching even if read only
        else:
            obj_quoter = getdata.get_obj_quoter_func(dd.dbe)
            SQL_get_count = u"""SELECT COUNT(*) FROM %s """ % obj_quoter(dd.tbl)
            dd.cur.execute(SQL_get_count)
            rows_n = dd.cur.fetchone()[0]
            if rows_n > 200000: # fast enough as long as column resizing is off
                if wx.MessageBox(_("This table has %s rows. "
                                   "Do you wish to open it?") % rows_n, 
                                   caption=_("LONG REPORT"), 
                                   style=wx.YES_NO) == wx.NO:
                    return
            wx.BeginBusyCursor()
            readonly = False
            if self.chk_readonly.IsEnabled():
                readonly = self.chk_readonly.IsChecked()
            set_col_widths = True if rows_n < 1000 else False
            dlg = db_grid.TblEditor(self, self.var_labels, self.var_notes, 
                                    self.var_types, self.val_dics, readonly, 
                                    set_col_widths=set_col_widths)
            lib.safe_end_cursor()
            dlg.ShowModal()
        event.Skip()
    
    def get_gen_fld_type(self, fld_type):
        """
        Get general field type from specific.
        """
        if fld_type.lower() in dbe_sqlite.NUMERIC_TYPES:
            gen_fld_type = mg.FLD_TYPE_NUMERIC
        elif fld_type.lower() in dbe_sqlite.DATE_TYPES:
            gen_fld_type = mg.FLD_TYPE_DATE
        else:
            gen_fld_type = mg.FLD_TYPE_STRING
        return gen_fld_type
    
    def get_tbl_config(self, tbl_name):
        """
        Get ordered list of field names and field types for named table.
        "Numeric", "Date", "Text".
        Only works for an SQLite database (should be the default one).
        """
        debug = False
        obj_quoter = getdata.get_obj_quoter_func(dd.dbe)
        dd.con.commit()
        dd.cur.execute(u"PRAGMA table_info(%s)" % obj_quoter(tbl_name))
        config = dd.cur.fetchall()
        if debug: print(config)
        table_config = [(x[1], self.get_gen_fld_type(fld_type=x[2])) for x in
                         config]
        return table_config
    
    def on_delete(self, event):
        """
        Delete selected table (giving user choice to back out).
        """
        if wx.MessageBox(_("Do you wish to delete \"%s\"?") % dd.tbl, 
                           caption=_("DELETE"), 
                           style=wx.YES_NO|wx.NO_DEFAULT) == wx.YES:
            obj_quoter = getdata.get_obj_quoter_func(dd.dbe)
            dd.cur.execute("DROP TABLE IF EXISTS %s" % obj_quoter(dd.tbl))
            dd.con.commit()
        dd.set_db(dd.db) # refresh tbls downwards
        self.reset_tbl_dropdown()
        self.ctrl_enablement()
        event.Skip()

    def on_design(self, event):
        """
        Open table config which reads values for the table.
        NB only enabled (for either viewing or editing) for the default SQLite 
            database.
        """
        debug = False
        readonly = False # only read only if the demo table
        if dd.tbl == mg.DEMO_TBL and not readonly:
            wx.MessageBox(_("The design of the default SOFA table cannot be "
                            "changed"))
            self.chk_readonly.SetValue(True)
            readonly = True
        tbl_name_lst = [dd.tbl,]
        data = self.get_tbl_config(dd.tbl)
        if debug: print("Initial table config data: %s" % data)
        config_data = []     
        dlgConfig = table_config.ConfigTableDlg(self.var_labels, self.val_dics, 
                                                tbl_name_lst, data, config_data, 
                                                readonly, new=False)
        ret = dlgConfig.ShowModal()
        if ret == mg.RET_CHANGED_DESIGN and not readonly:
            # update tbl dropdown
            self.reset_tbl_dropdown()
    
    def on_new(self, event):
        """
        Get table name (must be unique etc), create empty table in SOFA Default 
            database with that name, and start off with 5 fields ready to 
            rename.  Must be able to add fields, and rename fields.
        """
        debug = False
        try:
            con = dbe_sqlite.get_con(dd.con_dets, mg.SOFA_DB)
            # not dd.con because we may fail making a new one and need to 
            # stick with the original
            con.close()
        except Exception:
            wx.MessageBox(_("The current project does not include a link to "
                            "the default SOFA database so a new table cannot "
                            "be made there."))
            return
        tbl_name_lst = [] # not quite worth using validator mechanism ;-)
        data = [("sofa_id", "Numeric"),
                ("var001", "Numeric"),
                ]
        config_data = []
        dlgConfig = table_config.ConfigTableDlg(self.var_labels, self.val_dics, 
                                                tbl_name_lst, data, config_data, 
                                                readonly=False, new=True)
        ret = dlgConfig.ShowModal()
        if ret != mg.RET_CHANGED_DESIGN:
            event.Skip()
            return
        # update tbl dropdown
        self.reset_tbl_dropdown()
        # open data          
        wx.BeginBusyCursor()
        readonly = False
        dlg = db_grid.TblEditor(self, self.var_labels, self.var_notes, 
                                self.var_types, self.val_dics, readonly)
        lib.safe_end_cursor()
        dlg.ShowModal()
        self.ctrl_enablement()
        event.Skip()
    
    def on_close(self, event):
        self.Destroy()         
