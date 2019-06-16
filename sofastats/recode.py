import pprint
from textwrap import dedent
import wx

from . import basic_lib as b
from . import my_globals as mg
from . import lib
from . import config_output
from .dbe_plugins import dbe_sqlite
from . import getdata
from . import output
from . import projects
from . import settings_grid

TO = 'TO'
MIN = 'MIN'
MAX = 'MAX'
REMAINING = 'REMAINING'
MISSING = 'MISSING'

objqtr = dbe_sqlite.quote_obj
valqtr = dbe_sqlite.quote_val  ## only used on internal db in SQLite - all
## imported as utf-8 unicode from the start because SQLite3 (I believe).

"""
Take user input and translate into valid SQLite clauses for an update statement.

Note: need to rebuild table so that constraints (e.g. only accept numbers only)
can be added to the table.

on_recode() checks things out, then, if OK, calls recode_tbl().

get_case_when_clause() calls process_orig() for each line in the recoding
instructions e.g. 1 TO 6 --> "Inappropriate" becomes an SQLite clause ready to
include in the update statement.
"""

def make_when_clause(orig_clause, new, new_fldtype):
    if new_fldtype in (mg.FLDTYPE_STRING_KEY, mg.FLDTYPE_DATE_KEY):
        new = valqtr(new)
    when_clause = f'            WHEN {orig_clause} THEN {new}'
    return when_clause

def process_orig(orig, fldname, fldtype):
    """
    Turn an orig value into a clause ready for use in an SQL CASE WHEN snippet.

    Settings must be one per line. In simplest case, just enter a single value.

    Use "TO" for ranges rather than the ambiguous "-".

    Keywords are TO, MIN, MAX, REMAINING, MISSING.  If the user has values like
    that they wish to recode, e.g. "MISSING" -> 99, they will need to use SQLite
    to manipulate the data themselves.

    Virtue of keeping it very simple for easy cases, and adequate interface for
    more flexible recoding.

    If you want 1-6, 10+ to become "Inappropriate" you would have two lines:
    1 TO 6  -> Inappropriate
    10 TO MAX -> Inappropriate

    Using commas etc as separators meant problems when recoding text which
    contained commas. Would require escape characters etc. Rapidly becomes too
    complex for target users. The approach taken is sometimes slightly
    inefficient but it is easy to learn and apply and check for mistakes.

    Look for keywords. Patterns:
    1) Look for special keywords first:
    Special:
    REMAINING
    MISSING
    2) Then look for TO. OK to use for strings.
    If found, split and identify if either side is MIN or
    MAX. NB MIN must be on left and MAX on right. OK to have both.
    NB MIN TO MAX != REMAINING.  The latter includes NULLS.
    Examples: a TO b, a TO MAX, MIN TO MAX, MIN TO B
    3) Assume we are dealing with a single value e.g. 1 or Did Not Reply

    :param str orig: a string
    :param str fldname: field being used in the expression
    :param str fldtype: e.g. string
    """
    debug = False
    fld = objqtr(fldname)
    if not isinstance(orig, str):
        raise Exception('process_orig() expects strings')
    orig_clause = None
    ## 1 Special (except REMAINING which always appears as part of END)
    if orig.strip() == MISSING:
        orig_clause = f'{fld} IS NULL'
    ## 2 Range
    elif TO in orig:
        parts = orig.split(TO)
        if debug: print(parts)
        if len(parts) != 2:
            raise Exception(_("Unable to process \"%s\"") % orig)
        l_part = parts[0].strip()
        r_part = parts[1].strip()
        if r_part == MIN:
            raise Exception(_("%(min)s can only be on the left side "
                "e.g.%(min)s TO 12") % {'min': MIN})
        if l_part == MAX:
            raise Exception(_("%(max)s can only be on the right side "
                "e.g. %(max)s TO 12") % {'max': MAX})
        has_min = False
        has_max = False
        num_mismatch = False
        date_mismatch = False
        if l_part == MIN:
            has_min = True
        else:
            if (fldtype == mg.FLDTYPE_NUMERIC_KEY
                    and not lib.TypeLib.is_numeric(l_part)):
                num_mismatch = True
            elif (fldtype == mg.FLDTYPE_DATE_KEY
                    and not lib.DateLib.is_std_datetime_str(l_part)):
                date_mismatch = True
        if r_part == MAX:
            has_max = True
        else:
            if (fldtype == mg.FLDTYPE_NUMERIC_KEY
                    and not lib.TypeLib.is_numeric(r_part)):
                num_mismatch = True
            elif (fldtype == mg.FLDTYPE_DATE_KEY
                    and not lib.DateLib.is_std_datetime_str(r_part)):
                date_mismatch = True
        if num_mismatch:
            if debug: print(l_part, r_part)
            raise Exception(
                _('Only numeric values can be recoded for this variable'))
        if date_mismatch:
            if debug: print(l_part, r_part)
            raise Exception(
                _('Only date values can be recoded for this variable'))
        if fldtype in (mg.FLDTYPE_STRING_KEY, mg.FLDTYPE_DATE_KEY):
            l_prep = valqtr(l_part)
            r_prep = valqtr(r_part)
        else:
            l_prep = l_part
            r_prep = r_part
        if has_min:  ## MIN TO MAX
            if has_max:
                orig_clause = f'{fld} IS NOT NULL'
            else:  ## MIN TO b
                orig_clause = f'{fld} <= {r_prep}'
        else:
            if has_max:  ## a TO MAX
                orig_clause = f'{fld} >= {l_prep}'
            else:  ## a TO b
                orig_clause = f'{fld} BETWEEN {l_prep} AND {r_prep}'
    ## 3 Single value
    else:
        if fldtype in (mg.FLDTYPE_STRING_KEY, mg.FLDTYPE_DATE_KEY):
            orig_clause = f"{fld} = {valqtr(orig)}"
        elif fldtype == mg.FLDTYPE_NUMERIC_KEY:
            if not lib.TypeLib.is_numeric(orig):
                raise Exception(_("The field being recoded is numeric but you "
                    "are trying to recode a non-numeric value"))
            orig_clause = f'{fld} = {orig}'
        else:
            orig_clause = f'{fld} = {orig}'
    if orig_clause is None:
        raise Exception('Unable to process original value in recode config')
    return orig_clause

