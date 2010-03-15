from __future__ import print_function
import pprint
import pysqlite2
import sys
import wx

import my_globals as mg
import config_globals
import db_grid
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import projects
import table_config

sqlite_quoter = getdata.get_obj_quoter_func(mg.DBE_SQLITE)


class DataSelectDlg(wx.Dialog):
    def __init__(self, parent, proj_name):
        debug = False
        title = _("Data in \"%s\" Project") % proj_name
        wx.Dialog.__init__(self, parent=parent, title=title, 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        wx.BeginBusyCursor()
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  _("Choose an existing data table ..."))
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=proj_name)
        self.fil_var_dets = proj_dic["fil_var_dets"]
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(self.fil_var_dets)
        # which dbe? If a default, use that.  If not, use project default.
        if mg.DBE_DEFAULT:
            self.dbe = mg.DBE_DEFAULT
        else:
            self.dbe = proj_dic["default_dbe"]
        try:
            self.con_dets = proj_dic["con_dets"]
        except KeyError, e:
            wx.EndBusyCursor()
            msg = (u"The \"%s\" project uses the old " % proj_name +
                   u"conn_dets label rather than the new con_dets label. "
                   u" Please fix and try again.")
            wx.MessageBox(msg)
            raise Exception, msg # for debugging
            self.Destroy()
            return
        if debug: print(self.con_dets)
        self.default_dbs = proj_dic["default_dbs"] \
            if proj_dic["default_dbs"] else {}
        self.default_tbls = proj_dic["default_tbls"] \
            if proj_dic["default_tbls"] else {}
        # Try to use database and tables most recently used in session for this 
        # database engine.
        getdata.refresh_default_dbs_tbls(self.dbe, self.default_dbs, 
                                         self.default_tbls)
        # get various db settings
        dbdetsobj = getdata.get_db_dets_obj(self.dbe, self.default_dbs, 
                        self.default_tbls, self.con_dets)
        try:
            (self.con, self.cur, self.dbs, self.tbls, self.flds, 
                self.has_unique, self.idxs) = dbdetsobj.get_db_dets()
        except Exception, e:
            wx.EndBusyCursor()
            wx.MessageBox(_("Unable to connect to data as defined in " 
                "project %s.  Please check your settings." % proj_name))
            raise Exception, unicode(e) # for debugging
            self.Destroy()
            return
        # set up self.drop_dbs and self.drop_tbls
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        self.drop_dbs, self.drop_tbls = \
            getdata.get_data_dropdowns(self, self.panel, self.dbe, 
                            self.default_dbs, self.default_tbls, self.con_dets, 
                            self.dbs, self.db, self.tbls, self.tbl)
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
        lbl_make_new = wx.StaticText(self.panel, -1, 
                                   _("... or make a new data table"))
        btn_make_new = wx.Button(self.panel, wx.ID_NEW)
        btn_make_new.Bind(wx.EVT_BUTTON, self.on_new_click)
        szr_new.Add(lbl_make_new, 1, wx.GROW|wx.ALL, 10)
        szr_new.Add(btn_make_new, 0, wx.ALL, 10)
        self.lblFeedback = wx.StaticText(self.panel, -1, "")
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns.Add(self.lblFeedback, 1, wx.GROW|wx.ALL, 10)
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
        wx.EndBusyCursor()

    def add_feedback(self, feedback):
        self.lblFeedback.SetLabel(feedback)
        wx.Yield()
    
    def btn_enablement(self):
        """
        Can only open dialog for design details for tables in the default SOFA 
            database (except for the default one).
        """
        extra_enable = (self.dbe == mg.DBE_SQLITE 
                        and self.db == mg.SOFA_DEFAULT_DB
                        and self.tbl != mg.SOFA_DEFAULT_TBL)
        self.btn_delete.Enable(extra_enable)
        self.btn_design.Enable(extra_enable)
        
    def on_database_sel(self, event):
        (self.dbe, self.db, self.con, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.refresh_db_dets(self)
        self.reset_tbl_dropdown()
        self.btn_enablement()
        
    def reset_tbl_dropdown(self):
        "Set tables dropdown items and select item according to self.tbl"
        getdata.setup_drop_tbls(self.drop_tbls, self.dbe, self.db, self.tbls, 
                                self.tbl)
    
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.refresh_tbl_dets(self)
        self.btn_enablement()

    def on_open(self, event):
        ""
        if not self.has_unique:
            msg = _("Table \"%s\" cannot be opened because it " \
                   "lacks a unique index")
            wx.MessageBox(msg % self.tbl) # needed for caching even if read only
        else:
            obj_quoter = getdata.get_obj_quoter_func(self.dbe)
            s = "SELECT COUNT(*) FROM %s" % obj_quoter(self.tbl)
            self.cur.execute(s)
            n_rows = self.cur.fetchone()[0]
            if n_rows > 20000:
                if wx.MessageBox(_("This table has %s rows. "
                                   "Do you wish to open it?") % n_rows, 
                                   caption=_("LONG REPORT"), 
                                   style=wx.YES_NO) == wx.NO:
                    return
            wx.BeginBusyCursor()
            readonly = self.chk_readonly.IsChecked()
            dlg = db_grid.TblEditor(self, self.dbe, self.con, self.cur, self.db, 
                                    self.tbl, self.flds, self.var_labels, 
                                    self.var_notes, self.var_types,
                                    self.val_dics, self.fil_var_dets, self.idxs, 
                                    readonly)
            wx.EndBusyCursor()
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
        obj_quoter = getdata.get_obj_quoter_func(self.dbe)
        self.con.commit()
        self.cur.execute(u"PRAGMA table_info(%s)" % obj_quoter(tbl_name))
        config = self.cur.fetchall()
        if debug: print(config)
        table_config = [(x[1], self._get_gen_fld_type(fld_type=x[2])) for x in
                         config]
        return table_config
    
    def on_delete(self, event):
        """
        Delete selected table (giving user choice to back out).
        """
        if wx.MessageBox(_("Do you wish to delete \"%s\"?") % self.tbl, 
                           caption=_("DELETE"), 
                           style=wx.YES_NO|wx.NO_DEFAULT) == wx.YES:
            obj_quoter = getdata.get_obj_quoter_func(self.dbe)
            self.cur.execute("DROP TABLE IF EXISTS %s" % obj_quoter(self.tbl))
            self.con.commit()
        dbe = mg.DBE_SQLITE
        dbdetsobj = getdata.get_db_dets_obj(dbe, self.default_dbs, 
                                            self.default_tbls, self.con_dets, 
                                            mg.SOFA_DEFAULT_DB)
        (self.con, self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
         self.idxs) = dbdetsobj.get_db_dets()
        # update tbl dropdown
        self.tbl = self.tbls[0]
        self.reset_tbl_dropdown()
        self.btn_enablement()
        event.Skip()
    
    def make_strict_typing_tbl(self, oth_name_types, config_data):
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
        self.cur.execute(SQL_drop_tmp_tbl)
        # create table with strictly-typed fields
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=True,
                                                        inc_sofa_id=False)
        SQL_make_tmp_tbl = u"CREATE TABLE %s (%s) " % (tmp_name, 
                                                       create_fld_clause)
        if debug: print(SQL_make_tmp_tbl)
        self.cur.execute(SQL_make_tmp_tbl)
        # unable to use CREATE ... AS SELECT at same time as defining table.
        # attempt to insert data into strictly-typed fields.
        select_fld_clause = getdata.make_flds_clause(config_data)
        SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (tmp_name, 
                                    select_fld_clause, sqlite_quoter(self.tbl))
        if debug: print(SQL_insert_all)
        self.cur.execute(SQL_insert_all)
    
    def make_redesigned_tbl(self, oth_name_types, config_data):
        """
        Make new table with all the fields from the tmp table (which doesn't 
            have the sofa_id field) plus the sofa_id field.
        config_data -- dict with TBL_FLD_NAME, TBL_FLD_NAME_ORIG, TBL_FLD_TYPE,
            TBL_FLD_TYPE_ORIG. Includes row with sofa_id.
        """
        debug = False
        tmp_name = sqlite_quoter(mg.TMP_TBL_NAME)
        final_name = sqlite_quoter(self.tbl)
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=False,
                                                        inc_sofa_id=True)
        SQL_drop_orig = u"DROP TABLE %s" % final_name
        self.cur.execute(SQL_drop_orig)
        if debug: print(create_fld_clause)
        SQL_make_redesigned_tbl = u"CREATE TABLE %s (%s)" % (final_name, 
                                                             create_fld_clause)
        self.cur.execute(SQL_make_redesigned_tbl)
        oth_names = [sqlite_quoter(x[0]) for x in oth_name_types]
        null_plus_oth_flds = u" NULL, " + u", ".join(oth_names)
        SQL_insert_all = u"INSERT INTO %s SELECT %s FROM %s""" % (final_name, 
                                                            null_plus_oth_flds, 
                                                            tmp_name)
        if debug: print(SQL_insert_all)
        self.cur.execute(SQL_insert_all)
        SQL_drop_tmp = u"DROP TABLE %s" % tmp_name
        self.cur.execute(SQL_drop_tmp)
        self.con.commit()

    def on_design(self, event):
        """
        Open table config which reads values for the table.
        NB only enabled (for either viewing or editing) for the default SQLite 
            database.
        """
        debug = False
        tbl_name_lst = [self.tbl,]
        data = self._get_tbl_config(self.tbl)
        if debug: print("Initial table config data: %s" % data)
        config_data = []
        readonly = self.chk_readonly.IsChecked()
        dlgConfig = table_config.ConfigTableDlg(tbl_name_lst, data, config_data, 
                                                readonly)
        ret = dlgConfig.ShowModal()
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
            self.tbl = tbl_name_lst[0]
            # other (i.e. not the sofa_id) field details
            oth_name_types = getdata.get_oth_name_types(config_data)
            if debug: print("oth_name_types to feed into " 
                            "make_strict_typing_tbl %s" % oth_name_types)
            try:
                self.make_strict_typing_tbl(oth_name_types, config_data)
            except pysqlite2.dbapi2.IntegrityError, e:
                if debug: print(unicode(e))
                wx.MessageBox(_("Unable to modify table.  Some data does not "
                                "match the column type.  Please edit and try "
                                "again.\n\nOriginal error: %s" % e))
                SQL_drop_tmp_tbl = "DROP TABLE IF EXISTS %s" % \
                                sqlite_quoter(mg.TMP_TBL_NAME)
                self.cur.execute(SQL_drop_tmp_tbl)
                self.con.commit()
                return
            self.make_redesigned_tbl(oth_name_types, config_data)
            # refresh fld details etc
            self.tbl, self.flds, self.has_unique, self.idxs = \
                getdata.refresh_tbl_dets(self)
    
    def on_new_click(self, event):
        """
        Get table name (must be unique etc), create empty table in SOFA Default 
            database with that name, and start off with 5 fields ready to 
            rename.  Must be able to add fields, and rename fields.
        """
        debug = False
        try:
            self.con = dbe_sqlite.get_con(self.con_dets, mg.SOFA_DEFAULT_DB)
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
        dlgConfig = table_config.ConfigTableDlg(tbl_name_lst, data, config_data)
        ret = dlgConfig.ShowModal()
        if ret != wx.ID_OK:
            event.Skip()
            return
        # Make new table.  Include unique index on special field prepended as
        # with data imported.
        # Only interested in SQLite when making a fresh SOFA table
        # Use check constraints to enforce data type (based on user-defined 
        # functions)
        self.cur = self.con.cursor()
        tbl_name = tbl_name_lst[0]        
        oth_name_types = getdata.get_oth_name_types(config_data)
        if debug: print(config_data)
        getdata.make_sofa_tbl(self.con, self.cur, tbl_name, oth_name_types)
        # prepare to connect to the newly created table
        self.tbl = tbl_name
        dbe = mg.DBE_SQLITE
        dbdetsobj = getdata.get_db_dets_obj(dbe, self.default_dbs, 
                                        self.default_tbls, self.con_dets, 
                                        mg.SOFA_DEFAULT_DB, self.tbl)
        (self.con, self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
            self.idxs) = dbdetsobj.get_db_dets()
        # update tbl dropdown
        self.reset_tbl_dropdown()
        # explain to user
        wx.MessageBox(_("Your new table has been added to the default SOFA "
                        "database"))
        # open data          
        wx.BeginBusyCursor()
        readonly = False
        dlg = db_grid.TblEditor(self, dbe, self.con, self.cur, 
                                mg.SOFA_DEFAULT_DB, self.tbl, self.flds, 
                                self.var_labels, self.var_notes, self.var_types,
                                self.val_dics, self.fil_var_dets, self.idxs, 
                                readonly)
        wx.EndBusyCursor()
        dlg.ShowModal()
        self.btn_enablement()
        event.Skip()
    
    def on_close(self, event):
        debug = False
        mg.DBE_DEFAULT = self.dbe
        mg.DB_DEFAULTS[self.dbe] = self.db
        mg.TBL_DEFAULTS[self.dbe] = self.tbl
        if debug:
            print("For %s, default DB saved as: %s and default table saved as: "
                  "%s" % (self.dbe, self.db, self.tbl))
        self.Destroy()
         