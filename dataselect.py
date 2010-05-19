from __future__ import print_function
import pprint
import sqlite3 as sqlite
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
                           style=wx.CAPTION|wx.SYSTEM_MENU, pos=(300,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        wx.BeginBusyCursor()
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
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
        szr_data.Add(self.drop_dbs, 0)     
        lbl_tbls = wx.StaticText(self.panel, -1, _("Data tables:"))
        lbl_tbls.SetFont(lblfont)
        szr_data.Add(lbl_tbls, 0, wx.RIGHT, 5)
        szr_data.Add(self.drop_tbls, 1)        
        szr_existing_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_existing_bottom.Add(self.chk_readonly, 1, wx.TOP|wx.LEFT, 5)
        szr_existing_bottom.Add(self.btn_delete, 0, wx.RIGHT, 10)
        szr_existing_bottom.Add(self.btn_design, 0, wx.RIGHT, 10)
        szr_existing_bottom.Add(btn_open, 0)
        bx_existing = wx.StaticBox(self.panel, -1, _("Existing data tables"))
        szr_existing = wx.StaticBoxSizer(bx_existing, wx.VERTICAL)
        szr_existing.Add(szr_data, 0, wx.GROW|wx.ALL, 10)
        szr_existing.Add(szr_existing_bottom, 0, wx.GROW|wx.ALL, 10)        
        bx_new = wx.StaticBox(self.panel, -1, "")
        szr_new = wx.StaticBoxSizer(bx_new, wx.HORIZONTAL)
        lbl_make_new = wx.StaticText(self.panel, -1, _("... or add a new data "
                                        "table to the default SOFA database"))
        btn_make_new = wx.Button(self.panel, wx.ID_NEW)
        btn_make_new.Bind(wx.EVT_BUTTON, self.on_new_click)
        szr_new.Add(lbl_make_new, 1, wx.GROW|wx.ALL, 10)
        szr_new.Add(btn_make_new, 0, wx.ALL, 10)
        self.lbl_feedback = wx.StaticText(self.panel, -1, "")
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns.Add(self.lbl_feedback, 1, wx.GROW|wx.ALL, 10)
        self.szr_btns.Add(btn_close, 0, wx.RIGHT)
        szr_bottom.Add(self.szr_btns, 1, wx.GROW|wx.RIGHT, 15) # align with New        
        self.szr_main.Add(lblChoose, 0, wx.ALL, 10)
        self.szr_main.Add(szr_existing, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 
                          10)
        self.szr_main.Add(szr_new, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr_main.Add(szr_bottom, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.btn_enablement()
        lib.safe_end_cursor()

    def add_feedback(self, feedback):
        self.lbl_feedback.SetLabel(feedback)
        wx.Yield()
    
    def btn_enablement(self):
        """
        Can only open dialog for design details for tables in the default SOFA 
            database.
        """
        design_enable = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB)
        self.btn_design.Enable(design_enable)
        delete_enable = (dd.dbe == mg.DBE_SQLITE and dd.db == mg.SOFA_DB 
                         and dd.tbl != mg.DEMO_TBL)
        self.btn_delete.Enable(delete_enable)
        
    def on_database_sel(self, event):
        getdata.refresh_db_dets(self)
        self.reset_tbl_dropdown()
        self.btn_enablement()
        
    def reset_tbl_dropdown(self):
        "Set tables dropdown items and select item according to dd.tbl"
        getdata.setup_drop_tbls(self.drop_tbls)
    
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        getdata.refresh_tbl_dets(self)
        self.btn_enablement()

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
            readonly = self.chk_readonly.IsChecked()
            set_col_widths = True if rows_n < 1000 else False
            dlg = db_grid.TblEditor(self, self.var_labels, self.var_notes, 
                                    self.var_types, self.val_dics, readonly, 
                                    set_col_widths=set_col_widths)
            lib.safe_end_cursor()
            dlg.ShowModal()
        event.Skip()
    
    def _get_gen_fld_type(self, fld_type):
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
    
    def _get_tbl_config(self, tbl_name):
        """
        Get ordered list of field names and field types for named table.
        "Numeric", "Date", "String".
        Only works for an SQLite database (should be the default one).
        """
        debug = False
        obj_quoter = getdata.get_obj_quoter_func(dd.dbe)
        dd.con.commit()
        dd.cur.execute(u"PRAGMA table_info(%s)" % obj_quoter(tbl_name))
        config = dd.cur.fetchall()
        if debug: print(config)
        table_config = [(x[1], self._get_gen_fld_type(fld_type=x[2])) for x in
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
        self.btn_enablement()
        event.Skip()
    
    def wipe_orig_tbl(self, orig_tbl_name):
        SQL_drop_orig = u"DROP TABLE IF EXISTS %s" % \
            sqlite_quoter(orig_tbl_name)
        dd.con.commit()
        dd.cur.execute(SQL_drop_orig)
        dd.con.commit()
    
    def make_strict_typing_tbl(self, orig_tbl_name, oth_name_types, 
                               config_data):
        """
        Make table for purpose of forcing all data into strict type fields.  Not
            necessary to check sofa_id field (autoincremented integer) so not 
            included.
        Make table with all the fields apart from the sofa_id.  The fields
            should be set with strict check constraints so that, even though the
            table is SQLite, it cannot accept inappropriate data.
        Try to insert into strict table all fields in original table (apart from 
            the sofa_id which will be autoincremented from scratch).
        oth_name_types - name, type tuples excluding sofa_id.
        config_data -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
            TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
        """
        debug = False
        tmp_name = sqlite_quoter(mg.TMP_TBL_NAME)
        SQL_drop_tmp_tbl = u"DROP TABLE IF EXISTS %s" % tmp_name
        dd.cur.execute(SQL_drop_tmp_tbl)
        # create table with strictly-typed fields
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=True,
                                                        inc_sofa_id=False)
        SQL_make_tmp_tbl = u"CREATE TABLE %s (%s) " % (tmp_name, 
                                                       create_fld_clause)
        if debug: print(SQL_make_tmp_tbl)
        dd.cur.execute(SQL_make_tmp_tbl)
        # unable to use CREATE ... AS SELECT at same time as defining table.
        # attempt to insert data into strictly-typed fields.
        select_fld_clause = getdata.make_flds_clause(config_data)
        SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (tmp_name, 
                                                select_fld_clause, 
                                                sqlite_quoter(orig_tbl_name))
        if debug: print(SQL_insert_all)
        dd.cur.execute(SQL_insert_all)
        dd.con.commit()
    
    def make_redesigned_tbl(self, final_name, oth_name_types, config_data):
        """
        Make new table with all the fields from the tmp table (which doesn't 
            have the sofa_id field) plus the sofa_id field.
        config_data -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
            TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
        """
        debug = False
        tmp_name = sqlite_quoter(mg.TMP_TBL_NAME)
        final_name = sqlite_quoter(final_name)
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=False,
                                                        inc_sofa_id=True)
        SQL_drop_orig = u"DROP TABLE IF EXISTS %s" % final_name
        dd.con.commit()
        dd.cur.execute(SQL_drop_orig)
        dd.con.commit()
        if debug: print(create_fld_clause)
        SQL_make_redesigned_tbl = u"CREATE TABLE %s (%s)" % (final_name, 
                                                             create_fld_clause)
        dd.cur.execute(SQL_make_redesigned_tbl)
        oth_names = [sqlite_quoter(x[0]) for x in oth_name_types]
        null_plus_oth_flds = u" NULL, " + u", ".join(oth_names)
        SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (final_name, 
                                                null_plus_oth_flds, tmp_name)
        if debug: print(SQL_insert_all)
        dd.cur.execute(SQL_insert_all)
        SQL_drop_tmp = u"DROP TABLE %s" % tmp_name
        dd.cur.execute(SQL_drop_tmp)
        dd.con.commit()

    def on_design(self, event):
        """
        Open table config which reads values for the table.
        NB only enabled (for either viewing or editing) for the default SQLite 
            database.
        """
        debug = False
        readonly = self.chk_readonly.IsChecked()
        if dd.tbl == mg.DEMO_TBL and not readonly:
            wx.MessageBox(_("The design of the default SOFA table can only "
                            "be opened as read only"))
            self.chk_readonly.SetValue(True)
            readonly = True
        tbl_name_lst = [dd.tbl,]
        data = self._get_tbl_config(dd.tbl)
        if debug: print("Initial table config data: %s" % data)
        config_data = []     
        con = dbe_sqlite.get_con(dd.con_dets, dd.db)
        con.row_factory = dbe_sqlite.Row # see pysqlite usage-guide.txt
        cur_dict = con.cursor()
        dlgConfig = table_config.ConfigTableDlg(cur_dict, self.var_labels, 
                                self.val_dics, tbl_name_lst, data, config_data, 
                                readonly, new=False)
        ret = dlgConfig.ShowModal()
        cur_dict.close()
        con.close()
        if debug:
            print("Config data coming back:") 
            pprint.pprint(config_data)
        if ret == wx.ID_OK and not readonly:
            """
            Make temp table, with strict type enforcement for all fields.  
            Copy across all fields which remain in the original table (possibly 
                with new names and data types) plus add in all the new fields.
            NB SOFA_ID must be autoincrement.
            If any conversion errors (e.g. trying to change a field which 
                currently contains "fred" to a numeric field) abort 
                reconfiguration (with encouragement to fix source data or change
                type to string).
            Assuming reconfiguration is OK, create final table with original 
                table's name, without strict typing, but with an auto-
                incrementing and indexed SOFA_ID.
            Don't apply check constraints based on user-defined functions to
                final table as SQLite Database Browser can't open the database
                anymore.
            """
            orig_tbl_name = dd.tbl
            # other (i.e. not the sofa_id) field details
            oth_name_types = getdata.get_oth_name_types(config_data)
            if debug: print("oth_name_types to feed into " 
                            "make_strict_typing_tbl %s" % oth_name_types)
            try:
                self.make_strict_typing_tbl(orig_tbl_name, oth_name_types, 
                                            config_data)
            except sqlite.IntegrityError, e:
                #except pysqlite2.dbapi2.IntegrityError, e:
                if debug: print(unicode(e))
                wx.MessageBox(_("Unable to modify table.  Some data does not "
                                "match the column type.  Please edit and try "
                                "again.\n\nOriginal error: %s" % e))
                SQL_drop_tmp_tbl = "DROP TABLE IF EXISTS %s" % \
                                                sqlite_quoter(mg.TMP_TBL_NAME)
                dd.cur.execute(SQL_drop_tmp_tbl)
                dd.con.commit()
                return
            self.wipe_orig_tbl(orig_tbl_name)
            final_name = tbl_name_lst[0] # may have been renamed
            self.make_redesigned_tbl(final_name, oth_name_types, config_data)
            dd.set_db(dd.db, tbl=final_name) # refresh tbls downwards
            # update tbl dropdown
            self.reset_tbl_dropdown()
    
    def on_new_click(self, event):
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
        con.row_factory = dbe_sqlite.Row #see pysqlite usage-guide.txt
        cur_dict = con.cursor()
        dlgConfig = table_config.ConfigTableDlg(cur_dict, self.var_labels, 
                                                self.val_dics, tbl_name_lst, 
                                                data, config_data, new=True)
        ret = dlgConfig.ShowModal()
        cur_dict.close()
        con.close()
        if ret != wx.ID_OK:
            event.Skip()
            return
        # Make new table.  Include unique index on special field prepended as
        # with data imported.
        # Only interested in SQLite when making a fresh SOFA table
        # Use check constraints to enforce data type (based on user-defined 
        # functions)
        tbl_name = tbl_name_lst[0]        
        oth_name_types = getdata.get_oth_name_types(config_data)
        if debug: print(config_data)
        con = dbe_sqlite.get_con(dd.con_dets, mg.SOFA_DB)
        cur = con.cursor() # the cursor for the default db
        getdata.make_sofa_tbl(con, cur, tbl_name, oth_name_types)
        # Prepare to connect to the newly created table.
        # dd.con and dd.cur can now be updated now we are committed to new table
        tbl = tbl_name
        dd.set_dbe(dbe=mg.DBE_SQLITE, db=mg.SOFA_DB, tbl=tbl)
        # update tbl dropdown
        self.reset_tbl_dropdown()
        # explain to user
        wx.MessageBox(_("Your new table has been added to the default SOFA "
                        "database"))
        # open data          
        wx.BeginBusyCursor()
        readonly = False
        dlg = db_grid.TblEditor(self, self.var_labels, self.var_notes, 
                                self.var_types, self.val_dics, readonly)
        lib.safe_end_cursor()
        dlg.ShowModal()
        self.btn_enablement()
        event.Skip()
    
    def on_close(self, event):
        self.Destroy()         
