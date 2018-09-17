import os
import wx #@UnusedImport
import wx.html2

## enable headless use
try:
    _('')
except NameError:
    import gettext
    gettext.install(domain='sofastats', localedir='./locale')

from .. import basic_lib as b #@UnresolvedImport
from .. import my_globals as mg #@UnresolvedImport
from .. import lib #@UnresolvedImport
from .. import my_exceptions #@UnresolvedImport

from .. import setup_sofastats #@UnresolvedImport @UnusedImport
from .. import getdata  #@UnresolvedImport must be before anything referring to plugin modules
from ..dbe_plugins import dbe_sqlite #@UnresolvedImport

NULL_INDICATOR = None  #'NULL'
FILE_CSV = 'csv'
FILE_EXCEL = 'excel'
FILE_ODS = 'ods'
FILE_UNKNOWN = 'unknown'
FIRST_MISMATCH_TPL = ('\nRow: {row}'
    '\nValue: "{value}"'
    '\nExpected column type: {fldtype}')
ROWS_TO_SHOW_USER = 5  ## only need enough to decide if a header (except for csv when also needing to choose encoding)


class DlgChooseFldtype(wx.Dialog):
    def __init__(self, fldname):
        title_txt = _('CHOOSE FIELD TYPE')
        wx.Dialog.__init__(self, None, title=title_txt, size=(500,600),
            style=wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        choice_txt = (_("It wasn't possible to guess the appropriate field "
            "type for \"%(fldname)s\"\nbecause it only contained empty text in"
            " the rows SOFA sampled.\n\nPlease select the data type you want "
            "this entire column imported as. If in doubt, choose \"%(text)s\"") 
            % {'fldname': fldname, 'text': mg.FLDTYPE_STRING_LBL})
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
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        szr_btns.Add(btn_cancel, 0,  wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(lbl_choice, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_num(self, _event):
        self.Destroy()
        self.SetReturnCode(mg.RET_NUMERIC)

    def on_date(self, _event):
        self.Destroy()
        self.SetReturnCode(mg.RET_DATE)

    def on_text(self, _event):
        self.Destroy()
        self.SetReturnCode(mg.RET_TEXT)

    def on_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## only for dialogs 
        ## (MUST come after Destroy)


class DlgFixMismatch(wx.Dialog):
    ## weird bugs when using stdbtndialog here and calling dlg multiple times
    ## actual cause not known but buggy original had a setup_btns method
    def __init__(self, fldname, fldtype_choices, fldtypes, 
             faulty2missing_fld_list, details, assessing_sample=False):
        """
        fldtype_choices -- doesn't include string.
        """
        if assessing_sample:
            title_txt = _('MIX OF DATA TYPES')
        else:
            title_txt = _('DATA TYPE MISMATCH')
        self.fldname = fldname
        self.fldtype_choices = fldtype_choices
        self.fldtypes = fldtypes
        self.faulty2missing_fld_list = faulty2missing_fld_list
        wx.Dialog.__init__(self, None, title=title_txt, size=(500,600),
            style=wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        if assessing_sample:
            choice_txt = (_("A mix of data types was found in a sample of "
                "data in \"%(fldname)s\".\n\nFirst inconsistency:%(details)s"
                "\n\nPlease select the data type you want this entire column "
                "imported as.") % {"fldname": fldname,  ## no fldtypes if sample
                "details": details})
        else:
            choice_txt = (_("Data was found in \"%(fldname)s\" which doesn't "
                "match the expected data type (%(data_type)s). "
                "\n%(details)s"
                "\n\nPlease select the data type you want this entire column "
                "imported as.") % {"fldname": fldname,
                "data_type": mg.FLDTYPE_KEY2LBL[fldtypes[fldname]],
                "details": details})
        lbl_choice = wx.StaticText(self.panel, -1, choice_txt)
        types = ' or '.join([f'"{mg.FLDTYPE_KEY2LBL[x]}"'
            for x in self.fldtype_choices])
        lbl_implications = wx.StaticText(self.panel, -1, _("If you choose %s,"
            " any values that are not of that type will be turned to missing."
            % types))
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        if mg.FLDTYPE_NUMERIC_KEY in self.fldtype_choices:
            btn_num = wx.Button(
                self.panel, mg.RET_NUMERIC, mg.FLDTYPE_NUMERIC_LBL)
            btn_num.Bind(wx.EVT_BUTTON, self.on_num)
            szr_btns.Add(btn_num, 0, wx.LEFT|wx.RIGHT, 10)
        if mg.FLDTYPE_DATE_KEY in self.fldtype_choices:
            btn_date = wx.Button(self.panel, mg.RET_DATE, mg.FLDTYPE_DATE_LBL)
            btn_date.Bind(wx.EVT_BUTTON, self.on_date)
            szr_btns.Add(btn_date, 0,  wx.LEFT|wx.RIGHT, 10)
        btn_text = wx.Button(self.panel, mg.RET_TEXT, mg.FLDTYPE_STRING_LBL)
        btn_text.Bind(wx.EVT_BUTTON, self.on_text)
        szr_btns.Add(btn_text, 0, wx.LEFT|wx.RIGHT, 10)
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        szr_btns.Add(btn_cancel, 0,  wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(lbl_choice, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(lbl_implications, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def on_num(self, _event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_NUMERIC_KEY
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_NUMERIC)

    def on_date(self, _event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_DATE_KEY
        self.faulty2missing_fld_list.append(self.fldname)
        self.Destroy()
        self.SetReturnCode(mg.RET_DATE)

    def on_text(self, _event):
        self.fldtypes[self.fldname] = mg.FLDTYPE_STRING_KEY
        self.Destroy()
        self.SetReturnCode(mg.RET_TEXT)

    def on_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## only for dialogs 
        ## (MUST come after Destroy)

def has_header_row(row1_types, row2_types,
        str_type, empty_type, non_str_types):
    row1_types_set = set(row1_types)
    row2_types_set = set(row2_types)
    n_types = len(row1_types_set)
    has_strings = str_type in row1_types_set
    has_empties = empty_type in row1_types_set
    row1_strings_only = (has_strings and (n_types == 1 
        or (n_types == 2 and has_empties)))
    non_string_set = set(non_str_types)  ## ignore EMPTY
    row2_has_non_strings = len(row2_types_set.intersection(non_string_set)) > 0
    return row1_strings_only and row2_has_non_strings

def get_best_fldtype(fldname, type_set, faulty2missing_fld_list,
        first_mismatch='', *, headless=False):
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
                raise Exception(f'Needed a data type for "{fldname}".')
            elif ret == mg.RET_NUMERIC:
                fldtype = mg.FLDTYPE_NUMERIC_KEY
            elif ret == mg.RET_DATE:
                fldtype = mg.FLDTYPE_DATE_KEY
            elif ret == mg.RET_TEXT:
                fldtype = mg.FLDTYPE_STRING_KEY
            else:
                raise Exception('Unexpected return type from DlgChooseFldtype')
        else:
            fldtype = mg.FLDTYPE_STRING_KEY
    elif len(main_type_set) > 1:
        ## get user to choose
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
                raise Exception('Inconsistencies in data type.')         
            else:
                fldtype = fldtypes[fldname]
        else:
            fldtype = mg.FLDTYPE_STRING_KEY
    else:
        fldtype = mg.FLDTYPE_STRING_KEY
    return fldtype

def process_fldnames(raw_names, *, headless=False, force_quickcheck=False):
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
        for name in raw_names:
            name = name.replace(' ', '_')
            if len(name) > mg.MAX_VAL_LEN_IN_SQL_CLAUSE:
                ## just truncate - let the get_unique_fldnames function handle the shortened names as it normally would
                name = name[:mg.MAX_VAL_LEN_IN_SQL_CLAUSE - mg.FLDNAME_ZFILL]  ## Got to leave some room for what get_unique_fldnames() appends
            names.append(name)
            if mg.SOFA_ID in names:
                raise Exception(_('%s is a reserved field name.') % mg.SOFA_ID)
        names = lib.get_unique_fldnames(names)
    except AttributeError:
        raise Exception('Field names must all be text strings.')
    except TypeError:
        raise Exception('Field names should be supplied in a list')
    except Exception as e:
        raise Exception('Problem processing field names list.'
            f'\nCaused by error: {b.ue(e)}')
    quickcheck = False
    n_names = len(names)
    if n_names > 50:
        if headless:
            if force_quickcheck: quickcheck = True
        else:
            ## don't test each name individually - takes too long
            ## we gain speed and lose ability to single out bad variable name
            if wx.MessageBox(_('There are %s fields so the process of '
                    'checking them all will take a while. Do you want to do a '
                    'quick check only?') % n_names,
                    caption=_('QUICK CHECK ONLY?'), style=wx.YES_NO) == wx.YES:
                quickcheck = True
    if quickcheck:
        ## quick check
        valid, err = dbe_sqlite.valid_fldnames(fldnames=names, block_sz=100)
        if not valid:
            raise Exception(_('Unable to use field names provided. Please '
                'only use letters, numbers and underscores. No spaces, full '
                'stops etc. If you want to know which field name failed, try '
                'again and do the more thorough check (say No to quick check '
                'only).\nOrig error: %s') % err)
    else:
        ## thorough check
        for i, name in enumerate(names):
            valid, err = dbe_sqlite.valid_fldname(name)
            if not valid:
                raise Exception(_("Unable to use field name \"%(fldname)s\". "
                    'Please only use letters, numbers and underscores. No '
                    'spaces, full stops etc.\nOrig error: %(err)s')
                    % {'fldname': raw_names[i], 'err': err})
    return names

def process_tblname(rawname):
    """
    Turn spaces, hyphens and dots into underscores.
    NB doesn't check if a duplicate etc at this stage.
    """
    return lib.get_safer_name(rawname)

def assess_sample_fld(sample_data, ok_fldname, ok_fldnames,
        faulty2missing_fld_list, *,
        has_header=True, allow_none=True, comma_dec_sep_ok=False,
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
    first_mismatch = ''
    expected_fldtype = ''
    start_row_num = 2 if has_header else 1
    for row_num, row in enumerate(sample_data, start_row_num):
        if debug: print(row_num, row)  ## look esp for Nones
        if allow_none:
            val = lib.if_none(row[ok_fldname], '')
        else:  ## CSVs don't allow none for example
            val = row[ok_fldname]
            if val is None:
                report_fld_n_mismatch(row, row_num, ok_fldnames,
                    has_header=has_header, allow_none=allow_none)
        val_type = lib.get_val_type(val, comma_dec_sep_ok)
        if not expected_fldtype and val_type != mg.VAL_EMPTY_STRING:
            expected_fldtype = val_type
        type_set.add(val_type)
        ## more than one type (ignoring empty string)?
        main_type_set = type_set.copy()
        main_type_set.discard(mg.VAL_EMPTY_STRING)
        if len(main_type_set) > 1 and not first_mismatch:
            ## identify row and value to report to user
            first_mismatch = FIRST_MISMATCH_TPL.format(
                row=row_num, value=val, fldtype=expected_fldtype)
    fldtype = get_best_fldtype(fldname=ok_fldname, type_set=type_set,
        faulty2missing_fld_list=faulty2missing_fld_list,
        first_mismatch=first_mismatch, headless=headless)
    return fldtype

def is_blank_raw_val(raw_val):
    """
    Need to handle solo single quotes or solo double quotes. May be result of
    escaping issues but be derived from csv rows like 1,"",4.
    """
    return raw_val in ('', "''", '""', None)

def get_val_and_ok_status(feedback, raw_val, fldtype, *,
        is_pytime=False, comma_dec_sep_ok=False):
    debug = False
    ok_data = False        
    if fldtype == mg.FLDTYPE_NUMERIC_KEY:
        ## must be numeric, or empty string or dot (which we'll turn to NULL)
        if lib.TypeLib.is_numeric(raw_val, comma_dec_sep_ok=comma_dec_sep_ok):
            if raw_val == 'NaN':
                ok_data = True
                val = NULL_INDICATOR
            else:
                ok_data = True
                try:
                    if comma_dec_sep_ok:
                        val = raw_val.replace(',', '.')
                    else:
                        val = raw_val
                except AttributeError:
                    val = raw_val
        elif is_blank_raw_val(raw_val):
            ok_data = True
            val = NULL_INDICATOR
        elif raw_val == mg.MISSING_VAL_INDICATOR:  ## not ok in numeric field
            ok_data = True
            feedback[mg.NULLED_DOTS_KEY] = True
            val = NULL_INDICATOR
        else:
            val = raw_val  ## ok_data will still be false
    elif fldtype == mg.FLDTYPE_DATE_KEY:
        ## must be pytime or datetime string or usable date string
        ## or empty string or dot (which we'll turn to NULL).
        if is_pytime:
            if debug: print(f'pytime raw val: {raw_val}')
            val = lib.DateLib.pytime_to_datetime_str(raw_val)
            if debug: print(f'pytime val: {val}')
            ok_data = True
        else:
            if debug: print(f'Raw val: {raw_val}')
            if is_blank_raw_val(raw_val):
                ok_data = True
                val = NULL_INDICATOR
            elif raw_val == mg.MISSING_VAL_INDICATOR:  ## not ok in numeric fld
                ok_data = True
                if debug: print('Date field has a missing value.')
                feedback[mg.NULLED_DOTS_KEY] = True
                val = NULL_INDICATOR
            else:
                try:
                    if debug: print(f'Raw val: {raw_val}')
                    val = lib.DateLib.get_std_datetime_str(raw_val)
                    if debug: print(f'Date val: {val}')
                    ok_data = True
                except Exception:
                    val = raw_val  ## ok_data will still be false so exception will be raised
    elif fldtype == mg.FLDTYPE_STRING_KEY:
        ## None or empty string we'll turn to NULL_INDICATOR
        ok_data = True
        if is_blank_raw_val(raw_val):
            val = NULL_INDICATOR
        else:
            val = raw_val
    else:
        raise Exception('Unexpected field type in importer.get_val()')
    return val, ok_data

def get_val(feedback, raw_val, is_pytime, fldtype, ok_fldname,
        faulty2missing_fld_list, row_num, *, comma_dec_sep_ok=False):
    """
    feedback -- dic with mg.NULLED_DOTS_KEY

    Missing values are OK in numeric and date fields in the source field being
    imported, but a missing value indicator (e.g. ".") is not. Must be
    converted to a null. A missing value indicator is fine in the data _once it
    has been imported_ but not beforehand.

    Checking is always necessary, even for a sample which has already been
    examined. May have found a variable conflict and need to handle it after it
    raises a mismatch error by turning faulty values to nulls.
    """
    val, ok_data = get_val_and_ok_status(feedback, raw_val, fldtype,
        is_pytime=is_pytime, comma_dec_sep_ok=comma_dec_sep_ok)
    if not ok_data:
        if ok_fldname in faulty2missing_fld_list:
            val = NULL_INDICATOR  ## replace faulty value with a null
        else:
            details = FIRST_MISMATCH_TPL.format(row=row_num,
                value=raw_val, fldtype=mg.FLDTYPE_KEY2LBL[fldtype])
            raise my_exceptions.Mismatch(fldname=ok_fldname,
                expected_fldtype=fldtype, details=details)
    return val

def get_processed_val(feedback, row_num, row, ok_fldname, fldtypes,
        faulty2missing_fld_list, *, comma_dec_sep_ok=False):
    """
    Add val to vals.

    feedback -- dic with mg.NULLED_DOTS_KEY

    NB field types are only a guess based on a sample of the first rows in the
    file being imported.  Could be wrong.

    If checking, will validate and turn empty strings into nulls as required.
    Also turn '.' into null as required (and leave msg).

    If not checking (e.g. because a pre-tested sample) only do the
    pytime (Excel) and empty string to null conversions.

    If all is OK, will add val to vals. NB val will need to be internally
    quoted unless it is a NULL_INDICATOR. Watch for "But I say ""No"" don't I".

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
            msg = (' (NB some field names may have been altered to prevent '
                'duplicates or otherwise invalid names).')
        except Exception:
            msg = ''
        raise Exception(_("Row %(row_num)s doesn't have a value for the "
            "\"%(ok_fldname)s\" field %(msg)s") % {
            'row_num': row_num, 'ok_fldname': ok_fldname, 'msg': msg})
    is_pytime = lib.TypeLib.is_pytime(rawval)
    fldtype = fldtypes[ok_fldname]
    val = get_val(feedback, rawval, is_pytime, fldtype, ok_fldname, 
        faulty2missing_fld_list, row_num, comma_dec_sep_ok=comma_dec_sep_ok)
#     needs_quoting = (
#         fldtype != mg.FLDTYPE_NUMERIC_KEY and val != NULL_INDICATOR)
#     if needs_quoting:
#         try:
#             val = dbe_sqlite.quote_val(val)
#         except Exception:
#             raise Exception(
#                 _('Tried to quote %(val)s on row %(row_num)s but failed.')
#                 % {'val': val, 'row_num': row_num})
    if debug: print(val)
    return val

def report_fld_n_mismatch(row, row_num, ok_fldnames, *, has_header, allow_none):
    debug = False
    if debug: print(row_num, row)
    if not allow_none:
        n_row_items = len([x for x in row.values() if x is not None])
    else:
        n_row_items = len(row)
    n_flds = len(ok_fldnames)
    if n_row_items != n_flds:
        if has_header:
            row_msg = _('Row %s (including header row)') % (row_num+1,)
        else:
            row_msg = _('Row %s') % row_num  
        ## if csv has 2 flds and receives 3 vals will be var1: 1, var2: 2, None: [3]!
        vals = []
        for ok_fldname in ok_fldnames:
            vals.append(row[ok_fldname])
        vals_under_none = row.get(None)
        if vals_under_none:
            vals.extend(vals_under_none)
            ## subtract the None list item but add all its contents
            n_row_items = len(vals)
        ## remove quoting
        ## e.g. ['1', '2'] or ['1', '2', None]
        vals_str = (str(vals)
            .replace("', '", ',')
            .replace("['", '')
            .replace("']", '')
            .replace("',", ',')
            .replace(', None', '')
            .replace(']', ''))
        raise Exception(f'Incorrect number of fields in {row_msg}.'
            f'\n\nExpected {n_flds:,} but found {n_row_items:,}.'
            f'\n\nFaulty Row: {vals_str}')

def _process_row_dets(
        con, cur,
        feedback,
        rows_dets, ok_fldnames, fldnames_clause,
        fldtypes, faulty2missing_fld_list,
        progbar, steps_per_item, gauge_start, *,
        allow_none=True, comma_dec_sep_ok=False,
        has_header=False, headless=False):
    """
    Insert in blocks for efficiency. If an error, start again doing it row by
    row so we can identify the (first) row to fail and report back details to
    the user for correction.
    """
    debug = False
    verbose = False
    vals_rows = []
    placeholders = ', '.join(['?']*len(ok_fldnames))
    SQL_insert_row_tpl = f"""INSERT INTO {mg.TMP_TBLNAME}
        ({fldnames_clause})
        VALUES({placeholders})"""
    for row_num, row in rows_dets:
        if debug and verbose: print(str(row_num), row)
        vals = []
        report_fld_n_mismatch(row, row_num, ok_fldnames,
            has_header=has_header, allow_none=allow_none)
        try:
            for ok_fldname in ok_fldnames:
                val = get_processed_val(feedback, row_num, row,
                    ok_fldname, fldtypes, faulty2missing_fld_list,
                    comma_dec_sep_ok=comma_dec_sep_ok)
                vals.append(val)
        except my_exceptions.Mismatch as e:
            if debug: print(f'A mismatch exception {e}')
            raise  ## keep this particular type of exception bubbling out
        ## quoting must happen earlier so we can pass in NULL (None)
        vals_rows.append(vals)
    if debug and verbose: print(SQL_insert_row_tpl, vals_rows)
    try:
        cur.executemany(SQL_insert_row_tpl, vals_rows)
        if headless:
            gauge_val = row_num
        else:
            raw_gauge_val = gauge_start + (len(rows_dets)*steps_per_item)
            gauge_val = min(raw_gauge_val, mg.IMPORT_GAUGE_STEPS)  ## must never exceed IMPORT_GAUGE_STEPS through rounding errors etc.
        progbar.SetValue(gauge_val)
    except Exception as e:
        ## run through one by one to find faulty row
        for (row_num, unused), vals_row in zip(rows_dets, vals_rows):
            if debug and verbose: print(SQL_insert_row_tpl, vals_row)
            try:
                cur.execute(SQL_insert_row_tpl, vals_row)
            except Exception as e:
                raise Exception(f'Unable to add row {row_num:,}.'
                    f'\nCaused by error: {b.ue(e)}')
    con.commit()
    return gauge_val

def add_rows(
        con, cur,
        feedback, import_status,
        rows, ok_fldnames, fldtypes,
        faulty2missing_fld_list,
        progbar, rows_n, steps_per_item, gauge_start=0,
        allow_none=True, comma_dec_sep_ok=False,
        has_header=False, headless=False):
    """
    Add the rows of data (dicts), processing each cell as you go.

    Batch up into chunks of rows to increase performance.

    :param dict feedback: dic with mg.NULLED_DOTS_KEY
    :param bool allow_none : if Excel returns None for an empty cell that is
     correct behaviour. A CSV file returning None, however, is not. Should be
     empty str.
    """
    if rows_n < 1000:
        chunk_size = 50
    elif rows_n < 10000:
        chunk_size = 250
    elif rows_n < 100000:
        chunk_size = 1000
    elif rows_n < 1000000:
        chunk_size = 2500
    else:
        chunk_size = 5000
    fldnames_clause = ', '.join([dbe_sqlite.quote_obj(x) for x
        in ok_fldnames])
    start_row_num = 2 if has_header else 1
    rows_dets = []
    for row_num, row in enumerate(rows, start_row_num):
        rows_dets.append((row_num, row))
        if len(rows_dets) == chunk_size:
            wx.Yield()
            if import_status[mg.CANCEL_IMPORT]:
                progbar.SetValue(0)
                raise my_exceptions.ImportCancel
            gauge_start = _process_row_dets(
                con, cur,
                feedback, rows_dets,
                ok_fldnames, fldnames_clause,
                fldtypes, faulty2missing_fld_list,
                progbar, steps_per_item, gauge_start,
                allow_none=allow_none, comma_dec_sep_ok=comma_dec_sep_ok,
                has_header=has_header, headless=headless)
            rows_dets = []
    if rows_dets:  ## mop up - the final batch might have less than 50
        _process_row_dets(
            con, cur,
            feedback, rows_dets,
            ok_fldnames, fldnames_clause,
            fldtypes, faulty2missing_fld_list,
            progbar, steps_per_item, gauge_start,
            allow_none=allow_none, comma_dec_sep_ok=comma_dec_sep_ok,
            has_header=has_header, headless=headless)

def get_steps_per_item(items_n):
    """
    Needed for progress bar - how many items before displaying another of the
    steps as set by mg.IMPORT_GAUGE_STEPS.

    Chunks per item e.g. 0.01.
    """
    if items_n != 0:
        ## we go through the sample once at start for sampling and then again
        ## for adding to table
        steps_per_item = float(mg.IMPORT_GAUGE_STEPS)/items_n
    else:
        steps_per_item = None
    return steps_per_item

def drop_tmp_tbl(con, cur):
    con.commit()
    SQL_drop_disp_tbl = f'DROP TABLE IF EXISTS {mg.TMP_TBLNAME}'
    cur.execute(SQL_drop_disp_tbl)
    con.commit()

def post_fail_tidy(progbar, con, cur):
    drop_tmp_tbl(con, cur)
    lib.GuiLib.safe_end_cursor()
    cur.close()
    con.commit()
    con.close()
    progbar.SetValue(0)

def try_to_add_to_tmp_tbl(
        feedback, import_status,
        con, cur,
        tblname, ok_fldnames, fldtypes,
        faulty2missing_fld_list, data,
        progbar, rows_n, steps_per_item, gauge_start, *,
        allow_none=True, comma_dec_sep_ok=False,
        has_header=True, headless=False):
    debug = False
    if debug:
        print(f'Cleaned (ok) field names are: {ok_fldnames}')
        print(f'Field types are: {fldtypes}')
        print(f'Faulty to missing field list: {faulty2missing_fld_list}')
        print(f'Data is: {data}')
    try:
        con.commit()
        SQL_get_tblnames = """SELECT name 
            FROM sqlite_master 
            WHERE type = 'table'"""
        cur.execute(SQL_get_tblnames)  ## otherwise it doesn't always seem to have the latest data on which tables exist
        drop_tmp_tbl(con, cur)
        if debug: print(f'Successfully dropped {mg.TMP_TBLNAME}')
    except Exception as e:
        raise
    try:
        tblname = mg.TMP_TBLNAME
        ## oth_name_types -- ok_fldname, fldtype (taken from original source
        ## and the key will be ok_fldname)
        oth_name_types = []
        for ok_fldname in ok_fldnames:
            oth_name_types.append((ok_fldname, fldtypes[ok_fldname]))
        if debug: print(oth_name_types)
        getdata.make_sofa_tbl(
            con, cur, tblname, oth_name_types, headless=headless)
    except Exception as e:
        raise   
    try:
        ## Add sample and then remaining data to disposable table.
        ## Already been through sample once when assessing it so part way
        ## through process already.
        add_rows(
            con, cur,
            feedback, import_status,
            data, ok_fldnames, fldtypes,
            faulty2missing_fld_list,
            progbar, rows_n, steps_per_item, gauge_start=gauge_start,
            allow_none=allow_none, comma_dec_sep_ok=comma_dec_sep_ok,
            has_header=has_header, headless=headless)
        return True
    except my_exceptions.Mismatch as e:
        feedback[mg.NULLED_DOTS_KEY] = False
        con.commit()
        progbar.SetValue(0)
        if headless:
            raise Exception(f'Unable to import data. Orig error: {e}')
        else:
            ## go through again or raise an exception
            dlg = DlgFixMismatch(fldname=e.fldname,
                fldtype_choices=[e.expected_fldtype,], fldtypes=fldtypes,
                faulty2missing_fld_list=faulty2missing_fld_list,
                details=e.details, assessing_sample=False)
            ret = dlg.ShowModal()
            if ret == wx.ID_CANCEL:
                raise Exception(
                    'Mismatch between data in column and expected column type')
            else:
                return False  ## start again :-)

def add_to_tmp_tbl(
        feedback, import_status,
        con, cur,
        tblname, ok_fldnames, fldtypes,
        faulty2missing_fld_list, data,
        progbar, rows_n, steps_per_item, gauge_start, *,
        allow_none=True, comma_dec_sep_ok=False,
        has_header=True, headless=False):
    """
    Create fresh disposable table in SQLite and insert data into it.

    feedback -- dic with mg.NULLED_DOTS_KEY

    ok_fldnames -- cleaned field names (shouldn't have a sofa_id field)

    fldtypes -- dict with field types for original field names

    faulty2missing_fld_list -- list of fields where we should turn faulty values
    to missing.

    data -- list of dicts using orig fld names. Can't be a reader because need
    to be able to use it again assuming it stars from the same position.

    allow_none -- if Excel returns None for an empty cell that is correct bvr.

    If a csv files does, however, it is not. Should be empty str.

    Give it a unique identifier field as well.

    Set up the data type constraints needed.

    Keep trying till success or user decodes not to fix and keep going. Fix
    involves changing the relevant fldtype to string, which will accept
    anything.
    """
    while True:  ## keep trying till success or user decodes not to fix & continue
        try:
            data.reset()  ## needed by CSV because it uses a reader and we want to start from scratch each time
        except AttributeError:
            pass
        if try_to_add_to_tmp_tbl(
                feedback, import_status,
                con, cur,
                tblname, ok_fldnames, fldtypes,
                faulty2missing_fld_list, data,
                progbar, rows_n, steps_per_item, gauge_start,
                allow_none=allow_none, comma_dec_sep_ok=comma_dec_sep_ok,
                has_header=has_header, headless=headless):
            break

def tmp_to_named_tbl(con, cur, tblname, progbar, nulled_dots, *,
        headless=False):
    """
    Rename table to final name.

    This part is only called once at the end and is so fast there is no need to
    report progress till completion.
    """
    debug = False
    try:
        tblname_str = getdata.tblname_qtr(mg.DBE_SQLITE, tblname)
        SQL_drop_tbl = f'DROP TABLE IF EXISTS {tblname_str}'
        if debug: print(SQL_drop_tbl)
        cur.execute(SQL_drop_tbl)
        con.commit()
        tmp_tblname_str = getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)
        SQL_rename_tbl = (
            f'ALTER TABLE {tmp_tblname_str} RENAME TO {tblname_str}')
        if debug: print(SQL_rename_tbl)
        cur.execute(SQL_rename_tbl)
        con.commit()
    except Exception as e:
        raise Exception('Unable to rename temporary table.'
            f'\nCaused by error: {b.ue(e)}')
    progbar.SetValue(mg.IMPORT_GAUGE_STEPS)
    msg = _("Successfully imported data as\n\"%(tbl)s\".")
    if nulled_dots:
        msg += _("\n\nAt least one field contained a single dot '.'.  This was "
            "converted into a missing value.")
    msg += _("\n\nYou can check your imported data by clicking the "
        "'Enter/Edit Data' button on the main form. You'll find your "
        "data in the '%s' database.") % mg.SOFA_DB
    if not headless:
        wx.MessageBox(msg % {'tbl': tblname})

def get_content_dets(strdata):
    debug = False
    try:
        max_row_len = max([len(x) for x in strdata])
    except Exception:
        max_row_len = None
    lines = []  ## init
    for row in strdata:
        len_row = len(row)
        if debug: print(len_row, row)
        if len_row < max_row_len:
            ## right pad sequence with empty str (to become empty str cells)
            row += ['' for x in range(max_row_len - len_row)]
        line = '<tr><td>' + '</td><td>'.join(row) + '</td></tr>'
        lines.append(line)
    trows = '\n'.join(lines)
    content = ("<table border='1' style='border-collapse: collapse;'>"
        '<tbody>\n' + trows + '\n</tbody></table>')
    n_lines_actual = len(lines)
    content_height = 35*n_lines_actual
    content_height = 300 if content_height > 300 else content_height
    return content, content_height


class DlgHasHeader(wx.Dialog):
    def __init__(self, parent, ext):
        wx.Dialog.__init__(self, parent=parent, title=_('Header row?'),
            size=(550, 300), style=wx.CAPTION|wx.SYSTEM_MENU,
            pos=(mg.HORIZ_OFFSET + 200, 120))
        self.parent = parent
        self.panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        lbl_explan = wx.StaticText(self.panel, -1,
            _('Does your %s file have a header row?') % ext)
        lbl_with_header = wx.StaticText(self.panel, -1,
            _('Example with header'))
        lbl_with_header.SetFont(mg.LABEL_FONT)
        img_ctrl_with_header = wx.StaticBitmap(self.panel)
        img_with_header = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', f'{ext}_with_header.xpm'),
            wx.BITMAP_TYPE_XPM)
        bmp_with_header = wx.BitmapFromImage(img_with_header)
        img_ctrl_with_header.SetBitmap(bmp_with_header)
        lbl_without_header = wx.StaticText(self.panel, -1, _('Example without'))
        lbl_without_header.SetFont(mg.LABEL_FONT)
        img_ctrl_without_header = wx.StaticBitmap(self.panel)
        img_without_header = wx.Image(
            os.path.join(mg.SCRIPT_PATH, 'images', f'{ext}_without_header.xpm'),
            wx.BITMAP_TYPE_XPM)
        bmp_without_header = wx.BitmapFromImage(img_without_header)
        img_ctrl_without_header.SetBitmap(bmp_without_header)
        btn_has_header = wx.Button(self.panel, mg.HAS_HEADER, 
            _('Has Header Row'))
        btn_has_header.Bind(wx.EVT_BUTTON, self.on_btn_has_header)
        btn_has_header.SetDefault()
        btn_no_header = wx.Button(self.panel, -1, _('No Header'))
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

    def on_btn_has_header(self, unused_event):
        self.Destroy()
        self.SetReturnCode(mg.HAS_HEADER)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.

    def on_btn_no_header(self, unused_event):
        self.Destroy()
        self.SetReturnCode(mg.NO_HEADER)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.

    def on_btn_cancel(self, unused_event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.


class DlgHasHeaderGivenData(wx.Dialog):
    def __init__(self, parent, ext, strdata, prob_has_hdr=True):
        debug = False
        wx.Dialog.__init__(self, parent=parent, title=_('Header row?'),
            size=(850, 250), style=wx.CAPTION|wx.SYSTEM_MENU,
            pos=(mg.HORIZ_OFFSET + 200, 120))
        self.parent = parent
        self.panel = wx.Panel(self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.BoxSizer(wx.HORIZONTAL)
        explan = _('Does your %s file have a header row? Note - SOFA cannot '
            'handle multiple header rows.') % ext
        lbl_explan = wx.StaticText(self.panel, -1, explan)
        content, unused = get_content_dets(strdata)
        if debug: print(content)
        html_content = wx.html2.WebView.New(self.panel, -1, size=(820, 240))
        html_content.SetPage(content, mg.BASE_URL)
        btn_has_header = wx.Button(self.panel, mg.HAS_HEADER,
            _('Has Header Row'))
        btn_has_header.Bind(wx.EVT_BUTTON, self.on_btn_has_header)
        btn_no_header = wx.Button(self.panel, -1, _('No Header'))
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

    def on_btn_has_header(self, unused_event):
        self.Destroy()
        self.SetReturnCode(mg.HAS_HEADER)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.
        
    def on_btn_no_header(self, unused_event):
        self.Destroy()
        self.SetReturnCode(mg.NO_HEADER)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.
        
    def on_btn_cancel(self, unused_event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## or nothing happens!  
        ## Prebuilt dialogs presumably do this internally.


class DummyProgBar():

    def SetValue(self, value):
        print('Progress {:,} ...'.format(round(value, 3)))


class DummyLabel():
    def SetLabel(self, unused):
        pass


dummy_import_status = {mg.CANCEL_IMPORT: False}


class HeadlessImporter:
    def __init__(self):
        self.progbar = DummyProgBar()
        self.import_status = dummy_import_status.copy()  ## can change and running script can check on it.
        self.lbl_feedback = DummyLabel()


def check_tblname(tblname):
    """
    Returns tblname (None if no suitable name to use).

    Checks table name and gives user option of correcting it if problems.

    Raises exception if no suitable name selected.
    """
    ## check existing names
    valid, unused = dbe_sqlite.valid_tblname(tblname)
    if not valid:
        raise Exception('Faulty SOFA table name.')
    return tblname

def get_file_start_ext(path):
    unused, filename = os.path.split(path)
    filestart, extension = os.path.splitext(filename)
    return filestart, extension

def run_headless_import(fpath=None, tblname=None,
        supplied_encoding=None, *,
        headless_has_header=True, force_quickcheck=False):
    """
    Usage:
    fpath = '/home/g/grantshare/import_testing/xlsfiles/Data w Respondent ID.xlsx' #csvfiles/percent_names.csv'
    tblname = 'headless_yeah_baby'
    headless_has_header = True
    supplied_encoding = 'utf-8'
    force_quickcheck = True
    importer.run_headless_import(fpath, tblname, supplied_encoding,
        headless_has_header=True, force_quickcheck=False)

    Identify type of file by extension and open dialog if needed to get any
    additional choices e.g. separator used in 'csv'.
    """
    headless = True
    if not fpath:
        raise Exception(_('A file name must be supplied when importing if '
            'running in headless mode.'))
    ## identify file type
    unused, extension = get_file_start_ext(fpath)
    if extension.lower() in (mg.IMPORT_EXTENTIONS['csv'],
            mg.IMPORT_EXTENTIONS['tsv'], mg.IMPORT_EXTENTIONS['tab']):
        file_type = FILE_CSV
    elif extension.lower() == mg.IMPORT_EXTENTIONS['txt']:
        file_type = FILE_CSV
    elif extension.lower() == mg.IMPORT_EXTENTIONS['xlsx']:
        file_type = FILE_EXCEL
    elif extension.lower() == mg.IMPORT_EXTENTIONS['ods']:
        file_type = FILE_ODS
    elif extension.lower() == mg.IMPORT_EXTENTIONS['xls']:
        unknown_msg = (_("Files with the file name extension '%s' are "
            "not supported") % extension
            + '. Please convert to xlsx or another supported format first.')
        raise Exception(unknown_msg)
    else:
        unknown_msg = _("Files with the file name extension '%s' are "
            "not supported") % extension
        raise Exception(unknown_msg)
    if not tblname:
        raise Exception('Unable to import headless unless table name supplied')
    if ' ' in tblname:
        empty_spaces_msg = _("SOFA Table Name can't have empty spaces")
        raise Exception(empty_spaces_msg)
    bad_chars = ['-', ]
    for bad_char in bad_chars:
        if bad_char in tblname:
            bad_char_msg = (
                _("Do not include '%s' in SOFA Table Name") % bad_char)
            raise Exception(bad_char_msg)
    if tblname[0] in [str(x) for x in range(10)]:
        digit_msg = _('SOFA Table Names cannot start with a digit')
        raise Exception(digit_msg)
    try:
        final_tblname = check_tblname(tblname)
        if final_tblname is None:
            raise Exception(
                'Table name supplied is inappropriate for some reason.')
    except Exception:
        raise
    ## import file
    dummy_importer = HeadlessImporter()
    if file_type == FILE_CSV:
        from sofastats.importing import csv_importer_new as csv_importer #@UnresolvedImport
        file_importer = csv_importer.CsvImporter(dummy_importer, fpath,
            final_tblname, supplied_encoding,
            headless=headless, headless_has_header=headless_has_header,
            force_quickcheck=force_quickcheck)
    elif file_type == FILE_EXCEL:
        from sofastats.importing import excel_importer #@UnresolvedImport
        file_importer = excel_importer.ExcelImporter(dummy_importer, fpath,
            final_tblname, headless, headless_has_header, force_quickcheck)
    elif file_type == FILE_ODS:
        from sofastats.importing import ods_importer #@UnresolvedImport
        file_importer = ods_importer.OdsImporter(dummy_importer, fpath,
            final_tblname, headless, headless_has_header, force_quickcheck)
    proceed = file_importer.get_params()
    if proceed:
        file_importer.import_content()


class FileImporter():
    def __init__(self, parent, fpath, tblname, supplied_encoding=None, *,
            headless=False, headless_has_header=False):
        self.parent = parent
        self.fpath = fpath
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
            if debug: print(str(ret))
            if ret == wx.ID_CANCEL:
                return False
            else:
                self.has_header = (ret == mg.HAS_HEADER)
                return True


if __name__ == '__main__':
    """
    cd /home/g/projects/sofastats_proj/sofastatistics/ && python -m sofastats.importer
    """
    fpath = '/home/g/grantshare/import_testing/csvfiles/....csv'
    tblname = '...'
    supplied_encoding = 'utf-8'
    run_headless_import(fpath, tblname,
        supplied_encoding, headless_has_header=False, force_quickcheck=True)
