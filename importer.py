#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import pprint
import wx

import my_globals as mg
import lib
import my_exceptions
import config_dlg
import getdata # must be before anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
# import csv_importer etc below to avoid circular import
import gdata_downloader
import projects

FILE_CSV = u"csv"
FILE_EXCEL = u"excel"
FILE_ODS = u"ods"
FILE_UNKNOWN = u"unknown"
GAUGE_STEPS = 50

dd = getdata.get_dd()
obj_quoter = dbe_sqlite.quote_obj

class MismatchException(Exception):
    def __init__(self, fld_name, details):
        debug = False
        if debug: print("A mismatch exception")
        self.fld_name = fld_name
        Exception.__init__(self, (u"Found data not matching expected "
                                  u"column type.\n\n%s" % details))

def process_fld_names(raw_names):
    """
    Turn spaces into underscores and then check all names are unique.
    Expects a list of field name strings.
    """
    debug = False
    try:
        if debug: print(raw_names)
        names = []
        for raw_name in raw_names:
            if not isinstance(raw_name, unicode):
                try:
                    raw_name = raw_name.decode("utf8")
                except UnicodeDecodeError, e:
                    raise Exception(u"Unable to process raw field name."
                                    u"\nCaused by error: %s" % lib.ue(e))
            name = raw_name.replace(u" ", u"_")
            names.append(name)
    except AttributeError:
        raise Exception(u"Field names must all be text strings.")
    except TypeError:
        raise Exception(u"Field names should be supplied in a list")
    except Exception, e:
        raise Exception(u"Problem processing field names list."
                        u"\nCaused by error: %s" % lib.ue(e))
    if len(names) != len(set(names)):
        raise Exception(u"Duplicate field name (once spaces turned to "
                        u"underscores)")
    for i, name in enumerate(names):
        if not dbe_sqlite.valid_name(name):
            raise Exception(_("Unable to use field name \"%s\". Please only "
                              "use letters, numbers and underscores. No spaces,"
                              " full stops etc.") % raw_names[i])
    return names

def process_tbl_name(rawname):
    """
    Turn spaces into underscores.  NB doesn't check if a duplicate etc at this 
        stage.
    """
    return rawname.replace(u" ", u"_")

def assess_sample_fld(sample_data, has_header, orig_fld_name, orig_fld_names, 
                      allow_none=True, comma_dec_sep_ok=False):
    """
    NB client code gets number of fields in row 1.  Then for each field, it 
        traverses rows (i.e. travels down a col, then down the next etc).  If a
        row has more flds than are in the first row, no problems will be picked
        up here because we never go into the problematic column.  But we will
        strike None values in csv files, for eg, when a row is shorter than it
        should be.
    sample_data -- dict
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
        If a csv files does, however, it is not. Should be empty str.
    For individual values, if numeric, assume numeric, 
        if date, assume date, 
        if string, either an empty string or an ordinary string.
    For entire field sample, numeric if only contains numeric 
        and empty strings (could be missings).
    Date if only contains dates and empty strings (could be missings).
    String otherwise.   
    Return field type.
    """
    debug = False
    type_set = set()
    for row_num, row in enumerate(sample_data, 1):
        if debug: print(row_num, row) # look esp for Nones
        if allow_none:
            val = lib.if_none(row[orig_fld_name], u"")
        else: # csvs don't allow none for example
            val = row[orig_fld_name]
            if val is None:
                report_fld_n_mismatch(row, row_num, has_header, orig_fld_names, 
                                      allow_none)
        lib.update_type_set(type_set, val, comma_dec_sep_ok)
    fld_type = lib.get_overall_fld_type(type_set)
    return fld_type

