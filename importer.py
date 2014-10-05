#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import wx #@UnusedImport
import wx.html

import basic_lib as b
import my_globals as mg
import lib
import my_exceptions
import getdata # must be before anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite

FILE_CSV = u"csv"
FILE_EXCEL = u"excel"
FILE_ODS = u"ods"
FILE_UNKNOWN = u"unknown"
GAUGE_STEPS = 50
FIRST_MISMATCH_TPL = (u"\nRow: %(row)s"
    u"\nValue: \"%(value)s\""
    u"\nExpected column type: %(fldtype)s")
ROWS_TO_SHOW_USER = 5 # only need enough to decide if a header (except for csv when also needing to choose encoding)


class DlgChooseFldtype(wx.Dialog):
    def __init__(self, fldname):
        title_txt = _(u"CHOOSE FIELD TYPE")
        wx.Dialog.__init__(self, None, title=title_txt, size=(500,600), 
            style=wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        choice_txt = (_(u"It wasn't possible to guess the appropriate field "
            u"type for \"%(fldname)s\"\nbecause it only contained empty text in"
            u" the rows SOFA sampled.\n\nPlease select the data type you want "
            u"this entire column imported as. If in doubt, choose \"%(text)s\"") 
            % {u"fldname": fldname, "text": mg.FLDTYPE_STRING_LBL})
        lbl_choice = wx.StaticText(self.panel, -1, choice_txt)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_num = wx.Button(self.panel, mg.RET_NUMERIC, mg.FLDTYPE_NUMERIC_LBL)
        btn_num.Bind(wx.EVT_BUTTON, self.on_num)
        szr_btns.Add(btn_num, 0, wx.LEFT|wx.RIGHT, 10)
        btn_date = wx.Button(self.panel, mg.RET_DATE, mg.FLDTYPE_DATE_LBL)
        btn_date.Bind(wx.EVT_BUTTON, self.on_date)
        szr_btns.Add(btn_date, 0,  wx.LEFT|wx.RIGHT, 10)
        btn_text = wx.Button(self.panel, mg.RET_TEXT, mg.FLDTYPE_STRING_LBL)
        btn_text.Bind(wx.EVT_BUTTON, self.on_text)
        szr_btns.Add(btn_text, 0, wx.LEFT|wx.RIGHT, 10)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        szr_btns.Add(btn_cancel, 0,  wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(lbl_choice, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
    
    def on_num(self, event):
        self.Destroy()
        self.SetReturnCode(mg.RET_NUMERIC)
    
    def on_date(self, event):
        self.Destroy()
        self.SetReturnCode(mg.RET_DATE)
        
    def on_text(self, event):
        self.Destroy()
        self.SetReturnCode(mg.RET_TEXT)
        
    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)


class DlgFixMismatch(wx.Dialog):
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
                u"data in \"%(fldname)s\".\n\nFirst inconsistency:%(details)s"
                u"\n\nPlease select the data type you want this entire column "
                u"imported as.") % {u"fldname": fldname, # no fldtypes if sample
                u"details": details})
        else:
            choice_txt = (_(u"Data was found in \"%(fldname)s\" which doesn't "
                u"match the expected data type (%(data_type)s). "
                u"\n%(details)s"
                u"\n\nPlease select the data type you want this entire column "
                u"imported as.") % {u"fldname": fldname, 
                u"data_type": mg.FLDTYPE_KEY2LBL[fldtypes[fldname]], 
                u"details": details})
        lbl_choice = wx.StaticText(self.panel, -1, choice_txt)
        types = u" or ".join(["\"%s\"" % mg.FLDTYPE_KEY2LBL[x] for x 
            in self.fldtype_choices])
        lbl_implications = wx.StaticText(self.panel, -1, _(u"If you choose %s,"
            u" any values that are not of that type will be turned to missing."
            % types))
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        if mg.FLDTYPE_NUMERIC_KEY in self.fldtype_choices:
            btn_num = wx.Button(self.panel, mg.RET_NUMERIC, 
                mg.FLDTYPE_NUMERIC_LBL)
            btn_num.Bind(wx.EVT_BUTTON, self.on_num)
            szr_btns.Add(btn_num, 0, wx.LEFT|wx.RIGHT, 10)
        if mg.FLDTYPE_DATE_KEY in self.fldtype_choices:
            btn_date = wx.Button(self.panel, mg.RET_DATE, mg.FLDTYPE_DATE_LBL)
            btn_date.Bind(wx.EVT_BUTTON, self.on_date)
            szr_btns.Add(btn_date, 0,  wx.LEFT|wx.RIGHT, 10)
        btn_text = wx.Button(self.panel, mg.RET_TEXT, mg.FLDTYPE_STRING_LBL)
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
        self.fldtypes[self.fldname] = mg.FLDTYPE_NUMERIC_KEY
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_NUMERIC)
    
    def on_date(self, event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_DATE_KEY
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_DATE)
        
    def on_text(self, event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_STRING_KEY
        self.Destroy()
        self.SetReturnCode(mg.RET_TEXT)
        
    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)

