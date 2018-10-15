from abc import ABC, abstractmethod
from collections import namedtuple
import csv
import datetime
from pathlib import Path

import openpyxl #@UnresolvedImport
from openpyxl.styles import Alignment, Font
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from sofastats import getdata
from sofastats import output

dd = mg.DATADETS_OBJ


class Writer(ABC):

    """
    Write out content of table to output e.g. CSV. Optionally include label
    fields at end.
    """

    def __init__(self, colnames2use, *, inc_lbls):
        """
        :param list colnames2use: list of column names to use
        :param bool inc_lbls: if True, include label versions of fields at end
         as extra columns.
        """
        self.extra_lbl = '_with_labels' if inc_lbls else ''
        self.desktop = Path(mg.HOME_PATH) / 'Desktop'

    @abstractmethod
    def process_row(self, row, row_n, orig_and_lbl_col_dets, orig_col_has_lbl):
        """
        Iterate through items in row. If item has a label variant to display (i.e. its
        status in col_lbl_statuses is True
        """
        orig_col_has_lbl
        self.row_idx2all_cols_next_idx = {}

    @abstractmethod
    def save(self):
        pass


class CsvWriter(Writer):

    def __init__(self, colnames2use, *, inc_lbls):
        super().__init__(inc_lbls=inc_lbls)
        fname_csv = f'{dd.tbl}{self.extra_lbl}.csv'
        fpath_csv = str(self.desktop / fname_csv)
        self.f = open(fpath_csv, 'wb')
        self.csv_writer = csv.writer(
            self.f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        self.csv_writer.writerow(colnames2use)  ## write header row

    def process_row(self, row, row_n, orig_and_lbl_col_dets, orig_col_has_lbl):
        try:
            if row_n == 1:  ## header
                header_row = []
                for item in row:
                    if item == mg.SOFA_ID:
                        item = mg.WAS_SOFA_ID
                    header_row.append(item)
                row2write = header_row
            else:
                
                row2write = row
            self.csv_writer.writerow(row2write)
        
        except Exception as e:
            raise Exception(f'Unable to write row {row_n} to csv file. '
                f'Orig error: {e}')

    def save(self):
        self.f.close()


class SpreadsheetWriter(Writer):

    def __init__(self, colnames2use, *, inc_lbls):
        super().__init__(inc_lbls=inc_lbls)
        self.wb = openpyxl.Workbook(write_only=True)  ## requires lxml
        safe_sheetname = lib.get_safer_name(f'{dd.tbl[:20]} output')
        self.sheet = self.wb.create_sheet(safe_sheetname, 0)
        self.style_bold_12pt = Font(name='Arial', size=12, bold=True)

    def process_row(self, row, row_n, orig_and_lbl_col_dets, orig_col_has_lbl):
        """
        The number of columns in row is less than the total number of columns
        being written if we are including labels and there are labels available. 

        So as we iterate through columns in the row we need to see if there is a
        label column to display as well. If so, the index for the next column in
        the row will be higher by one because of the presence of a label column
        before it. We need that index to access the correct dets in
        orig_and_lbl_col_dets.
        """
        idx_orig_and_lbl_cols = 0  ## tracker for where we are in orig_and_lbl_col_dets

#         if all_col_dets[idx_final_col].isdate:
#             if isinstance(val, datetime.datetime):
#                 val2use = val
#             else:
#                 try:
#                     val2use = lib.DateLib.get_datetime_from_str(
#                         val)
#                 except Exception:
#                     val2use = ''
#              
#              
#             self.sheet.write(
#                 idx_row, idx_final_col, val2use, date_style)
#              
#              
#         else:
#             self.sheet.write(idx_row, idx_final_col, val)

    def save(self):
        fname_xlsx = f'{dd.tbl}{self.extra_lbl}.xls'
        fpath_xlsx = str(self.desktop / fname_xlsx)
        self.wb.save(fpath_xlsx)


class DlgExportData(wx.Dialog):

    def __init__(self, n_rows):
        """
        temp_desktop_report_only -- exporting output to a temporary desktop
        folder

        Works with SQLite, PostgreSQL, MySQL, CUBRID, MS Access and SQL Server.
        """
        title = f'Export {dd.tbl} to spreadsheet'
        wx.Dialog.__init__(self, parent=None, id=-1, title=title,
            pos=(mg.HORIZ_OFFSET+200, 300),
            style=(wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX
                |wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN))
        szr = wx.BoxSizer(wx.VERTICAL)
        self.n_rows = n_rows
        self.export_status = {mg.CANCEL_EXPORT: False}  ## can change and running script can check on it.
        self.chk_inc_lbls = wx.CheckBox(
            self, -1, _('Include extra label columns (if available)'))
        szr.Add(self.chk_inc_lbls, 0, wx.ALL, 10)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        self.btn_cancel.Enable(False)
        self.btn_export = wx.Button(self, -1, 'Export')
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
        self.btn_export.Enable(True)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=0)
        szr_btns.AddGrowableCol(1,2)  ## idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_export, 0, wx.ALIGN_RIGHT)
        self.progbar = wx.Gauge(self, -1, mg.EXPORT_DATA_GAUGE_STEPS,
            size=(-1, 20), style=wx.GA_HORIZONTAL)
        self.btn_close = wx.Button(self, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close)
        szr.Add(szr_btns, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr.Add(self.progbar, 0, wx.GROW|wx.ALIGN_RIGHT|wx.ALL, 10)
        szr.Add(self.btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(szr)
        szr.SetSizeHints(self)
        szr.Layout()

    def extract_col_dets(self, orig_col_names, *, val_dics, inc_lbls):
        """
        Get details for each column e.g. whether numeric, and whether it has a
        label to be displayed as well as then original value. If showing lbl
        fields may be more than one set of col dets per col (if labels available
        for particular columns).

        :return: a two-tuple with:
         orig_col_has_lbl - True or False for every original field.
         orig_and_lbl_col_dets - all fields in order. Label fields appear immediately
         after original version if we are including labels and there are labels
         for that field.
        :rtype: tuple
        """
        debug = False
        orig_col_has_lbl = []
        orig_and_lbl_col_dets = []
        ColDet = namedtuple('ColDet', 'col_name, numeric, isdate, valdic')
        for orig_colname in orig_col_names:
            numericfld = dd.flds[orig_colname][mg.FLD_BOLNUMERIC]
            datefld = dd.flds[orig_colname][mg.FLD_BOLDATETIME]
            if debug and datefld: print(f'{orig_colname} is a datetime field')
            orig_and_lbl_col_dets.append(
                ColDet(orig_colname, numericfld, datefld, None))  ## always raw first so no valdic
            has_lbls = val_dics.get(orig_colname)
            if inc_lbls and has_lbls:
                orig_col_has_lbl.append(True)
                valdic = val_dics.get(orig_colname)
                orig_and_lbl_col_dets.append(
                    ColDet(f'{orig_colname}_Label', False, False, valdic))  ## labels are not dates or numeric
            else:
                orig_col_has_lbl.append(False)
        return orig_col_has_lbl, orig_and_lbl_col_dets

    @staticmethod
    def _get_sql(orig_col_names):
        debug = False
        objqtr = getdata.get_obj_quoter_func(dd.dbe)
        colnames_clause = ', '.join([objqtr(x) for x in orig_col_names])
        dbe_tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
        sql_get_data = f'SELECT {colnames_clause} FROM {dbe_tblname}'
        if debug: print(sql_get_data)
        return sql_get_data

    def write_out(self, orig_col_has_lbl, orig_and_lbl_col_dets, orig_col_names,
            *, inc_lbls, do_spreadsheet):
        """
        For each writer (CSV and, optionally, spreadsheet) write out content.
        """
        colnames2use = [det.col_name for det in orig_and_lbl_col_dets]
        writers = [CsvWriter(colnames2use, inc_lbls=inc_lbls), ]
        if do_spreadsheet:
            writers.append(SpreadsheetWriter(colnames2use, inc_lbls=inc_lbls))
        sql_get_data = DlgExportData._get_sql(orig_col_names)
        dd.cur.execute(sql_get_data)  ## must be dd.cur
        row_n = 1
        while True:
            row = dd.cur.fetchone()  ## Note - won't have the extra columns, just the original columns
            if row is None:
                break
            for writer in writers:
                writer.process_row(
                    row, row_n, orig_and_lbl_col_dets, orig_col_has_lbl)
            gauge2set = min(
                (row_n/self.n_rows)*mg.EXPORT_DATA_GAUGE_STEPS,
                mg.EXPORT_DATA_GAUGE_STEPS)
            self.progbar.SetValue(gauge2set)
            row_n += 1
        for writer in writers:
            writer.save()

    def on_btn_export(self, _evt):
        """
        Make CSV and, if possible, a spreadsheet as well (must not have too many
        columns).

        Follows format of original data source where possible.

        Start with original list of columns and column names. If including
        labels, with insert additional fields as required.
        """
        self.progbar.SetValue(0)
        wx.BeginBusyCursor()
        inc_lbls = self.chk_inc_lbls.IsChecked()
        orig_col_names = getdata.fldsdic_to_fldnames_lst(fldsdic=dd.flds)
        cc = output.get_cc()
        (_var_labels, _var_notes,
         _var_types, val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        orig_col_has_lbl, orig_and_lbl_col_dets = self.extract_col_dets(
            orig_col_names, val_dics, inc_lbls=inc_lbls)
        n_cols = len(orig_and_lbl_col_dets)
        do_spreadsheet = (n_cols <= 256)
        if not do_spreadsheet:
            wx.MessageBox(f'Too many columns ({n_cols}) for an xls spreadsheet.'
                ' Only making the csv')

        self.write_out(orig_col_has_lbl, orig_and_lbl_col_dets, orig_col_names,
            inc_lbls=inc_lbls, do_spreadsheet=do_spreadsheet)

        self.progbar.SetValue(mg.EXPORT_DATA_GAUGE_STEPS)
        lib.GuiLib.safe_end_cursor()
        self.align_btns_to_exporting(exporting=False)
        wx.MessageBox(_('Your data has been exported to your desktop'))
        self.progbar.SetValue(0)

    def on_btn_cancel(self, _evt):
        self.export_status[mg.CANCEL_EXPORT] = True

    def align_btns_to_exporting(self, exporting):
        self.btn_close.Enable(not exporting)
        self.btn_cancel.Enable(exporting)
        self.btn_export.Enable(not exporting)

    def on_btn_close(self, _evt):
        self.Destroy()