def get_val(raw_val, check, is_pytime, fld_type, orig_fld_name, row_num,
            comma_dec_sep_ok=False):
    """
    Missing values are OK in numeric and date fields in the source field being 
        imported, but a missing value indicator (e.g. ".") is not.  A missing
        value indicator is fine in the data _once it has been imported_ but
        not beforehand.
    check -- not necessary if part of a sample (will already have been tested)
    """
    if not check:
        # still need to handle pytime, turn empty strings into NULLs for 
        # non string fields, and handle decimal separators.
        if is_pytime:
            val = lib.pytime_to_datetime_str(raw_val)
        if not is_pytime:
            if raw_val is None or (fld_type in [mg.FLD_TYPE_NUMERIC, 
                                        mg.FLD_TYPE_DATE] and raw_val == u""):
                val = u"NULL"
            elif raw_val == mg.MISSING_VAL_INDICATOR:
                nulled_dots = True
                val = u"NULL"
            elif fld_type == mg.FLD_TYPE_NUMERIC:
                try:
                    if comma_dec_sep_ok:
                        val = raw_val.replace(u",", u".")
                    else:
                        val = raw_val
                except AttributeError, e:
                    val = raw_val
            else:
                val = raw_val
    else: # checking
        ok_data = False        
        if fld_type == mg.FLD_TYPE_NUMERIC:
            # must be numeric or empty string or dot (which we'll turn to NULL)
            if lib.is_numeric(raw_val, comma_dec_sep_ok):
                ok_data = True
                try:
                    if comma_dec_sep_ok:
                        val = raw_val.replace(u",", u".")
                    else:
                        val = raw_val
                except AttributeError, e:
                    val = raw_val
            elif raw_val == u"" or raw_val is None:
                ok_data = True
                val = u"NULL"
            elif raw_val == mg.MISSING_VAL_INDICATOR: # not ok in numeric field
                nulled_dots = True
                val = u"NULL"
            else:
                pass # no need to set val - not ok_data so exception later
        elif fld_type == mg.FLD_TYPE_DATE:
            # must be pytime or datetime 
            # or empty string or dot (which we'll turn to NULL).
            if is_pytime:
                ok_data = True
                val = lib.pytime_to_datetime_str(raw_val)
            else:
                if raw_val == u"" or raw_val is None:
                    ok_data = True
                    val = u"NULL"
                elif raw_val == mg.MISSING_VAL_INDICATOR: # not ok in numeric fld
                    nulled_dots = True
                    val = u"NULL"
                else:
                    try:
                        val = lib.get_std_datetime_str(raw_val)
                        ok_data = True
                    except Exception:
                        pass # no need to set val - not ok_data so excepn later
        elif fld_type == mg.FLD_TYPE_STRING:
            # None or dot or empty string we'll turn to NULL
            ok_data = True
            if raw_val is None or raw_val == u"":
                val = u"NULL"
            elif raw_val == mg.MISSING_VAL_INDICATOR:
                nulled_dots = True
                val = u"NULL"
            else:
                val = raw_val
        else:
            raise Exception(u"Unexpected field type in importer.get_val()")
        if not ok_data:
            raise MismatchException(fld_name=orig_fld_name,
                                    details=(u"Column: %s" % orig_fld_name +
                                    u"\nRow: %s" % (row_num) +
                                    u"\nValue: \"%s\"" % raw_val +
                                    u"\nExpected column type: %s" % fld_type))    
    return val

def process_val(vals, row_num, row, orig_fld_name, fld_types, check, 
                comma_dec_sep_ok=False):
    """
    Add val to vals.
    NB field types are only a guess based on a sample of the first rows in the 
        file being imported.  Could be wrong.
    If checking, will validate and turn empty strings into nulls
        as required.  Also turn '.' into null as required (and leave msg).
    If not checking (e.g. because a pre-tested sample) only do the
        pytime (Excel) and empty string to null conversions.
    If all is OK, will add val to vals.  NB val will need to be internally 
        quoted unless it is a NULL. 
    If not, will raise an exception.
    Quote ready for inclusion in SQLite SQL insert query.
    Returns nulled_dots (boolean).
    """
    debug = False
    nulled_dots = False
    try:
       rawval = row[orig_fld_name]
    except KeyError:
        raise Exception(_("Row %(row_num)s doesn't have a value for the "
                          "\"%(orig_fld_name)s\" field") % {u"row_num": row_num, 
                           u"orig_fld_name": orig_fld_name})
    is_pytime = lib.is_pytime(rawval)
    fld_type = fld_types[orig_fld_name]
    val = get_val(rawval, check, is_pytime, fld_type, orig_fld_name, row_num, 
                  comma_dec_sep_ok)
    if fld_type != mg.FLD_TYPE_NUMERIC and val != u"NULL":
        val = dbe_sqlite.quote_val(val)
    vals.append(val)
    if debug: print(val)
    return nulled_dots

