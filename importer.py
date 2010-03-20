from __future__ import print_function
import os
import wx

import my_globals as mg
import lib
from my_exceptions import ImportCancelException
import config_dlg
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import csv_importer
if mg.IN_WINDOWS:
    import excel_importer
import ods_importer
import projects

FILE_CSV = u"csv"
FILE_EXCEL = u"excel"
FILE_ODS = u"ods"
FILE_UNKNOWN = u"unknown"
TMP_SQLITE_TBL = u"tmptbl"
GAUGE_STEPS = 50


class MismatchException(Exception):
    def __init__(self, fld_name, details):
        debug = False
        if debug: print("Yep - a mismatch exception")
        self.fld_name = fld_name
        Exception.__init__(self, u"Found data not matching expected " + \
                           u"column type.\n\n%s" % details)

def process_fld_names(raw_names):
    """
    Turn spaces into underscores and then check all names are unique.
    Expects a list of field name strings.
    """
    debug = False
    try:
        if debug: print(raw_names)
        names = [x.replace(u" ", u"_") for x in raw_names]
    except AttributeError:
        raise Exception, "Field names must all be text strings."
    except TypeError:
        raise Exception, "Field names should be supplied in a list"
    except Exception:
        raise Exception, "Unknown problem processing field names list"
    if len(names) != len(set(names)):
        raise Exception, ("Duplicate field name (once spaces turned to "
                          "underscores)")
    for i, name in enumerate(names):
        if not dbe_sqlite.valid_name(name):
            raise Exception, _("Unable to use field name \"%s\". "
                              "It is recommended that you only use letters, "
                              "numbers and underscores. No spaces, full stops"
                              " etc." % raw_names[i])
    return names