def process_label(dict_labels, new_fldtype, new, label):
    """
    Add non-empty label to dictionary of labels for variable
    """
    debug = False
    if label == '':
        return
    if new_fldtype in (mg.FLDTYPE_STRING_KEY, mg.FLDTYPE_DATE_KEY):
        new = valqtr(new)
    elif new_fldtype in (mg.FLDTYPE_NUMERIC_KEY):
        new = float(new)
    if debug: print(new, label)
    dict_labels[new] = label

def recode_cell_invalidation(recode_dlg, val, row, col, grid, col_dets):  ## unused vars because using a standard interface
    """
    Return boolean and string message.
    No dots as from or too (idxes 0 and 1).
    """
    if val == mg.MISSING_VAL_INDICATOR and col in (0,1):
        return True, _("Please do not use the \"%s\" to recode to or from. "
            "Use MISSING for missing as required.") % mg.MISSING_VAL_INDICATOR
    return False, ''

def warn_about_existing_labels(recode_dlg, val, row, col, grid, col_dets):  ## unused vars because using a standard interface
    """
    If a non-empty value, check to see if this variable has value labels
    already. If it does, let the user know.
    """
    debug = False
    if recode_dlg.new_fldname in recode_dlg.warned:  ## once is enough
        return
    if col == 2 and val != '' and recode_dlg.new_fldname != '':
        recode_dlg.warned.append(recode_dlg.new_fldname)
        if debug: print(recode_dlg.new_fldname)
        if recode_dlg.val_dics.get(recode_dlg.new_fldname):
            if debug: print(recode_dlg.val_dics[recode_dlg.new_fldname])
            max_width = 0
            fld_val_dic = recode_dlg.val_dics[recode_dlg.new_fldname]
            for key, label in fld_val_dic.items():
                max_width = (len(str(key)) if len(str(key)) > max_width
                    else max_width)
            existing_labels_lst = []
            for key, label in fld_val_dic.items():
                display = f'{str(key).ljust(max_width)}:   {label}'
                existing_labels_lst.append(display)
            existing_labels = '\n'.join(existing_labels_lst)
            wx.MessageBox(_("\"%(new_fldname)s\" already has value labels set. "
                "Only add labels here if you wish to add to or override "
                "existing value labels\n\nExisting labels:\n\n"
                "%(existing_labels)s") % {"new_fldname": recode_dlg.new_fldname, 
                "existing_labels": existing_labels})