def report_fld_n_mismatch(row, row_num, has_header, orig_fld_names, allow_none):
    debug = False
    if debug: print(row_num, row)
    if not allow_none:
        n_row_items = len([x for x in row.values() if x is not None])
    else:
        n_row_items = len(row)
    n_flds = len(orig_fld_names)
    if n_row_items != n_flds:
        if has_header:
            row_msg = _("Row %s (including header row)") % (row_num+1,)
        else:
            row_msg = _("Row %s") % row_num  
        # if csv has 2 flds and receives 3 vals will be var1:1,var2:2,None:[3]!
        vals = []
        for orig_fld_name in orig_fld_names:
            vals.append(row[orig_fld_name])
        vals_under_none = row.get(None)
        if vals_under_none:
            vals.extend(vals_under_none)
            # subtract the None list item but add all its contents
            n_row_items = len(vals)
        # remove quoting
        # e.g. ['1', '2'] or ['1', '2', None]
        vals_str = unicode(vals).replace(u"', '", u",").replace(u"['", u"")\
            .replace(u"']", u"").replace(u"',", u",").replace(u", None", u"")\
            .replace(u"]", u"")
        raise Exception(_("Incorrect number of fields in %(row_msg)s.\n\n"
                          "Expected %(n_flds)s but found %(n_row_items)s.\n\n"
                          "Faulty Row: %(vals_str)s")
                          % {"row_msg": row_msg, "n_flds": n_flds, 
                             "n_row_items": n_row_items, 
                             "vals_str": vals_str})

def add_rows(con, cur, rows, has_header, ok_fld_names, orig_fld_names, 
             fld_types, progbar, steps_per_item, gauge_start=0, row_num_start=0, 
             check=False, keep_importing=None, allow_none=True, 
             comma_dec_sep_ok=False):
    """
    Add the rows of data (dicts), processing each cell as you go.
    If checking, will validate and turn empty strings into nulls
        as required.
    If not checking (e.g. because a pre-tested sample) only do the
        empty string to null conversions.
    Returns nulled_dots (boolean).
    row_num_start -- row number (not idx) starting on
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
        If a csv files does, however, it is not. Should be empty str.
    TODO - insert multiple lines at once for performance.
    """
    debug = False
    nulled_dots = False
    fld_names_clause = u", ".join([obj_quoter(x) for x in ok_fld_names])
    for row_idx, row in enumerate(rows):
        if row_idx % 50 == 0:
            wx.Yield()
            if keep_importing == set([False]):
                progbar.SetValue(0)
                raise my_exceptions.ImportCancelException
        gauge_start += 1
        row_num = row_num_start + row_idx
        #if debug and row_num == 12:
        #    print("Break on this line :-)")
        vals = []
        report_fld_n_mismatch(row, row_num, has_header, orig_fld_names, 
                              allow_none)
        for orig_fld_name in orig_fld_names:
            if process_val(vals, row_num, row, orig_fld_name, fld_types, check, 
                           comma_dec_sep_ok):
                nulled_dots = True
        # quoting must happen earlier so we can pass in NULL  
        fld_vals_clause = u", ".join([u"%s" % x for x in vals])
        SQL_insert_row = u"INSERT INTO %s " % mg.TMP_TBL_NAME + \
            u"(%s) VALUES(%s)" % (fld_names_clause, fld_vals_clause)
        if debug: print(SQL_insert_row)
        try:
            cur.execute(SQL_insert_row)
            gauge_val = gauge_start + (row_num*steps_per_item)
            progbar.SetValue(gauge_val)
        except MismatchException, e:
            raise # keep this particular type of exception bubbling out
        except Exception, e:
            raise Exception(u"Unable to add row %s.\nCaused by error: %s"
                            % (row_num, lib.ue(e)))
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

