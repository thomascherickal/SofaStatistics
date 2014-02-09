#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
from collections import namedtuple
import csv
import cStringIO
import os

import wx

import my_globals as mg
import lib
import my_exceptions
import config_output
import getdata

GAUGE_STEPS = 100


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class DlgExportData(wx.Dialog):
    
    def __init__(self, n_rows):
        """
        temp_desktop_report_only -- exporting output to a temporary desktop 
        folder
        """
        dd = mg.DATADETS_OBJ
        title = u"Export %s to spreadsheet" % dd.tbl
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
            pos=(mg.HORIZ_OFFSET+200, 300), style=wx.MINIMIZE_BOX
            |wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU
            |wx.CAPTION|wx.CLIP_CHILDREN)
        szr = wx.BoxSizer(wx.VERTICAL)
        self.n_rows = n_rows
        self.export_status = {mg.CANCEL_EXPORT: False} # can change and running
            # script can check on it.
        self.chk_inc_lbls = wx.CheckBox(self, -1, 
            _("Include extra label columns (if available)"))
        szr.Add(self.chk_inc_lbls, 0, wx.ALL, 10)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        self.btn_cancel.Enable(False)
        self.btn_export = wx.Button(self, -1, u"Export")
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
        self.btn_export.Enable(True)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=0)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_export, 0, wx.ALIGN_RIGHT)
        self.progbar = wx.Gauge(self, -1, GAUGE_STEPS, size=(-1, 20),
            style=wx.GA_PROGRESSBAR)
        self.btn_close = wx.Button(self, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close)
        szr.Add(szr_btns, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr.Add(self.progbar, 0, wx.GROW|wx.ALIGN_RIGHT|wx.ALL, 10)
        szr.Add(self.btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(szr)
        szr.SetSizeHints(self)
        szr.Layout()

    def on_btn_export(self, event):
        """
        Follow style of Data List code where possible.
        """
        self.progbar.SetValue(0)
        wx.BeginBusyCursor()
        inc_lbls = self.chk_inc_lbls.IsChecked()
        debug = False
        dd = mg.DATADETS_OBJ
        cc = config_output.get_cc()
        filname_csv = u"%s.csv" % dd.tbl
        filname_xls = u"%s.xls" % dd.tbl
        desktop = os.path.join(mg.HOME_PATH, u"Desktop")
        filpath_csv = os.path.join(desktop, filname_csv)
        filpath_xls = os.path.join(desktop, filname_xls)
        if debug: 
            print(filpath_csv)
            print(filpath_xls)
        objqtr = getdata.get_obj_quoter_func(dd.dbe)
        col_names = getdata.fldsdic_to_fldnames_lst(fldsdic=dd.flds)
        (unused, unused, 
         unused, val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        # get alignment and val_dics (if showing lbl fields may be more than one set of col dets per col)
        col_dets = []
        col_det = namedtuple('col_det', 'alignright, valdic')
        for i, col_name in enumerate(col_names):
            numericfld = dd.flds[col_name][mg.FLD_BOLNUMERIC]
            col_dets.append([col_det(numericfld, None)]) # always raw first so no valdic
            has_lbls = val_dics.get(col_name)
            if inc_lbls and has_lbls:
                col_dets[i].append(col_det(False, val_dics.get(col_name))) # labels are always left aligned
        raw_list = []
        html = [u"""<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta name='I♥unicode'>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>%s</title>\n<body>""" % dd.tbl]
        # add header row
        html.append(u"<table>\n<thead>\n<tr>")
        colnames2use = []
        for idx_cols, col_name in enumerate(col_names):
            col_det_lst = col_dets[idx_cols]
            for idx_col_det in range(len(col_det_lst)): # should be at least 1 and at most 2
                if idx_col_det > 1:
                    raise Exception(u"Excessive column details received for %s"
                        % col_name)
                colname2use = (col_name if idx_col_det == 0 
                        else u"%s_Label" % col_name)
                colnames2use.append(colname2use)
        raw_list.append(colnames2use)
        html.append(u"".join([u"<th>%s</th>" % x for x in colnames2use]))
        html.append(u"</tr>\n</thead>")
        # get data from SQL line by line
        colnames_clause = u", ".join([objqtr(x) for x in col_names])
        SQL_get_data = u"""SELECT %s 
        FROM %s""" % (colnames_clause, getdata.tblname_qtr(dd.dbe, dd.tbl))
        if debug: print(SQL_get_data)
        dd.cur.execute(SQL_get_data) # must be dd.cur
        html.append(u"<tbody>\n")
        idx_row = 0
        while True:
            try:
                row = dd.cur.fetchone()
                if row is None:
                    break # run out of rows
                row_raw = []
                row_html = [u"<tr>\n"]
                for i, col_name in enumerate(col_names):
                    col_det_lst = col_dets[i]
                    for det in col_det_lst:
                        alignright = (u" style='text-align: right'" 
                            if det.alignright else u"")
                        val2show = (det.valdic.get(row[i], row[i]) if det.valdic 
                            else row[i])
                        row_raw.append(unicode(val2show)) # must be a string
                        row_html.append(u"<td %s>%s</td>" % (alignright, 
                            val2show))
                row_html.append(u"</tr>\n")
                raw_list.append(row_raw)
                html.append(u"".join(row_html))
                idx_row += 1
                gauge2set = ((1.0*idx_row)/self.n_rows)*GAUGE_STEPS
                self.progbar.SetValue(gauge2set)
            except my_exceptions.ExportCancel:
                wx.MessageBox(u"Export Cancelled")
            except Exception, e:
                msg = (u"Problem exporting output. Orig error: %s" % lib.ue(e))
                if debug: print(msg)
                wx.MessageBox(msg)
                self.progbar.SetValue(0)
                lib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                return
        html.append(u"</tbody>\n</table></body></html>")
        with open(filpath_csv, 'wb') as f_csv: # no special encoding needed given what writer does, must be in binary mode otherwise extra line breaks on Windows 
            csv_writer = UnicodeWriter(f_csv, delimiter=',', quotechar='"', 
                quoting=csv.QUOTE_MINIMAL)
            for i, row in enumerate(raw_list, 1):
                try:
                    csv_writer.writerow(row)
                except Exception, e:
                    raise Exception(u"Unable to write row %s to csv file. "
                        u"Orig error: %s" % (i, e))
            f_csv.close()
        html2save = u"\n".join(html)
        with codecs.open(filpath_xls, "w", "utf-8") as f_xls:
            f_xls.write(html2save)
            f_xls.close()
        self.progbar.SetValue(GAUGE_STEPS)
        lib.safe_end_cursor()
        self.align_btns_to_exporting(exporting=False)
        wx.MessageBox(_(u"Your data has been exported to your desktop"))
        self.progbar.SetValue(0)

    def on_btn_cancel(self, event):
        self.export_status[mg.CANCEL_EXPORT] = True

    def align_btns_to_exporting(self, exporting):
        self.btn_close.Enable(not exporting)
        self.btn_cancel.Enable(exporting)
        self.btn_export.Enable(not exporting)
    
    def on_btn_close(self, event):
        self.Destroy()
    