from __future__ import print_function
import wx

import dbe_plugins.dbe_sqlite as dbe_sqlite
import excel_reader
import getdata
import importer
import util
from my_exceptions import ImportCancelException

ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few


class FileImporter(object):
    """
    Import excel file into default SOFA SQLite database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, file_path, tbl_name):                    
        self.file_path = file_path
        self.tbl_name = tbl_name
        self.has_header = True
        
    def GetParams(self):
        """
        Get any user choices required.
        """
        retCode = wx.MessageBox(_("Does the spreadsheet have a header row?"), 
							    _("HEADER ROW?"), 
							    wx.YES_NO | wx.ICON_INFORMATION)
        self.has_header = (retCode == wx.YES)
        return True
    
    def AssessDataSample(self, wksheet, fld_names, progBackup, gauge_chunk, 
                         keep_importing):
        """
        Assess data sample to identify field types based on values in fields.
        If a field has mixed data types will define as string.
        Returns fld_types, sample_data.
        fld_types - dict with field names as keys and field types as values.
        sample_data - list of dicts containing the first rows of data 
            (no point reading them all again during subsequent steps).   
        Sample first N rows (at most) to establish field types.   
        """
        debug = False
        bolhas_rows = False
        sample_data = []
        for i, row in enumerate(wksheet):
            if i % 50 == 0:
                wx.Yield()
                if keep_importing == set([False]):
                    progBackup.SetValue(0)
                    raise ImportCancelException
            if debug: print(row)
            # if has_header, starts at 1st data row
            bolhas_rows = True
            # process row
            sample_data.append(row)
            gauge_val = i*gauge_chunk
            progBackup.SetValue(gauge_val)
            if i == (ROWS_TO_SAMPLE - 1):
                break
        fld_types = []
        for fld_name in fld_names:
            fld_type = importer.assess_sample_fld(sample_data, fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(fld_names, fld_types))
        if not bolhas_rows:
            raise Exception, "No data to import"
        return fld_types, sample_data
    
    def ImportContent(self, progBackup, keep_importing):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        try:
            wkbook = excel_reader.Workbook(self.file_path)
            sheets = wkbook.GetSheets()
            if debug: print(sheets)
            wksheet = wkbook.GetSheet(name=sheets[0], 
                                      has_header=self.has_header)
            n_rows = wksheet.GetRowsN()
            # get field names
            fld_names = wksheet.GetFldNames()
            if debug: print(fld_names)
            if self.has_header:
                for row in wksheet: # prepare sheet to start after first row
                    break
        except Exception, e:
            raise Exception, "Unable to read spreadsheet. " + \
                "Orig error: %s" % e
        conn, cur, unused, unused, unused, unused, unused = \
            getdata.GetDefaultDbDets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= n_rows else n_rows
        gauge_chunk = importer.getGaugeChunkSize(n_rows, sample_n)
        if debug: 
            print("gauge_chunk: %s" % gauge_chunk)
            print("About to assess data sample")
        fld_types, sample_data = self.AssessDataSample(wksheet, fld_names,
                                        progBackup, gauge_chunk, keep_importing)
        if debug:
            print("Just finished assessing data sample")
            print(fld_types)
            print(sample_data)
        # NB wksheet will be at position ready to access records after sample
        remaining_data = wksheet
        importer.AddToTmpTable(conn, cur, self.file_path, self.tbl_name, 
                               fld_names, fld_types, sample_data, sample_n,
                               remaining_data, progBackup,
                               gauge_chunk, keep_importing)
        importer.TmpToNamedTbl(conn, cur, self.tbl_name, self.file_path,
                               progBackup)
        cur.close()
        conn.commit()
        conn.close()
        progBackup.SetValue(0)