class DlgRecode(settings_grid.DlgSettingsEntry):

    def __init__(self, tblname, fld_settings):
        """
        :param str tblname: table containing the variable we are recoding
        :param list fld_settings: a list of dicts with the following keys:
         mg.TBL_FLDNAME, mg.TBL_FLDNAME_ORIG,
         mg.TBL_FLDTYPE, mg.TBL_FLDTYPE_ORIG
        """
        cc = output.get_cc()
        self.tblname = tblname
        self.warned = []  ## For cell_response_func.  Lists vars warned about.
        self.from_lbl = _('FROM original value(s)')
        self.to_lbl = _('TO new value')
        self.label_lbl = _('With LABEL')
        col_dets = [
            {'col_label': self.from_lbl,
             'coltype': settings_grid.COL_STR,
             'colwidth': 200},
            {'col_label': self.to_lbl,
             'coltype': settings_grid.COL_STR,
             'colwidth': 200},
            {'col_label': self.label_lbl,
             'coltype': settings_grid.COL_STR,
             'colwidth': 200, 'empty_ok': True},
        ]
        grid_size = (640, 250)
        wx.Dialog.__init__(self, None, title=_('Recode Variable'),
            size=(700, 350), pos=(mg.HORIZ_OFFSET + 150, 100),
            style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        (self.var_labels, self.var_notes, self.var_types, 
         self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        self.panel = wx.Panel(self)
        ## New controls
        lbl_from = wx.StaticText(self.panel, -1, _('Recode:'))
        lbl_from.SetFont(mg.LABEL_FONT)
        self.settings_data = fld_settings
        ## [('string', 'fname', 'fname (string)'), ...]
        ## field type is used for validation and constructing recode SQL string
        fld_dets = [
            (x[mg.TBL_FLDTYPE], x[mg.TBL_FLDNAME],
            f'{x[mg.TBL_FLDNAME]} ({x[mg.TBL_FLDTYPE]})')
            for x in self.settings_data]
        fld_dets.sort(key=lambda s: s[2].upper())  ## needed consistent sorting
        self.fld_type_keys = [mg.FLDTYPE_LBL2KEY[x[0]] for x in fld_dets]
        self.fldnames = [x[1] for x in fld_dets]
        self.fldchoices = [x[2] for x in fld_dets]
        self.fldname = self.fldnames[0]
        self.new_fldname = ''
        self.drop_from = wx.Choice(self.panel, -1, choices=self.fldchoices, 
             size=(250,-1))
        self.drop_from.SetSelection(0)
        self.drop_from.Bind(wx.EVT_CHOICE, self.on_var_sel)
        self.drop_from.Bind(wx.EVT_CONTEXT_MENU, self.on_var_rclick)
        self.drop_from.SetToolTip(_('Right click to view variable details'))
        lbl_to = wx.StaticText(self.panel, -1, 'To:')
        lbl_to.SetFont(mg.LABEL_FONT)
        self.txt_to = wx.TextCtrl(self.panel, -1, size=(250, -1))
        self.txt_to.Bind(wx.EVT_CHAR, self.on_txt_to_char)
        init_recode_clauses_data = []
        self.recode_clauses_data = []
        self.tabentry = settings_grid.SettingsEntry(self, self.panel,
            grid_size, col_dets, init_recode_clauses_data,
            self.recode_clauses_data,
            cell_invalidation_func=recode_cell_invalidation,
            cell_response_func=warn_about_existing_labels)
        self.tabentry.grid.Enable(False)
        self.tabentry.grid.SetToolTip(
            _('Disabled until there is a variable to recode to'))
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_help = wx.Button(self.panel, wx.ID_HELP)
        btn_help.Bind(wx.EVT_BUTTON, self.on_help)
        btn_recode = wx.Button(self.panel, -1, _('Recode'))
        btn_recode.Bind(wx.EVT_BUTTON, self.on_recode)
        btn_recode.SetToolTip(
            _('Recode an existing variable into a new variable'))
        ## sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_vars = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_btns = wx.FlexGridSizer(rows=1, cols=3, hgap=5, vgap=0)
        self.szr_btns.AddGrowableCol(0,2)  ## idx, propn
        self.szr_vars.Add(lbl_from, 0, wx.RIGHT, 5)
        self.szr_vars.Add(self.drop_from, 1, wx.RIGHT, 10)
        self.szr_vars.Add(lbl_to, 0, wx.RIGHT, 5)
        self.szr_vars.Add(self.txt_to, 1)
        self.szr_main.Add(self.szr_vars, 0, wx.GROW|wx.ALL, 10)
        self.szr_btns.Add(btn_cancel)
        self.szr_btns.Add(btn_help)
        self.szr_btns.Add(btn_recode)
        self.szr_main.Add(self.tabentry.grid, 2, wx.GROW|wx.ALL, 5)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.drop_from.SetFocus()

    def on_var_sel(self, _event):
        var_idx = self.drop_from.GetSelection()
        self.fldname = self.fldnames[var_idx]

    def on_var_rclick(self, _event):
        var_label = lib.GuiLib.get_item_label(self.var_labels, self.fldname)
        choice_item = lib.GuiLib.get_choice_item(self.var_labels, self.fldname)
        unused = config_output.set_var_props(choice_item, self.fldname,
            var_label, self.var_labels, self.var_notes, self.var_types,
            self.val_dics)

    def on_txt_to_char(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN:
            self.tabentry.grid.SetFocus()
            return
        ## NB callafter to allow data to updated in text ctrl
        wx.CallAfter(self.update_new_fldname)
        event.Skip()

    def update_new_fldname(self):
        debug = False
        self.new_fldname = self.txt_to.GetValue()
        if debug: print(self.new_fldname)
        enable = (self.new_fldname.strip() != '')
        self.tabentry.grid.Enable(enable)

    def on_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)

    def on_help(self, event):
        rules = dedent(f"""\
        1. If you are trying to recode a range
        e.g. ages 1-19 into a single age group,
        put 1 TO 19 in the '{self.from_lbl}' column,
        not 1 in the first column and 19 in the second.
        
        2. Ranges use the keyword TO e.g. 150 TO 250. All keywords must be upper case,
        so 150 TO 250 will work but 150 to 250 will not.
        
        3. MIN and MAX can be used in ranges e.g. MIN TO 100, or 100 TO MAX.
        You can even use MIN TO MAX if you want to leave out missing values.
        
        4. REMAINING and MISSING are the two remaining keywords you can use
        e.g. if you want all missing values to become 99 you would have a line with
        '{self.from_lbl}' as MISSING, and '{self.to_lbl}' as 99
        
        5. Only one condition is allowed per line. So if you want to recode
        <=5 and 10+ to 99 you would have one line with
        
            '{self.from_lbl}' as MIN TO 5 and '{self.to_lbl}' as 99
        
            and another line with
        
            '{self.from_lbl}' as 10 TO MAX and '{self.to_lbl}' as 99.
        
        6. Ranges are inclusive so 1 TO 5, for example, includes both 1 and 5
        """)
        dlg = lib.DlgHelp(parent=self, title=_('Recoding Help'),
            guidance_lbl=_('Recoding Rules'), activity_lbl='recoding',
            guidance=rules, help_pg='recoding_data')
        dlg.ShowModal()
        event.Skip()

    def recover_from_failed_recode(self):
        """
        If this goes wrong, delete freshly-created table with orig name, and
        rename tmp table back to orig name. That way, we haven't wiped the
        original table merely because of a recode problem
        """
        dd = mg.DATADETS_OBJ
        dd.con.commit()
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        SQL_drop_orig = (f'DROP TABLE IF EXISTS '
            f'{getdata.tblname_qtr(mg.DBE_SQLITE, self.tblname)}')
        dd.cur.execute(SQL_drop_orig)
        dd.con.commit()
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        SQL_rename_tbl = (
            f'ALTER TABLE {getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)} '
            f'RENAME TO {getdata.tblname_qtr(mg.DBE_SQLITE, self.tblname)}')
        dd.cur.execute(SQL_rename_tbl)
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        dd.set_db(dd.db, tbl=self.tblname)

    def recode_tbl(self, case_when, oth_name_types,
            idx_new_fld_in_oth_name_types):
        """
        Build SQL, rename existing to tmp table, create empty table with orig
        name, and then mass into it.

        oth_name_types -- includes the new field

        idx_new_fld_in_oth_name_types -- needed an index which could be used in
        oth_name_types. An idx for the orig field wouldn't work if the field
        was the sofa_id.

        Doesn't use ALTER TABLE mytable ADD newvar syntax etc followed by

        UPDATE mytable SET newvar = ... because we want to put the new variable
        in straight after the source variable.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        ## rename table to tmp
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        SQL_drop_tmp = ('DROP TABLE IF EXISTS '
            f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)}')
        dd.cur.execute(SQL_drop_tmp)
        SQL_rename_tbl = (
            f'ALTER TABLE {getdata.tblname_qtr(mg.DBE_SQLITE, self.tblname)} '
            f'RENAME TO {getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)}')
        dd.cur.execute(SQL_rename_tbl)
        ## create new table with orig name and extra field
        create_fld_clause = getdata.get_create_flds_txt(oth_name_types, 
            strict_typing=False, inc_sofa_id=True)
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        SQL_make_recoded_tbl = (
            f'CREATE TABLE {getdata.tblname_qtr(mg.DBE_SQLITE, self.tblname)} '
            f'({create_fld_clause}) ')
        if debug: print(f'SQL_make_recoded_tbl: {SQL_make_recoded_tbl}')
        dd.cur.execute(SQL_make_recoded_tbl)
        ## want fields before new field, then case when, then any remaining flds
        fld_clauses_lst = []
        fld_clauses_lst.append(f'NULL AS {objqtr(mg.SOFA_ID)}')
        ## fldnames from start of other (non sofa_id) fields to before new field
        ## (may be none)
        if debug: 
            print(f'oth_name_types: {oth_name_types}')
            print('idx_new_fld_in_oth_name_types: '
                f'{idx_new_fld_in_oth_name_types}')
        name_types_pre_new = oth_name_types[: idx_new_fld_in_oth_name_types]
        if debug: print(f'name_types_pre_new: {name_types_pre_new}')
        for name, unused in name_types_pre_new:
            fld_clauses_lst.append(objqtr(name))
        fld_clauses_lst.append(case_when)
        ## want fields after new field (if any). Skip new recoded fld.
        name_types_post_new = oth_name_types[idx_new_fld_in_oth_name_types+1:]
        if debug: print(f'name_types_post_new: {name_types_post_new}')
        for name, unused in name_types_post_new:
            fld_clauses_lst.append(objqtr(name))
        fld_clauses = ',\n    '.join(fld_clauses_lst)
        SQL_insert_content = (
            f'INSERT INTO {getdata.tblname_qtr(mg.DBE_SQLITE, self.tblname)} '
            f'\n    SELECT {fld_clauses} '
            f'\n    FROM {getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)}')
        print('*'*60)
        print(SQL_insert_content)  ## worth keeping and not likely to be overdone
        print('*'*60)
        try:
            dd.cur.execute(SQL_insert_content)
        except Exception as e:
            print(SQL_insert_content)
            print(str(e))
            self.recover_from_failed_recode()
            raise
        dd.con.commit()
        getdata.force_sofa_tbls_refresh(sofa_default_db_cur=dd.cur)
        SQL_drop_tmp = (
            'DROP TABLE IF EXISTS '
            f'{getdata.tblname_qtr(mg.DBE_SQLITE, mg.TMP_TBLNAME)}')
        dd.cur.execute(SQL_drop_tmp)
        dd.con.commit()
        dd.set_db(dd.db, tbl=self.tblname)

    def update_labels(self, fldname, dict_labels):
        """
        Look in vdt file in current project
        Variable name updated to fldname if not present
        """
        if fldname not in self.var_labels:
            self.var_labels[fldname] = fldname.title()  ## else leave alone
        try:
            self.val_dics[fldname].update(dict_labels)
        except KeyError:
            self.val_dics[fldname] = dict_labels
        projects.update_vdt(self.var_labels, self.var_notes, self.var_types, 
            self.val_dics)

    def get_case_when_clause(self, new_fldname, new_fldtype, fldtype, 
            dict_labels):
        """
        Recoding into new variable with a CASE WHEN SQL syntax clause.

        Order doesn't matter except for REMAINING which is ELSE in CASE
        statement. Must come last and only once.
        """
        debug = False
        when_clauses = []
        remaining_to = None
        for orig, new, label in self.recode_clauses_data:
            if debug: print(orig, new, label)
            if orig.strip() != REMAINING:  ## i.e. ordinary
                orig_clause = process_orig(orig, self.fldname, fldtype)
                process_label(dict_labels, new_fldtype, new, label)
                when_clauses.append(make_when_clause(orig_clause, new, 
                    new_fldtype))
            else:  ## REMAINING
                ## if multiple REMAINING clauses the last 'wins'
                if new_fldtype in (mg.FLDTYPE_STRING_KEY, mg.FLDTYPE_DATE_KEY):
                    remaining_to = valqtr(new)
                else:
                    remaining_to = new
                remaining_new = new
                remaining_label = label
        if remaining_to:
            if when_clauses:  ## pop it on the end
                remaining_clause = ' '*12 + f'ELSE {remaining_to}'
            else:  ## the only clause
                remaining_clause = ' '*12 + f'WHEN 1=1 THEN {remaining_to}'
            when_clauses.append(remaining_clause)
            process_label(dict_labels, new_fldtype, remaining_new, 
                remaining_label)
        case_when_lst = []
        case_when_lst.append('    CASE')
        case_when_lst.extend(when_clauses)
        case_when_lst.append(f'        END\n    AS {objqtr(new_fldname)}')
        case_when = '\n'.join(case_when_lst)
        if debug: 
            pprint.pprint(dict_labels)
            pprint.pprint(case_when)
        return case_when

    def on_recode(self, _event):
        """
        Get settings, validate when Recode button clicked, make recoded table,
        give message that a once-off recode - won't be automatic if new rows
        added or cells edited.
        """
        debug = False
        fld_idx = self.drop_from.GetSelection()
        new_fldname = self.txt_to.GetValue()
        if not new_fldname:
            wx.MessageBox(_('Please add a new field name'))
            self.txt_to.SetFocus()
            return
        valid, err = dbe_sqlite.valid_fldname(new_fldname)
        if not valid:
            wx.MessageBox(_('Field names can only contain letters, numbers, '
                'and underscores.\nOrig error: %s') % err)
            return
        ## can't already be in use
        if new_fldname in self.fldnames:
            wx.MessageBox(_('Unable to use an existing field name (%s)')
                % new_fldname)
            return
        fldtype = self.fld_type_keys[fld_idx]
        self.tabentry.update_settings_data()
        if debug: 
            print(pprint.pformat(self.recode_clauses_data))
            print(self.fldname)
            print(fldtype)
        ## get settings (and build labels)
        if not self.recode_clauses_data:
            wx.MessageBox(_('Please add some recode details'))
            return
        dict_labels = {}
        ## get field type of recoded values (and thus, new field)
        type_set = set()
        new_vals = [x[1] for x in self.recode_clauses_data]
        for new_val in new_vals:
            val_type = lib.get_val_type(new_val)
            type_set.add(val_type)
        new_fldtype = lib.get_overall_fldtype(type_set)
        try:
            case_when = self.get_case_when_clause(
                new_fldname, new_fldtype, fldtype, dict_labels)
        except Exception as e:
            wx.MessageBox(_('Problem with your recode configuration.'
                '\nCaused by error: %s') % b.ue(e))
            return
        oth_name_types = getdata.get_oth_name_types(self.settings_data)
        ## insert new field just after the source field
        if self.fldname == mg.SOFA_ID:
            idx_new_fld_in_oth_name_types = 0  ## idx in oth_name_types
        else:
            idx_new_fld_in_oth_name_types = (
                [x[0] for x in oth_name_types].index(self.fldname) + 1)
        oth_name_types.insert(idx_new_fld_in_oth_name_types,
                (new_fldname, new_fldtype))
        if debug: print(oth_name_types)
        try:
            self.recode_tbl(
                case_when, oth_name_types, idx_new_fld_in_oth_name_types)
            wx.MessageBox(_('Please Note - this was a once-off recode - it '
                "won't be applied automatically when new rows are added or "
                'cells are edited.'))
        except Exception as e:
            raise Exception(_('Problem recoding table.'
                '\nCaused by error: %s') % b.ue(e))
        self.update_labels(new_fldname, dict_labels)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
