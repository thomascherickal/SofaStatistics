import os
import util
import wx

import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import csv_importer
import projects

SCRIPT_PATH = util.get_script_path()
FILE_CSV = "csv"
FILE_UNKNOWN = "unknown"
FLD_NUMERIC = "numeric field"
FLD_DATETIME = "datetime field"
FLD_STRING = "string field"
# DATETIME is not a native storage class but can still be discovered
# via PRAGMA table_info()
FLD_TYPE_TO_SQLITE_TYPE = {
   FLD_NUMERIC: "REAL", 
   FLD_DATETIME: "DATETIME",
   FLD_STRING: "TEXT"}
VAL_NUMERIC = "numeric value"
VAL_DATETIME = "datetime value"
VAL_STRING = "string value"
VAL_EMPTY_STRING = "empty string value"
TMP_SQLITE_TBL = "tmptbl"


class MismatchException(Exception):
    def __init__(self, fld_name, details):
        self.fld_name = fld_name
        Exception.__init__(self, "Found data not matching expected " + \
                           "column type.\n\n%s" % details)

def GetDefaultDbDets():
    """
    Returns conn, cur, dbs, tbls, flds, has_unique, idxs from default
        SOFA SQLite database.
    """
    proj_dic = projects.GetProjSettingsDic(projects.SOFA_DEFAULT_PROJ)
    dbdetsobj = getdata.getDbDetsObj(dbe=getdata.DBE_SQLITE, 
                                     conn_dets=proj_dic["conn_dets"])
    conn, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.getDbDets()
    return conn, cur, dbs, tbls, flds, has_unique, idxs

def AssessSampleFld(sample_data, fld_name):
    """
    For individual values, if numeric, assume numeric, 
        if date, assume date, 
        if string, either an empty string or an ordinary string.
    For entire field sample, numeric if only contains numeric 
        and empty strings (could be missings).
    Date if only contains dates and empty strings (could be missings).
    String otherwise.   
    Return field type.
    """
    type_set = set()
    numeric_only_set = set([VAL_NUMERIC])
    numeric_or_empt_str_set = set([VAL_NUMERIC, VAL_EMPTY_STRING])
    datetime_only_set = set([VAL_DATETIME])
    datetime_or_empt_str_set = set([VAL_DATETIME, VAL_EMPTY_STRING])
    for row in sample_data:
        val = row[fld_name]
        if util.isNumeric(val):
            type_set.add(VAL_NUMERIC)
        else:
            boldatetime, time_obj = util.valid_datetime_str(val)
            if boldatetime:
                type_set.add(VAL_DATETIME)
            elif val == "":
                type_set.add(VAL_EMPTY_STRING)
            else:
                type_set.add(VAL_STRING)
    if type_set == numeric_only_set or \
            type_set == numeric_or_empt_str_set:
        fld_type = FLD_NUMERIC
    elif type_set == datetime_only_set or \
            type_set == datetime_or_empt_str_set:
        fld_type = FLD_DATETIME
    else:
        fld_type = FLD_STRING
    return fld_type

def ProcessVal(vals, row_num, row, fld_name, fld_types, check):
    """
    If checking, will validate and turn empty strings into nulls
        as required.
    If not checking (e.g. because a pre-tested sample) only do the
        empty string to null conversions.
    If all is OK, will add val to vals.  NB val will need to be internally 
        quoted unless it is a NULL. 
    If not, will raise an exception.
    """
    val = row[fld_name]
    fld_type = fld_types[fld_name]
    if not check:
        # still need to turn empty strings into NULLs for non string fields
        if fld_type in [FLD_NUMERIC, FLD_DATETIME] and val == "":
            val = "NULL"
    else:            
        bolOK_data = False
        boldatetime, time_obj = util.valid_datetime_str(val)
        if fld_type == FLD_NUMERIC:
            # must be numeric or empty string (which we'll turn to NULL)
            if util.isNumeric(val):
                bolOK_data = True
            elif val == "":
                bolOK_data = True
                val = "NULL"
        elif fld_type == FLD_DATETIME:
            # must be datetime or empty string (which we'll turn to NULL)
            if boldatetime:
                bolOK_data = True
                val = util.timeobj_to_datetime_str(timeobj)
            elif val == "":
                bolOK_data = True
                val = "NULL"
        elif fld_type == FLD_STRING:
            bolOK_data = True
        if not bolOK_data:
            raise MismatchException(fld_name,
                "Column: %s" % fld_name + \
                "\nRow: %s" % row_num + \
                "\nValue: \"%s\"" % val + \
                "\nExpected column type: %s" % fld_type)
    if val != "NULL":
        val = "\"%s\"" % val
    vals.append(val)
    