def has_header_row(row1_types, row2_types, str_type, empty_type, non_str_types):
    row1_types_set = set(row1_types)
    row2_types_set = set(row2_types)
    n_types = len(row1_types_set)
    has_strings = str_type in row1_types_set
    has_empties = empty_type in row1_types_set
    row1_strings_only = (has_strings and (n_types == 1 
        or (n_types == 2 and has_empties)))
    non_string_set = set(non_str_types) # ignore EMPTY
    row2_has_non_strings = len(row2_types_set.intersection(non_string_set)) > 0
    return row1_strings_only and row2_has_non_strings

def get_sample_rows(file_path):
    debug = False
    try:
        f = open(file_path) # don't use "U" - let it fail if necessary
            # and suggest an automatic cleanup.
        sample_rows = []
        for i, row in enumerate(f):
            if i < 20:
                if debug: print(row)
                sample_rows.append(row)
    except IOError:
            raise Exception(u"Unable to find file \"%s\" for importing. "
                u"Please check that file exists." % file_path)
    except Exception, e:
        raise Exception(u"Unable to open and sample file. "
            u"\nCaused by error: %s" % b.ue(e))
    return sample_rows

def get_best_fldtype(fldname, type_set, faulty2missing_fld_list, 
        first_mismatch=u"", headless=False):
    """
    type_set may contain empty_str as well as actual types. Useful to remove
    empty str and see what is left.
    
    faulty2missing_fld_list -- so we can stay with the selected best type by 
    setting faulty values that don't match type to missing.
    
    headless -- shouldn't require user input. 
    
    STRING is the fallback.
    """
    assessing_sample = True
    main_type_set = type_set.copy()
    main_type_set.discard(mg.VAL_EMPTY_STRING)
    if main_type_set == set([mg.VAL_NUMERIC]):
        fldtype = mg.FLDTYPE_NUMERIC_KEY
    elif main_type_set == set([mg.VAL_DATE]):
        fldtype = mg.FLDTYPE_DATE_KEY
    elif main_type_set == set([mg.VAL_STRING]):
        fldtype = mg.FLDTYPE_STRING_KEY
    elif type_set == set([mg.VAL_EMPTY_STRING]):
        if not headless:
            dlg = DlgChooseFldtype(fldname)
            ret = dlg.ShowModal()
            if ret == wx.ID_CANCEL:
                raise Exception(u"Needed a data type for \"%s\"." % fldname)
            elif ret == mg.RET_NUMERIC:
                fldtype = mg.FLDTYPE_NUMERIC_KEY
            elif ret == mg.RET_DATE:
                fldtype = mg.FLDTYPE_DATE_KEY
            elif ret == mg.RET_TEXT:
                fldtype = mg.FLDTYPE_STRING_KEY
            else:
                raise Exception(u"Unexpected return type from DlgChooseFldtype")
        else:
            fldtype = mg.FLDTYPE_STRING_KEY
    elif len(main_type_set) > 1:
        # get user to choose
        fldtypes = {}
        fldtype_choices = []
        if mg.VAL_NUMERIC in main_type_set:
            fldtype_choices.append(mg.FLDTYPE_NUMERIC_KEY)
        if mg.VAL_DATE in main_type_set:
            fldtype_choices.append(mg.FLDTYPE_DATE_KEY)
        if not headless:
            dlg = DlgFixMismatch(fldname=fldname, 
                fldtype_choices=fldtype_choices, fldtypes=fldtypes, 
                faulty2missing_fld_list=faulty2missing_fld_list, 
                details=first_mismatch, assessing_sample=assessing_sample)
            ret = dlg.ShowModal()
            if ret == wx.ID_CANCEL:
                raise Exception(u"Inconsistencies in data type.")         
            else:
                fldtype = fldtypes[fldname]
        else:
            fldtype = mg.FLDTYPE_STRING_KEY
    else:
        fldtype = mg.FLDTYPE_STRING_KEY
    return fldtype

