from __future__ import print_function
import pprint
import pysqlite2
import sys
import wx

import my_globals
import config_globals
import db_grid
import dbe_plugins.dbe_sqlite as dbe_sqlite
import getdata
import projects
import table_config

sqlite_quoter = getdata.get_obj_quoter_func(my_globals.DBE_SQLITE)


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
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  _("Choose an existing data table ..."))
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=proj_name)
        self.fil_var_dets = proj_dic["fil_var_dets"]
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(self.fil_var_dets)
        # which dbe? If a default, use that.  If not, use project default.
        if my_globals.DBE_DEFAULT:
            self.dbe = my_globals.DBE_DEFAULT
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
                self.has_unique, self.idxs) = dbdetsobj.getDbDets()
        except Exception, e:
            wx.EndBusyCursor()
            wx.MessageBox(_("Unable to connect to data as defined in " 
                "project %s.  Please check your settings." % proj_name))
            raise Exception, unicode(e) # for debugging
            self.Destroy()
            return
        # set up self.dropDatabases and self.dropTables
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        self.dropDatabases, self.dropTables = \
            getdata.get_data_dropdowns(self, self.panel, self.dbe, 
                            self.default_dbs, self.default_tbls, self.con_dets, 
                            self.dbs, self.db, self.tbls, self.tbl)
        self.chkReadOnly = wx.CheckBox(self.panel, -1, _("Read Only"))
        self.chkReadOnly.SetValue(True)
        self.btnDelete = wx.Button(self.panel, -1, _("Delete"))
        self.btnDelete.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.btnDesign = wx.Button(self.panel, -1, _("Design"))
        self.btnDesign.Bind(wx.EVT_BUTTON, self.OnDesign)
        btnOpen = wx.Button(self.panel, wx.ID_OPEN)
        btnOpen.Bind(wx.EVT_BUTTON, self.OnOpen)
        szrData = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=5)  
        szrData.AddGrowableCol(1, 1)      
        lblDbs = wx.StaticText(self.panel, -1, _("Databases:"))
        lblDbs.SetFont(lblfont)        
        szrData.Add(lblDbs, 0, wx.RIGHT, 5)
        szrData.Add(self.dropDatabases, 0)     
        lblTbls = wx.StaticText(self.panel, -1, _("Data tables:"))
        lblTbls.SetFont(lblfont)
        szrData.Add(lblTbls, 0, wx.RIGHT, 5)
        szrData.Add(self.dropTables, 1)        
        szrExistingBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrExistingBottom.Add(self.chkReadOnly, 1, wx.TOP|wx.LEFT, 5)
        szrExistingBottom.Add(self.btnDelete, 0, wx.RIGHT, 10)
        szrExistingBottom.Add(self.btnDesign, 0, wx.RIGHT, 10)
        szrExistingBottom.Add(btnOpen, 0)
        bxExisting = wx.StaticBox(self.panel, -1, _("Existing data tables"))
        szrExisting = wx.StaticBoxSizer(bxExisting, wx.VERTICAL)
        szrExisting.Add(szrData, 0, wx.GROW|wx.ALL, 10)
        szrExisting.Add(szrExistingBottom, 0, wx.GROW|wx.ALL, 10)        
        bxNew = wx.StaticBox(self.panel, -1, "")
        szrNew = wx.StaticBoxSizer(bxNew, wx.HORIZONTAL)
        lblMakeNew = wx.StaticText(self.panel, -1, 
                                   _("... or make a new data table"))
        btnMakeNew = wx.Button(self.panel, wx.ID_NEW)
        btnMakeNew.Bind(wx.EVT_BUTTON, self.OnNewClick)
        szrNew.Add(lblMakeNew, 1, wx.GROW|wx.ALL, 10)
        szrNew.Add(btnMakeNew, 0, wx.ALL, 10)
        self.lblFeedback = wx.StaticText(self.panel, -1, "")
        btnClose = wx.Button(self.panel, wx.ID_CLOSE)
        btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szrBtns = wx.BoxSizer(wx.HORIZONTAL)
        self.szrBtns.Add(self.lblFeedback, 1, wx.GROW|wx.ALL, 10)
        self.szrBtns.Add(btnClose, 0, wx.RIGHT)
        szrBottom.Add(self.szrBtns, 1, wx.GROW|wx.RIGHT, 15) # align with New        
        self.szrMain.Add(lblChoose, 0, wx.ALL, 10)
        self.szrMain.Add(szrExisting, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 10)
        self.szrMain.Add(szrNew, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szrMain.Add(szrBottom, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.button_enablement()
        wx.EndBusyCursor()

    def AddFeedback(self, feedback):
        self.lblFeedback.SetLabel(feedback)
        wx.Yield()
    
    def button_enablement(self):
        """
        Can only open dialog for design details for tables in the default SOFA 
            database (except for the default one).
        """
        extra_enable = (self.dbe == my_globals.DBE_SQLITE
                        and self.db == my_globals.SOFA_DEFAULT_DB
                        and self.tbl != my_globals.SOFA_DEFAULT_TBL)
        self.btnDelete.Enable(extra_enable)
        self.btnDesign.Enable(extra_enable)
        
    def OnDatabaseSel(self, event):
        (self.dbe, self.db, self.con, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.refresh_db_dets(self)
        self.reset_tbl_dropdown()
        self.button_enablement()
        
    def reset_tbl_dropdown(self):
        "Set tables dropdown items and select item according to self.tbl"
        getdata.setup_drop_tbls(self.dropTables, self.dbe, self.db, self.tbls, 
                                self.tbl)
    
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.refresh_tbl_dets(self)
        self.button_enablement()

    def OnOpen(self, event):
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
            readonly = self.chkReadOnly.IsChecked()
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
            gen_fld_type = my_globals.FLD_TYPE_NUMERIC
        elif fld_type.lower() in dbe_sqlite.DATE_TYPES:
            gen_fld_type = my_globals.FLD_TYPE_DATE
        else:
            gen_fld_type = my_globals.FLD_TYPE_STRING
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
    
    def OnDelete(self, event):
        """
        Delete selected table (giving user choice to back out).
        """
        if wx.MessageBox(_("Do you wish to delete \"%s\"?") % self.tbl, 
                           caption=_("DELETE"), 
                           style=wx.YES_NO|wx.NO_DEFAULT) == wx.YES:
            obj_quoter = getdata.get_obj_quoter_func(self.dbe)
            self.cur.execute("DROP TABLE IF EXISTS %s" % obj_quoter(self.tbl))
            self.con.commit()
        dbe = my_globals.DBE_SQLITE
        dbdetsobj = getdata.get_db_dets_obj(dbe, self.default_dbs, 
                                            self.default_tbls, self.con_dets, 
                                            my_globals.SOFA_DEFAULT_DB)
        (self.con, self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
         self.idxs) = dbdetsobj.getDbDets()
        # update tbl dropdown
        self.tbl = self.tbls[0]
        self.reset_tbl_dropdown()
        self.button_enablement()
        event.Skip()
    
    def make_strict_typing_tbl(self, tbl_name, final_name_types, config_data):
        ""
        debug = False
        create_fld_clause = getdata.get_create_flds_txt(final_name_types, 
                                                        strict_typing=True)
        orig_new_names = getdata.get_oth_name_types(config_data)
        select_fld_clause = \
            getdata.make_select_renamed_flds_clause(orig_new_names)
        SQL_drop_tmp_tbl = "DROP TABLE IF EXISTS %s" % \
                                sqlite_quoter(my_globals.TMP_TBL_NAME)
        self.cur.execute(SQL_drop_tmp_tbl)
        SQL_make_tmp_tbl = "CREATE TABLE %s (%s) " % \
            (sqlite_quoter(my_globals.TMP_TBL_NAME), create_fld_clause)
        if debug: print(SQL_make_tmp_tbl)
        self.cur.execute(SQL_make_tmp_tbl)
        # unable to use CREATE ... AS SELECT at same time as defining table.
        SQL_insert_all = "INSERT INTO %s SELECT %s FROM %s""" % \
            (sqlite_quoter(my_globals.TMP_TBL_NAME), select_fld_clause,
             sqlite_quoter(self.tbl))
        if debug: print(SQL_insert_all)
        self.cur.execute(SQL_insert_all)
    
    def make_redesigned_tbl(self, oth_name_types, config_data):
        """
        Make new table with all the fields from the tmp table but the SOFA_ID
            field autoincrementing and an index.
        """
        debug = False
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
                                                        strict_typing=False)
        SQL_drop_orig = "DROP TABLE %s" % sqlite_quoter(self.tbl)
        self.cur.execute(SQL_drop_orig)
        SQL_make_redesigned_tbl = "CREATE TABLE %s (%s)" % \
                                    (sqlite_quoter(self.tbl), create_fld_clause)
        self.cur.execute(SQL_make_redesigned_tbl)
        SQL_insert_all = "INSERT INTO %s SELECT * FROM %s""" % \
                                        (sqlite_quoter(self.tbl), 
                                         sqlite_quoter(my_globals.TMP_TBL_NAME))
        if debug: print(SQL_insert_all)
        self.cur.execute(SQL_insert_all)
        SQL_drop_tmp = "DROP TABLE %s" % sqlite_quoter(my_globals.TMP_TBL_NAME)
        self.cur.execute(SQL_drop_tmp)
        self.con.commit()
    
    def OnDesign(self, event):
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
        readonly = self.chkReadOnly.IsChecked()
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
            try:
                self.make_strict_typing_tbl(self.tbl, oth_name_types, 
                                            config_data)
            except pysqlite2.dbapi2.IntegrityError, e:
                if debug: print(unicode(e))
                wx.MessageBox(_("Unable to modify table.  Some data does not "
                                "match the column type.  Please edit and try "
                                "again.\n\nOriginal error: %s" % e))
                SQL_drop_tmp_tbl = "DROP TABLE IF EXISTS %s" % \
                                sqlite_quoter(my_globals.TMP_TBL_NAME)
                self.cur.execute(SQL_drop_tmp_tbl)
                self.con.commit()
                return
            self.make_redesigned_tbl(oth_name_types, config_data)
            # refresh fld details etc
            self.tbl, self.flds, self.has_unique, self.idxs = \
                getdata.refresh_tbl_dets(self)
    
    def OnNewClick(self, event):
        """
        Get table name (must be unique etc), create empty table in SOFA Default 
            database with that name, and start off with 5 fields ready to 
            rename.  Must be able to add fields, and rename fields.
        """
        debug = False
        try:
            self.con = dbe_sqlite.get_con(self.con_dets, 
                                          my_globals.SOFA_DEFAULT_DB)
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
        dbe = my_globals.DBE_SQLITE
        dbdetsobj = getdata.get_db_dets_obj(dbe, self.default_dbs, 
                                        self.default_tbls, self.con_dets, 
                                        my_globals.SOFA_DEFAULT_DB, self.tbl)
        (self.con, self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
            self.idxs) = dbdetsobj.getDbDets()
        # update tbl dropdown
        self.reset_tbl_dropdown()
        # explain to user
        wx.MessageBox(_("Your new table has been added to the default SOFA "
                        "database"))
        # open data          
        wx.BeginBusyCursor()
        readonly = False
        dlg = db_grid.TblEditor(self, dbe, self.con, self.cur, 
                                my_globals.SOFA_DEFAULT_DB, self.tbl, self.flds, 
                                self.var_labels, self.var_notes, self.var_types,
                                self.val_dics, self.fil_var_dets, self.idxs, 
                                readonly)
        wx.EndBusyCursor()
        dlg.ShowModal()
        self.button_enablement()
        event.Skip()
    
    def OnClose(self, event):
        debug = False
        my_globals.DBE_DEFAULT = self.dbe
        my_globals.DB_DEFAULTS[self.dbe] = self.db
        my_globals.TBL_DEFAULTS[self.dbe] = self.tbl
        if debug:
            print("For %s, default DB saved as: %s and default table saved as: "
                  "%s" % (self.dbe, self.db, self.tbl))
        self.Destroy()    