def AddRows(conn, cur, rows, fld_names, fld_types, check=False):
    """
    Add the rows of data, processing each cell as you go.
    If checking, will validate and turn empty strings into nulls
        as required.
    If not checking (e.g. because a pre-tested sample) only do the
        empty string to null conversions.
    TODO - insert multiple lines at once for performance
    """
    debug = False
    fld_names_clause = ", ".join([dbe_sqlite.quote_identifier(x) \
                                  for x in fld_names])
    for i, row in enumerate(rows):
        vals = []
        for fld_name in fld_names:
            row_num = i + 1
            ProcessVal(vals, row_num, row, fld_name, fld_types, check)
        # quoting must happen earlier so we can pass in NULL  
        fld_vals_clause = ", ".join(["%s" % x for x in vals])
        SQL_insert_row = "INSERT INTO %s " % TMP_SQLITE_TBL + \
            "(%s) VALUES(%s)" % (fld_names_clause, fld_vals_clause)
        if debug: print SQL_insert_row
        try:
            cur.execute(SQL_insert_row)
        except MismatchException, e:
            raise # keep this particular type of exception bubbling out
        except Exception, e:
            raise Exception, "Unable to add row %s. " % (i+1,) + \
                "Orig error: %s" % e
    conn.commit()

def AddToTmpTable(conn, cur, file_path, tbl_name, fld_names, fld_types, 
                  sample_data, remaining_data):
    """
    Create fresh disposable table in SQLite and insert data into it.
    """
    debug = False
    if debug:
        print "Field names are: %s" % fld_names
        print "Field types are: %s" % fld_types
        print "Sample data is: %s" % sample_data
    # create fresh disposable table to store data in.
    # give it a unique identifier field as well.
    fld_clause_items = ["sofa_id INTEGER PRIMARY KEY"]
    for fld_name in fld_names:
        fld_type = fld_types[fld_name]
        sqlite_type = FLD_TYPE_TO_SQLITE_TYPE[fld_type]
        fld_clause_items.append("%s %s" % \
                (dbe_sqlite.quote_identifier(fld_name), sqlite_type))
    fld_clause_items.append("UNIQUE(sofa_id)")
    fld_clause = ", ".join(fld_clause_items)
    try:
        conn.commit()
        cur.execute("VACUUM") # otherwise it doesn't always seem to have the 
            # latest data on which tables exist
        SQL_drop_disp_tbl = "DROP TABLE IF EXISTS %s" % TMP_SQLITE_TBL
        cur.execute(SQL_drop_disp_tbl)        
        conn.commit()
        if debug: print "Successfully dropped %s" % TMP_SQLITE_TBL
    except Exception, e:
        raise
    try:
        SQL_create_disp_tbl = "CREATE TABLE %s " % TMP_SQLITE_TBL + \
            " (%s)" % fld_clause
        if debug: print SQL_create_disp_tbl
        cur.execute(SQL_create_disp_tbl)
        conn.commit()
        if debug: print "Successfully created  %s" % TMP_SQLITE_TBL
    except Exception, e:
        raise
    try:
        # add sample and then remaining data to disposable table
        AddRows(conn, cur, sample_data, fld_names, fld_types, check=False)
        AddRows(conn, cur, remaining_data, fld_names, fld_types, check=True)
    except MismatchException, e:
        conn.commit()
        # go through again or raise an exception
        retCode = wx.MessageBox("%s\n\nFix and keep going?" % e, 
                                "KEEP GOING?", 
                                wx.YES_NO | wx.ICON_QUESTION)
        if retCode == wx.YES:
            # change fld_type to string and start again
            fld_types[e.fld_name] = FLD_STRING
            AddToTmpTable(conn, cur, file_path, tbl_name, fld_names, fld_types, 
                          sample_data, remaining_data)
        else:
            raise Exception, "Mismatch between data in column and expected " + \
                "column type"
    