def process_fldnames(raw_names, headless=False, force_quickcheck=False):
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
                    raw_name = raw_name.decode("utf-8")
                except UnicodeDecodeError, e:
                    raise Exception(u"Unable to process raw field name."
                        u"\nCaused by error: %s" % b.ue(e))
            name = raw_name.replace(u" ", u"_")
            if len(name) > mg.MAX_VAL_LEN_IN_SQL_CLAUSE:
                # just truncate - let the get_unique_fldnames function handle the shortened names as it normally would
                name = name[:mg.MAX_VAL_LEN_IN_SQL_CLAUSE-mg.FLDNAME_ZFILL] # Got to leave some room for what get_unique_fldnames() appends
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
            u"\nCaused by error: %s" % b.ue(e))
    quickcheck = False
    n_names = len(names)
    if n_names > 50:
        if headless:
            if force_quickcheck: quickcheck = True
        else:
            # don't test each name individually - takes too long
            # we gain speed and lose ability to single out bad variable name
            if wx.MessageBox(_(u"There are %s fields so the process of "
                    u"checking them all will take a while. Do you want to do a "
                    u"quick check only?") % n_names, 
                    caption=_("QUICK CHECK ONLY?"), style=wx.YES_NO) == wx.YES:
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
    return lib.get_safer_name(rawname)

def assess_sample_fld(sample_data, has_header, ok_fldname, ok_fldnames, 
        faulty2missing_fld_list, allow_none=True, comma_dec_sep_ok=False, 
        headless=False):
    """
    NB client code gets number of fields in row 1. Then for each field, it 
    traverses rows (i.e. travels down a col, then down the next etc). If a row 
    has more flds than are in the first row, no problems will be picked up here 
    because we never go into the problematic column. But we will strike None 
    values in csv files, for eg, when a row is shorter than it should be.
    
    sample_data -- list of dicts.
    
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
    If a csv files does, however, it is not. Should be empty str.
    
    For individual values, if numeric, assume numeric, 
        if date, assume date, 
        if string, either an empty string or an ordinary string.
    
    For entire field sample, numeric if only contains numeric and empty strings 
    (could be missings).
    
    Date if only contains dates and empty strings (could be missings).
    
    String otherwise.   
    
    Return field type.
    """
    debug = False
    type_set = set()
    first_mismatch = u""
    expected_fldtype = u""
    start_row_num = 2 if has_header else 1
    for row_num, row in enumerate(sample_data, start_row_num):
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
                u"value": val, 
                u"fldtype": expected_fldtype})
    fldtype = get_best_fldtype(fldname=ok_fldname, type_set=type_set, 
        faulty2missing_fld_list=faulty2missing_fld_list,
        first_mismatch=first_mismatch, headless=headless)
    return fldtype

def is_blank_raw_val(raw_val):
    """
    Need to handle solo single quotes or solo double quotes. May be result of 
    escaping issues but be derived from csv rows like 1,"",4. 
    """
    return raw_val in (u"", u"''", u'""', None)

def get_val(feedback, raw_val, is_pytime, fldtype, ok_fldname, 
        faulty2missing_fld_list, row_num, comma_dec_sep_ok=False):
    """
    feedback -- dic with mg.NULLED_DOTS
    
    Missing values are OK in numeric and date fields in the source field being 
    imported, but a missing value indicator (e.g. ".") is not. Must be 
    converted to a null. A missing value indicator is fine in the data _once it 
    has been imported_ but not beforehand.
    
    Checking is always necessary, even for a sample which has already been 
    examined. May have found a variable conflict and need to handle it after it 
    raises a mismatch error by turning faulty values to nulls.
    """
    debug = False
    ok_data = False        
    if fldtype == mg.FLDTYPE_NUMERIC_KEY:
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
        elif is_blank_raw_val(raw_val):
            ok_data = True
            val = u"NULL"
        elif raw_val == mg.MISSING_VAL_INDICATOR: # not ok in numeric field
            ok_data = True
            feedback[mg.NULLED_DOTS] = True
            val = u"NULL"
        else:
            pass # no need to set val - not ok_data so exception later
    elif fldtype == mg.FLDTYPE_DATE_KEY:
        # must be pytime or datetime string or usable date string
        # or empty string or dot (which we'll turn to NULL).
        if is_pytime:
            if debug: print(u"pytime raw val: %s" % raw_val)
            val = lib.pytime_to_datetime_str(raw_val)
            if debug: print(u"pytime val: %s" % val)
            ok_data = True
        else:
            if debug: print(u"Raw val: %s" % raw_val)
            if is_blank_raw_val(raw_val):
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
                    pass
                    # no need to set val - not ok_data so exception later
    elif fldtype == mg.FLDTYPE_STRING_KEY:
        # None or empty string we'll turn to NULL
        ok_data = True
        if is_blank_raw_val(raw_val):
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
                u"fldtype": mg.FLDTYPE_KEY2LBL[fldtype]}
            raise my_exceptions.Mismatch(fldname=ok_fldname,
                expected_fldtype=fldtype, details=details)
    return val

