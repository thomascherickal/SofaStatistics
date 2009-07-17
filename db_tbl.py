"""
DbTbl is the link between the grid and the underlying data.
"""

import pprint
import wx
import wx.grid

import my_globals
import getdata

MISSING_VAL_INDICATOR = "."


class DbTbl(wx.grid.PyGridTableBase):
    def __init__(self, grid, dbe, conn, cur, tbl, flds, var_labels, idxs, 
                 read_only):
        wx.grid.PyGridTableBase.__init__(self)
        self.debug = False
        self.tbl = tbl
        self.grid = grid
        self.dbe = dbe
        self.quote_obj = getdata.get_obj_quoter_func(self.dbe)
        self.quote_val = getdata.get_val_quoter_func(self.dbe)
        self.conn = conn
        self.cur = cur
        self.read_only = read_only        
        self.SetNumberRows()
        # dict with key = fld name and vals = dict of characteristics
        self.flds = flds 
        self.fld_names = getdata.FldsDic2FldNamesLst(flds_dic=self.flds)
        self.fld_labels = [var_labels.get(x, x.title()) for x in self.fld_names]
        self.idxs = idxs
        self.idx_id, self.must_quote = self.GetIndexCol()
        self.id_col_name = self.fld_names[self.idx_id]
        self.SetRowIdDic()
        self.row_vals_dic = {} # key = row, val = list of values
        if self.debug:
            pprint.pprint(self.fld_names)
            pprint.pprint(self.fld_labels)
            pprint.pprint(self.flds)
            pprint.pprint(self.row_id_dic)
        self.bol_attempt_cell_update = False
        self.SQL_cell_to_update = None
        self.val_of_cell_to_update = None
        self.new_buffer = {} # where new values are stored until 
            #ready to be saved
        self.new_is_dirty = False # TextEditor can set to True.  Is reset to 
            # False when adding a new record
    
    def SetRowIdDic(self):
        """
        Row number and the value of the primary key will not always be 
            the same.  Need quick way of translating from row e.g. 0
            to value of the id field e.g. "ABC123" or 128797 or even 0 ;-).
        """
        SQL_get_id_vals = "SELECT %s FROM %s ORDER BY %s" % \
            (self.quote_obj(self.id_col_name), self.quote_obj(self.tbl), 
             self.quote_obj(self.id_col_name))
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
            name = idx[my_globals.IDX_NAME] 
            is_unique = idx[my_globals.IDX_IS_UNIQUE]
            fld_names = idx[my_globals.IDX_FLDS]
            if is_unique:
                # pretend only ever one field (TODO see above)
                fld_to_use = fld_names[0]
                must_quote = not \
                    self.flds[fld_to_use][my_globals.FLD_BOLNUMERIC]
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
        SQL_num_rows = "SELECT COUNT(*) FROM %s" % self.quote_obj(self.tbl)
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
        if val is None:
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
            for row_n in range(row_min, row_max + 1):
                if self.must_quote:
                    value = self.quote_val(self.row_id_dic[row_n])
                else:
                    value = "%s" % self.row_id_dic[row_n]
                IN_clause_lst.append(value)
            IN_clause = ", ".join(IN_clause_lst)
            SQL_get_values = "SELECT * " + \
                " FROM %s " % self.quote_obj(self.tbl) + \
                " WHERE %s IN(%s)" % (self.quote_obj(self.id_col_name), 
                                      IN_clause) + \
                " ORDER BY %s" % self.quote_obj(self.id_col_name)
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
        proc_data_lst = [self.NoneToMissingVal(x) for x in data_tup]
        row_vals_dic[row_idx] = proc_data_lst
    
    def IsEmptyCell(self, row, col):
        value = self.GetValue(row, col)
        return value == MISSING_VAL_INDICATOR
    
    def SetValue(self, row, col, value):
        """
        Only called if data entered.
        
        Fires first if use mouse to move from a cell you have edited.
        Fires after keypress and SelectCell if you use TAB to move.
        
        If a new row, stores value in new row buffer ready to be saved if 
            OK to save row.
        If an existing, ordinary row, stores SQL to update cell if OK to update
            cell.  Cache will be updated if, and only if, the cell is actually
            updated.
        """
        if self.debug: print "SetValue - row %s, " % row + \
            "col %s with value \"%s\" *************************" % (col, value)
        if self.NewRow(row):
            self.new_buffer[(row, col)] = value
        else:
            self.bol_attempt_cell_update = True
            row_id = self.GetValue(row, self.idx_id)
            col_name = self.fld_names[col]
            raw_val_to_use = getdata.PrepValue(dbe=self.dbe, val=value, 
                                               fld_dic=self.flds[col_name])
            self.val_of_cell_to_update = raw_val_to_use            
            if self.must_quote:
                id_value = self.quote_val(self.row_id_dic[row])
            else:
                id_value = self.row_id_dic[row]
            val2use = "NULL" if raw_val_to_use is None \
                else "\"%s\"" % raw_val_to_use
            # TODO - think about possibilities of SQL injection by hostile party
            SQL_update_value = "UPDATE %s " % self.tbl + \
                " SET %s = %s " % (self.quote_obj(col_name), val2use) + \
                " WHERE %s = " % self.id_col_name + str(id_value)
            if self.debug: 
                print "SetValue - SQL update value: %s" % SQL_update_value
                print "SetValue - Value of cell to update: %s" % \
                    self.val_of_cell_to_update
            self.SQL_cell_to_update = SQL_update_value

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
        
    def ForceRefresh(self):
        msg = wx.grid.GridTableMessage(self, 
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)