def drop_tmp_tbl(con, cur):
    con.commit()
    SQL_drop_disp_tbl = u"DROP TABLE IF EXISTS %s" % mg.TMP_TBL_NAME
    cur.execute(SQL_drop_disp_tbl)
    con.commit()

def post_fail_tidy(progbar, con, cur):
    drop_tmp_tbl(con, cur)
    lib.safe_end_cursor()
    cur.close()
    con.commit()
    con.close()
    progbar.SetValue(0)
    
def add_to_tmp_tbl(con, cur, file_path, tbl_name, has_header, 
                   ok_fld_names, orig_fld_names, fld_types, 
                   sample_data, sample_n, remaining_data, 
                   progbar, steps_per_item, gauge_start, 
                   keep_importing, allow_none=True, comma_dec_sep_ok=False):
    """
    Create fresh disposable table in SQLite and insert data into it.
    ok_fld_names -- cleaned field names (shouldn't have a sofa_id field)
    orig_fld_names -- original names - useful for taking data from row dicts but 
        not the names to use for the new table.
    fld_types -- dict with field types for original field names
    sample_data -- list of dicts using orig fld names
    remaining_data -- as for sample data
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
        If a csv files does, however, it is not. Should be empty str.
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
        drop_tmp_tbl(con, cur)
        if debug: print(u"Successfully dropped %s" % mg.TMP_TBL_NAME)
    except Exception, e:
        raise
    try:
        tbl_name = mg.TMP_TBL_NAME
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
        if add_rows(con, cur, sample_data, has_header, ok_fld_names, 
                    orig_fld_names, fld_types, progbar, steps_per_item, 
                    gauge_start=gauge_start, row_num_start=1, check=False, 
                    keep_importing=keep_importing, allow_none=allow_none, 
                    comma_dec_sep_ok=comma_dec_sep_ok):
            nulled_dots = True
        # been through sample since gauge_start
        remainder_gauge_start = gauge_start + (sample_n*steps_per_item)
        row_num_start = sample_n + 1
        if add_rows(con, cur, remaining_data, has_header, ok_fld_names, 
                    orig_fld_names, fld_types, progbar, steps_per_item, 
                    gauge_start=remainder_gauge_start, 
                    row_num_start=row_num_start, check=True, 
                    keep_importing=keep_importing, allow_none=allow_none,
                    comma_dec_sep_ok=comma_dec_sep_ok):
            nulled_dots = True
    except MismatchException, e:
        nulled_dots = False
        con.commit()
        progbar.SetValue(0)
        # go through again or raise an exception
        retCode = wx.MessageBox(u"%s\n\n" % lib.ue(e) + \
                                _("Fix and keep going?"), 
                                _("KEEP GOING?"), wx.YES_NO|wx.ICON_QUESTION)
        if retCode == wx.YES:
            # change fld_type to string and start again
            fld_types[e.fld_name] = mg.FLD_TYPE_STRING
            if add_to_tmp_tbl(con, cur, file_path, tbl_name, has_header, 
                              ok_fld_names, orig_fld_names, fld_types, 
                              sample_data, sample_n, remaining_data, 
                              progbar, steps_per_item, gauge_start,
                              keep_importing):
                nulled_dots = True
        else:
            raise Exception(u"Mismatch between data in column and expected "
                            u"column type")
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
        SQL_drop_tbl = u"DROP TABLE IF EXISTS %s" % obj_quoter(tbl_name)
        if debug: print(SQL_drop_tbl)
        cur.execute(SQL_drop_tbl)
        con.commit()
        SQL_rename_tbl = (u"ALTER TABLE %s RENAME TO %s" % 
                          (obj_quoter(mg.TMP_TBL_NAME), obj_quoter(tbl_name)))
        if debug: print(SQL_rename_tbl)
        cur.execute(SQL_rename_tbl)
        con.commit()
    except Exception, e:
        raise Exception(u"Unable to rename temporary table."
                        u"\nCaused by error: %s" % lib.ue(e))
    progbar.SetValue(GAUGE_STEPS)
    msg = _("Successfully imported data as\n\"%(tbl)s\".")
    if nulled_dots:
        msg += _("\n\nAt least one field contained a single dot '.'.  This was "
                 "converted into a missing value.")
    msg += _("\n\nYou can view your imported data by clicking on "
             "'Enter/Edit Data' on the main form. You'll find it in the "
             "'%s' database.") % mg.SOFA_DB
    wx.MessageBox(msg % {"tbl": tbl_name})

class HasHeaderDlg(wx.Dialog):
    def __init__(self, parent, ext):
        wx.Dialog.__init__(self, parent=parent, title=_("Header row?"),
                           size=(550, 300), style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+200,120))
        self.parent = parent
        self.panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        lbl_explan = wx.StaticText(self.panel, -1, _("Does your %s file have a "
                                                     "header row?") % ext)
        bold = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        lbl_with_header = wx.StaticText(self.panel, -1, 
                                        _("Example with header"))
        lbl_with_header.SetFont(font=bold)
        img_ctrl_with_header = wx.StaticBitmap(self.panel)
        img_with_header = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                                u"%s_with_header.xpm" % ext), 
                                                wx.BITMAP_TYPE_XPM)
        bmp_with_header = wx.BitmapFromImage(img_with_header)
        img_ctrl_with_header.SetBitmap(bmp_with_header)
        lbl_without_header = wx.StaticText(self.panel, -1, _("Example without"))
        lbl_without_header.SetFont(font=bold)
        img_ctrl_without_header = wx.StaticBitmap(self.panel)
        img_without_header = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                               u"%s_without_header.xpm" % ext), 
                                               wx.BITMAP_TYPE_XPM)
        bmp_without_header = wx.BitmapFromImage(img_without_header)
        img_ctrl_without_header.SetBitmap(bmp_without_header)
        btn_has_header = wx.Button(self.panel, mg.HAS_HEADER, 
                                   _("Has Header Row"))
        btn_has_header.Bind(wx.EVT_BUTTON, self.on_btn_has_header)
        btn_has_header.SetDefault()
        btn_no_header = wx.Button(self.panel, -1, _("No Header"))
        btn_no_header.Bind(wx.EVT_BUTTON, self.on_btn_no_header)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        szr_btns.Add(btn_has_header, 0)
        szr_btns.Add(btn_no_header, 0, wx.LEFT, 5)
        szr_btns.Add(btn_cancel, 0, wx.LEFT, 20)
        szr_main.Add(lbl_explan, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(lbl_with_header, 0, wx.TOP|wx.LEFT, 10)
        szr_main.Add(img_ctrl_with_header, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        szr_main.Add(lbl_without_header, 0, wx.TOP|wx.LEFT, 10)
        szr_main.Add(img_ctrl_without_header, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        
    def on_btn_has_header(self, event):
        self.Destroy()
        self.SetReturnCode(mg.HAS_HEADER) # or nothing happens!  
        # Prebuilt dialogs presumably do this internally.
        
    def on_btn_no_header(self, event):
        self.Destroy()
        self.SetReturnCode(mg.NO_HEADER) # or nothing happens!  
        # Prebuilt dialogs presumably do this internally.
        
    def on_btn_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # or nothing happens!  
        # Prebuilt dialogs presumably do this internally.
        
        
class FileImporter(object):
    def __init__(self, parent, file_path, tbl_name):
        self.parent = parent
        self.file_path = file_path
        self.tbl_name = tbl_name
        self.has_header = True
    
    def get_params(self):
        """
        Get any user choices required.
        """
        debug = False
        dlg = HasHeaderDlg(self.parent, self.ext)
        ret = dlg.ShowModal()
        if debug: print(unicode(ret))
        if ret == wx.ID_CANCEL:
            return False
        else:
            self.has_header = (ret == mg.HAS_HEADER)
        return True
    
    
class ImportFileSelectDlg(wx.Dialog):
    def __init__(self, parent):
        """
        Make selection based on file extension 
            and possibly inspection of sample of rows (e.g. csv dialect).
        """
        title = _("Select file to import") + \
            u" (csv/xls/ods/Google spreadsheet)"
        wx.Dialog.__init__(self, parent=parent, title=title,
                           size=(550,300), style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,-1))
        self.CentreOnScreen(wx.VERTICAL)
        self.parent = parent
        self.panel = wx.Panel(self)
        self.keep_importing = set([True]) # can change and running script can 
            # check on it.
        self.file_type = FILE_UNKNOWN
        config_dlg.add_icon(frame=self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # file path
        lbl_file_path = wx.StaticText(self.panel, -1, _("Source File:"))
        lbl_file_path.SetFont(lblfont)
        self.txt_file = wx.TextCtrl(self.panel, -1, u"", size=(320,-1))
        self.txt_file.Bind(wx.EVT_CHAR, self.on_file_char)
        self.txt_file.SetFocus()
        btn_file_path = wx.Button(self.panel, -1, _("Browse ..."))
        btn_file_path.Bind(wx.EVT_BUTTON, self.on_btn_file_path)
        btn_file_path.SetDefault()
        btn_file_path.SetToolTipString(_("Browse for file locally"))
        btn_google = wx.Button(self.panel, -1, _("Google Spreadsheet ..."))
        btn_google.SetToolTipString(_("Browse for Google Spreadsheet"))
        btn_google.Bind(wx.EVT_BUTTON, self.on_btn_google)
        # comment
        lbl_comment = wx.StaticText(self.panel, -1, 
            _("The Source File will be imported into SOFA with the SOFA Table "
              "Name recorded below:"))
        # internal SOFA name
        lbl_int_name = wx.StaticText(self.panel, -1, _("SOFA Table Name:"))
        lbl_int_name.SetFont(lblfont)
        self.txt_int_name = wx.TextCtrl(self.panel, -1, "", size=(280,-1))
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
        szr_file_path.Add(btn_google, 0, wx.RIGHT, 10)
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
        szr_main.Add(szr_int_name, 0, wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(self.progbar, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_close, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_file_char(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN:
            self.txt_int_name.SetFocus()
            return
        # NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.align_btns_to_completeness)
        event.Skip()
        
    def on_int_name_char(self, event):
        wx.CallAfter(self.align_btns_to_completeness)
        event.Skip()

    def on_btn_file_path(self, event):
        "Open dialog and take the file selected (if any)"
        dlg_get_file = wx.FileDialog(self) #, message=..., wildcard=...
        # defaultDir="spreadsheets", defaultFile="", )
        # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            path = dlg_get_file.GetPath()
            self.txt_file.SetValue(path)
            filestart, unused = self.get_file_start_ext(path)
            newname = process_tbl_name(filestart)
            self.txt_int_name.SetValue(newname)
        dlg_get_file.Destroy()
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        self.btn_import.SetDefault()
        event.Skip()
    
    def on_btn_google(self, event):
        "Open dialog and take the file selected (if any)"
        dlg_gdata = gdata_downloader.GdataDownloadDlg(self)
        # MUST have a parent to enforce modal in Windows
        retval = dlg_gdata.ShowModal()
        if retval != wx.ID_CLOSE:
            path = os.path.join(mg.INT_PATH, mg.GOOGLE_DOWNLOAD)
            self.txt_file.SetValue(path)
            filestart, unused = self.get_file_start_ext(path)
            newname = process_tbl_name(filestart)
            self.txt_int_name.SetValue(newname)
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        self.btn_import.SetDefault()
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
            title = _("FAULTY SOFA TABLE NAME")
            msg = _("You can only use letters, numbers and underscores in a "
                "SOFA Table Name.  Use another name?")
            retval = wx.MessageBox(msg, title, wx.YES_NO|wx.ICON_QUESTION)
            if retval == wx.NO:
                raise Exception(u"Had a problem with faulty SOFA Table Name but"
                            u" user cancelled initial process of resolving it")
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
                wx.MessageBox(_("Please change the SOFA Table Name and try "
                                "again"))
                self.txt_int_name.SetFocus()
                return None
            elif retval == wx.YES:
                pass # use the name (and overwrite original)
        return tbl_name

    def align_btns_to_completeness(self):
        debug = False
        filename = self.txt_file.GetValue()
        int_name = self.txt_int_name.GetValue()
        complete = (filename != u"" and int_name != u"")
        if debug: print("filename: \"%s\" int_name: \"%s\" complete: %s" % \
                        (filename, int_name, complete))
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
            if mg.PLATFORM != mg.WINDOWS:
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
            wx.MessageBox(_("Please select a SOFA Table Name for the file"))
            self.align_btns_to_importing(importing=False)
            self.txt_int_name.SetFocus()
            return
        if u" " in tbl_name:
            wx.MessageBox(_("SOFA Table Name can't have empty spaces"))
            self.align_btns_to_importing(importing=False)
            return
        bad_chars = [u"-", ]
        for bad_char in bad_chars:
            if bad_char in tbl_name:
                wx.MessageBox(_("Do not include '%s' in SOFA Table Name") % 
                              bad_char)
                self.align_btns_to_importing(importing=False)
                return
        if tbl_name[0] in [unicode(x) for x in range(10)]:
            wx.MessageBox(_("SOFA Table Names cannot start with a digit"))
            self.align_btns_to_importing(importing=False)
            return
        try:
            final_tbl_name = self.check_tbl_name(file_path, tbl_name)
            if final_tbl_name is None:
                self.align_btns_to_importing(importing=False)
                self.progbar.SetValue(0)
                return
        except Exception:
            wx.MessageBox(_("Please select a suitable SOFA Table Name "
                            "and try again"))
            self.align_btns_to_importing(importing=False)
            return
        # import file
        if self.file_type == FILE_CSV:
            import csv_importer
            file_importer = csv_importer.CsvImporter(self, file_path, 
                                                     final_tbl_name)
        elif self.file_type == FILE_EXCEL:
            import excel_importer
            file_importer = excel_importer.ExcelImporter(self, file_path,
                                                         final_tbl_name)
        elif self.file_type == FILE_ODS:
            import ods_importer
            file_importer = ods_importer.OdsImporter(self, file_path,
                                                     final_tbl_name)
        proceed = False
        try:
            proceed = file_importer.get_params()
        except Exception, e:
            wx.MessageBox(_("Unable to import data\n\nError") + u": %s" % 
                          lib.ue(e))
            lib.safe_end_cursor()
        if proceed:
            try:
                file_importer.import_content(self.progbar, self.keep_importing,
                                             self.lbl_feedback)
                dd.set_db(dd.db, tbl=tbl_name)
                lib.safe_end_cursor()
            except my_exceptions.ImportConfirmationRejected, e:
                lib.safe_end_cursor()
                wx.MessageBox(lib.ue(e))
            except my_exceptions.ImportCancelException, e:
                lib.safe_end_cursor()
                self.keep_importing.discard(False)
                self.keep_importing.add(True)
                wx.MessageBox(lib.ue(e))
            except Exception, e:
                lib.safe_end_cursor()
                wx.MessageBox(_("Unable to import data\n\nError") + u": %s" % 
                              lib.ue(e))
        self.align_btns_to_importing(importing=False)
        event.Skip()