def assess_sample_fld(sample_data, orig_fld_name):
    """
    sample_data -- dict
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
    for row in sample_data:
        val = lib.if_none(row[orig_fld_name], u"")
        if lib.is_numeric(val): # anything that SQLite can add _as a number_ 
                # into a numeric field
            type_set.add(mg.VAL_NUMERIC)
        elif lib.is_pytime(val): # COM on Windows
            type_set.add(mg.VAL_DATETIME)
        else:
            usable_datetime = lib.is_usable_datetime_str(val)
            if usable_datetime:
                type_set.add(mg.VAL_DATETIME)
            elif val == u"":
                type_set.add(mg.VAL_EMPTY_STRING)
            else:
                type_set.add(mg.VAL_STRING)
    fld_type = get_overall_fld_type(type_set)
    return fld_type

def get_overall_fld_type(type_set):
    numeric_only_set = set([mg.VAL_NUMERIC])
    numeric_or_empt_str_set = set([mg.VAL_NUMERIC, mg.VAL_EMPTY_STRING])
    datetime_only_set = set([mg.VAL_DATETIME])
    datetime_or_empt_str_set = set([mg.VAL_DATETIME, mg.VAL_EMPTY_STRING])
    if type_set == numeric_only_set or type_set == numeric_or_empt_str_set:
        fld_type = mg.FLD_TYPE_NUMERIC
    elif type_set == datetime_only_set or type_set == datetime_or_empt_str_set:
        fld_type = mg.FLD_TYPE_DATE
    else:
        fld_type = mg.FLD_TYPE_STRING    
    return fld_type

def process_val(vals, row_idx, row, orig_fld_name, fld_types, check):
    """
    NB field types are only a guess based on a sample of the first rows in the 
        file being imported.  Could be wrong.
    If checking, will validate and turn empty strings into nulls
        as required.  Also turn '.' into null as required (and leave msg).
    If not checking (e.g. because a pre-tested sample) only do the
        pytime (Excel) and empty string to null conversions.
    If all is OK, will add val to vals.  NB val will need to be internally 
        quoted unless it is a NULL. 
    If not, will raise an exception.
    Returns nulled_dots (boolean).
    """
    debug = False
    nulled_dots = False
    try:
        val = row[orig_fld_name]
    except KeyError:
        raise Exception, _("Row %s doesn't have a value for the \"%s\" field") \
            % (row_idx, orig_fld_name)
    is_pytime = lib.is_pytime(val)
    fld_type = fld_types[orig_fld_name]
    if not check:
        # still need to handle pytime and turn empty strings into NULLs 
        # for non string fields.
        if is_pytime:
            val = lib.pytime_to_datetime_str(val)
        if not is_pytime:
            if val is None or (fld_type in [mg.FLD_TYPE_NUMERIC, 
                                            mg.FLD_TYPE_DATE] and val == u""):
                val = u"NULL"
            elif val == u".":
                nulled_dots = True
                val = u"NULL"
    else: # checking
        bolOK_data = False        
        if fld_type == mg.FLD_TYPE_NUMERIC:
            # must be numeric or empty string or dot (which we'll turn to NULL)
            if lib.is_numeric(val):
                bolOK_data = True
            elif val == u"" or val is None:
                bolOK_data = True
                val = u"NULL"
            elif val == u".":
                nulled_dots = True
                val = u"NULL"
        elif fld_type == mg.FLD_TYPE_DATE:
            # must be pytime or datetime 
            # or empty string or dot (which we'll turn to NULL).
            if is_pytime:
                bolOK_data = True
                val = lib.pytime_to_datetime_str(val)
            else:
                if val == u"" or val is None:
                    bolOK_data = True
                    val = u"NULL"
                elif val == u".":
                    nulled_dots = True
                    val = u"NULL"
                else:
                    try:
                        val = lib.get_std_datetime_str(val)
                        bolOK_data = True
                    except Exception:
                        pass # leave val as is for error reporting
        elif fld_type == mg.FLD_TYPE_STRING:
            # None or dot we'll turn to NULL
            if val is None:
                val = u"NULL"
            elif val == u".":
                nulled_dots = True
                val = u"NULL"
            bolOK_data = True
        if not bolOK_data:
            raise MismatchException(fld_name=orig_fld_name,
                                    details=(u"Column: %s" % orig_fld_name +
                                    u"\nRow: %s" % (row_idx + 1) +
                                    u"\nValue: \"%s\"" % val +
                                    u"\nExpected column type: %s" % fld_type))
    if val != u"NULL":
        val = u"\"%s\"" % val
    vals.append(val)
    if debug: print(val)
    return nulled_dots
    
def add_rows(con, cur, rows, ok_fld_names, orig_fld_names, fld_types, 
             progbar, steps_per_item, gauge_start=0, check=False, 
             keep_importing=None):
    """
    Add the rows of data (dicts), processing each cell as you go.
    If checking, will validate and turn empty strings into nulls
        as required.
    If not checking (e.g. because a pre-tested sample) only do the
        empty string to null conversions.
    Returns nulled_dots (boolean).
    TODO - insert multiple lines at once for performance.
    """
    debug = False
    nulled_dots = False
    fld_names_clause = u", ".join([dbe_sqlite.quote_obj(x) for x \
                                                            in ok_fld_names])
    for row_idx, row in enumerate(rows):
        if row_idx % 50 == 0:
            wx.Yield()
            if keep_importing == set([False]):
                progbar.SetValue(0)
                raise ImportCancelException
        gauge_start += 1
        row_idx += 1
        vals = []
        for orig_fld_name in orig_fld_names:
            if process_val(vals, row_idx, row, orig_fld_name, fld_types, check):
                nulled_dots = True
        # quoting must happen earlier so we can pass in NULL  
        fld_vals_clause = u", ".join([u"%s" % x for x in vals])
        SQL_insert_row = u"INSERT INTO %s " % TMP_SQLITE_TBL + \
            u"(%s) VALUES(%s)" % (fld_names_clause, fld_vals_clause)
        if debug: print(SQL_insert_row)
        try:
            cur.execute(SQL_insert_row)
            gauge_val = gauge_start + (row_idx*steps_per_item)
            progbar.SetValue(gauge_val)
        except MismatchException, e:
            raise # keep this particular type of exception bubbling out
        except Exception, e:
            raise Exception, u"Unable to add row %s. Orig error: %s" % \
                (row_idx+1, e)
    con.commit()
    return nulled_dots

def get_steps_per_item(items_n):
    """
    Needed for progress bar - how many items before displaying another of the 
        steps as set by GAUGE_STEPS.
    Chunks per item e.g. 0.01.
    """
    if items_n != 0:
        # we go through the sample once at start for sampling and then again
        # for adding to table
        steps_per_item = float(GAUGE_STEPS)/items_n
    else:
        steps_per_item = None
    return steps_per_item

def add_to_tmp_tbl(con, cur, file_path, tbl_name, ok_fld_names, orig_fld_names, 
                   fld_types, sample_data, sample_n, remaining_data, progbar, 
                   steps_per_item, gauge_start, keep_importing):
    """
    Create fresh disposable table in SQLite and insert data into it.
    ok_fld_names -- cleaned field names (shouldn't have a sofa_id field)
    orig_fld_names -- original names - useful for taking data from row dicts but 
        not the names to use for the new table.
    fld_types -- dict with field types for original field names
    sample_data -- list of dicts using orig fld names
    remaining_data -- as for sample data
    Give it a unique identifier field as well.
    Set up the data type constraints needed.
    Returns nulled_dots (boolean).
    """
    debug = False
    nulled_dots = False
    if debug:
        print(u"Original field names are: %s" % orig_fld_names)
        print(u"Cleaned (ok) field names are: %s" % ok_fld_names)
        print(u"Field types are: %s" % fld_types)
        print(u"Sample data is: %s" % sample_data)
    try:
        con.commit()
        SQL_get_tbl_names = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'"""
        cur.execute(SQL_get_tbl_names) # otherwise it doesn't always seem to have the 
            # latest data on which tables exist
        SQL_drop_disp_tbl = u"DROP TABLE IF EXISTS %s" % TMP_SQLITE_TBL
        cur.execute(SQL_drop_disp_tbl)
        con.commit()
        if debug: print(u"Successfully dropped %s" % TMP_SQLITE_TBL)
    except Exception, e:
        raise
    try:
        tbl_name = TMP_SQLITE_TBL
        # oth_name_types -- ok_fld_name, fld_type (taken from original source 
        # and the key will be orig_fld_name)
        oth_name_types = []
        fld_names = zip(ok_fld_names, orig_fld_names)
        for ok_fld_name, orig_fld_name in fld_names:
            oth_name_types.append((ok_fld_name, fld_types[orig_fld_name]))
        getdata.make_sofa_tbl(con, cur, tbl_name, oth_name_types)
    except Exception, e:
        raise   
    try:
        # Add sample and then remaining data to disposable table.
        # Already been through sample once when assessing it so part way through 
        # process already.
        if add_rows(con, cur, sample_data, ok_fld_names, orig_fld_names, 
                    fld_types, progbar, steps_per_item, gauge_start=gauge_start, 
                    check=False, keep_importing=keep_importing):
            nulled_dots = True
        # been through sample since gauge_start
        remainder_gauge_start = gauge_start + (sample_n*steps_per_item)
        if add_rows(con, cur, remaining_data, ok_fld_names, orig_fld_names, 
                                 fld_types, progbar, steps_per_item, 
                                 gauge_start=remainder_gauge_start, check=True, 
                                 keep_importing=keep_importing):
            nulled_dots = True
    except MismatchException, e:
        nulled_dots = False
        con.commit()
        progbar.SetValue(0)
        # go through again or raise an exception
        retCode = wx.MessageBox(u"%s\n\n" % e + _("Fix and keep going?"), 
                                _("KEEP GOING?"), wx.YES_NO|wx.ICON_QUESTION)
        if retCode == wx.YES:
            # change fld_type to string and start again
            fld_types[e.fld_name] = mg.FLD_TYPE_STRING
            if add_to_tmp_tbl(con, cur, file_path, tbl_name, ok_fld_names, 
                              orig_fld_names, fld_types, sample_data, sample_n, 
                              remaining_data, progbar, steps_per_item, 
                              keep_importing):
                nulled_dots = True
        else:
            
            raise Exception, u"Mismatch between data in column and " + \
                "expected column type"
    return nulled_dots
    
def tmp_to_named_tbl(con, cur, tbl_name, file_path, progbar, nulled_dots):
    """
    Rename table to final name.
    Separated from add_to_tmp_tbl to allow the latter to recurse.
    This part is only called once at the end and is so fast there is no need to
        report progress till completion.
    """
    debug = False
    try:
        SQL_drop_tbl = u"DROP TABLE IF EXISTS %s" % \
            dbe_sqlite.quote_obj(tbl_name)
        if debug: print(SQL_drop_tbl)
        cur.execute(SQL_drop_tbl)
        con.commit()
        SQL_rename_tbl = u"ALTER TABLE %s RENAME TO %s" % \
            (dbe_sqlite.quote_obj(TMP_SQLITE_TBL), 
             dbe_sqlite.quote_obj(tbl_name))
        if debug: print(SQL_rename_tbl)
        cur.execute(SQL_rename_tbl)
        con.commit()
    except Exception, e:
        raise Exception, u"Unable to rename temporary table.  Orig error: %s" \
            % e
    progbar.SetValue(GAUGE_STEPS)
    msg = _("Successfully imported data from '%(fil)s' to '%(tbl)s' in the "
            "default SOFA database.")
    if nulled_dots:
        msg += _("\n\nAt least one field contained a single dot '.'.  This was "
                 "converted into a missing value.")
    msg += _("\n\nClick on 'Enter/Edit Data' on the main form to view your "
             "imported data.")
    wx.MessageBox(msg % {"fil": file_path, "tbl": tbl_name})
        
    
class ImportFileSelectDlg(wx.Dialog):
    def __init__(self, parent):
        """
        Make selection based on file extension 
            and possibly inspection of sample of rows (e.g. csv dialect).
        """
        title = _("Select file to import") + u" (csv/xls/ods)"
        wx.Dialog.__init__(self, parent=parent, title=title,
                           size=(500, 300), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.keep_importing = set([True]) # can change and running script can 
            # check on it.
        self.file_type = FILE_UNKNOWN
        config_dlg.add_icon(frame=self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # file path
        lbl_file_path = wx.StaticText(self.panel, -1, _("File:"))
        lbl_file_path.SetFont(lblfont)
        self.txt_file = wx.TextCtrl(self.panel, -1, u"", size=(320,-1))
        self.txt_file.Bind(wx.EVT_CHAR, self.on_file_char)
        self.txt_file.SetFocus()      
        btn_file_path = wx.Button(self.panel, -1, _("Browse ..."))
        btn_file_path.Bind(wx.EVT_BUTTON, self.on_btn_file_path)
        btn_file_path.SetDefault()
        # comment
        lbl_comment = wx.StaticText(self.panel, -1, 
            _("The file will be imported into the SOFA_Default_db database "
              "with the table name recorded below"))
        # internal SOFA name
        lbl_int_name = wx.StaticText(self.panel, -1, _("SOFA Name:"))
        lbl_int_name.SetFont(lblfont)
        self.txt_int_name = wx.TextCtrl(self.panel, -1, "")
        self.txt_int_name.Bind(wx.EVT_CHAR, self.on_int_name_char)
        # feedback
        self.lbl_feedback = wx.StaticText(self.panel)
        # buttons
        self.btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.btn_cancel.Enable(False)
        self.btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        self.btn_import = wx.Button(self.panel, -1, _("IMPORT"))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
        self.btn_import.Enable(False)
        # progress
        self.progbar = wx.Gauge(self.panel, -1, GAUGE_STEPS, size=(-1, 20),
                                style=wx.GA_PROGRESSBAR)
        # sizers
        szr_file_path = wx.BoxSizer(wx.HORIZONTAL)
        szr_file_path.Add(lbl_file_path, 0, wx.LEFT, 10)
        szr_file_path.Add(self.txt_file, 1, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szr_file_path.Add(btn_file_path, 0, wx.RIGHT, 10)
        szr_int_name = wx.BoxSizer(wx.HORIZONTAL)
        szr_int_name.Add(lbl_int_name, 0, wx.RIGHT, 5)
        szr_int_name.Add(self.txt_int_name, 1)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_import, 0, wx.ALIGN_RIGHT)
        szr_close = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_close.AddGrowableCol(0,2) # idx, propn
        szr_close.Add(self.lbl_feedback)        
        szr_close.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_file_path, 0, wx.GROW|wx.TOP, 20)
        szr_main.Add(lbl_comment, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_int_name, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(self.progbar, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_close, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_file_char(self, event):
        self.align_btns_to_completeness()
        event.Skip()
        
    def on_int_name_char(self, event):
        self.align_btns_to_completeness()
        event.Skip()

    def on_btn_file_path(self, event):
        "Open dialog and takes the file selected (if any)"
        dlg_get_file = wx.FileDialog(self) #, message=..., wildcard=...
        # defaultDir="spreadsheets", defaultFile="", )
        # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            path = dlg_get_file.GetPath()
            self.txt_file.SetValue(path)
            filestart, unused = self.get_file_start_ext(path)
            self.txt_int_name.SetValue(filestart)
        dlg_get_file.Destroy()
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        event.Skip()
    
    def get_file_start_ext(self, path):
        unused, filename = os.path.split(path)
        filestart, extension = os.path.splitext(filename)
        return filestart, extension
    
    def on_close(self, event):
        self.Destroy()
    
    def on_cancel(self, event):
        self.keep_importing.discard(True)
        self.keep_importing.add(False)
    
    def check_tbl_name(self, file_path, tbl_name):
        """
        Returns tbl_name (None if no suitable name to use).
        Checks table name and gives user option of correcting it if problems.
        Raises exception if no suitable name selected.
        """
        # check existing names
        valid_name = dbe_sqlite.valid_name(tbl_name)
        if not valid_name:
            title = _("FAULTY SOFA NAME")
            msg = _("You can only use letters, numbers and underscores in a "
                "SOFA name.  Use another name?")
            retval = wx.MessageBox(msg, title, wx.YES_NO|wx.ICON_QUESTION)
            if retval == wx.NO:
                raise Exception, u"Had a problem with faulty SOFA table " + \
                    u"name but user cancelled initial process of resolving it"
            elif retval == wx.YES:
                self.txt_int_name.SetFocus()
                return None
        duplicate = getdata.dup_tbl_name(tbl_name)
        if duplicate:
            title = _("SOFA NAME ALREADY EXISTS")
            msg = _("A table named \"%(tbl)s\" "
                  "already exists in the SOFA default database.\n\n"
                  "Do you want to replace it with the new data from "
                  "\"%(fil)s\"?") 
            retval = wx.MessageBox(msg % {"tbl": tbl_name, "fil": file_path}, 
                                   title, wx.YES_NO|wx.ICON_QUESTION)
            if retval == wx.NO: # no overwrite so get new one (or else!)
                wx.MessageBox(_("Please change the SOFA name and try again"))
                self.txt_int_name.SetFocus()
                return None
            elif retval == wx.YES:
                pass # use the name (and overwrite original)
        return tbl_name

    def align_btns_to_completeness(self):
        complete = (self.txt_int_name.GetValue() != u"" 
                    and self.txt_file.GetValue() != u"")
        self.btn_import.Enable(complete)

    def align_btns_to_importing(self, importing):
        self.btn_close.Enable(not importing)
        self.btn_cancel.Enable(importing)
        self.btn_import.Enable(not importing)

    def on_import(self, event):
        """
        Identify type of file by extension and open dialog if needed
            to get any additional choices e.g. separator used in 'csv'.
        """
        self.align_btns_to_importing(importing=True)
        self.progbar.SetValue(0)
        file_path = self.txt_file.GetValue()
        if not file_path:
            wx.MessageBox(_("Please select a file"))
            self.align_btns_to_importing(importing=False)
            self.txt_file.SetFocus()
            return
        # identify file type
        unused, extension = self.get_file_start_ext(file_path)
        if extension.lower() == u".csv":
            self.file_type = FILE_CSV
        elif extension.lower() == u".xls":
            if not mg.IN_WINDOWS:
                wx.MessageBox(_("Excel spreadsheets are only supported on "
                              "Windows.  Try exporting to CSV first from "
                              "Excel (within Windows)"))
                self.align_btns_to_importing(importing=False)
                return
            else:
                self.file_type = FILE_EXCEL
        elif extension.lower() == u".ods":
            self.file_type = FILE_ODS
        else:
            self.file_type == FILE_UNKNOWN
            wx.MessageBox(_("Files with the file name extension "
                            "'%s' are not supported") % extension)
            self.align_btns_to_importing(importing=False)
            return
        tbl_name = self.txt_int_name.GetValue()
        if not tbl_name:
            wx.MessageBox(_("Please select a name for the file"))
            self.align_btns_to_importing(importing=False)
            self.txt_int_name.SetFocus()
            return
        bad_chars = [u"-", u" "]
        for bad_char in bad_chars:
            if bad_char in tbl_name:
                wx.MessageBox(_("Do not include '%s' in name") % bad_char)
                self.align_btns_to_importing(importing=False)
                return
        if tbl_name[0] in [unicode(x) for x in range(10)]:
            wx.MessageBox(_("Table names cannot start with a digit"))
            self.align_btns_to_importing(importing=False)
            return
        try:
            final_tbl_name = self.check_tbl_name(file_path, tbl_name)
            if final_tbl_name is None:
                self.align_btns_to_importing(importing=False)
                self.progbar.SetValue(0)
                return
        except Exception:
            wx.MessageBox(_("Please select a suitable table name and "
                            "try again"))
            self.align_btns_to_importing(importing=False)
            return
        # import file
        if self.file_type == FILE_CSV:
            file_importer = csv_importer.FileImporter(file_path, 
                                                      final_tbl_name)
        elif self.file_type == FILE_EXCEL:
            file_importer = excel_importer.FileImporter(file_path,
                                                        final_tbl_name)
        elif self.file_type == FILE_ODS:
            file_importer = ods_importer.FileImporter(file_path,
                                                      final_tbl_name)
        if file_importer.get_params():
            try:
                file_importer.import_content(self.progbar, self.keep_importing,
                                             self.lbl_feedback)
                lib.safe_end_cursor()
            except ImportCancelException, e:
                lib.safe_end_cursor()
                self.keep_importing.discard(False)
                self.keep_importing.add(True)
                wx.MessageBox(unicode(e))
            except Exception, e:
                lib.safe_end_cursor()
                wx.MessageBox(_("Unable to import data\n\nError") + u": %s" % e)
            
        self.align_btns_to_importing(importing=False)
        event.Skip()