def process_val(feedback, vals, row_num, row, ok_fldname, fldtypes, 
        faulty2missing_fld_list, comma_dec_sep_ok=False):
    """
    Add val to vals.
    
    feedback -- dic with mg.NULLED_DOTS
    
    NB field types are only a guess based on a sample of the first rows in the 
    file being imported.  Could be wrong.
    
    If checking, will validate and turn empty strings into nulls as required. 
    Also turn '.' into null as required (and leave msg).
    
    If not checking (e.g. because a pre-tested sample) only do the 
    pytime (Excel) and empty string to null conversions.
    
    If all is OK, will add val to vals. NB val will need to be internally 
    quoted unless it is a NULL. Watch for "But I say ""No"" don't I".
    
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
            "\"%(ok_fldname)s\" field %(msg)s") % {u"row_num": row_num, 
            u"ok_fldname": ok_fldname, u"msg": msg})
    is_pytime = lib.is_pytime(rawval)
    fldtype = fldtypes[ok_fldname]
    val = get_val(feedback, rawval, is_pytime, fldtype, ok_fldname, 
        faulty2missing_fld_list, row_num, comma_dec_sep_ok)
    if fldtype != mg.FLDTYPE_NUMERIC_KEY and val != u"NULL":
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
        vals_str = (unicode(vals).replace(u"', '", u",").replace(u"['", u"")
            .replace(u"']", u"").replace(u"',", u",").replace(u", None", u"")
            .replace(u"]", u""))
        raise Exception(_("Incorrect number of fields in %(row_msg)s.\n\n"
            "Expected %(n_flds)s but found %(n_row_items)s.\n\n"
            "Faulty Row: %(vals_str)s") % {"row_msg": row_msg, "n_flds": n_flds, 
            "n_row_items": n_row_items, "vals_str": vals_str})

def add_rows(feedback, import_status, con, cur, rows, has_header, ok_fldnames, 
        fldtypes, faulty2missing_fld_list, progbar, steps_per_item, 
        gauge_start=0, allow_none=True, comma_dec_sep_ok=False):
    """
    feedback -- dic with mg.NULLED_DOTS
    
    Add the rows of data (dicts), processing each cell as you go.
    
    If checking, will validate and turn empty strings into nulls as required.
    
    If not checking (e.g. because a pre-tested sample) only do the
    empty string to null conversions.
    
    allow_none -- if Excel returns None for an empty cell that is correct bvr.
    
    If a csv files does, however, it is not. Should be empty str.
    
    TODO - insert multiple lines at once for performance.
    """
    debug = False
    fldnames_clause = u", ".join([dbe_sqlite.quote_obj(x) for x 
        in ok_fldnames])
    start_row_num = 2 if has_header else 1
    for row_num, row in enumerate(rows, start_row_num):
        if debug: 
            print(row)
            print(str(row_num))
        if row_num % 50 == 0:
            wx.Yield()
            if import_status[mg.CANCEL_IMPORT]:
                progbar.SetValue(0)
                raise my_exceptions.ImportCancel
        gauge_start += 1
        #if debug and row_num == 12:
        #    print("Break on this line :-)")
        vals = []
        report_fld_n_mismatch(row, row_num, has_header, ok_fldnames, 
            allow_none)
        try:
            for ok_fldname in ok_fldnames:
                process_val(feedback, vals, row_num, row, ok_fldname, 
                    fldtypes, faulty2missing_fld_list, comma_dec_sep_ok)
        except my_exceptions.Mismatch, e:
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
                % (row_num, b.ue(e)))
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
        tblname, has_header, ok_fldnames, fldtypes, faulty2missing_fld_list, 
        data, progbar, steps_per_item, gauge_start, allow_none=True, 
        comma_dec_sep_ok=False, headless=False):
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
        getdata.make_sofa_tbl(con, cur, tblname, oth_name_types, 
            headless=headless)
    except Exception, e:
        raise   
    try:
        # Add sample and then remaining data to disposable table.
        # Already been through sample once when assessing it so part way through 
        # process already.
        add_rows(feedback, import_status, con, cur, data, has_header, 
            ok_fldnames, fldtypes, faulty2missing_fld_list, progbar, 
            steps_per_item, gauge_start=gauge_start, allow_none=allow_none, 
            comma_dec_sep_ok=comma_dec_sep_ok)
        return True
    except my_exceptions.Mismatch, e:
        feedback[mg.NULLED_DOTS] = False
        con.commit()
        progbar.SetValue(0)
        # go through again or raise an exception
        dlg = DlgFixMismatch(fldname=e.fldname, 
            fldtype_choices=[e.expected_fldtype,], fldtypes=fldtypes, 
            faulty2missing_fld_list=faulty2missing_fld_list, details=e.details,
            assessing_sample=False)
        ret = dlg.ShowModal()
        if ret == wx.ID_CANCEL:
            raise Exception(u"Mismatch between data in column and expected "
                u"column type")             
        else:
            return False # start again :-)

def add_to_tmp_tbl(feedback, import_status, con, cur, file_path, tblname, 
        has_header, ok_fldnames, fldtypes, faulty2missing_fld_list, data, 
        progbar, steps_per_item, gauge_start, allow_none=True, 
        comma_dec_sep_ok=False, headless=False):
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
    
    Keep trying till success or user decodes not to fix and keep going. Fix 
    involves changing the relevant fldtype to string, which will accept 
    anything.
    """
    while True: # keep trying till success or user decodes not to fix & continue
        if try_to_add_to_tmp_tbl(feedback, import_status, con, cur, file_path, 
                tblname, has_header, ok_fldnames, fldtypes, 
                faulty2missing_fld_list, data, progbar, steps_per_item, 
                gauge_start, allow_none=True, 
                comma_dec_sep_ok=comma_dec_sep_ok, headless=headless):
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
        SQL_drop_tbl = (u"DROP TABLE IF EXISTS %s" % 
            getdata.tblname_qtr(mg.DBE_SQLITE, tblname))
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
            u"\nCaused by error: %s" % b.ue(e))
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


