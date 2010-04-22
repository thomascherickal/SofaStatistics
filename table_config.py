import pprint
import random
import string
import wx

import my_globals as mg
import lib
import getdata # must be anything referring to plugin modules
import dbe_plugins.dbe_sqlite as dbe_sqlite
import full_html
import settings_grid

WAITING_MSG = _("<p>Waiting for at least one field to be configured.</p>")

def insert_data(row_idx, grid_data):
    """
    Return list of values to display in inserted row.
    Needs to know row index plus already used variable labels (to prevent 
        collisions).
    """
    existing_var_names = [x[0] for x in grid_data]
    next_fld_name = lib.get_next_fld_name(existing_var_names)
    row_data = [next_fld_name, mg.FLD_TYPE_NUMERIC]
    return row_data

def cell_invalidation(row, col, grid, col_dets):
    """
    The first column text must be either empty, or 
        alphanumeric (and underscores), and unique (field name) 
        and the second must be empty or from mg.CONF_... e.g. "numeric"
    """
    if col == 0:
        return _invalid_fld_name(row, grid)
    elif col == 1:
        return _invalid_fld_type(row, grid)
    else:
        raise Exception, u"Two many columns for default cell invalidation test"

def _invalid_fld_name(row, grid):
    "Return boolean and string message"
    other_fld_names = []
    for i in range(grid.GetNumberRows()):
        if i == row:
            continue
        other_fld_names.append(grid.GetCellValue(row=i, col=0))
    field_name = grid.GetCellValue(row=row, col=0)
    if field_name.strip() == u"":
        return False, ""
    if not dbe_sqlite.valid_name(field_name):
        msg = _("Field names can only contain letters, numbers, and "
              "underscores")
        return True, msg
    if field_name in other_fld_names:
        msg = _("%s has already been used as a field name") % field_name
        return True, msg
    return False, u""

def _invalid_fld_type(row, grid):
    "Return boolean and string message"
    field_type = grid.GetCellValue(row=row, col=1)
    if field_type.strip() == u"":
        return False, ""
    if field_type not in [mg.FLD_TYPE_NUMERIC, 
                          mg.FLD_TYPE_STRING, 
                          mg.FLD_TYPE_DATE]:
        msg = _("%s is not a valid field type") % field_type
        return True, msg
    return False, u""

def validate_tbl_name(tbl_name, name_ok_to_reuse):
    "Returns boolean plus string message"
    valid_name = dbe_sqlite.valid_name(tbl_name)
    if not valid_name:
        msg = _("You can only use letters, numbers and underscores "
            "in a SOFA name.  Use another name?")
        return False, msg
    if tbl_name == name_ok_to_reuse: # we're just editing an existing table
        duplicate = False
    else:
        duplicate = getdata.dup_tbl_name(tbl_name)
    if duplicate:
        msg = _("Cannot use this name.  A table named \"%s\" already exists in"
                " the default SOFA database") % tbl_name
        return False, msg
    return True, u""


class SafeTblNameValidator(wx.PyValidator):
    def __init__(self, name_ok_to_reuse):
        """
        Not ok to duplicate an existing name unless it is the same table i.e.
            a name ok to reuse.  None if a new table.
        """
        wx.PyValidator.__init__(self)
        self.name_ok_to_reuse = name_ok_to_reuse
        self.Bind(wx.EVT_CHAR, self.on_char)
    
    def Clone(self):
        # wxPython
        return SafeTblNameValidator(self.name_ok_to_reuse)
        
    def Validate(self, win):
        # wxPython
        text_ctrl = self.GetWindow()
        text = text_ctrl.GetValue()
        valid, msg = validate_tbl_name(text, self.name_ok_to_reuse)
        if not valid:
            wx.MessageBox(msg)
            text_ctrl.SetFocus()
            text_ctrl.Refresh()
            return False
        else:
            text_ctrl.Refresh()
            return True
    
    def on_char(self, event):
        # allow backspace and delete (both) etc
        if event.GetKeyCode() in [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, 
                                  wx.WXK_BACK, wx.WXK_LEFT, wx.WXK_RIGHT]:
            event.Skip()
            return
        try:
            keycode = chr(event.GetKeyCode())
        except Exception:
            return
        # allow alphanumeric and underscore
        if keycode not in string.letters and keycode not in string.digits \
                and keycode != "_":
            return
        event.Skip()
    
    def TransferToWindow(self):
        # wxPython
        return True
    
    def TransferFromWindow(self):
        # wxPython
        return True

    
