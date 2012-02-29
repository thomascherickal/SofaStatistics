"""
DbTbl is the link between the grid and the underlying data.
"""

import pprint
import wx
import wx.grid

import my_globals as mg
import lib
import getdata

debug = False


class DbTbl(wx.grid.PyGridTableBase):
    def __init__(self, grid, var_labels, readonly):
        dd = mg.DATADETS_OBJ
        wx.grid.PyGridTableBase.__init__(self)
        self.debug = False
        self.grid = grid
        self.objqtr = getdata.get_obj_quoter_func(dd.dbe)
        self.quote_val = getdata.get_val_quoter_func(dd.dbe)
        self.readonly = readonly        
        self.set_num_rows()
        self.fldnames = getdata.fldsdic_to_fldnames_lst(fldsdic=dd.flds)
        self.fldlbls = [var_labels.get(x, x.title()) for x in self.fldnames]
        self.idx_id, self.must_quote = self.get_index_col()
        self.id_col_name = self.fldnames[self.idx_id]
        self.set_row_ids_lst()
        self.row_vals_dic = {} # key = row, val = list of values
        if self.debug:
            pprint.pprint(self.fldnames)
            pprint.pprint(self.fldlbls)
            pprint.pprint(dd.flds)
            pprint.pprint(self.row_ids_lst)
        self.bol_attempt_cell_update = False
        self.sql_cell_to_update = None
        self.val_of_cell_to_update = None
        self.new_buffer = {} # where new values are stored until 
            #ready to be saved
        self.new_is_dirty = False # db_grid can set to True.  Is reset to 
            # False when adding a new record
    
    def set_row_ids_lst(self):
        """
        Row number and the value of the primary key will not always be 
            the same.  Need quick way of translating from row e.g. 0
            to value of the id field e.g. "ABC123" or 128797 or even 0 ;-).
        Using a list makes it easy to delete items and insert them.
        Zero-based.
        """
        dd = mg.DATADETS_OBJ
        SQL_get_id_vals = u"SELECT %s FROM %s ORDER BY %s" % \
                                        (self.objqtr(self.id_col_name), 
                                         getdata.tblname_qtr(dd.dbe, dd.tbl), 
                                         self.objqtr(self.id_col_name))
        if debug: print(SQL_get_id_vals)
        dd.cur.execute(SQL_get_id_vals)
        # NB could easily be 10s or 100s of thousands of records
        self.row_ids_lst = [x[0] for x in dd.cur.fetchall()]
    
    def get_fldname(self, col):
        return self.fldnames[col]
    
    def get_fld_dic(self, col):
        dd = mg.DATADETS_OBJ
        fldname = self.get_fldname(col)
        return dd.flds[fldname]
    
    def get_index_col(self):
        """
        Pick first unique indexed column and return 
            col position, and must_quote (e.g. for string or date fields).
        TODO - cater to composite indexes properly esp when getting values
        idxs = [idx0, idx1, ...]
        each idx = (name, is_unique, flds)
        """
        dd = mg.DATADETS_OBJ
        for idx in dd.idxs:
            is_unique = idx[mg.IDX_IS_UNIQUE]
            fldnames = idx[mg.IDX_FLDS]
            if is_unique:
                # pretend only ever one field (TODO see above)
                fld2use = fldnames[0]
                must_quote = not dd.flds[fld2use][mg.FLD_BOLNUMERIC]
                col_idx = self.fldnames.index(fld2use)
                if self.debug:
                    print(u"Col idx: %s" % col_idx)
                    print(u"Must quote:" + unicode(must_quote))
                return col_idx, must_quote
    
    def GetNumberCols(self):
        # wxPython
        dd = mg.DATADETS_OBJ
        num_cols = len(dd.flds)
        if self.debug:
            print(u"N cols: %s" % num_cols)
        return num_cols

    def DeleteRows(self, pos=0, numRows=1):
        # wxPython
        # always allow
        return True

    def set_num_rows(self):
        debug = False
        dd = mg.DATADETS_OBJ
        SQL_rows_n = u"SELECT COUNT(*) FROM %s" % getdata.tblname_qtr(dd.dbe, 
                                                                      dd.tbl)
        dd.cur.execute(SQL_rows_n)
        self.rows_n = dd.cur.fetchone()[0]
        if not self.readonly:
            self.rows_n += 1
        if self.debug or debug: print(u"N rows: %s" % self.rows_n)
        self.rows_to_fill = self.rows_n - 1 if self.readonly \
                                            else self.rows_n - 2
    
    def GetNumberRows(self):
        # wxPython
        return self.rows_n
    
    def is_new_row(self, row):
        new_row = row > self.rows_to_fill
        return new_row
    
    def is_final_row(self, row):
        final_row = (row == self.rows_to_fill)
        return final_row 
    
    def GetRowLabelValue(self, row):
        # wxPython
        new_row = row > self.rows_to_fill
        if new_row:
            if self.new_is_dirty:
                return mg.NEW_IS_DIRTY
            else:
                return mg.NEW_IS_READY
        else:
            return row + 1
    
    def GetColLabelValue(self, col):
        # wxPython
        return self.fldlbls[col]
    
    def none_to_missing_val(self, val):
        if val is None:
            val = mg.MISSING_VAL_INDICATOR
        return val
    
    def GetValue(self, row, col):
        # wxPython
        """
        NB row and col are 0-based.
        The performance of this method is critical to the performance
            of the grid as a whole - displaying, scrolling, updating etc.
        Very IMPORTANT to have a unique field we can use to identify rows
            if at all possible.
        On larger datasets (> 10,000) performance is hideous
            using order by and limit or similar.
        Need to be able to filter to individual, unique, indexed row.
        Use unique index where possible - if < 1000 recs and no unique
            index, could use the method below (while telling the user the lack 
            of an index significantly harms performance esp while scrolling). 
        SQL_get_value = "SELECT %s " % col_name + \
            " FROM %s " % dd.tbl + \
            " ORDER BY %s " % id_col_name + \
            " LIMIT %s, 1" % row
        Much, much faster to do one database call per row than once per cell 
            (esp with lots of columns).
        NB if not read only will be an empty row at the end.
        Turn None (Null) into . as missing value identifier.
        """
        # try cache first
        debug = False
        dd = mg.DATADETS_OBJ
        try:
            val = self.row_vals_dic[row][col]
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
            if self.is_new_row(row):
                return self.new_buffer.get((row, col), mg.MISSING_VAL_INDICATOR)
            # identify row range            
            row_min = row - extra if row - extra > 0 else 0
            row_max = row + extra if row + extra < self.rows_to_fill \
                else self.rows_to_fill
            # create IN clause listing id values
            IN_clause_lst = []
            for row_idx in range(row_min, row_max + 1):
                try:
                    raw_val = self.row_ids_lst[row_idx]
                except IndexError:
                    if debug:
                        print("row_idx: %s\n\n%s" % (row_idx, self.row_ids_lst))
                if self.must_quote:
                    value = self.quote_val(raw_val)
                else:
                    value = u"%s" % raw_val
                IN_clause_lst.append(value)
            IN_clause = u", ".join(IN_clause_lst)
            SQL_get_values = u"SELECT * " + \
                u" FROM %s " % getdata.tblname_qtr(dd.dbe, dd.tbl) + \
                u" WHERE %s IN(%s)" % (self.objqtr(self.id_col_name), 
                                      IN_clause) + \
                u" ORDER BY %s" % self.objqtr(self.id_col_name)
            if debug or self.debug: print(SQL_get_values)
            #dd.con.commit() # extra commits keep postgresql problems
                # away when a cell change is rejected by SOFA Stats validation
                # [update - unable to confirm]
            # problem accessing cursor if committed in MS SQL
            # see http://support.microsoft.com/kb/321714
            dd.cur.execute(SQL_get_values)
            #dd.con.commit()
            row_idx = row_min
            for data_tup in dd.cur.fetchall(): # tuple of values
                # handle microsoft characters
                data_tup = tuple([lib.handle_ms_data(x) for x in data_tup])
                if debug or self.debug: print(data_tup)
                self.add_data_to_row_vals_dic(self.row_vals_dic, row_idx, 
                                              data_tup)
                row_idx += 1
            val = self.row_vals_dic[row][col] # the bit we're interested in now
        display_val = lib.any2unicode(val)
        return display_val
    
    def add_data_to_row_vals_dic(self, row_vals_dic, row_idx, data_tup):
        """
        row_vals_dic - key = row, val = tuple of values
        Add new row to row_vals_dic.
        """
        debug = False # only do this for a small table!
        proc_data_lst = [self.none_to_missing_val(x) for x in data_tup]
        row_vals_dic[row_idx] = proc_data_lst
        if self.debug or debug: print(row_vals_dic)
    
    def IsEmptyCell(self, row, col):
        # wxPython
        value = self.GetValue(row, col)
        return value == mg.MISSING_VAL_INDICATOR
    
    def SetValue(self, row, col, value):
        # wxPython
        """
        Only called if data entered.        
        Fires first if use mouse to move from a cell you have edited.
        Fires after keypress and SelectCell if you use TAB to move.
        If a new row, stores value in new row buffer ready to be saved if 
            OK to save row.
        If an existing, ordinary row, stores sql_cell_to_update if OK to update
            cell.  Cache will be updated if, and only if, the cell is actually
            updated.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        if self.debug or debug: 
            print(u"SetValue - row %s, " % row +
            u"col %s with value \"%s\" ************************" % (col, value))
        if self.is_new_row(row):
            self.new_buffer[(row, col)] = value
        else:
            self.bol_attempt_cell_update = True
            colname = self.fldnames[col]
            raw_val_to_use = getdata.prep_val(dbe=dd.dbe, val=value, 
                                              fld_dic=dd.flds[colname])
            self.val_of_cell_to_update = raw_val_to_use         
            if self.must_quote: # only refers to index column
                id_value = self.quote_val(self.row_ids_lst[row])
            else:
                id_value = self.row_ids_lst[row]
            val2use = u"NULL" if raw_val_to_use is None \
                else self.quote_val(raw_val_to_use)
            # TODO - think about possibilities of SQL injection by hostile party
            SQL_update_value = u"UPDATE %s " % \
                    getdata.tblname_qtr(dd.dbe, dd.tbl) + \
                    u" SET %s = %s " % (self.objqtr(colname), val2use) + \
                    u" WHERE %s = " % self.id_col_name + unicode(id_value)
            if self.debug or debug: 
                print(u"SetValue - SQL update value: %s" % SQL_update_value)
                print(u"SetValue - Value of cell to update: %s" %
                    self.val_of_cell_to_update)
            self.sql_cell_to_update = SQL_update_value

    def display_new_row(self):
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
        
    def force_refresh(self):
        msg = wx.grid.GridTableMessage(self, 
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)