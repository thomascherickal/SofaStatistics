#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import wx
import wx.html

import my_globals as mg
import lib
import my_exceptions
import config_output
import getdata # must be before anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
# import csv_importer etc below to avoid circular import
import gdata_downloader

FILE_CSV = u"csv"
FILE_EXCEL = u"excel"
FILE_ODS = u"ods"
FILE_UNKNOWN = u"unknown"
GAUGE_STEPS = 50
FIRST_MISMATCH_TPL = (u"\nRow: %(row)s"
                      u"\nValue: \"%(value)s\""
                      u"\nExpected column type: %(fldtype)s")


class FixMismatchDlg(wx.Dialog):
    # weird bugs when using stdbtndialog here and calling dlg multiple times
    # actual cause not known but buggy original had a setup_btns method
    def __init__(self, fldname, fldtype_choices, fldtypes, 
             faulty2missing_fld_list, details, assessing_sample=False):
        """
        fldtype_choices -- doesn't include string.
        """
        if assessing_sample:
            title_txt = _("MIX OF DATA TYPES")
        else:
            title_txt = _("DATA TYPE MISMATCH")
        self.fldname = fldname
        self.fldtype_choices = fldtype_choices
        self.fldtypes = fldtypes
        self.faulty2missing_fld_list = faulty2missing_fld_list
        wx.Dialog.__init__(self, None, title=title_txt, size=(500,600), 
                           style=wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        if assessing_sample:
            choice_txt = (_(u"A mix of data types was found in a sample of "
                           u"data in \"%(fldname)s\"."
                           u"\n\nFirst inconsistency:%(details)s"
                           u"\n\nPlease select the data type you want this "
                           u"entire column imported as.") % 
                                {u"fldname": fldname, # no fldtypes if sample
                                 u"details": details})
        else:
            choice_txt = (_(u"Data was found in \"%(fldname)s\" which doesn't "
               u"match the expected data type (%(data_type)s). "
               u"\n%(details)s"
               u"\n\nPlease select the data type you want this entire column "
               u"imported as.") % {u"fldname": fldname, 
                                   u"data_type": fldtypes[fldname], 
                                   u"details": details})
        lbl_choice = wx.StaticText(self.panel, -1, choice_txt)
        types = u" or ".join(["\"%s\"" % x for x in self.fldtype_choices])
        lbl_implications = wx.StaticText(self.panel, -1, _(u"If you choose %s ,"
            u" any values that are not of that type will be turned to missing."
            % types))
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        if mg.FLDTYPE_NUMERIC in self.fldtype_choices:
            btn_num = wx.Button(self.panel, mg.RET_NUMERIC, mg.FLDTYPE_NUMERIC)
            btn_num.Bind(wx.EVT_BUTTON, self.on_num)
            szr_btns.Add(btn_num, 0, wx.LEFT|wx.RIGHT, 10)
        if mg.FLDTYPE_DATE in self.fldtype_choices:
            btn_date = wx.Button(self.panel, mg.RET_DATE, mg.FLDTYPE_DATE)
            btn_date.Bind(wx.EVT_BUTTON, self.on_date)
            szr_btns.Add(btn_date, 0,  wx.LEFT|wx.RIGHT, 10)
        btn_text = wx.Button(self.panel, mg.RET_TEXT, mg.FLDTYPE_STRING)
        btn_text.Bind(wx.EVT_BUTTON, self.on_text)
        szr_btns.Add(btn_text, 0, wx.LEFT|wx.RIGHT, 10)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        szr_btns.Add(btn_cancel, 0,  wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(lbl_choice, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(lbl_implications, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
    
    def on_num(self, event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_NUMERIC
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_NUMERIC)
    
    def on_date(self, event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_DATE
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_DATE)
        
    def on_text(self, event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_STRING
        self.Destroy()
        self.SetReturnCode(mg.RET_TEXT)
        
    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
    
    
def get_best_fldtype(fldname, type_set, faulty2missing_fld_list, 
                     first_mismatch=u"", testing=False):
    """
    type_set may contain empty_str as well as actual types. Useful to remove
        empty str and see what is left.
    faulty2missing_fld_list -- so we can stay with the selected best type by 
        setting faulty values that don't match type to missing.
    STRING is the fallback.
    """
    main_type_set = type_set.copy()
    main_type_set.discard(mg.VAL_EMPTY_STRING)
    if main_type_set == set([mg.VAL_NUMERIC]):
        fldtype = mg.FLDTYPE_NUMERIC
    elif main_type_set == set([mg.VAL_DATE]):
        fldtype = mg.FLDTYPE_DATE
    elif (main_type_set == set([mg.VAL_STRING]) 
            or type_set == set([mg.VAL_EMPTY_STRING])):
        fldtype = mg.FLDTYPE_STRING
    elif len(main_type_set) > 1:
        # get user to choose
        fldtypes = {}
        fldtype_choices = []
        if mg.VAL_NUMERIC in main_type_set:
            fldtype_choices.append(mg.FLDTYPE_NUMERIC)
        if mg.VAL_DATE in main_type_set:
            fldtype_choices.append(mg.FLDTYPE_DATE)
        if not testing:
            dlg = FixMismatchDlg(fldname=fldname, 
                            fldtype_choices=fldtype_choices, fldtypes=fldtypes, 
                            faulty2missing_fld_list=faulty2missing_fld_list, 
                            details=first_mismatch, assessing_sample=True)
            ret = dlg.ShowModal()
            if ret == wx.ID_CANCEL:
                raise Exception(u"Inconsistencies in data type.")         
            else:
                fldtype = fldtypes[fldname]
        else:
            fldtype = mg.FLDTYPE_STRING
    else:
        fldtype = mg.FLDTYPE_STRING    
    return fldtype

def process_fldnames(raw_names, headless=False):
    """
    Turn spaces into underscores, fills blank field names with a safe and 
        uniquely numbered name, and appends a unique number to duplicate field 
        names.
    Checks all field names OK for sqlite and none are empty strings.
    Expects a list of field name strings. Returns the same number of field 
        names.
    The client code should not rely on the row data it extracts having the same 
        field names exactly as they may be modified e.g. spaces turned to 
        underscores.
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
            if mg.SOFA_ID in names:
                raise Exception(_(u"%s is a reserved field name.") % mg.SOFA_ID)
        names = lib.get_unique_fldnames(names)
    except AttributeError:
        raise Exception(u"Field names must all be text strings.")
    except TypeError:
        raise Exception(u"Field names should be supplied in a list")
    except Exception, e:
        raise Exception(u"Problem processing field names list."
                        u"\nCaused by error: %s" % lib.ue(e))
    quickcheck = False
    n_names = len(names)
    if n_names > 50:
        if headless:
            pass
        else:
            # don't test each name individually - takes too long
            # we gain speed and lose ability to single out bad variable name
            if wx.MessageBox(_(u"There are %s fields so the process of "
                               u"checking them all will take a while. "
                               u"Do you want to do a quick check only?") % 
                                                                    n_names, 
                             caption=_("QUICK CHECK ONLY?"), 
                             style=wx.YES_NO) == wx.YES:
                quickcheck = True
    if quickcheck:
        # quick check
        valid, err = dbe_sqlite.valid_fldnames(fldnames=names, block_sz=100)
        if not valid:
            raise Exception(_(u"Unable to use field names provided. Please "
                u"only use letters, numbers and underscores. No spaces, full "
                u"stops etc. If you want to know which field name failed, try "
                u"again and do the more thorough check (say No to quick check "
                u"only).\nOrig error: %s") % err)
    else:
        # thorough check
        for i, name in enumerate(names):
            valid, err = dbe_sqlite.valid_fldname(name)
            if not valid:
                raise Exception(_(u"Unable to use field name \"%(fldname)s\". "
                      u"Please only use letters, numbers and underscores. No "
                      u"spaces, full stops etc.\nOrig error: %(err)s") % 
                                {"fldname": raw_names[i], "err": err})
    return names

def process_tblname(rawname):
    """
    Turn spaces, hyphens and dots into underscores.
    NB doesn't check if a duplicate etc at this stage.
    """
    return rawname.replace(u" ", u"_").replace(u".", u"_").replace(u"-", u"_")

def assess_sample_fld(sample_data, has_header, ok_fldname, ok_fldnames, 
                      faulty2missing_fld_list, allow_none=True, 
                      comma_dec_sep_ok=False, testing=False):
    """
    NB client code gets number of fields in row 1. Then for each field, it 
        traverses rows (i.e. travels down a col, then down the next etc).  If a
        row has more flds than are in the first row, no problems will be picked
        up here because we never go into the problematic column. But we will
        strike None values in csv files, for eg, when a row is shorter than it
        should be.
    sample_data -- list of dicts.
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
    first_mismatch = u""
    expected_fldtype = u""
    for row_num, row in enumerate(sample_data, 1):
        if debug: print(row_num, row) # look esp for Nones
        if allow_none:
            val = lib.if_none(row[ok_fldname], u"")
        else: # csvs don't allow none for example
            val = row[ok_fldname]
            if val is None:
                report_fld_n_mismatch(row, row_num, has_header, ok_fldnames, 
                                      allow_none)
        val_type = lib.get_val_type(val, comma_dec_sep_ok)
        if not expected_fldtype and val_type != mg.VAL_EMPTY_STRING:
            expected_fldtype = val_type
        type_set.add(val_type)
        # more than one type (ignoring empty string)?
        main_type_set = type_set.copy()
        main_type_set.discard(mg.VAL_EMPTY_STRING)
        if len(main_type_set) > 1 and not first_mismatch:
            # identify row and value to report to user
            first_mismatch = (FIRST_MISMATCH_TPL % {u"row": row_num, 
                                u"value": val, u"fldtype": expected_fldtype})
    fldtype = get_best_fldtype(fldname=ok_fldname, type_set=type_set, 
                               faulty2missing_fld_list=faulty2missing_fld_list,
                               first_mismatch=first_mismatch, testing=testing)
    return fldtype

def get_val(feedback, raw_val, is_pytime, fldtype, ok_fldname, 
            faulty2missing_fld_list, row_num, comma_dec_sep_ok=False):
    """
    feedback -- dic with mg.NULLED_DOTS
    Missing values are OK in numeric and date fields in the source field being 
        imported, but a missing value indicator (e.g. ".") is not. Must be 
        converted to a null.  A missing value indicator is fine in the data 
        _once it has been imported_ but not beforehand.
    Checking is always necessary, even for a sample which has already been 
        examined. May have found a variable conflict and need to handle it after 
        it raises a mismatch error by turning faulty values to nulls.
    """
    debug = False
    ok_data = False        
    if fldtype == mg.FLDTYPE_NUMERIC:
        # must be numeric or empty string or dot (which we'll turn to NULL)
        if lib.is_numeric(raw_val, comma_dec_sep_ok):
            ok_data = True
            try:
                if comma_dec_sep_ok:
                    val = raw_val.replace(u",", u".")
                else:
                    val = raw_val
            except AttributeError:
                val = raw_val
        elif raw_val == u"" or raw_val is None:
            ok_data = True
            val = u"NULL"
        elif raw_val == mg.MISSING_VAL_INDICATOR: # not ok in numeric field
            ok_data = True
            feedback[mg.NULLED_DOTS] = True
            val = u"NULL"
        else:
            pass # no need to set val - not ok_data so exception later
    elif fldtype == mg.FLDTYPE_DATE:
        # must be pytime or datetime string or usable date string
        # or empty string or dot (which we'll turn to NULL).
        if is_pytime:
            if debug: print(u"pytime raw val: %s" % raw_val)
            val = lib.pytime_to_datetime_str(raw_val)
            if debug: print(u"pytime val: %s" % val)
            ok_data = True
        else:
            if debug: print(u"Raw val: %s" % raw_val)
            if raw_val == u"" or raw_val is None:
                ok_data = True
                val = u"NULL"
            elif raw_val == mg.MISSING_VAL_INDICATOR: # not ok in numeric fld
                ok_data = True
                if debug: print(u"Date field has a missing value.")
                feedback[mg.NULLED_DOTS] = True
                val = u"NULL"
            else:
                try:
                    if debug: print(u"Raw val: %s" % raw_val)
                    val = lib.get_std_datetime_str(raw_val)
                    if debug: print(u"Date val: %s" % val)
                    ok_data = True
                except Exception:
                    my_exceptions.DoNothingException("no need to set val - not "
                                                "ok_data so exception later")
    elif fldtype == mg.FLDTYPE_STRING:
        # None or empty string we'll turn to NULL
        ok_data = True
        if raw_val is None or raw_val == u"":
            val = u"NULL"
        else:
            val = raw_val
    else:
        raise Exception(u"Unexpected field type in importer.get_val()")
    if not ok_data:
        if ok_fldname in faulty2missing_fld_list:
            val = u"NULL" # replace faulty value with a null
        else:
            details = FIRST_MISMATCH_TPL % {u"row": row_num, u"value": raw_val, 
                                            u"fldtype": fldtype}
            raise my_exceptions.MismatchException(fldname=ok_fldname,
                                    expected_fldtype=fldtype, details=details)
    return val

def process_val(feedback, vals, row_num, row, ok_fldname, fldtypes, 
                faulty2missing_fld_list, comma_dec_sep_ok=False):
    """
    Add val to vals.
    feedback -- dic with mg.NULLED_DOTS
    NB field types are only a guess based on a sample of the first rows in the 
        file being imported.  Could be wrong.
    If checking, will validate and turn empty strings into nulls
        as required.  Also turn '.' into null as required (and leave msg).
    If not checking (e.g. because a pre-tested sample) only do the
        pytime (Excel) and empty string to null conversions.
    If all is OK, will add val to vals. NB val will need to be internally 
        quoted unless it is a NULL. 
    If not, will turn to missing if in faulty2missing_fld_list, otherwise will 
        raise an exception.
    Quote ready for inclusion in SQLite SQL insert query.
    """
    debug = False
    try:
        rawval = row[ok_fldname]
    except KeyError:
        try:
            int(ok_fldname[-3:])
            msg = (u" (NB some field names may have been altered to prevent "
                   u"duplicates or otherwise invalid names).")
        except Exception:
            msg = u""
        raise Exception(_("Row %(row_num)s doesn't have a value for the "
                          "\"%(ok_fldname)s\" field %(msg)s") % 
                        {u"row_num": row_num, u"ok_fldname": ok_fldname, 
                         u"msg": msg})
    is_pytime = lib.is_pytime(rawval)
    fldtype = fldtypes[ok_fldname]
    val = get_val(feedback, rawval, is_pytime, fldtype, ok_fldname, 
                  faulty2missing_fld_list, row_num, comma_dec_sep_ok)
    if fldtype != mg.FLDTYPE_NUMERIC and val != u"NULL":
        try:
            val = dbe_sqlite.quote_val(val)
        except Exception:
            raise Exception(_("Tried to quote %(val)s on row %(row_num)s but "
                              "failed.") % {u"val": val, u"row_num": row_num})
    vals.append(val)
    if debug: print(val)

def report_fld_n_mismatch(row, row_num, has_header, ok_fldnames, allow_none):
    debug = False
    if debug: print(row_num, row)
    if not allow_none:
        n_row_items = len([x for x in row.values() if x is not None])
    else:
        n_row_items = len(row)
    n_flds = len(ok_fldnames)
    if n_row_items != n_flds:
        if has_header:
            row_msg = _("Row %s (including header row)") % (row_num+1,)
        else:
            row_msg = _("Row %s") % row_num  
        # if csv has 2 flds and receives 3 vals will be var1:1,var2:2,None:[3]!
        vals = []
        for ok_fldname in ok_fldnames:
            vals.append(row[ok_fldname])
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

def add_rows(feedback, import_status, con, cur, rows, has_header, ok_fldnames, 
             fldtypes, faulty2missing_fld_list, progbar, steps_per_item, 
             gauge_start=0, row_num_start=0, allow_none=True, 
             comma_dec_sep_ok=False):
    """
    feedback -- dic with mg.NULLED_DOTS
    Add the rows of data (dicts), processing each cell as you go.
    If checking, will validate and turn empty strings into nulls
        as required.
    If not checking (e.g. because a pre-tested sample) only do the
        empty string to null conversions.
    row_num_start -- row number (not idx) starting on
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
        If a csv files does, however, it is not. Should be empty str.
    TODO - insert multiple lines at once for performance.
    """
    debug = False
    fldnames_clause = u", ".join([dbe_sqlite.quote_obj(x) for x 
                                   in ok_fldnames])
    for row_idx, row in enumerate(rows):
        if debug: 
            print(row)
            print(str(row_idx))
        if row_idx % 50 == 0:
            wx.Yield()
            if import_status[mg.CANCEL_IMPORT]:
                progbar.SetValue(0)
                raise my_exceptions.ImportCancelException
        gauge_start += 1
        row_num = row_num_start + row_idx
        #if debug and row_num == 12:
        #    print("Break on this line :-)")
        vals = []
        report_fld_n_mismatch(row, row_num, has_header, ok_fldnames, 
                              allow_none)
        try:
            for ok_fldname in ok_fldnames:
                process_val(feedback, vals, row_num, row, ok_fldname, 
                            fldtypes, faulty2missing_fld_list, comma_dec_sep_ok)
        except my_exceptions.MismatchException, e:
            if debug: print("A mismatch exception")
            raise # keep this particular type of exception bubbling out
        except Exception, e:
            raise
        # quoting must happen earlier so we can pass in NULL  
        fld_vals_clause = u", ".join([u"%s" % x for x in vals])
        SQL_insert_row = u"INSERT INTO %s " % mg.TMP_TBLNAME + \
            u"(%s) VALUES(%s)" % (fldnames_clause, fld_vals_clause)
        if debug: print(SQL_insert_row)
        try:
            cur.execute(SQL_insert_row)
            gauge_val = gauge_start + (row_num*steps_per_item)
            progbar.SetValue(gauge_val)
        except Exception, e:
            raise Exception(u"Unable to add row %s.\nCaused by error: %s"
                            % (row_num, lib.ue(e)))
    con.commit()

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
    SQL_drop_disp_tbl = u"DROP TABLE IF EXISTS %s" % mg.TMP_TBLNAME
    cur.execute(SQL_drop_disp_tbl)
    con.commit()

def post_fail_tidy(progbar, con, cur):
    drop_tmp_tbl(con, cur)
    lib.safe_end_cursor()
    cur.close()
    con.commit()
    con.close()
    progbar.SetValue(0)

def try_to_add_to_tmp_tbl(feedback, import_status, con, cur, file_path, 
                          tblname, has_header, ok_fldnames, fldtypes, 
                          faulty2missing_fld_list, data, progbar, 
                          steps_per_item, gauge_start, allow_none=True, 
                          comma_dec_sep_ok=False):
    debug = False
    if debug:
        print(u"Cleaned (ok) field names are: %s" % ok_fldnames)
        print(u"Field types are: %s" % fldtypes)
        print(u"Faulty to missing field list: %s" % faulty2missing_fld_list)
        print(u"Data is: %s" % data)
    try:
        con.commit()
        SQL_get_tblnames = u"""SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'"""
        cur.execute(SQL_get_tblnames) # otherwise it doesn't always seem to have the 
            # latest data on which tables exist
        drop_tmp_tbl(con, cur)
        if debug: print(u"Successfully dropped %s" % mg.TMP_TBLNAME)
    except Exception, e:
        raise
    try:
        tblname = mg.TMP_TBLNAME
        # oth_name_types -- ok_fldname, fldtype (taken from original source 
        # and the key will be ok_fldname)
        oth_name_types = []
        for ok_fldname in ok_fldnames:
            oth_name_types.append((ok_fldname, fldtypes[ok_fldname]))
        if debug: print(oth_name_types)
        getdata.make_sofa_tbl(con, cur, tblname, oth_name_types)
    except Exception, e:
        raise   
    try:
        # Add sample and then remaining data to disposable table.
        # Already been through sample once when assessing it so part way through 
        # process already.
        add_rows(feedback, import_status, con, cur, data, has_header, 
                 ok_fldnames, fldtypes, faulty2missing_fld_list, progbar, 
                 steps_per_item, gauge_start=gauge_start, row_num_start=1, 
                 allow_none=allow_none, comma_dec_sep_ok=comma_dec_sep_ok)
        return True
    except my_exceptions.MismatchException, e:
        feedback[mg.NULLED_DOTS] = False
        con.commit()
        progbar.SetValue(0)
        # go through again or raise an exception
        dlg = FixMismatchDlg(fldname=e.fldname, 
                             fldtype_choices=[e.expected_fldtype,], 
                             fldtypes=fldtypes, 
                             faulty2missing_fld_list=faulty2missing_fld_list, 
                             details=e.details,
                             assessing_sample=False)
        ret = dlg.ShowModal()
        if ret == wx.ID_CANCEL:
            raise Exception(u"Mismatch between data in column and expected "
                            u"column type")             
        else:
            return False # start again :-)

def add_to_tmp_tbl(feedback, import_status, con, cur, file_path, tblname, 
                   has_header, ok_fldnames, fldtypes, 
                   faulty2missing_fld_list, data, progbar, steps_per_item, 
                   gauge_start, allow_none=True, comma_dec_sep_ok=False):
    """
    Create fresh disposable table in SQLite and insert data into it.
    feedback -- dic with mg.NULLED_DOTS
    ok_fldnames -- cleaned field names (shouldn't have a sofa_id field)
    fldtypes -- dict with field types for original field names
    faulty2missing_fld_list -- list of fields where we should turn faulty values 
        to missing.
    data -- list of dicts using orig fld names
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
        If a csv files does, however, it is not. Should be empty str.
    Give it a unique identifier field as well.
    Set up the data type constraints needed.
    Keep trying till success or user decodes not to fix and keep going.  Fix 
        involves changing the relevant fldtype to string, which will accept 
        anything.
    """
    while True: # keep trying till success or user decodes not to fix & continue
        if try_to_add_to_tmp_tbl(feedback, import_status, con, cur, file_path, 
                tblname, has_header, ok_fldnames, fldtypes, 
                faulty2missing_fld_list, data, progbar, steps_per_item, 
                gauge_start, allow_none=True, 
                comma_dec_sep_ok=comma_dec_sep_ok):
            break
    
def tmp_to_named_tbl(con, cur, tblname, file_path, progbar, nulled_dots,
                     headless=False):
    """
    Rename table to final name.
    This part is only called once at the end and is so fast there is no need to
        report progress till completion.
    """
    debug = False
    try:
        SQL_drop_tbl = u"DROP TABLE IF EXISTS %s" % \
                                    getdata.tblname_qtr(mg.DBE_SQLITE, tblname)
        if debug: print(SQL_drop_tbl)
        cur.execute(SQL_drop_tbl)
        con.commit()
        SQL_rename_tbl = (u"ALTER TABLE %s RENAME TO %s" % 
                          (getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME), 
                           getdata.tblname_qtr(mg.DBE_SQLITE, tblname)))
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
    msg += _("\n\nYou can check your imported data by clicking the "
             "'Enter/Edit Data' button on the main form. You'll find your "
             "data in the '%s' database.") % mg.SOFA_DB
    if not headless:
        wx.MessageBox(msg % {"tbl": tblname})

def get_content_dets(strdata):
    debug = False
    try:
        max_row_len = max([len(x) for x in strdata])
    except Exception:
        max_row_len = None
    lines = [] # init
    for row in strdata:
        len_row = len(row)
        if debug: print(len_row, row)
        if len_row < max_row_len:
            # right pad sequence with empty str (to become empty str cells)
            row += [u"" for x in range(max_row_len - len_row)]
        line = u"<tr><td>" + u"</td><td>".join(row) + u"</td></tr>"
        lines.append(line)
    trows = u"\n".join(lines)
    content = u"<table border='1' style='border-collapse: collapse;'>" + \
                                u"<tbody>\n" + trows + u"\n</tbody></table>"
    n_lines_actual = len(lines)
    content_height = 35*n_lines_actual
    content_height = 300 if content_height > 300 else content_height
    return content, content_height


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
    
    
class HasHeaderGivenDataDlg(wx.Dialog):
    def __init__(self, parent, ext, strdata):
        debug = False
        wx.Dialog.__init__(self, parent=parent, title=_("Header row?"),
                           size=(850, 450), style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+200,120))
        self.parent = parent
        self.panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        explan = _(u"Does your %s file have a header row? Note - SOFA cannot "
                   u"handle multiple header rows.") % ext
        lbl_explan = wx.StaticText(self.panel, -1, explan)
        content, unused = get_content_dets(strdata)
        if debug: print(content)
        html_content = wx.html.HtmlWindow(self.panel, -1, size=(820,440))
        html_content.SetPage(content)
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
        szr_main.Add(html_content, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
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
    def __init__(self, parent, file_path, tblname, headless, 
                 headless_has_header, supplied_encoding=None):
        self.parent = parent
        self.file_path = file_path
        self.tblname = tblname
        self.headless = headless
        self.headless_has_header = headless_has_header
        self.supplied_encoding = supplied_encoding
        self.has_header = True
    
    def get_params(self):
        """
        Get any user choices required.
        """
        debug = False
        if self.headless:
            self.has_header = True
            return True
        else:
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
                           size=(550,300), 
                           style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,-1))
        self.CentreOnScreen(wx.VERTICAL)
        self.parent = parent
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.import_status = {mg.CANCEL_IMPORT: False} # can change and 
                                            # running script can check on it.
        self.file_type = FILE_UNKNOWN
        config_output.add_icon(frame=self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # file path
        lbl_file_path = wx.StaticText(self.panel, -1, _("Source File:"))
        lbl_file_path.SetFont(lblfont)
        self.txt_file = wx.TextCtrl(self.panel, -1, u"", size=(400,-1))
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
              "Name entered below:"))
        # internal SOFA name
        lbl_int_name = wx.StaticText(self.panel, -1, _("SOFA Table Name:"))
        lbl_int_name.SetFont(lblfont)
        self.txt_int_name = wx.TextCtrl(self.panel, -1, "", size=(280,-1))
        self.txt_int_name.Bind(wx.EVT_CHAR, self.on_int_name_char)
        # feedback
        self.lbl_feedback = wx.StaticText(self.panel)
        # buttons
        btn_help = wx.Button(self.panel, wx.ID_HELP)
        btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
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
        szr_file_path.Add(btn_help, 0, wx.LEFT, 10)
        szr_file_path.Add(lbl_file_path, 0, wx.LEFT, 10)
        szr_file_path.Add(self.txt_file, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_get_file = wx.FlexGridSizer(rows=1, cols=2, hgap=0, vgap=0)
        szr_get_file.AddGrowableCol(0,1) # idx, propn
        szr_get_file.Add(btn_file_path, 0, wx.ALIGN_RIGHT|wx.RIGHT, 10)
        szr_get_file.Add(btn_google, 0, wx.ALIGN_RIGHT|wx.RIGHT, 10)
        szr_int_name = wx.FlexGridSizer(rows=1, cols=2, hgap=0, vgap=0)
        szr_int_name.AddGrowableCol(0,1) # idx, propn
        szr_int_name.Add(lbl_int_name, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5)
        szr_int_name.Add(self.txt_int_name, 1, wx.ALIGN_RIGHT)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_import, 0, wx.ALIGN_RIGHT)
        szr_close = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_close.AddGrowableCol(0,2) # idx, propn
        szr_close.Add(self.lbl_feedback)        
        szr_close.Add(self.btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_file_path, 0, wx.GROW|wx.TOP, 20)
        szr_main.Add(szr_get_file, 0, wx.GROW|wx.TOP, 10)
        szr_main.Add(lbl_comment, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_int_name, 0, wx.GROW|wx.ALL, 10)
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
            filestart, unused = get_file_start_ext(path)
            newname = process_tblname(filestart)
            self.txt_int_name.SetValue(newname)
        dlg_get_file.Destroy()
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        self.btn_import.SetDefault()
        event.Skip()
    
    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:importing"
        webbrowser.open_new_tab(url)
        event.Skip()
    
    def on_btn_google(self, event):
        "Open dialog and take the file selected (if any)"
        dlg_gdata = gdata_downloader.GdataDownloadDlg(self)
        # MUST have a parent to enforce modal in Windows
        ret = dlg_gdata.ShowModal()
        downloaded = False
        if ret != wx.ID_CLOSE: # successfully downloaded
            downloaded = True
            path = os.path.join(mg.INT_PATH, mg.GOOGLE_DOWNLOAD)
            self.txt_file.SetValue(path)
            filestart, unused = get_file_start_ext(path)
            newname = process_tblname(filestart)
            self.txt_int_name.SetValue(newname)
        self.txt_int_name.SetFocus()
        self.align_btns_to_completeness()
        self.btn_import.SetDefault()
        if downloaded:
            # start import automatically
            self.run_import()
        event.Skip()
        
    def on_close(self, event):
        self.Destroy()
    
    def on_cancel(self, event):
        self.import_status[mg.CANCEL_IMPORT] = True

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
        run_gui_import(self)
        event.Skip()

def get_file_start_ext(path):
    unused, filename = os.path.split(path)
    filestart, extension = os.path.splitext(filename)
    return filestart, extension

def check_tblname(file_path, tblname, headless):
    """
    Returns tblname (None if no suitable name to use).
    Checks table name and gives user option of correcting it if problems.
    Raises exception if no suitable name selected.
    """
    # check existing names
    valid, err = dbe_sqlite.valid_tblname(tblname)
    if not valid:
        if headless:
            raise Exception("Faulty SOFA table name.")
        else:
            title = _("FAULTY SOFA TABLE NAME")
            msg = (_("You can only use letters, numbers and underscores in "
                   "a SOFA Table Name. Use another name?\nOrig error: %s") 
                   % err)
            ret = wx.MessageBox(msg, title, wx.YES_NO|wx.ICON_QUESTION)
            if ret == wx.NO:
                raise Exception(u"Had a problem with faulty SOFA Table "
                                u"Name but user cancelled initial process "
                                u"of resolving it")
            elif ret == wx.YES:
                return None
    duplicate = getdata.dup_tblname(tblname)
    if duplicate:
        if not headless: # assume OK to overwrite existing table name with 
            # fresh data if running headless
            title = _("SOFA NAME ALREADY EXISTS")
            msg = _("A table named \"%(tbl)s\" "
                  "already exists in the SOFA default database.\n\n"
                  "Do you want to replace it with the new data from "
                  "\"%(fil)s\"?")
            ret = wx.MessageBox(msg % {"tbl": tblname, "fil": file_path}, 
                                title, wx.YES_NO|wx.ICON_QUESTION)
            if ret == wx.NO: # no overwrite so get new one (or else!)
                wx.MessageBox(_("Please change the SOFA Table Name and try "
                                "again"))
                return None
            elif ret == wx.YES:
                my_exceptions.DoNothingException() # use name (overwrite orig)
    return tblname

class DummyProgbar(object):
    def SetValue(self, unused):
        pass

class DummyLabel(object):
    def SetLabel(self, unused):
        pass      

class DummyImporter(object):    
    def __init__(self):
        self.progbar = DummyProgbar()
        self.import_status = {mg.CANCEL_IMPORT: False} # can change and 
        # running script can check on it.
        self.lbl_feedback = DummyLabel()
        
def run_gui_import(self):
    run_import(self)
    
def run_headless_import(file_path, tblname, headless_has_header, 
                        supplied_encoding=None):
    dummy_importer = DummyImporter()
    run_import(dummy_importer, headless=True, file_path=file_path, 
               tblname=tblname, headless_has_header=headless_has_header,
               supplied_encoding=supplied_encoding)

def run_import(self, headless=False, file_path=None, tblname=None, 
               headless_has_header=True, supplied_encoding=None):
    """
    Identify type of file by extension and open dialog if needed
        to get any additional choices e.g. separator used in 'csv'.
    headless -- enable script to be run without user intervention. Anything
        that would normally prompt user decisions raises an exception 
        instead.
    headless_has_header -- seeing as we won't tell it through the GUI if 
        headless, need to tell it here.
    supplied_encoding -- if headless, we can't manually select from likely 
        encoding so must supply here.
    """
    dd = mg.DATADETS_OBJ
    if not headless:
        self.align_btns_to_importing(importing=True)
        self.progbar.SetValue(0)
        file_path = self.txt_file.GetValue()
    if not file_path:
        if headless:
            raise Exception(_(u"A file name must be supplied when importing"
                              u" if running in headless mode."))
        else:
            wx.MessageBox(_("Please select a file"))
            self.align_btns_to_importing(importing=False)
            self.txt_file.SetFocus()
            return
    # identify file type
    unused, extension = get_file_start_ext(file_path)
    if extension.lower() == u".csv":
        self.file_type = FILE_CSV
    elif extension.lower() == u".txt":
        if headless:
            self.file_type = FILE_CSV
        else:
            ret = wx.MessageBox(_("SOFA imports txt files as csv files.\n\n"
                                 "Is your txt file a valid csv file?"), 
                                 caption=_("CSV FILE?"), style=wx.YES_NO)
            if ret == wx.NO:
                wx.MessageBox(_("Unable to import txt files unless csv "
                                "format inside"))
                self.align_btns_to_importing(importing=False)
                return
            else:
                self.file_type = FILE_CSV
    elif extension.lower() == u".xls":
        self.file_type = FILE_EXCEL
    elif extension.lower() == u".ods":
        self.file_type = FILE_ODS
    elif extension.lower() == u".xlsx":
        self.file_type = FILE_UNKNOWN
        xlsx_msg = ("XLSX files are not currently supported. Please save"
                    " as XLS or convert to another supported format.")
        if headless:
            raise Exception(xlsx_msg)
        else:
            wx.MessageBox(xlsx_msg)
            self.align_btns_to_importing(importing=False)
            return
    else:
        unknown_msg = _("Files with the file name extension "
                        "'%s' are not supported") % extension
        if headless:
            raise Exception(unknown_msg)
        else:
            self.file_type = FILE_UNKNOWN
            wx.MessageBox(unknown_msg)
            self.align_btns_to_importing(importing=False)
            return
    if not headless:
        tblname = self.txt_int_name.GetValue()
    if not tblname:
        if headless:
            raise Exception("Unable to import headless unless a table "
                            "name supplied")
        else:
            wx.MessageBox(_("Please select a SOFA Table Name for the file"))
            self.align_btns_to_importing(importing=False)
            self.txt_int_name.SetFocus()
            return
    if u" " in tblname:
        empty_spaces_msg = _("SOFA Table Name can't have empty spaces")
        if headless:
            raise Exception(empty_spaces_msg)
        else:
            wx.MessageBox(empty_spaces_msg)
            self.align_btns_to_importing(importing=False)
            return
    bad_chars = [u"-", ]
    for bad_char in bad_chars:
        if bad_char in tblname:
            bad_char_msg = (_("Do not include '%s' in SOFA Table Name") % 
                            bad_char)
            if headless:
                raise Exception(bad_char_msg)
            else:
                wx.MessageBox(bad_char_msg)
                self.align_btns_to_importing(importing=False)
                return
    if tblname[0] in [unicode(x) for x in range(10)]:
        digit_msg = _("SOFA Table Names cannot start with a digit")
        if headless:
            raise Exception(digit_msg)
        else:
            wx.MessageBox(digit_msg)
            self.align_btns_to_importing(importing=False)
            return
    try:
        final_tblname = check_tblname(file_path, tblname, headless)
        if final_tblname is None:
            if headless:
                raise Exception("Table name supplied is inappropriate for "
                                "some reason.")
            else:
                self.txt_int_name.SetFocus()
                self.align_btns_to_importing(importing=False)
                self.progbar.SetValue(0)
                return
    except Exception:
        if headless:
            raise
        else:
            wx.MessageBox(_("Please select a suitable SOFA Table Name "
                            "and try again"))
            self.align_btns_to_importing(importing=False)
            return
    # import file
    if self.file_type == FILE_CSV:
        import csv_importer
        file_importer = csv_importer.CsvImporter(self, file_path, 
                                final_tblname, headless, headless_has_header,
                                supplied_encoding)
    elif self.file_type == FILE_EXCEL:
        import excel_importer
        file_importer = excel_importer.ExcelImporter(self, file_path,
                                final_tblname, headless, headless_has_header)
    elif self.file_type == FILE_ODS:
        import ods_importer
        file_importer = ods_importer.OdsImporter(self, file_path,
                                final_tblname, headless, headless_has_header)
    proceed = False
    try:
        proceed = file_importer.get_params()
    except Exception, e:
        if headless:
            raise
        else:
            wx.MessageBox(_("Unable to import data\n\nError") + u": %s" % 
                          lib.ue(e))
            lib.safe_end_cursor()
    if proceed:
        try:
            file_importer.import_content(self.progbar, self.import_status,
                                         self.lbl_feedback)
            dd.set_db(dd.db, tbl=tblname)
            lib.safe_end_cursor()
        except my_exceptions.ImportConfirmationRejected, e:
            lib.safe_end_cursor()
            if headless: # although should never occur when headless
                raise
            else:
                wx.MessageBox(lib.ue(e))
        except my_exceptions.ImportCancelException, e:
            lib.safe_end_cursor()
            self.import_status[mg.CANCEL_IMPORT] = False # reinit
            if not headless: # should never occur when headless
                wx.MessageBox(lib.ue(e))
        except Exception, e:
            if headless:
                raise
            else:
                self.progbar.SetValue(0)
                lib.safe_end_cursor()
                wx.MessageBox(_("Unable to import data\n\nError") + u": %s" % 
                              lib.ue(e))
    if not headless:
        self.align_btns_to_importing(importing=False)
