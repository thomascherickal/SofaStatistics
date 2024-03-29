"""
DbTbl is the link between the grid and the underlying data.
"""

import pprint
import wx #@UnusedImport
import wx.grid

from sofastats import my_globals as mg  #@UnresolvedImport
from sofastats import lib  #@UnresolvedImport
from sofastats import getdata  #@UnresolvedImport

debug = False


class DbTbl(wx.grid.PyGridTableBase):
    """
    row and col idxs are zero-based.
    """
    def __init__(self, grid, var_labels, *, read_only):
        wx.grid.GridTableBase.__init__(self)
        self.debug = False
        self.dd = mg.DATADETS_OBJ
        self.grid = grid
        self.objqtr = getdata.get_obj_quoter_func(self.dd.dbe)
        self.quote_val = getdata.get_val_quoter_func(self.dd.dbe)
        self.read_only = read_only        
        self.set_num_rows()
        self.fldnames = getdata.fldsdic_to_fldnames_lst(fldsdic=self.dd.flds)
        self.fldlbls = [var_labels.get(x, x.title()) for x in self.fldnames]
        self.idx_id, self.must_quote = self.get_index_col()
        self.id_col_name = self.fldnames[self.idx_id]
        self.set_row_ids_lst()
        self.row_vals_dic = {}  ## key = row, val = list of values
        if self.debug:
            pprint.pprint(self.fldnames)
            pprint.pprint(self.fldlbls)
            pprint.pprint(self.dd.flds)
            pprint.pprint(self.row_ids_lst)
        self.bol_attempt_cell_update = False
        self.sql_cell_to_update = None
        self.val_of_cell_to_update = None
        self.new_buffer = {}  ## where new values are stored until ready to be saved
        self.new_is_dirty = False  ## db_grid can set to True. Is reset to False when adding a new record

    def set_row_ids_lst(self):
        """
        Row number and the value of the primary key will not always be the same.
        Need quick way of translating from row e.g. 0 to value of the id field
        e.g. "ABC123" or 128797 or even 0 ;-).

        Using a list makes it easy to delete items and insert them.

        Zero-based.
        """
        dd = mg.DATADETS_OBJ
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_filt, unused = lib.FiltLib.get_tbl_filts(tbl_filt)
        id_col_name = self.objqtr(self.id_col_name)
        tblname = getdata.tblname_qtr(self.dd.dbe, self.dd.tbl)
        SQL_get_id_vals = f"""
        SELECT {id_col_name}
        FROM {tblname}
        {where_filt}
        ORDER BY {id_col_name}"""
        if debug: print(SQL_get_id_vals)
        self.dd.cur.execute(SQL_get_id_vals)
        ## NB could easily be 10s or 100s of thousands of records
        self.row_ids_lst = [x[0] for x in self.dd.cur.fetchall()]

    def get_fldname(self, col):
        return self.fldnames[col]

    def get_fld_dic(self, col):
        fldname = self.get_fldname(col)
        return self.dd.flds[fldname]

    def get_index_col(self):
        """
        Pick first unique indexed column and return col position, and must_quote
        (e.g. for string or date fields).

        TODO - cater to composite indexes properly esp when getting values

        idxs = [idx0, idx1, ...]

        each idx = (name, is_unique, flds)
        """
        for idx in self.dd.idxs:
            is_unique = idx[mg.IDX_IS_UNIQUE]
            fldnames = idx[mg.IDX_FLDS]
            if is_unique:
                ## pretend only ever one field (TODO see above)
                fld2use = fldnames[0]
                must_quote = not self.dd.flds[fld2use][mg.FLD_BOLNUMERIC]
                col_idx = self.fldnames.index(fld2use)
                if self.debug:
                    print(f'Col idx: {col_idx}')
                    print(f'Must quote: {must_quote}')
                return col_idx, must_quote

    def GetNumberCols(self):
        ## wxPython
        num_cols = len(self.dd.flds)
        if self.debug: print(f'N cols: {num_cols}')
        return num_cols

    def DeleteRows(self, _pos=0, _numRows=1):
        ## wxPython
        ## always allow
        return True

    def set_num_rows(self):
        """
        rows_n -- number of rows in grid including empty row at end if there is
        one. Thinking from a grid, not a data, point of view.

        idx_final_data_row -- index of final data row.
        """
        debug = False
        dd = mg.DATADETS_OBJ
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_filt, unused = lib.FiltLib.get_tbl_filts(tbl_filt)
        tblname = getdata.tblname_qtr(self.dd.dbe, self.dd.tbl)
        SQL_rows_n = f'SELECT COUNT(*) FROM {tblname} {where_filt}'
        self.dd.cur.execute(SQL_rows_n)
        self.rows_n = self.dd.cur.fetchone()[0]
        self.idx_final_data_row = self.rows_n - 1
        if not self.read_only:
            self.rows_n += 1  ## An extra row for data entry
        if self.debug or debug:
            print(f'N rows: {self.rows_n}')
            print(f'idx_final_data_row: {self.idx_final_data_row}')

    def GetNumberRows(self):
        """Includes new data row if there is one."""
        ## wxPython
        return self.rows_n

    def get_n_data_rows(self):
        return self.idx_final_data_row + 1

    def is_new_row(self, row):
        new_row = row > self.idx_final_data_row
        return new_row

    def is_final_row(self, row):
        final_row = (row == self.idx_final_data_row)
        return final_row 

    def GetRowLabelValue(self, row):
        ## wxPython
        new_row = (row > self.idx_final_data_row)
        if new_row:
            if self.new_is_dirty:
                return mg.NEW_IS_DIRTY
            else:
                return mg.NEW_IS_READY
        else:
            return str(row + 1)

    def GetColLabelValue(self, col):
        ## wxPython
        return self.fldlbls[col]

    def none_to_missing_val(self, val):
        if val is None:
            val = mg.MISSING_VAL_INDICATOR
        return val

    def GetValue(self, row, col):
        ## wxPython
        """
        NB row and col are 0-based.

        The performance of this method is critical to the performance of the
        grid as a whole - displaying, scrolling, updating etc.

        Very IMPORTANT to have a unique field we can use to identify rows if at
        all possible.

        On larger datasets (> 10,000) performance is hideous using order by and
        limit or similar.

        Need to be able to filter to individual, unique, indexed row.

        Use unique index where possible - if < 1000 recs and no unique index,
        could use the method below (while telling the user the lack of an index
        significantly harms performance esp while scrolling).

        SQL_get_value = "SELECT %s " % col_name + \
            " FROM %s " % dd.tbl + \
            " ORDER BY %s " % id_col_name + \
            " LIMIT %s, 1" % row

        Much, much faster to do one database call per row than once per cell
        (esp with lots of columns).

        NB if not read only will be an empty row at the end.

        Turn None (Null) into . as missing value identifier.
        """
        ## try cache first
        debug = False
        try:
            val = self.row_vals_dic[row][col]
        except KeyError:
            extra = 10
            """
            If new row, just return value from new_buffer (or missing value).

            Otherwise, fill cache (up to extra (e.g. 10) rows above and below)
            and then grab this col value.

            More expensive for first cell but heaps less expensive for rest.

            Set cell editor while at it. Very expensive for large table so do it
            as needed.
            """
            dd = mg.DATADETS_OBJ
            unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
            unused, and_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
            if self.is_new_row(row):
                return self.new_buffer.get((row, col), mg.MISSING_VAL_INDICATOR)
            ## identify row range            
            row_min = row - extra if row - extra > 0 else 0
            row_max = (row + extra if row + extra < self.idx_final_data_row
                else self.idx_final_data_row)
            ## create IN clause listing id values
            IN_clause_lst = []
            for row_idx in range(row_min, row_max + 1):
                try:
                    raw_val = self.row_ids_lst[row_idx]
                except IndexError:
                    if debug:
                        print(f'row_idx: {row_idx}\n\n{self.row_ids_lst}')
                if self.must_quote:
                    fld_dic = self.get_fld_dic(col)
                    value = self.quote_val(raw_val,
                        charset2try=fld_dic[mg.FLD_CHARSET])
                else:
                    value = f'{raw_val}'
                IN_clause_lst.append(value)
            IN_clause = ', '.join(IN_clause_lst)
            tbl_name = getdata.tblname_qtr(self.dd.dbe, self.dd.tbl)
            id_col_name = self.id_col_name
            SQL_get_values = f"""SELECT *
                FROM {tbl_name}
                WHERE {id_col_name}
                IN({IN_clause})
                {and_filt}
                ORDER BY {id_col_name}"""
            if debug or self.debug: print(SQL_get_values)
            #dd.con.commit() # extra commits keep postgresql problems
            #    away when a cell change is rejected by SOFA Stats validation
            #    [update - unable to confirm]
            # problem accessing cursor if committed in MS SQL
            # see http://support.microsoft.com/kb/321714
            self.dd.cur.execute(SQL_get_values)
            #dd.con.commit()
            row_idx = row_min
            for data_tup in self.dd.cur.fetchall():
                if debug or self.debug: print(data_tup)
                self.add_data_to_row_vals_dic(
                    self.row_vals_dic, row_idx, data_tup)
                row_idx += 1
            val = self.row_vals_dic[row][col]  ## the bit we're interested in now
        display_val = lib.UniLib.any2unicode(val)
        return display_val

    def add_data_to_row_vals_dic(self, row_vals_dic, row_idx, data_tup):
        """
        row_vals_dic - key = row, val = tuple of values
        Add new row to row_vals_dic.
        """
        debug = False  ## only do this for a small table!
        proc_data_lst = [self.none_to_missing_val(x) for x in data_tup]
        row_vals_dic[row_idx] = proc_data_lst
        if self.debug or debug: print(row_vals_dic)

    def IsEmptyCell(self, row, col):
        ## wxPython
        value = self.GetValue(row, col)
        return value == mg.MISSING_VAL_INDICATOR

    def SetValue(self, row, col, value):
        ## wxPython
        """
        Only called if data entered.

        Fires first if use mouse to move from a cell you have edited.

        Fires after keypress and SelectCell if you use TAB to move.

        If a new row, stores value in new row buffer ready to be saved if OK to
        save row.

        If an existing, ordinary row, stores sql_cell_to_update if OK to update
        cell. Cache will be updated if, and only if, the cell is actually
        updated.
        """
        debug = False
        if self.debug or debug: 
            print(f'SetValue - row {row}, col {col} with value "{value}" '
                '************************')
        if self.is_new_row(row):
            self.new_buffer[(row, col)] = value
        else:
            self.bol_attempt_cell_update = True
            colname = self.fldnames[col]
            raw_val_to_use = getdata.prep_val(dbe=self.dd.dbe, val=value,
                fld_dic=self.dd.flds[colname])
            self.val_of_cell_to_update = raw_val_to_use
            fld_dic = self.get_fld_dic(col)     
            if self.must_quote:  ## only refers to index column
                id_value = self.quote_val(self.row_ids_lst[row])
            else:
                id_value = self.row_ids_lst[row]
            val2use = ('NULL' if raw_val_to_use is None
                else self.quote_val(raw_val_to_use))
            ## TODO - think about possibilities of SQL injection by hostile party
            tblname = getdata.tblname_qtr(self.dd.dbe, self.dd.tbl)
            col_name = self.objqtr(colname)
            SQL_update_value = f"""UPDATE {tblname}
                SET {col_name} = {val2use}
                WHERE {self.id_col_name} = {id_value}"""
            if self.debug or debug: 
                print(f'SetValue - SQL update value: {SQL_update_value}')
                print('SetValue - Value of cell to '
                    f'update: {self.val_of_cell_to_update}')
            self.sql_cell_to_update = SQL_update_value

    def display_new_row(self):
        """
        http://wiki.wxpython.org/wxGrid

        The example uses getGrid() instead of wxPyGridTableBase::GetGrid() can
        be issues depending on version of wxPython.

        Safest to pass in the grid.
        """
        self.grid.BeginBatch()
        msg = wx.grid.GridTableMessage(
            self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
        self.grid.ProcessTableMessage(msg)
        msg = wx.grid.GridTableMessage(
            self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)
        self.grid.EndBatch()
        self.grid.ForceRefresh()

    def force_refresh(self):
        self.row_vals_dic = {}  ## flush cache
        msg = wx.grid.GridTableMessage(
            self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)
