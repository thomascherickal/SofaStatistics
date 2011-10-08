from __future__ import print_function
import os
import wx

import my_globals as mg
import lib
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


class OdsImporter(importer.FileImporter):
    """
    Import ODS file (OpenOffice Calc, Gnumeric etc) into default SOFA SQLite 
        database.
    Needs to identify data types to ensure only consistent data in a field.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, parent, file_path, tbl_name):
        importer.FileImporter.__init__(self, parent, file_path, tbl_name)
        self.ext = u"ODS"
        
    def get_params(self):
        """
        Get any user choices required.
        """
        debug = False
        if not os.path.exists(self.file_path):
            raise Exception(u"Unable to find file \"%s\" for importing. "
                            u"Please check that file exists." % self.file_path)
        size = ods_reader.get_ods_xml_size(self.file_path)
        if size > mg.ODS_GETTING_LARGE:
            ret = wx.MessageBox(_("This spreadsheet may take a while to "
                    "import.\n\nInstead of importing, it could be faster to "
                    "save as csv and import the csv version." 
                    "\n\nImport now anyway?"), 
                    _("SLOW IMPORT"), wx.YES_NO|wx.ICON_INFORMATION)
            if ret == wx.NO:
                return False
            return importer.FileImporter.get_params(self) # check for header
        else:
            wx.BeginBusyCursor()
            tree = ods_reader.get_contents_xml_tree(self.file_path)
            tbl = ods_reader.get_tbl(tree)
            fldnames = ods_reader.get_fld_names(tbl, has_header=False, 
                                                rows_to_sample=ROWS_TO_SAMPLE)
            if not fldnames:
                raise Exception(_("Unable to extract or generate field names"))
            rows = ods_reader.get_rows(tbl, inc_empty=False)
            lib.safe_end_cursor()
            strdata = []
            for i, row in enumerate(rows):
                strrow = ods_reader.get_vals_from_row(row, len(fldnames))
                strdata.append(strrow)
                if i > 3:
                    break
            dlg = importer.HasHeaderGivenDataDlg(self.parent, self.ext, strdata)
            ret = dlg.ShowModal()
            if debug: print(unicode(ret))
            if ret == wx.ID_CANCEL:
                return False
            else:
                self.has_header = (ret == mg.HAS_HEADER)
                return True
    
    def import_content(self, progbar, import_status, lbl_feedback):
        """
        Get field types dict.  Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        faulty2missing_fld_list = []
        large = True
        wx.BeginBusyCursor()
        # Use up 2/3rds of the progress bar in initial step (parsing html and  
        # then extracting data from it) and 1/3rd adding to the SQLite database.
        prog_steps_for_xml_steps = importer.GAUGE_STEPS*(2.0/3.0)
        prog_step1 = prog_steps_for_xml_steps/5.0 # to encourage them ;-)
        prog_step2 = prog_steps_for_xml_steps/2.0
        tree = ods_reader.get_contents_xml_tree(self.file_path, lbl_feedback, 
                                                progbar, prog_step1, prog_step2)
        tbl = ods_reader.get_tbl(tree)
        fldnames = ods_reader.get_fld_names(tbl, self.has_header, 
                                            ROWS_TO_SAMPLE)
        if not fldnames:
            raise Exception(_("Unable to extract or generate field names"))
        # Will expect exactly the same number of fields as we have names for.
        # Have to process twice as much before it will add another step on bar.
        fld_types, rows = ods_reader.get_ods_dets(lbl_feedback, progbar, tbl,
                                        fldnames, faulty2missing_fld_list, 
                                        prog_steps_for_xml_steps, 
                                        next_prog_val=prog_step2, 
                                        has_header=self.has_header)
        if debug:
            if large:
                print("%s" % rows[:20])
            else:
                print("%s" % rows)
        default_dd = getdata.get_default_db_dets()
        rows_n = len(rows)
        items_n = rows_n*3 # pass through it all 3 times (parse, process, save)
        steps_per_item = importer.get_steps_per_item(items_n)
        gauge_start = prog_steps_for_xml_steps
        try:
            feedback = {mg.NULLED_DOTS: False}
            importer.add_to_tmp_tbl(feedback, import_status, default_dd.con, 
                default_dd.cur, self.file_path, self.tbl_name, self.has_header, 
                fldnames, fldnames, fld_types, faulty2missing_fld_list, rows, 
                progbar, steps_per_item, gauge_start)
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
        lib.safe_end_cursor()