def TmpToNamedTbl(conn, cur, tbl_name, file_path):
    """
    Rename table to final name.
    Separated from AddToTmpTable to allow the latter to recurse.
    This part is only called once at the end.
    """
    debug = False
    try:
        SQL_drop_tbl = "DROP TABLE IF EXISTS %s" % \
            dbe_sqlite.quote_identifier(tbl_name)
        if debug: print SQL_drop_tbl
        cur.execute(SQL_drop_tbl)
        conn.commit()
        SQL_rename_tbl = "ALTER TABLE %s RENAME TO %s" % \
            (dbe_sqlite.quote_identifier(TMP_SQLITE_TBL), 
             dbe_sqlite.quote_identifier(tbl_name))
        if debug: print SQL_rename_tbl
        cur.execute(SQL_rename_tbl)
        conn.commit()
    except Exception, e:
        raise Exception, "Unable to rename temporary table.  Orig error: %s" \
            % e
    wx.MessageBox("Successfully imported data from '%s' " % file_path + \
                  "to '%s' in the default SOFA database" % tbl_name)
        
    
class ImportFileSelectDlg(wx.Dialog):
    def __init__(self, parent):
        """
        Make selection based on file extension 
            and possibly inspection of sample of rows (e.g. csv dialect).
        """
        title = "Select file to import"
        wx.Dialog.__init__(self, parent=parent, title=title,
                           size=(500, 300), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, "images", "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        # file path
        lblFilePath = wx.StaticText(self.panel, -1, "File:")
        lblFilePath.SetFont(lblfont)
        self.txtFile = wx.TextCtrl(self.panel, -1, "", size=(320,-1))
        self.txtFile.SetFocus()
        btnFilePath = wx.Button(self.panel, -1, "Browse ...")
        btnFilePath.Bind(wx.EVT_BUTTON, self.OnButtonFilePath)
        # internal SOFA name
        lblIntName = wx.StaticText(self.panel, -1, "SOFA Name:")
        lblIntName.SetFont(lblfont)
        self.txtIntName = wx.TextCtrl(self.panel, -1, "")
        #buttons
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnImport = wx.Button(self.panel, -1, "IMPORT")
        btnImport.Bind(wx.EVT_BUTTON, self.OnImport)
        # sizers
        self.szrFilePath = wx.BoxSizer(wx.HORIZONTAL)
        self.szrFilePath.Add(lblFilePath, 0, wx.LEFT, 10)
        self.szrFilePath.Add(self.txtFile, 1, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        self.szrFilePath.Add(btnFilePath, 0, wx.RIGHT, 10)
        self.szrIntName = wx.BoxSizer(wx.HORIZONTAL)
        self.szrIntName.Add(lblIntName, 0, wx.RIGHT, 5)
        self.szrIntName.Add(self.txtIntName, 1)
        self.szrButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szrButtons.Add(btnCancel, 0)
        self.szrButtons.Add(btnImport, 0, wx.GROW|wx.LEFT, 10)
        self.szrMain.Add(self.szrFilePath, 0, wx.GROW|wx.TOP, 20)
        self.szrMain.Add(self.szrIntName, 0, wx.GROW|wx.ALL, 10)
        self.szrMain.Add(self.szrButtons, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()

    def OnButtonFilePath(self, event):
        "Open dialog and takes the file selected (if any)"
        dlgGetFile = wx.FileDialog(self) #, message=..., wildcard=...
        #defaultDir="spreadsheets", defaultFile="", )
        #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            path = dlgGetFile.GetPath()
            self.txtFile.SetValue(path)
            filestart, _ = self.GetFilestartExt(path)
            self.txtIntName.SetValue(filestart)
        dlgGetFile.Destroy()
        self.txtIntName.SetFocus()
        event.Skip()
    
    def GetFilestartExt(self, path):
        _, filename = os.path.split(path)
        filestart, extension = os.path.splitext(filename)
        return filestart, extension
    
    def OnCancel(self, event):
        self.Destroy()
    
    def CheckTblName(self, file_path, tbl_name):
        """
        Returns final_tbl_name.
        Checks table name and gives user option of correcting it if problems.
        Raises exception if no suitable name selected.
        """
        final_tbl_name = tbl_name # unless overridden
        # check existing names
        conn, _, _, tbls, _, _, _ = GetDefaultDbDets()
        if tbl_name in tbls:
            msg = "A table named \"%s\" " % tbl_name + \
                  "already exists in the SOFA default database.\n\n" + \
                  "Do you want to replace it with the new data from " + \
                  "\"%s\"?" % file_path
            retCode = wx.MessageBox(msg, "TABLE ALREADY EXISTS",
                wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
            if retCode == wx.CANCEL: # Not wx.ID_CANCEL
                raise Exception, "Had a name collision but cancelled out " + \
                    "of beginning to resolve it"
            elif retCode == wx.NO:
                # get new one
                dlg = wx.TextEntryDialog(None, 
                                         "Please enter new name for table",
                                         "NEW TABLE NAME",
                                         style=wx.OK|wx.CANCEL)
                if dlg.ShowModal() == wx.ID_OK:
                    val_entered = dlg.GetValue()
                    if val_entered != "":
                        conn.close()
                        final_tbl_name = self.CheckTblName(file_path, 
                                                           val_entered)
                        tbl_name = val_entered
                    else:
                        raise Exception, "No table name entered " + \
                            "when give chance"
                else:
                    raise Exception, "Had a name collision but cancelled " + \
                        "out of completing resolution of it"
        return final_tbl_name

    def OnImport(self, event):
        """
        Identify type of file by extension and open dialog if needed
            to get any additional choices e.g. separator used in 'csv'.
        """
        file_path = self.txtFile.GetValue()
        if not file_path:
            wx.MessageBox("Please select a file")
            return
        # identify file type
        _, extension = self.GetFilestartExt(file_path)
        if extension.lower() == ".csv":
            self.file_type = FILE_CSV
        else:
            wx.MessageBox("Files with the file name extension " + \
                              "'%s' are not supported" % extension)
            return
        tbl_name = self.txtIntName.GetValue()
        if not tbl_name:
            wx.MessageBox("Please select a name for the file")
            return
        bad_chars = ["-", " "]
        for bad_char in bad_chars:
            if bad_char in tbl_name:
                wx.MessageBox("Do not include '%s' in name" % bad_char)
                return
        if tbl_name[0] in [str(x) for x in range(10)]:
            wx.MessageBox("Table names cannot start with a digit")
            return
        try:
            final_tbl_name = self.CheckTblName(file_path, tbl_name)
        except Exception:
            wx.MessageBox("Please select a suitable table name and try again")
            return
        # import file
        if self.file_type == FILE_CSV:
            file_importer = csv_importer.FileImporter(file_path, 
                                                      final_tbl_name)
        if file_importer.GetParams():
            try:
                file_importer.ImportContent()
            except Exception, e:
                wx.MessageBox("Unable to import data\n\nError: %s" % e)
        event.Skip()
        

if __name__ == "__main__":
    app = wx.PySimpleApp()
    myframe = ImportFileSelectDlg(None)
    myframe.Show()
    app.MainLoop()
