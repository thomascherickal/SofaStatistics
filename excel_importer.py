from __future__ import print_function
import wx

import dbe_plugins.dbe_sqlite as dbe_sqlite
import excel_reader
import getdata
import importer
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
        
    def get_params(self):
        """
        Get any user choices required.
        """
        retCode = wx.MessageBox(_("Does the spreadsheet have a header row?"), 
                                _("HEADER ROW?"), 
                                wx.YES_NO | wx.ICON_INFORMATION)
        self.has_header = (retCode == wx.YES)
        return True
    
    def assess_sample(self, wksheet, orig_fld_names, progbar, gauge_chunk, 
                      keep_importing):
        """
        Assess data sample to identify field types based on values in fields.
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
        for i, row in enumerate(wksheet): # iterates through data rows only
            if i % 50 == 0:
                wx.Yield()
                if keep_importing == set([False]):
                    progbar.SetValue(0)
                    raise ImportCancelException
            if debug: print(row)
            # if has_header, starts at 1st data row
            has_rows = True
            # process row
            sample_data.append(row)
            gauge_val = i*gauge_chunk
            progbar.SetValue(gauge_val)
            if i == (ROWS_TO_SAMPLE - 1):
                break
        fld_types = []
        for orig_fld_name in orig_fld_names:
            fld_type = importer.assess_sample_fld(sample_data, orig_fld_name)
            fld_types.append(fld_type)
        fld_types = dict(zip(orig_fld_names, fld_types))
        if not has_rows:
            raise Exception, "No data to import"
        return fld_types, sample_data
    
    def import_content(self, progbar, keep_importing):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        try:
            wkbook = excel_reader.Workbook(self.file_path, 
                                           sheets_have_hdrs=self.has_header)
            sheets = wkbook.get_sheet_names()
            if debug: print(sheets)
            wksheet = wkbook.get_sheet(name=sheets[0])
            n_rows = wksheet.get_data_rows_n()
            # get field names
            orig_fld_names = wksheet.get_fld_names()
            ok_fld_names = importer.process_fld_names(orig_fld_names)
            if debug: print(ok_fld_names)
        except IOError, e:
            raise Exception, (u"Unable to find file \"%s\" for importing." % 
                              self.file_path)
        except Exception, e:
            raise Exception, (u"Unable to read spreadsheet. "
                u"Orig error: %s" % e)
        con, cur, unused, unused, unused, unused, unused = \
            getdata.get_default_db_dets()
        sample_n = ROWS_TO_SAMPLE if ROWS_TO_SAMPLE <= n_rows else n_rows
        gauge_chunk = importer.get_gauge_chunk_size(n_rows, sample_n)
        if debug: 
            print("gauge_chunk: %s" % gauge_chunk)
            print("About to assess data sample")
        fld_types, sample_data = self.assess_sample(wksheet, orig_fld_names, 
                                        progbar, gauge_chunk, keep_importing)
        if debug:
            print("Just finished assessing data sample")
            print(fld_types)
            print(sample_data)
        # NB wksheet will NOT be at position ready to access records after 
        # sample.  Can't just pass in spreadsheet.
        remaining_data = [x for x in wksheet][sample_n:]
        nulled_dots = importer.add_to_tmp_tbl(con, cur, self.file_path, 
                            self.tbl_name, ok_fld_names, orig_fld_names, 
                            fld_types, sample_data, sample_n, remaining_data, 
                            progbar, gauge_chunk, keep_importing)
        importer.tmp_to_named_tbl(con, cur, self.tbl_name, self.file_path,
                                  progbar, nulled_dots)
        cur.close()
        con.commit()
        con.close()
        progbar.SetValue(0)