class ConfigTableDlg(settings_grid.SettingsEntryDlg):
    
    debug = False
    styles = u"""
        table {
            border-collapse: collapse;
        }
        th {
            margin: 0;
            padding: 9px 6px;
            border-left: solid 1px #c0c0c0;
            border-right: solid 1px #c0c0c0;
            vertical-align: top;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
            color: white;
            background-color: #333435;
        }
        td{
            margin: 0;
            padding: 2px 6px;
            border: solid 1px #c0c0c0;
            font-size: 11px;
            color: #5f5f5f; # more clearly just demo data
        }"""
    
    def __init__(self, cur_dict, var_labels, val_dics,
                 tbl_name_lst, data, config_data, readonly=False, new=False,
                 insert_data_func=None, cell_invalidation_func=None):
        """
        tbl_name_lst -- passed in as a list so changes can be made without 
            having to return anything. 
        data -- list of tuples (must have at least one tuple in the list, even
            if only a "rename me".
        config_data -- add details to it in form of a list of tuples.
        """
        self.cur_dict = cur_dict
        self.var_labels = var_labels
        self.val_dics = val_dics
        if tbl_name_lst:
            name_ok_to_reuse = tbl_name_lst[0]
        else:
            name_ok_to_reuse = None
        self.tbl_name_lst = tbl_name_lst
        # set up new grid data based on data
        self.config_data = config_data
        self.init_config_data(data)
        self.readonly = readonly
        self.new = new
        if not insert_data_func:
            insert_data_func = insert_data
        if not cell_invalidation_func:
            cell_invalidation_func = cell_invalidation
        # col_dets - See under settings_grid.SettingsEntry
        col_dets = [{"col_label": _("Field Name"), 
                     "col_type": settings_grid.COL_STR, 
                     "col_width": 100}, 
                    {"col_label": _("Data Type"), 
                     "col_type": settings_grid.COL_DROPDOWN, 
                     "col_width": 100,
                     "dropdown_vals": [mg.FLD_TYPE_NUMERIC, 
                                       mg.FLD_TYPE_STRING, 
                                       mg.FLD_TYPE_DATE]},
                     ]
        grid_size = (300,250)
        wx.Dialog.__init__(self, None, title=_("Configure Data Table"),
                           size=(500,400), 
                           style=wx.RESIZE_BORDER|wx.CAPTION|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        # New controls
        lbl_tbl_label = wx.StaticText(self.panel, -1, _("Table Name:"))
        lbl_tbl_label.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        tbl_name = tbl_name_lst[0] if tbl_name_lst else _("table") + u"001"
        self.txt_tbl_name = wx.TextCtrl(self.panel, -1, tbl_name, size=(450,-1))
        self.txt_tbl_name.Enable(not self.readonly)
        self.txt_tbl_name.SetValidator(SafeTblNameValidator(name_ok_to_reuse))
        # sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label = wx.BoxSizer(wx.HORIZONTAL)
        szr_design = wx.BoxSizer(wx.HORIZONTAL)
        szr_design_left = wx.BoxSizer(wx.VERTICAL)
        szr_design_right = wx.BoxSizer(wx.VERTICAL)
        self.szr_tbl_label.Add(lbl_tbl_label, 0, wx.RIGHT, 5)
        self.szr_tbl_label.Add(self.txt_tbl_name, 0)
        bold = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        design_here_lbl = _("Design Here:") if not self.readonly \
            else _("Design:")
        lbl_design_here = wx.StaticText(self.panel, -1, design_here_lbl)
        lbl_design_here.SetFont(font=bold)
        see_result_lbl = _("See Demonstration Result Here:") \
            if not self.readonly else _("Demonstration Result:")
        lbl_see_result = wx.StaticText(self.panel, -1, see_result_lbl)
        lbl_see_result.SetFont(font=bold)
        self.html = full_html.FullHTML(self.panel, size=(500,200))
        szr_design_left.Add(lbl_design_here, 0)
        if not self.readonly:
            lbl_sofa_id = wx.StaticText(self.panel, -1, 
                            _("The sofa_id is required and cannot be edited"))
            szr_design_left.Add(lbl_sofa_id, 0)
        self.tabentry = ConfigTableEntry(self, self.panel, szr_design_left, 1, 
                                         self.readonly, grid_size, col_dets, 
                                         data, config_data, insert_data_func,
                                         cell_invalidation_func)
        szr_design_right.Add(lbl_see_result, 0)
        szr_design_right.Add(self.html, 1, wx.GROW|wx.ALL, 10)
        szr_design.Add(szr_design_left, 0, wx.GROW)
        szr_design.Add(szr_design_right, 1, wx.GROW)
        self.setup_btns(self.readonly)
        self.szr_main.Add(self.szr_tbl_label, 0, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(szr_design, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.update_demo()
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.txt_tbl_name.SetFocus()
    
    def get_demo_val(self, row_idx, col_label, type):
        """
        Get best possible demo value for display in absence of source data.
        """
        if col_label.lower() == mg.SOFA_ID:
            val = row_idx+1
        else:
            if self.val_dics.get(col_label):
                val = random.choice(self.val_dics[col_label])
            else:
                val = lib.get_rand_val_of_type(type)
        return val
    
    def get_demo_row_lst(self, row_idx, col_labels, types):
        debug = False
        row_lst = []
        label_types = zip(col_labels, types)
        if debug: print("Label types:\n%s" % label_types)
        for col_label, type in label_types:
            val2use = self.get_demo_val(row_idx, col_label, type)
            row_lst.append(val2use)
        return row_lst
    
    def update_demo(self):
        """
        Get data (if any) as a dict using orig fld names.
        Use this data (or labelled version) if possible, else random according 
            to type.        
        """
        debug = False
        if not self.config_data:
            self.html.show_html(WAITING_MSG)
            return
        if debug: print(self.config_data)
        # 1) part before the table-specific items e.g. column names and data
        html = [mg.DEFAULT_HDR % (u"Demonstration table", self.styles)]
        html.append(u"<table cellspacing='0'>\n<thead>\n<tr>")
        # 2) the table-specific items (inc column labels)
        col_labels = [] # using the new ones
        types = [] # ditto
        new_fldnames = []
        orig_fldnames = [] # These will be the key for any dicts taken from db
            # NB will be None for new or inserted flds.
        for data_dict in self.config_data:
            # all must have same num of elements (even if a None) in same order
            fldname = data_dict[mg.TBL_FLD_NAME]
            new_fldnames.append(fldname)
            col_labels.append(self.var_labels.get(fldname, fldname.title()))
            orig_fldnames.append(data_dict.get(mg.TBL_FLD_NAME_ORIG))
            types.append(data_dict[mg.TBL_FLD_TYPE])
        if debug:
            print(col_labels)
            print(orig_fldnames)
            print(types)
        # column names
        for col_label in col_labels:
            html.append(u"<th>%s</th>" % col_label)
        # get data rows (list of lists)
        rows = []
        display_n = 4 # demo rows to display
        if self.new:
            for i in range(display_n):
                row_lst = self.get_demo_row_lst(i, col_labels, types)
                rows.append(row_lst)
        else:
            # add as many rows from orig data as possible up to the 4 row limit
            obj_quoter = getdata.get_obj_quoter_func(mg.DBE_SQLITE)
            flds_clause = u", ".join([obj_quoter(x) for x in orig_fldnames
                                      if x is not None])
            SQL_get_data = u"""SELECT %s FROM %s """ % (flds_clause,
                                            obj_quoter(self.tbl_name_lst[0]))
            self.cur_dict.execute(SQL_get_data)
            # returns dict with orig fld names as keys
            # NB will not contain any new or inserted flds
            row_idx = 0
            while True:
                if display_n:
                    if row_idx >= display_n:
                        break # got all we need
                row_obj = self.cur_dict.fetchone()
                if row_obj is None:
                    break # run out of rows
                row_dict = dict(row_obj)
                if debug: print(row_dict)
                row_lst = []
                for orig_fldname, new_fldname, col_label, type in \
                            zip(orig_fldnames, new_fldnames, col_labels, types):
                    if orig_fldname is None:
                        rawval = self.get_demo_val(row_idx, col_label, type)
                    else:
                        try:
                            rawval = row_dict[orig_fldname]
                        except KeyError:
                            raise Exception, (u"orig_fldname %s not in "
                                    "row_dict %s" % (orig_fldname, row_dict))
                    if rawval is None:
                        rawval = mg.MISSING_VAL_INDICATOR
                    valdic = self.val_dics.get(new_fldname)
                    if valdic:
                        val2use = valdic.get(rawval, rawval)
                    else:
                        val2use = rawval
                    row_lst.append(val2use)
                rows.append(row_lst)
                row_idx+=1
            while row_idx < display_n:
                row_lst = self.get_demo_row_lst(row_idx, col_labels, types)
                rows.append(row_lst)
                row_idx+=1
        # data rows into html
        for row in rows:
            html.append(u"</tr>\n</thead>\n<tbody><tr>")
            for raw_val in row:
                html.append(u"<td>%s</td>" % raw_val)
            html.append(u"</tr>")
        html.append(u"\n</tbody>\n</table></body></html>")
        html2show = u"".join(html)
        self.html.show_html(html2show)
    
    def init_config_data(self, data):
        debug = False
        extra = []
        for row in data:
            new_row = {mg.TBL_FLD_NAME: row[0], 
                       mg.TBL_FLD_NAME_ORIG: row[0], 
                       mg.TBL_FLD_TYPE: row[1], 
                       mg.TBL_FLD_TYPE_ORIG: row[1]}
            extra.append(new_row)
        self.config_data += extra
        if debug: print("Initialised extra config data: %s" % self.config_data)
    
    def insert_before(self):
        """
        Overrides SettingsEntryDlg (only part where different is if pos == 0.
        Returns bolinserted, row inserted before (or None if no insertion),
            and row data (or None if no content added). 
        """
        selected_rows = self.tabentry.grid.GetSelectedRows()
        if not selected_rows:
            wx.MessageBox(_("Please select a row first (click to the left of "
                            "the row)"))
            return False, None, None
        pos = selected_rows[0]
        if pos == 0: # for table config only
            wx.MessageBox(_("The %s must always come first") % mg.SOFA_ID)
            return False, None, None
        bolinserted, row_data = self.tabentry.insert_row_above(pos)
        return bolinserted, pos, row_data

    def on_insert(self, event):
        """
        Insert before.
        Overridden so we can update config_data with details of new row.
        Also need overridden insert_before().
        """
        bolinserted, row_before, row_data = self.insert_before()
        if bolinserted:
            self.add_new_to_config(row_before, row_data) # should be only change
            self.update_demo()
        self.tabentry.grid.SetFocus()
        event.Skip()
    
    def add_new_to_config(self, row_before, row_data):
        if self.debug: print("Row we inserted before was %s" % row_before)
        # insert new row into config_data - Nones for original values
        new_row = {mg.TBL_FLD_NAME: row_data[0], 
                   mg.TBL_FLD_NAME_ORIG: None, 
                   mg.TBL_FLD_TYPE: row_data[1], 
                   mg.TBL_FLD_TYPE_ORIG: None}
        self.config_data.insert(row_before, new_row)
        if self.debug: pprint.pprint(self.config_data)
            
    def on_delete(self, event):
        "Overridden so we can update config_data."
        row_del = self.tabentry.try_to_delete_row()
        if row_del is not None:
            if self.debug: print("Row deleted was %s" % row_del)
            # remove row from config_data.
            del self.config_data[row_del]
            self.update_demo()
            if self.debug: pprint.pprint(self.config_data)
        self.tabentry.grid.SetFocus()
        event.Skip()

    def on_ok(self, event):
        """
        Override so we can extend to include table name.
        """
        if not self.readonly:
            # NB must run Validate on the panel because the objects are 
            # contained by that and not the dialog itself. 
            # http://www.nabble.com/validator-not-in-a-dialog-td23112169.html
            if not self.panel.Validate(): # runs validators on all assoc ctrls
                return True
        if self.tbl_name_lst: # empty ready to repopulate
            del self.tbl_name_lst[0]
        self.tbl_name_lst.append(self.txt_tbl_name.GetValue())
        self.tabentry.update_config_data()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
        
    
class ConfigTableEntry(settings_grid.SettingsEntry):
    """
    config_data should be returned as a list of dicts with the keys:
    mg.TBL_FLD_NAME, etc
    """
    
    def __init__(self, frame, panel, szr, dim_share, readonly, grid_size, 
                col_dets, data, config_data, insert_data_func=None, 
                cell_invalidation_func=None):
        self.frame = frame
        self.readonly = readonly
        force_focus = False
        settings_grid.SettingsEntry.__init__(self, frame, panel, szr, 
            dim_share, readonly, grid_size, col_dets, data, config_data, 
            force_focus, insert_data_func, cell_invalidation_func)
        self.debug = False # otherwise set in the parent class ;-)
        # disable first row (SOFA_ID)
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly(True)
        self.grid.SetRowAttr(0, attr)
    
    def process_cell_move(self, src_ctrl, src_row, src_col, dest_row, dest_col, 
                          direction):
        """
        dest row and col still unknown if from a return or TAB keystroke.
        So is the direction (could be down or down_left if end of line).
        """
        debug = False
        stayed_still, saved_new_row = \
            settings_grid.SettingsEntry.process_cell_move(self, src_ctrl, 
                                src_row, src_col, dest_row, dest_col, direction)
        if self.readonly or stayed_still:
            return
        fld_name = self.grid.GetCellValue(src_row, 0)
        fld_type = self.grid.GetCellValue(src_row, 1)
        if saved_new_row:
            if self.debug or debug: print("Row moved from was %s" % src_row)
            # For row we're leaving, fill in new details.
            # If an existing row, leave original values alone.
            try:
                self.config_data[src_row][mg.TBL_FLD_NAME] = fld_name
                self.config_data[src_row][mg.TBL_FLD_TYPE] = fld_type
            except IndexError: # leaving what was the new row
                new_row = {mg.TBL_FLD_NAME: fld_name, 
                           mg.TBL_FLD_NAME_ORIG: None, 
                           mg.TBL_FLD_TYPE: fld_type, 
                           mg.TBL_FLD_TYPE_ORIG: None}
                self.config_data.append(new_row)
            if self.debug or debug: pprint.pprint(self.config_data)
            self.frame.update_demo()
        else:
            if src_row == len(self.config_data):
                # arriving at final row on init
                changed = False
            else:
                try:
                    changed = \
                        ((fld_name != self.config_data[src_row][mg.TBL_FLD_NAME]) \
                        or (fld_type != self.config_data[src_row][mg.TBL_FLD_TYPE]))
                except IndexError:
                    changed = True
            if changed:
                self.update_config_data()
                self.frame.update_demo()
            
    def update_config_data(self):
        """
        Update config_data.  Overridden so we can include original field 
            details (needed when making new version of the original table).
        Fill in details of fld_names and fld_types (leaving original versions
            untouched).
        """
        debug = False
        grid_data = self.get_grid_data() # only saved data
        if debug: 
            print("grid data: %s" % grid_data)
            print("Original config data:")
            pprint.pprint(self.config_data)
        for i, row in enumerate(grid_data):
            if debug: print(row)
            self.config_data[i][mg.TBL_FLD_NAME] = row[0]
            self.config_data[i][mg.TBL_FLD_TYPE] = row[1]
        if self.debug or debug:
            print("Final config data:")
            pprint.pprint(self.config_data)
    
    def ok_to_delete_row(self, row):
        """
        Overridden settings_grid.SettingsEntry to handle row == 0.
        Should be the same otherwise.
        Can delete any row except the new row or the SOFA_ID row
        Returns boolean and msg.
        """
        if self.is_new_row(row):
            return False, _("Unable to delete new row")
        elif row == 0:
            return False, _("Unable to delete sofa id row")
        elif self.new_is_dirty:
            return False, _("Cannot delete a row while in the middle of making "
                            "a new one")
        else:
            return True, None