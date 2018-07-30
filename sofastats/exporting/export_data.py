from collections import namedtuple
import csv
import datetime
import os
from pathlib import Path

import xlwt #@UnresolvedImport
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from sofastats import getdata
from sofastats import output


class DlgExportData(wx.Dialog):

    def __init__(self, n_rows):
        """
        temp_desktop_report_only -- exporting output to a temporary desktop
        folder

        Works with SQLite, PostgreSQL, MySQL, CUBRID, MS Access and SQL Server.
        """
        dd = mg.DATADETS_OBJ
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

    def on_btn_export(self, _event):
        """
        Follow style of Data List code where possible.
        
        Start with original list of columns and column names. If including 
        labels, with insert additional fields as required.
        
        Collect details for each (original) field. Then loop through column 
        names and 
        """
        debug = False
        self.progbar.SetValue(0)
        wx.BeginBusyCursor()
        inc_lbls = self.chk_inc_lbls.IsChecked()
        dd = mg.DATADETS_OBJ
        cc = output.get_cc()
        extra_lbl = '_with_labels' if inc_lbls else ''
        filname_csv = f'{dd.tbl}{extra_lbl}.csv'
        filname_xls = f'{dd.tbl}{extra_lbl}.xls'
        desktop = str(Path(mg.HOME_PATH) / 'Desktop')
        filpath_csv = str(Path(desktop) / filname_csv)
        filpath_xls = str(Path(desktop) / filname_xls)
        if debug:
            print(filpath_csv)
            print(filpath_xls)
        objqtr = getdata.get_obj_quoter_func(dd.dbe)
        orig_col_names = getdata.fldsdic_to_fldnames_lst(fldsdic=dd.flds)
        (unused, unused,
         unused, val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        ## get alignment and val_dics (if showing lbl fields may be more than one set of col dets per col)
        all_col_dets = []
        col_lbl_statuses = []
        ColDet = namedtuple('ColDet', 'col_name, numeric, isdate, valdic')
        for i, orig_colname in enumerate(orig_col_names):
            numericfld = dd.flds[orig_colname][mg.FLD_BOLNUMERIC]
            datefld = dd.flds[orig_colname][mg.FLD_BOLDATETIME]
            if debug and datefld: print(f'{orig_colname} is a datetime field')
            all_col_dets.append(
                ColDet(orig_colname, numericfld, datefld, None))  ## always raw first so no valdic
            has_lbls = val_dics.get(orig_colname)
            if inc_lbls and has_lbls:
                col_lbl_statuses.append(True)
                valdic = val_dics.get(orig_colname)
                all_col_dets.append(
                    ColDet(f'{orig_colname}_Label', False, False, valdic)) # labels are not dates or numeric
            else:
                col_lbl_statuses.append(False)
        n_cols = len(all_col_dets)
        do_spreadsheet = (n_cols <= 256)
        if not do_spreadsheet:
            wx.MessageBox(f'Too many columns ({n_cols}) for an xls spreadsheet.'
                ' Only making the csv')
        if do_spreadsheet:   
            book = xlwt.Workbook(encoding='utf8')
            safe_sheetname = lib.get_safer_name(f'{dd.tbl[:20]} output')
            sheet = book.add_sheet(safe_sheetname)
            style_bold_12pt = xlwt.XFStyle()
            font = xlwt.Font()
            font.name = 'Arial'
            font.bold = True
            font.height = 12*20  ##12pt
            style_bold_12pt.font = font
        colnames2use = [det.col_name for det in all_col_dets]
        raw_list = [colnames2use, ]
        for idx_col, colname2use in enumerate(colnames2use):
            if colname2use == mg.SOFA_ID:
                colname2use = mg.WAS_SOFA_ID
            if do_spreadsheet:
                col_style = xlwt.XFStyle()
                det = all_col_dets[idx_col]
                if det.numeric:
                    alignment = xlwt.Alignment()
                    alignment.horz = xlwt.Alignment.HORZ_RIGHT
                    col_style.alignment = alignment
                sheet.col(idx_col).set_style(col_style)
                if det.isdate:
                    sheet.col(idx_col).width = 256*20  
                sheet.write(0, idx_col, colname2use, style_bold_12pt)  ## actual hdr row content
        ## get data from SQL line by line
        colnames_clause = ', '.join([objqtr(x) for x in orig_col_names])
        dbe_tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
        SQL_get_data = f'SELECT {colnames_clause} FROM {dbe_tblname}'
        if debug: print(SQL_get_data)
        dd.cur.execute(SQL_get_data)  ## must be dd.cur
        idx_row = 1
        date_style = xlwt.XFStyle()
        date_style.num_format_str = 'yyyy-mm-dd hh:mm:ss'
        while True:
            try:
                row = dd.cur.fetchone()  ## Note - won't have the extra columns, just the original
                if row is None:
                    break  ## run out of rows
                row_raw = []
                idx_final_cols = 0  ## have to manage these ourselves
                for idx_orig_col, val in enumerate(row):
                    has_lbl = col_lbl_statuses[idx_orig_col]
                    if do_spreadsheet:
                        if all_col_dets[idx_final_cols].isdate:
                            if isinstance(val, datetime.datetime):
                                val2use = val
                            else:
                                try:
                                    val2use = lib.DateLib.get_datetime_from_str(
                                        val)
                                except Exception:
                                    val2use = ''
                            sheet.write(
                                idx_row, idx_final_cols, val2use, date_style)
                        else:
                            sheet.write(idx_row, idx_final_cols, val)
                    row_raw.append(str(val))  ## must be a string
                    idx_final_cols += 1
                    if has_lbl:
                        det = all_col_dets[idx_final_cols] 
                        lbl2show = (det.valdic.get(val, val) if det.valdic
                            else val)
                        if do_spreadsheet:
                            sheet.write(idx_row, idx_final_cols, lbl2show)
                        row_raw.append(str(lbl2show))  ## must be a string
                        idx_final_cols += 1
                raw_list.append(row_raw)
                idx_row += 1
                gauge2set = min(
                    ((1.0*idx_row)/self.n_rows)*mg.EXPORT_DATA_GAUGE_STEPS,
                    mg.EXPORT_DATA_GAUGE_STEPS)
                self.progbar.SetValue(gauge2set)
            except my_exceptions.ExportCancel:
                wx.MessageBox('Export Cancelled')
            except Exception as e:
                msg = (f'Problem exporting output. Orig error: {b.ue(e)}')
                if debug: print(msg)
                wx.MessageBox(msg)
                self.progbar.SetValue(0)
                lib.GuiLib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                return
        with open(filpath_csv, 'wb') as f_csv:  ## no special encoding needed given what writer does, must be in binary mode otherwise extra line breaks on Windows 
            csv_writer = csv.writer(
                f_csv, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i, row in enumerate(raw_list, 1):
                try:
                    if i == 1:  ## header
                        header_row = []
                        for item in row:
                            if item == mg.SOFA_ID:
                                item = mg.WAS_SOFA_ID
                            header_row.append(item)
                        row = header_row
                    csv_writer.writerow(row)
                except Exception as e:
                    raise Exception(f'Unable to write row {i} to csv file. '
                        f'Orig error: {e}')
            f_csv.close()
        if do_spreadsheet:
            book.save(filpath_xls)
        self.progbar.SetValue(mg.EXPORT_DATA_GAUGE_STEPS)
        lib.GuiLib.safe_end_cursor()
        self.align_btns_to_exporting(exporting=False)
        wx.MessageBox(_('Your data has been exported to your desktop'))
        self.progbar.SetValue(0)

    def on_btn_cancel(self, _event):
        self.export_status[mg.CANCEL_EXPORT] = True

    def align_btns_to_exporting(self, exporting):
        self.btn_close.Enable(not exporting)
        self.btn_cancel.Enable(exporting)
        self.btn_export.Enable(not exporting)

    def on_btn_close(self, _event):
        self.Destroy()
