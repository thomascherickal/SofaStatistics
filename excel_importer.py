from __future__ import print_function

from datetime import datetime
import wx

import my_globals as mg
from my_exceptions import ImportCancelException
import lib
import getdata
import importer
import xlrd

ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few


class ExcelImporter(importer.FileImporter):
    """
    Import excel file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, parent, file_path, tblname):
        importer.FileImporter.__init__(self, parent, file_path, tblname)
        self.ext = u"XLS"
    
    def get_params(self):
        """
        Display each cell based on cell characteristics only - no attempt to 
            collapse down to one data type e.g. dates only or numbers only.
        """
        debug = False
        wkbook = xlrd.open_workbook(self.file_path)
        wksheet = wkbook.sheet_by_index(0)
        strdata = []
        for rowx in range(wksheet.nrows):
            rowtypes = wksheet.row_types(rowx)
            newrow = []
            for colx in range(wksheet.ncols):
                rawval = wksheet.cell_value(rowx, colx)
                val2show = self.getval2use(wkbook, rowtypes[colx], rawval)
                newrow.append(val2show)
            strdata.append(newrow)
            if rowx > 2:
                break
        dlg = importer.HasHeaderGivenDataDlg(self.parent, self.ext, strdata)
        ret = dlg.ShowModal()
        if debug: print(unicode(ret))
        if ret == wx.ID_CANCEL:
            return False
        else:
            self.has_header = (ret == mg.HAS_HEADER)
        return True
    
    def get_fldnames(self, wksheet):
        if self.has_header:
            # use values of first row
            fldnames = []
            for col_idx in range(wksheet.ncols):
                raw_fldname = wksheet.cell_value(rowx=0, colx=col_idx)
                fldname = (raw_fldname if isinstance(raw_fldname, basestring) 
                                       else unicode(raw_fldname))
                fldnames.append(fldname)
        else:
            # numbered is OK
            fldnames = [mg.NEXT_FLDNAME_TEMPLATE % (x+1,) for x 
                        in range(wksheet.ncols)]
        return fldnames
    
    def getval2use(self, wkbook, coltype, rawval):
        if coltype == xlrd.XL_CELL_DATE:
            datetup = xlrd.xldate_as_tuple(rawval, wkbook.datemode)
            cellval = datetime(*datetup).isoformat(" ")
        else:
            cellval = rawval
        val2use = (cellval if isinstance(cellval, basestring) 
                           else unicode(cellval))
        return val2use
            
    def get_rowdict(self, rowx, wkbook, wksheet, fldnames):
        rowvals = []
        rowtypes = wksheet.row_types(rowx)
        rawrowvals = wksheet.row_values(rowx) # more efficient to grab once
        for colx in range(wksheet.ncols):
            rawval = rawrowvals[colx]
            val2use = self.getval2use(wkbook, rowtypes[colx], rawval)
            rowvals.append(val2use)
        rowdict = dict(zip(fldnames, rowvals))
        return rowdict
    
    def assess_sample(self, wkbook, wksheet, orig_fld_names, progbar, 
                      steps_per_item, import_status, faulty2missing_fld_list):
        """
        Assess data sample to identify field types based on values in fields.
        Doesn't really use built-in xlrd functionality for getting type data.
        Uses it indirectly to get values e.g. dates in correct form.
        Decided to stay with existing approach. 
        If a field has mixed data types will define as string.
        Returns fld_types, sample_data.
        fld_types - dict with original field names as keys and field types as 
            values.
        sample_data - list of dicts containing the first rows of data 
            (no point reading them all again during subsequent steps).   
        Sample first N rows (at most) to establish field types.   
        """
        debug = False
        has_rows = False
        sample_data = []
        fldnames = self.get_fldnames(wksheet)
        row_idx = 1 if self.has_header else 0
        while row_idx < wksheet.nrows: # iterates through data rows only
            if row_idx % 50 == 0:
                wx.Yield()
                if import_status[mg.CANCEL_IMPORT]:
                    progbar.SetValue(0)
                    raise ImportCancelException
            if debug: print(wksheet.row(row_idx))
            # if has_header, starts at 1st data row
            has_rows = True
            rowdict = self.get_rowdict(row_idx, wkbook, wksheet, fldnames)
            sample_data.append(rowdict)
            gauge_val = row_idx*steps_per_item
            progbar.SetValue(gauge_val)
            if row_idx == (ROWS_TO_SAMPLE - 1):
                break
            row_idx += 1
        fld_types = []
        for orig_fld_name in orig_fld_names:
            fld_type = importer.assess_sample_fld(sample_data, self.has_header, 
                                                  orig_fld_name, orig_fld_names,
                                                  faulty2missing_fld_list)
            fld_types.append(fld_type)            
        fld_types = dict(zip(orig_fld_names, fld_types))
        if not has_rows:
            raise Exception(u"No data to import")
        return fld_types, sample_data 
    
    def import_content(self, progbar, import_status, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        faulty2missing_fld_list = []
        wx.BeginBusyCursor()
        try:
            wkbook = xlrd.open_workbook(self.file_path,)
            wksheet = wkbook.sheet_by_index(0)
            n_datarows = wksheet.nrows -1 if self.has_header else wksheet.nrows
            # get field names
            orig_fld_names = self.get_fldnames(wksheet)
            ok_fld_names = importer.process_fld_names(orig_fld_names)
            if debug: print(ok_fld_names)
        except IOError, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to find file \"%s\" for importing."
                            % self.file_path)
        except Exception, e:
            lib.safe_end_cursor()
            raise Exception(u"Unable to read spreadsheet."
                            u"\nCaused by error: %s" % lib.ue(e))
        default_dd = getdata.get_default_db_dets()
        sample_n = (ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= n_datarows 
                                   else n_datarows)
        items_n = n_datarows + sample_n
        steps_per_item = importer.get_steps_per_item(items_n)
        if debug: 
            print("steps_per_item: %s" % steps_per_item)
            print("About to assess data sample")
        fld_types, sample_data = self.assess_sample(wkbook, wksheet, 
                                        orig_fld_names, progbar, steps_per_item, 
                                        import_status, faulty2missing_fld_list)
        if debug:
            print("Just finished assessing data sample")
            print(fld_types)
            print(sample_data)
        data = []
        row_idx = 1 if self.has_header else 0
        while row_idx < wksheet.nrows: # iterates through data rows only
            data.append(self.get_rowdict(row_idx, wkbook, wksheet, 
                                         orig_fld_names))
            row_idx += 1
        gauge_start = steps_per_item*sample_n
        try:
            feedback = {mg.NULLED_DOTS: False}
            importer.add_to_tmp_tbl(feedback, import_status, default_dd.con, 
                default_dd.cur, self.file_path, self.tbl_name, self.has_header, 
                ok_fld_names, orig_fld_names, fld_types, 
                faulty2missing_fld_list, data, progbar, steps_per_item, 
                gauge_start)
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                                      self.tbl_name, self.file_path,
                                      progbar, feedback[mg.NULLED_DOTS])
        except Exception, e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        