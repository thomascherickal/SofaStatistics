
import datetime
import wx
import xlrd

from sofastats import basic_lib as b  #@UnresolvedImport
from sofastats import my_globals as mg  #@UnresolvedImport
from sofastats import my_exceptions  #@UnresolvedImport
from sofastats import lib  #@UnresolvedImport
from sofastats import getdata  #@UnresolvedImport
from sofastats import importer  #@UnresolvedImport

ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few


class ExcelImporter(importer.FileImporter):
    """
    Import excel file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, parent, file_path, tblname, headless, 
            headless_has_header, force_quickcheck=False):
        importer.FileImporter.__init__(self, parent, file_path, tblname,
            headless, headless_has_header)
        self.ext = u"XLS/XLSX"
        self.force_quickcheck = force_quickcheck
    
    def has_header_row(self, row1_types, row2_types):
        """
        Will return True if nothing but strings or in first row and anything in 
        other rows that is not e.g. a number or a date. Empty is OK.
        XL_CELL_BLANK = 6
        XL_CELL_BOOLEAN = 4
        XL_CELL_DATE = 3
        XL_CELL_EMPTY = 0
        XL_CELL_ERROR = 5
        XL_CELL_NUMBER = 2
        XL_CELL_TEXT = 1
        """
        debug = False
        if debug: print(row1_types, row2_types)
        str_type = xlrd.XL_CELL_TEXT
        empty_type = xlrd.XL_CELL_EMPTY
        non_str_types = [xlrd.XL_CELL_BOOLEAN, xlrd.XL_CELL_DATE, 
            xlrd.XL_CELL_NUMBER] # ignore EMPTY and ERROR
        return importer.has_header_row(row1_types, row2_types, str_type, 
            empty_type, non_str_types)
    
    def get_params(self):
        """
        Display each cell based on cell characteristics only - no attempt to 
        collapse down to one data type e.g. dates only or numbers only.
        """
        debug = False
        if self.headless:
            self.has_header = self.headless_has_header
            return True
        else:
            wkbook = xlrd.open_workbook(self.file_path) # , encoding_override="cp1252"
            wksheet = wkbook.sheet_by_index(0)
            strdata = []
            for rowx in range(wksheet.nrows):
                rowtypes = wksheet.row_types(rowx)
                if rowx == 0:
                    row1_types = rowtypes
                elif rowx == 1:
                    row2_types = rowtypes
                newrow = []
                for colx in range(wksheet.ncols):
                    rawval = wksheet.cell_value(rowx, colx)
                    try:
                        rawval = rawval.strip()
                    except AttributeError:
                        pass
                    val2show = self.getval2use(wkbook, rowtypes[colx], rawval)
                    newrow.append(val2show)
                strdata.append(newrow)
                if (rowx+1) >= importer.ROWS_TO_SHOW_USER:
                    break
            try:
                prob_has_hdr = self.has_header_row(row1_types, row2_types)
            except Exception:
                prob_has_hdr = False
            dlg = importer.DlgHasHeaderGivenData(self.parent, self.ext, strdata,
                prob_has_hdr)
            ret = dlg.ShowModal()
            if debug: print(str(ret))
            if ret == wx.ID_CANCEL:
                return False
            else:
                self.has_header = (ret == mg.HAS_HEADER)
            return True
    
    def get_ok_fldnames(self, wksheet):
        if self.has_header:
            # use values of first row
            orig_fldnames = []
            for col_idx in range(wksheet.ncols):
                raw_fldname = wksheet.cell_value(rowx=0, colx=col_idx)
                fldname = (raw_fldname if isinstance(raw_fldname, str) 
                    else str(raw_fldname))
                orig_fldnames.append(fldname)
            fldnames = importer.process_fldnames(orig_fldnames, 
                headless=self.headless, force_quickcheck=self.force_quickcheck)
        else:
            # numbered is OK
            fldnames = [mg.NEXT_FLDNAME_TEMPLATE % (x+1,) for x 
                in range(wksheet.ncols)]
        return fldnames
    
    def getval2use(self, wkbook, coltype, rawval):
        if coltype == xlrd.XL_CELL_DATE:
            try:
                datetup = xlrd.xldate_as_tuple(rawval, wkbook.datemode)
                # Handle times (NB if they are trying to record duration, they 
                # should use an integer e.g. seconds
                if datetup[0] == 0:
                    cellval = datetime.time(datetup[3], datetup[4], datetup[5])
                else:
                    cellval = datetime.datetime(*datetup).isoformat(" ")
            except Exception:
                raise Exception(u"Invalid date - unable to import.")
        else:
            cellval = rawval
        val2use = (cellval if isinstance(cellval, str) 
            else str(cellval))
        return val2use
            
    def get_rowdict(self, rowx, wkbook, wksheet, fldnames):
        rowvals = []
        rowtypes = wksheet.row_types(rowx)
        rawrowvals = wksheet.row_values(rowx) # more efficient to grab once
        for colx in range(wksheet.ncols):
            rawval = rawrowvals[colx]
            try:
                rawval = rawval.strip()
            except AttributeError:
                pass
            try:
                val2use = self.getval2use(wkbook, rowtypes[colx], rawval)
            except Exception as e:
                raise Exception(u"Problem with value in field \"%s\", row %s. "
                    u"Orig error: %s" % (fldnames[colx], rowx+1, b.ue(e)))
            rowvals.append(val2use)
        rowdict = dict(zip(fldnames, rowvals))
        return rowdict
    
    def assess_sample(self, wkbook, wksheet, ok_fldnames, progbar, 
                      steps_per_item, import_status, faulty2missing_fld_list):
        """
        Assess data sample to identify field types based on values in fields.
        
        Doesn't really use built-in xlrd functionality for getting type data.
        
        Uses it indirectly to get values e.g. dates in correct form.
        
        Decided to stay with existing approach. 
        
        If a field has mixed data types will define as string.
        
        Returns fldtypes, sample_data.
        
        fldtypes - dict with ok field names as keys and field types as 
        values.
        
        sample_data - list of dicts containing the first rows of data 
        (no point reading them all again during subsequent steps).   
        
        Sample first N rows (at most) to establish field types.   
        """
        debug = False
        has_rows = False
        sample_data = []
        #ok_fldnames = self.get_ok_fldnames(wksheet)
        row_idx = 1 if self.has_header else 0
        while row_idx < wksheet.nrows: # iterates through data rows only
            if row_idx % 50 == 0:
                if not self.headless:
                    wx.Yield()
                if import_status[mg.CANCEL_IMPORT]:
                    progbar.SetValue(0)
                    raise my_exceptions.ImportCancel
            if debug: print(wksheet.row(row_idx))
            # if has_header, starts at 1st data row
            has_rows = True
            rowdict = self.get_rowdict(row_idx, wkbook, wksheet, ok_fldnames)
            sample_data.append(rowdict)
            gauge_val = min(row_idx*steps_per_item, mg.IMPORT_GAUGE_STEPS)
            progbar.SetValue(gauge_val)
            if not self.headless:
                if row_idx == (ROWS_TO_SAMPLE - 1):
                    break
            row_idx += 1
        fldtypes = []
        for ok_fldname in ok_fldnames:
            fldtype = importer.assess_sample_fld(sample_data, self.has_header, 
                ok_fldname, ok_fldnames, faulty2missing_fld_list,
                headless=self.headless)
            fldtypes.append(fldtype)            
        fldtypes = dict(zip(ok_fldnames, fldtypes))
        if not has_rows:
            raise Exception(u"No data to import")
        return fldtypes, sample_data

    def import_content(self,
            lbl_feedback=None, import_status=None, progbar=None):
        """
        Get field types dict.  Use it to test each and every item before they 
        are added to database (after adding the records already tested).
        
        Add to disposable table first and if completely successful, rename
        table to final name.
        """
        debug = False
        if lbl_feedback is None: lbl_feedback = importer.DummyLabel()
        if import_status is None:
            import_status = importer.dummy_import_status.copy()
        if progbar is None: progbar = importer.DummyProgBar()
        faulty2missing_fld_list = []
        if not self.headless:
            wx.BeginBusyCursor()
        try:
            wkbook = xlrd.open_workbook(self.file_path,)
            wksheet = wkbook.sheet_by_index(0)
            n_datarows = wksheet.nrows -1 if self.has_header else wksheet.nrows
            # get field names
            ok_fldnames = self.get_ok_fldnames(wksheet)
            if debug: print(ok_fldnames)
        except OSError as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception(u"Unable to find file \"%s\" for importing."
                % self.file_path)
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            raise Exception(u"Unable to read spreadsheet."
                u"\nCaused by error: %s" % b.ue(e))
        default_dd = getdata.get_default_db_dets()
        if self.headless:
            global ROWS_TO_SAMPLE
            ROWS_TO_SAMPLE = n_datarows
        sample_n = min(ROWS_TO_SAMPLE, n_datarows)
        items_n = n_datarows + sample_n
        steps_per_item = importer.get_steps_per_item(items_n)
        if debug: 
            print("steps_per_item: %s" % steps_per_item)
            print("About to assess data sample")
        (fldtypes, 
         sample_data) = self.assess_sample(wkbook, wksheet, ok_fldnames, 
            progbar, steps_per_item, import_status, faulty2missing_fld_list)
        if debug:
            print("Just finished assessing data sample")
            print(fldtypes)
            print(sample_data)
        data = []
        row_idx = 1 if self.has_header else 0
        while row_idx < wksheet.nrows: # iterates through data rows only
            data.append(self.get_rowdict(row_idx, wkbook, wksheet, 
                ok_fldnames))
            row_idx += 1
        gauge_start = steps_per_item*sample_n
        try:
            feedback = {mg.NULLED_DOTS: False}
            importer.add_to_tmp_tbl(
                feedback, import_status,
                default_dd.con, default_dd.cur,
                self.tblname, self.has_header, ok_fldnames, fldtypes,
                faulty2missing_fld_list, data,
                progbar, n_datarows, steps_per_item, gauge_start,
                headless=self.headless)
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                self.tblname, progbar, feedback[mg.NULLED_DOTS], self.headless)
        except Exception as e:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        