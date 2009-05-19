from decimal import Decimal
import pprint
import util
import wx
import wx.grid

import getdata

MISSING_VAL_INDICATOR = "."

"""
DbTbl is the link between the grid and the underlying data.
TextEditor is the custom grid cell editor - currently only used for the cells
    in the new row.  Needed so that the edited value can be captured when
    navigating away from a cell in editing mode (needed for validation).
TblEditor is the grid (the Dialog containing the grid).
Cell values are taken from the database in batches and cached for performance
    reasons.
Navigation around inside the grid triggers data saving (cells updated or 
    a new row added).  Validation occurs first to ensure that values will be
    acceptable to the underlying database.  If not, the cursor stays at the 
    original location.
"""


class DbTbl(wx.grid.PyGridTableBase):
    def __init__(self, grid, dbe, conn, cur, tbl, flds, var_labels, idxs, 
                 read_only):
        wx.grid.PyGridTableBase.__init__(self)
        self.debug = False
        self.tbl = tbl
        self.grid = grid
        self.dbe = dbe
        self.quote = getdata.DBE_MODULES[self.dbe].quote_identifier
        self.conn = conn
        self.cur = cur
        self.read_only = read_only
        self.SetNumberRows()
        self.flds = flds # dict with key = fld name and vals = dict of characteristics
        self.fld_names = getdata.FldsDic2FldNamesLst(flds_dic=self.flds)
        self.fld_labels = [var_labels.get(x, x.title()) for x in self.fld_names]
        self.idxs = idxs
        
        self.idx_id, self.must_quote = self.GetIndexCol()
        self.id_col_name = self.fld_names[self.idx_id]
        self.SetRowIdDic()
        self.row_vals_dic = {} # key = row, val = tuple of values
        if self.debug:
            pprint.pprint(self.fld_names)
            pprint.pprint(self.fld_labels)
            pprint.pprint(self.flds)
            pprint.pprint(self.row_id_dic)
        self.new_buffer = {} # where new values are stored until ready to be saved
        self.new_is_dirty = False # TextEditor can set to True.  Is reset to 
            # False when adding a new record
    
    def SetRowIdDic(self):
        """
        Row number and the value of the primary key will not always be 
            the same.  Need quick way of translating from row e.g. 0
            to value of the id field e.g. "ABC123" or 128797 or even 0 ;-).
        """
        SQL_get_id_vals = "SELECT %s FROM %s ORDER BY %s" % \
            (self.quote(self.id_col_name), self.quote(self.tbl), 
             self.quote(self.id_col_name))
        self.cur.execute(SQL_get_id_vals)
        # NB could easily be 10s or 100s of thousands of records
        ids_lst = [x[0] for x in self.cur.fetchall()]
        n_lst = range(len(ids_lst)) # 0-based to match row_n
        self.row_id_dic = dict(zip(n_lst, ids_lst))        
    
    def GetFldDic(self, col):
        fld_name = self.fld_names[col]
        return self.flds[fld_name]
    
    def GetIndexCol(self):
        """
        Pick first unique indexed column and return 
            col position, and must_quote (e.g. for string or date fields).
        TODO - cater to composite indexes properly esp when getting values
        idxs = [idx0, idx1, ...]
        each idx = (name, is_unique, flds)
        """
        idx_is_unique = 1
        idx_flds = 2
        for idx in self.idxs:
            name = idx[getdata.IDX_NAME] 
            is_unique = idx[getdata.IDX_IS_UNIQUE]
            fld_names = idx[getdata.IDX_FLDS]
            if is_unique:
                # pretend only ever one field (TODO see above)
                fld_to_use = fld_names[0]
                must_quote = not self.flds[fld_to_use][getdata.FLD_BOLNUMERIC]
                col_idx = self.fld_names.index(fld_to_use)
                if self.debug:
                    print "Col idx: %s" % col_idx
                    print "Must quote:" + str(must_quote)
                return col_idx, must_quote
    
    def GetNumberCols(self):
        num_cols = len(self.flds)
        if self.debug:
            print "N cols: %s" % num_cols
        return num_cols

    def SetNumberRows(self):
        SQL_num_rows = "SELECT COUNT(*) FROM %s" % self.quote(self.tbl)
        self.cur.execute(SQL_num_rows)
        self.num_rows = self.cur.fetchone()[0]
        if not self.read_only:
            self.num_rows += 1
        if self.debug:
            print "N rows: %s" % self.num_rows
        self.rows_to_fill = self.num_rows - 1 if self.read_only \
                else self.num_rows - 2
    
    def GetNumberRows(self):
        return self.num_rows
    
    def NewRow(self, row):
        new_row = row > self.rows_to_fill
        return new_row
    
    def GetRowLabelValue(self, row):
        new_row = row > self.rows_to_fill
        if new_row:
            if self.new_is_dirty:
                return "..."
            else:
                return "*"
        else:
            return row + 1
    
    def GetColLabelValue(self, col):
        return self.fld_labels[col]
    
    def NoneToMissingVal(self, val):
        if val == None:
            val = MISSING_VAL_INDICATOR
        return val
    
    def GetValue(self, row, col):
        """
        NB row and col are 0-based.
        The performance of this method is critical to the performance
            of the grid as a whole - displaying, scrolling, updating etc.
        Very IMPORTANT to have a unique field we can use to identify rows
            if at all possible.
        Much, much faster to do one database call per row than once per cell 
            (esp with lots of columns).
        On larger datasets (> 10,000) performance is hideous
            using order by and limit or similar.
        Need to be able to filter to individual, unique, indexed row.
        Use unique index where possible - if < 1000 recs and no unique
            index, use the method below (while telling the user the lack of 
            an index significantly harms performance esp while scrolling). 
        SQL_get_value = "SELECT %s " % col_name + \
            " FROM %s " % self.tbl + \
            " ORDER BY %s " % id_col_name + \
            " LIMIT %s, 1" % row
        NB if not read only will be an empty row at the end.
        Turn None (Null) into . as missing value identifier.
        """
        # try cache first
        try:
            return self.row_vals_dic[row][col]
        except KeyError:
            extra = 10
            """
            If new row, just return value from new_buffer (or missing value).
            Otherwise, fill cache (up to extra (e.g. 10) rows above and below) 
                 and then grab this col value.
            More expensive for first cell but heaps 
                less expensive for rest.
            Set cell editor while at it.  Very expensive for large table 
                so do it as needed.
            """
            if self.NewRow(row):
                return self.new_buffer.get((row, col), MISSING_VAL_INDICATOR)
            # identify row range            
            row_min = row - extra if row - extra > 0 else 0
            row_max = row + extra if row + extra < self.rows_to_fill \
                else self.rows_to_fill
            # create IN clause listing id values
            IN_clause_lst = []
            if self.must_quote:
                val_part = "\"%s\"" 
            else:
                val_part = "%s"
            for row_n in range(row_min, row_max + 1):
                IN_clause_lst.append(val_part % self.row_id_dic[row_n])
            IN_clause = ", ".join(IN_clause_lst)
            SQL_get_values = "SELECT * " + \
                " FROM %s " % self.quote(self.tbl) + \
                " WHERE %s IN(%s)" % (self.quote(self.id_col_name), 
                                      IN_clause) + \
                " ORDER BY %s" % self.quote(self.id_col_name)
            if self.debug:
                print SQL_get_values
            self.cur.execute(SQL_get_values)
            row_idx = row_min
            for data_tup in self.cur.fetchall(): # tuple of values
                self.AddDataToRowValsDic(self.row_vals_dic, row_idx, data_tup)
                row_idx += 1
            return self.row_vals_dic[row][col] # the bit we're interested in now
    
    def AddDataToRowValsDic(self, row_vals_dic, row_idx, data_tup):
        """
        row_vals_dic - key = row, val = tuple of values
        Add new row to row_vals_dic.
        """
        proc_data_tup = tuple([self.NoneToMissingVal(x) for x \
                              in data_tup])
        row_vals_dic[row_idx] = proc_data_tup
    
    def IsEmptyCell(self, row, col):
        value = self.GetValue(row, col)
        return value == MISSING_VAL_INDICATOR
    
    def SetValue(self, row, col, value):
        # not called if enter edit mode and then directly jump out ...
        if self.NewRow(row):
            self.new_buffer[(row, col)] = value
        else:
            existing_row_data_list = list(self.row_vals_dic.get(row))
            if existing_row_data_list:
                existing_row_data_list[col] = value
            row_id = self.GetValue(row, self.idx_id)
            col_name = self.fld_names[col]
            if self.must_quote:
                val_part = "\"%s\"" % self.row_id_dic[row]
            else:
                val_part = "%s" % self.row_id_dic[row]
            SQL_update_value = "UPDATE %s " % self.tbl + \
                " SET %s = \"%s\" " % (self.quote(col_name), value) + \
                " WHERE %s = " % self.id_col_name + \
                val_part
            if self.debug: print SQL_update_value
            self.cur.execute(SQL_update_value)
            self.conn.commit()

    def DisplayNewRow(self):
        """
        http://wiki.wxpython.org/wxGrid
        The example uses getGrid() instead of wxPyGridTableBase::GetGrid()
          can be issues depending on version of wxPython.
        Safest to pass in the grid.
        """
        self.grid.BeginBatch()
        msg = wx.grid.GridTableMessage(self, 
                            wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
        self.grid.ProcessTableMessage(msg)
        msg = wx.grid.GridTableMessage(self, 
                            wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)
        self.grid.EndBatch()
        self.grid.ForceRefresh()


class TextEditor(wx.grid.PyGridCellEditor):
    
    def __init__(self, tbl_editor, row, col, new_row, new_buffer):
        wx.grid.PyGridCellEditor.__init__(self)
        self.debug = False
        self.tbl_editor = tbl_editor
        self.row = row
        self.col = col
        self.new_row = new_row
        self.new_buffer = new_buffer
    
    def BeginEdit(self, row, col, grid):
        if self.debug: print "Editing started"
        val = grid.GetTable().GetValue(row, col)
        self.start_val = val
        self.txt.SetValue(val)
        self.txt.SetFocus()

    def Clone(self):
        return TextEditor(self.tbl_editor, self.row, self.col, self.new_row, 
                          self.new_buffer)
    
    def Create(self, parent, id, evt_handler):
        # created when clicked
        self.txt = wx.TextCtrl(parent, -1, "")
        self.SetControl(self.txt)
        if evt_handler:
            # so the control itself doesn't handle events but passes to handler
            self.txt.PushEventHandler(evt_handler)
            evt_handler.Bind(wx.EVT_KEY_DOWN, self.OnTxtEdKeyDown)
    
    def EndEdit(self, row, col, grid):
        if self.debug: print "Editing ending"
        changed = False
        val = self.txt.GetValue()
        if val != self.start_val:
            changed = True
            grid.GetTable().SetValue(row, col, val)
        if self.debug:
            print "Value entered was \"%s\"" % val
            print "Editing ended"
        if changed:
            if self.debug: print "Some data in new record has changed"
            self.tbl_editor.dbtbl.new_is_dirty = True
        return changed
        
    def StartingKey(self, event):
        key_code = event.GetKeyCode()
        if self.debug: print "Starting key was \"%s\"" % chr(key_code)
        if key_code <= 255 :
            self.txt.SetValue(chr(key_code))
            self.txt.SetInsertionPoint(1)
        else:
            event.Skip()

    def Reset(self):
        pass # N/A
    
    def OnTxtEdKeyDown(self, event):
        """
        Very tricky code re: impact of event.Skip().  Small changes can 
            have big impacts. Test thoroughly.
        """
        if event.GetKeyCode() in [wx.WXK_TAB]:
            raw_val = self.txt.GetValue()
            if self.debug:
                print "[OnTxtEdKeyDown] Tabbing away from field with " + \
                    "value \"%s\"" % raw_val
            if self.new_row:
                if self.debug: print "Tabbing within new row"
                self.new_buffer[(self.row, self.col)] = raw_val
                final_col = (self.col == len(self.tbl_editor.flds) - 1)
                if final_col:
                    # only attempt to save if value is OK to save
                    if not self.tbl_editor.CellOKToSave(self.row, self.col):
                        self.tbl_editor.grid.SetFocus()
                        return
                    if self.debug: print "OnTxtEdKeyDown - Trying to leave " + \
                        "new record"
                    saved_ok = self.tbl_editor.SaveRow(self.row)
                    if saved_ok:
                        if self.debug: print "OnTxtEdKeyDown - Was able " + \
                            "to save record after tabbing away"
                    else:
                        # CellOkToSave obviously failed to give correct answer
                        if self.debug: print "OnTxtEdKeyDown - Unable " + \
                            "to save record after tabbing away"
                        wx.MessageBox("Unable to save record - please " + \
                                      "check values")
                    return
        event.Skip()
        
        
class TblEditor(wx.Dialog):
    def __init__(self, parent, dbe, conn, cur, db, tbl_name, flds, var_labels,
                 idxs, read_only=True):
        self.debug = False
        wx.Dialog.__init__(self, None, 
                           title="Data from %s.%s" % (db, tbl_name),
                           size=(500, 500),
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.parent = parent
        self.dbe = dbe
        self.conn = conn
        self.cur = cur
        self.tbl_name = tbl_name
        self.flds = flds
        self.panel = wx.Panel(self, -1)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.grid.Grid(self.panel, size=(500, 600))
        self.grid.EnableEditing(not read_only)
        self.dbtbl = DbTbl(self.grid, self.dbe, self.conn, self.cur, tbl_name, 
                           self.flds, var_labels, idxs, read_only)
        self.grid.SetTable(self.dbtbl, takeOwnership=True)
        if read_only:
            self.grid.SetGridCursor(0, 0)
            self.current_row_idx = 0
            self.current_col_idx = 0
        else:
            # start at new line
            new_row_idx = self.dbtbl.GetNumberRows() - 1
            self.FocusOnNewRow(new_row_idx)
            self.SetNewRowEd(new_row_idx)
        self.SetColWidths()
        self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
        self.grid.Bind(wx.EVT_KEY_DOWN, self.OnGridKeyDown)
        self.szrMain.Add(self.grid, 1, wx.GROW)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.panel.Layout()
        self.grid.SetFocus()

    def OnGridKeyDown(self, event):
        if event.GetKeyCode() in [wx.WXK_TAB]:
            row = self.current_row_idx
            col = self.current_col_idx
            if self.dbtbl.NewRow(row):
                if self.debug: print "New buffer is " + str(self.dbtbl.new_buffer)
                raw_val = self.dbtbl.new_buffer.get((row, col), 
                                                    MISSING_VAL_INDICATOR)
            else:
                raw_val = self.grid.GetCellValue(row, col)
            if self.debug:
                print "[OnGridKeyDown] Tabbing away from field with value \"%s\"" % raw_val
            if self.NewRow(row):
                if self.debug: print "Tabbing within new row"
                self.dbtbl.new_buffer[(row, col)] = raw_val
                final_col = (col == len(self.flds) - 1)
                if final_col:
                    # only attempt to save if value is OK to save
                    if not self.CellOKToSave(row, col):
                        self.grid.SetFocus()
                        return
                    if self.debug: print "OnGridKeyDown - Trying to leave new record"
                    saved_ok = self.SaveRow(row)
                    if saved_ok:
                        if self.debug: print "OnGridKeyDown - Was able " + \
                            "to save record after tabbing away"
                    else:
                        # CellOkToSave obviously failed to give correct answer
                        if self.debug: print "OnGridKeyDown - Unable to " + \
                            "save record after tabbing away"
                        wx.MessageBox("Unable to save record - please " + \
                                      "check values")
                    return
        event.Skip()

    def SetNewRowEd(self, new_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            text_ed = TextEditor(self, new_row_idx, col_idx, new_row=True, 
                                 new_buffer=self.dbtbl.new_buffer)
            self.grid.SetCellEditor(new_row_idx, col_idx, text_ed)
    
    def FocusOnNewRow(self, new_row_idx):
        "Focus on cell in new row - set current to refer to that cell etc"
        self.grid.SetGridCursor(new_row_idx, 0)
        self.grid.MakeCellVisible(new_row_idx, 0)
        self.current_row_idx = new_row_idx
        self.current_col_idx = 0
    
    def SetColWidths(self):
        "Set column widths based on display widths of fields"
        self.parent.AddFeedback("Setting column widths " + \
            "(%s columns for %s rows)..." % (self.dbtbl.GetNumberCols(), 
                                             self.dbtbl.GetNumberRows()))
        pix_per_char = 8
        sorted_fld_names = getdata.FldsDic2FldNamesLst(self.flds)
        for col_idx, fld_name in enumerate(sorted_fld_names):
            fld_dic = self.flds[fld_name]
            col_width = None
            if fld_dic[getdata.FLD_BOLTEXT]:
                txt_len = fld_dic[getdata.FLD_TEXT_LENGTH]
                col_width = txt_len*pix_per_char if txt_len != None \
                    and txt_len < 25 else None # leave for auto
            elif fld_dic[getdata.FLD_BOLNUMERIC]:
                num_len = fld_dic[getdata.FLD_NUM_WIDTH]
                col_width = num_len*pix_per_char if num_len != None else None
            elif fld_dic[getdata.FLD_BOLDATETIME]:
                col_width = 170
            if col_width:
                if self.debug: print "Width of %s set to %s" % (fld_name, 
                                                                col_width)
                self.grid.SetColSize(col_idx, col_width)
            else:
                if self.debug: print "Autosizing %s" % fld_name
                self.grid.AutoSizeColumn(col_idx, setAsMin=False)            
            fld_name_width = len(fld_name)*pix_per_char
            # if actual column width is small and the label width is larger,
            # use label width.
            self.grid.ForceRefresh()
            actual_width = self.grid.GetColSize(col_idx)
            if actual_width < 15*pix_per_char \
                    and actual_width < fld_name_width:
                self.grid.SetColSize(col_idx, fld_name_width)
            if self.debug: print "%s %s" % (fld_name, 
                                            self.grid.GetColSize(col_idx))
        
        self.parent.AddFeedback("")
    
    def NewRow(self, row):
        new_row = self.dbtbl.NewRow(row)
        return new_row
    
    def OnSelectCell(self, event):
        """
        Prevent selection away from a record still in process of being saved,
            whether by mouse or keyboard, unless saved OK.
        Don't allow to leave cell in invalid state.
        Check the following:
            If jumping around within new row, cell cannot be invalid.
            If not in a new row (i.e. in existing), cell must be ok to save.
            If leaving new row, must be ready to save whole row.
        If any rules are broken, abort the jump.
        """
        row = event.GetRow()
        col = event.GetCol()
        was_new_row = self.NewRow(self.current_row_idx)
        jump_row_new = self.NewRow(row)
        if was_new_row and jump_row_new: # jumping within new
            if self.debug: print "Jumping within new row"
            ok_to_move = not self.CellInvalid(self.current_row_idx, 
                                              self.current_col_idx)
        elif not was_new_row:
            if self.debug: print "Was in existing row"
            ok_to_move = self.CellOKToSave(self.current_row_idx, 
                                           self.current_col_idx)
        elif was_new_row and not jump_row_new: # leaving new row
            if self.debug: print "Leaving new row"
            # only attempt to save if value is OK to save
            if not self.CellOKToSave(self.current_row_idx, 
                                     self.current_col_idx):
                ok_to_move = False
            else:
                ok_to_move = self.SaveRow(self.current_row_idx)
        if ok_to_move:
            self.current_row_idx = row
            self.current_col_idx = col
            event.Skip() # will allow us to move to the new cell
    
    def ValueInRange(self, raw_val, fld_dic):
        "NB may be None if N/A e.g. SQLite"
        min = fld_dic[getdata.FLD_NUM_MIN_VAL]
        max = fld_dic[getdata.FLD_NUM_MAX_VAL]        
        if min != None:
            if Decimal(raw_val) < Decimal(str(min)):
                if self.debug: print "%s is < the min of %s" % (raw_val, min)
                return False
        if max != None:
            if Decimal(raw_val) > Decimal(str(max)):
                if self.debug: print "%s is > the max of %s" % (raw_val, max)
                return False
        if self.debug: print "%s was accepted" % raw_val
        return True
    
    def CellInvalid(self, row, col):
        """
        Does a cell contain a value which shouldn't be allowed (even
            temporarily)?
        Values which are OK to allow temporarily are missing values 
            where data is required (for saving).
        If field numeric, value must be numeric ;-)
            Cannot be negative if unsigned.
            Must not be too big (turn 1.00 into 1 first etc).
            And if a not decimal, cannot have decimal places.
        If field is datetime, value must be valid date (or datetime).
        If field is text, cannot be longer than maximum length.
        """
        cell_invalid = False # innocent until proven guilty
        if self.dbtbl.NewRow(row):
            if self.debug: print "New buffer is " + str(self.dbtbl.new_buffer)
            raw_val = self.dbtbl.new_buffer.get((row, col), 
                                                MISSING_VAL_INDICATOR)
        else:
            raw_val = self.grid.GetCellValue(row, col)
            existing_row_data_tup = self.dbtbl.row_vals_dic.get(row)
            if existing_row_data_tup:
                prev_val = str(existing_row_data_tup[col])
            if self.debug: print "prev_val: %s raw_val: %s" % (prev_val, 
                                                               raw_val)
            if raw_val == prev_val:
                if self.debug: print "Unchanged"
                return False
        fld_dic = self.dbtbl.GetFldDic(col)
        if self.debug: print "\"%s\"" % raw_val
        if raw_val == MISSING_VAL_INDICATOR:
            return False
        elif not fld_dic[getdata.FLD_DATA_ENTRY_OK]: # and raw_val != MISSING_VAL_INDICATOR
            wx.MessageBox("This field does not accept user data entry.  " + \
                          "Leave as missing value (.)")
            return True
        elif fld_dic[getdata.FLD_BOLNUMERIC]:
            if not util.isNumeric(raw_val):
                wx.MessageBox("\"%s\" is not a valid number.\n\n" % raw_val + \
                              "Either enter a valid number or " + \
                              "the missing value character (.)")
                return True
            if not self.ValueInRange(raw_val, fld_dic):
                if self.debug: print "\"%s\" is invalid for data type" % raw_val
                return True
            return False
        elif fld_dic[getdata.FLD_BOLDATETIME]:
            valid_datetime, _ = util.datetime_str_valid(raw_val)
            if not valid_datetime:
                wx.MessageBox("\"%s\" is not a valid datetime.\n\n" % raw_val + \
                              "Either enter a valid date/ datetime\n" + \
                              "e.g. 31/3/2009 or 2:30pm 31/3/2009 or " + \
                              "the missing value character (.)")
                return True
            return False
        elif fld_dic[getdata.FLD_BOLTEXT]:
            max_len = fld_dic[getdata.FLD_TEXT_LENGTH]
            if len(raw_val) > max_len:
                wx.MessageBox("\"%s\" is longer than the maximum of %s" % \
                              (raw_val, max_len) + "Either enter a shorter" + \
                              "value or the missing value character (.)")
                return True
            return False
        else:
            raise Exception, "Field supposedly not numeric, datetime, or text"
    
    def CellOKToSave(self, row, col):
        """
        Cannot be an invalid value (must be valid or missing value).
        And if missing value, must be nullable field.
        """
        raw_val = self.grid.GetCellValue(row, col)
        fld_dic = self.dbtbl.GetFldDic(col)
        missing_not_nullable_prob = (raw_val == MISSING_VAL_INDICATOR and \
                                    not fld_dic[getdata.FLD_BOLNULLABLE] and \
                                    fld_dic[getdata.FLD_DATA_ENTRY_OK])
        if missing_not_nullable_prob:
            wx.MessageBox("This field will not allow missing values to " + \
                          "be stored")
        ok_to_save = not self.CellInvalid(row, col) and \
            not missing_not_nullable_prob
        return ok_to_save

    def InitNewRowBuffer(self):
        "Initialise new row buffer"
        self.dbtbl.new_is_dirty = False
        self.dbtbl.new_buffer = {}

    def ResetPrevRowEd(self, prev_row_idx):
        "Set new line custom cell editor for new row"
        for col_idx in range(len(self.flds)):
            self.grid.SetCellEditor(prev_row_idx, col_idx, 
                                    wx.grid.GridCellTextEditor())

    def SetupNewRow(self, data):
        """
        Setup new row ready to receive new data.
        data = [(value as string, fld_name, fld_dets), ...]
        """
        self.dbtbl.SetRowIdDic()
        self.dbtbl.SetNumberRows() # need to refresh        
        new_row_idx = self.dbtbl.GetNumberRows() - 1
        data_tup = tuple([x[0] for x in data])
        # do not add to row_vals_dic - force it to look it up from the db
        # will thus show autocreated values e.g. timestamp, autoincrement etc
        self.DisplayNewRow()
        self.ResetRowLabels(new_row_idx)
        self.InitNewRowBuffer()
        self.FocusOnNewRow(new_row_idx)
        self.ResetPrevRowEd(new_row_idx - 1)
        self.SetNewRowEd(new_row_idx)
    
    def DisplayNewRow(self):
        "Display a new entry row on end of grid"
        self.dbtbl.DisplayNewRow()
    
    def ResetRowLabels(self, row):
        "Reset new row label and restore previous new row label to default"
        prev_row = row - 1
        self.grid.SetRowLabelValue(prev_row, str(prev_row))
        self.grid.SetRowLabelValue(row, "*")
    
    def SaveRow(self, row):
        data = []
        fld_names = getdata.FldsDic2FldNamesLst(self.flds) # sorted list
        for col in range(len(self.flds)):
            raw_val = self.dbtbl.new_buffer.get((row, col), None)
            if raw_val == MISSING_VAL_INDICATOR:
                raw_val = None
            fld_name = fld_names[col]
            fld_dic = self.flds[fld_name]
            data.append((raw_val, fld_name, fld_dic))
        row_inserted = getdata.InsertRow(self.dbe, self.conn, self.cur, 
                                         self.tbl_name, data)
        if row_inserted:
            if self.debug: print "Just inserted row in SaveRow()"
        else:
            if self.debug: print "Unable to insert row in SaveRow()"
            return False
        try:
            self.SetupNewRow(data)
            return True
        except:
            if self.debug: print "Unable to setup new row"
            return False
        
    def OnCellChange(self, event):
        self.grid.ForceRefresh()
        event.Skip()
