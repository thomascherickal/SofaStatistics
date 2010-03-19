from __future__ import print_function
import wx

import dbe_plugins.dbe_sqlite as dbe_sqlite
import ods_reader
import getdata
import importer
from my_exceptions import ImportCancelException

debug = False
if debug:
    ROWS_TO_SAMPLE = 2
else:
    ROWS_TO_SAMPLE = 500 # fast enough to sample quite a few


class FileImporter(object):
    """
    Import ODS file (OpenOffice Calc, Gnumeric etc) into default SOFA SQLite 
        database.
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
        size = ods_reader.get_ods_xml_size(self.file_path)
        if size > 1000000:
            size_lbl = "%s MB" % (round(size/(1024*1024.0),2),)
            retval = wx.MessageBox(_("This spreadsheet is large (%s).  "
                            "Instead of importing, it would be faster to save "
                            "as csv and import the csv version.\n\nImport now "
                            "anyway?" % size_lbl), 
                            _("SLOW IMPORT"), 
                            wx.YES_NO | wx.ICON_INFORMATION)
            if retval == wx.NO:
                return False
        retval = wx.MessageBox(_("Does the spreadsheet have a header row?"), 
                               _("HEADER ROW?"), 
                               wx.YES_NO | wx.ICON_INFORMATION)
        self.has_header = (retval == wx.YES)
        return True
    
    def import_content(self, progbar, keep_importing, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        large = False
        wx.BeginBusyCursor()
        # Use up 2/3rds of the progress bar in initial step (parsing html and  
        # then extracting data from it) and 1/3rd adding to the SQLite database.
        prog_steps_for_xml_steps = importer.GAUGE_STEPS*(2.0/3.0)
        prog_step1 = prog_steps_for_xml_steps/5.0 # to encourage them ;-)
        prog_step2 = prog_steps_for_xml_steps/2.0
        tree = ods_reader.get_contents_xml_tree(lbl_feedback, progbar, 
                                                prog_step1, prog_step2,
                                                self.file_path)
        tbl = ods_reader.get_tbl(tree)
        fldnames = ods_reader.get_fld_names(tbl, self.has_header, 
                                            ROWS_TO_SAMPLE)
        if not fldnames:
            raise Exception, _("Unable to extract or generate field names")
        # Will expect exactly the same number of fields as we have names for.
        # Have to process twice as much before it will add another step on bar.
        fld_types, rows = ods_reader.get_ods_dets(lbl_feedback, progbar, tbl,
                                            fldnames, prog_steps_for_xml_steps, 
                                            next_prog_val=prog_step2, 
                                            has_header=self.has_header)
        if debug and not large:
            print("%s" % rows)
        con, cur, unused, unused, unused, unused, unused = \
                                                getdata.get_default_db_dets()
        rows_n = len(rows)
        items_n = rows_n*3 # pass through it all 3 times (parse, process, save)
        steps_per_item = importer.get_steps_per_item(items_n)
        sample_data = {}
        sample_n = 0
        gauge_start = prog_steps_for_xml_steps
        try:
            nulled_dots = importer.add_to_tmp_tbl(con, cur, self.file_path, 
                                self.tbl_name, fldnames, fldnames, fld_types, 
                                sample_data, sample_n, rows, progbar, 
                                steps_per_item, gauge_start, keep_importing)
            importer.tmp_to_named_tbl(con, cur, self.tbl_name, self.file_path,
                                      progbar, nulled_dots)
        except Exception:
            wx.EndBusyCursor()
        cur.close()
        con.commit()
        con.close()
        progbar.SetValue(0)
        wx.EndBusyCursor()