class DlgHasHeader(wx.Dialog):
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
        lbl_with_header = wx.StaticText(self.panel, -1, 
            _("Example with header"))
        lbl_with_header.SetFont(mg.LABEL_FONT)
        img_ctrl_with_header = wx.StaticBitmap(self.panel)
        img_with_header = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
            u"%s_with_header.xpm" % ext), wx.BITMAP_TYPE_XPM)
        bmp_with_header = wx.BitmapFromImage(img_with_header)
        img_ctrl_with_header.SetBitmap(bmp_with_header)
        lbl_without_header = wx.StaticText(self.panel, -1, _("Example without"))
        lbl_without_header.SetFont(mg.LABEL_FONT)
        img_ctrl_without_header = wx.StaticBitmap(self.panel)
        img_without_header = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
            u"%s_without_header.xpm" % ext), wx.BITMAP_TYPE_XPM)
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
    
    
class DlgHasHeaderGivenData(wx.Dialog):
    def __init__(self, parent, ext, strdata, prob_has_hdr=True):
        debug = False
        wx.Dialog.__init__(self, parent=parent, title=_("Header row?"),
            size=(850, 250), style=wx.CAPTION|wx.SYSTEM_MENU, 
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
        html_content = wx.html.HtmlWindow(self.panel, -1, size=(820,240))
        html_content.SetPage(content)
        btn_has_header = wx.Button(self.panel, mg.HAS_HEADER, 
            _("Has Header Row"))
        btn_has_header.Bind(wx.EVT_BUTTON, self.on_btn_has_header)
        btn_no_header = wx.Button(self.panel, -1, _("No Header"))
        btn_no_header.Bind(wx.EVT_BUTTON, self.on_btn_no_header)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        if prob_has_hdr:
            btn_has_header.SetDefault()
        else:
            btn_no_header.SetDefault()
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
            dlg = DlgHasHeader(self.parent, self.ext)
            ret = dlg.ShowModal()
            if debug: print(unicode(ret))
            if ret == wx.ID_CANCEL:
                return False
            else:
                self.has_header = (ret == mg.HAS_HEADER)
                return True
