from __future__ import print_function
import os
import wx

import my_globals as mg
import lib
import ods_reader
import getdata
import importer

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
    
    def __init__(self, parent, file_path, tblname, headless, 
                 headless_has_header):
        importer.FileImporter.__init__(self, parent, file_path, tblname,
                                       headless, headless_has_header)
        self.ext = u"ODS"

    def has_header_row(self, strdata):
        """
        Will return True if nothing but strings in first row and anything in 
            other rows that is not e.g. a number or a date. Empty is OK.
        """
        debug = False
        comma_dec_sep_ok = True
        if debug: print(strdata)
        if len(strdata) < 2: # a header row needs a following row to be a header
            return False
        first_row = strdata[0]
        for val in first_row: # must all be non-empty strings to be a header
            val_type = lib.get_val_type(val, comma_dec_sep_ok)
            if val_type != mg.VAL_STRING: # empty strings no good as heading values
                return False
        for row in strdata[1:]: # Only strings in potential header. Must look 
                # for any non-strings to be sure.
            for val in row:
                val_type = lib.get_val_type(val, comma_dec_sep_ok)
                if val_type in [mg.VAL_DATE, mg.VAL_NUMERIC]:
                    return True
        return False
    
    def get_params(self):
        """
        Get any user choices required.
        """
        debug = False
        if self.headless:
            self.has_header = self.headless_has_header
            return True
        else:
            if not os.path.exists(self.file_path):
                raise Exception(u"Unable to find file \"%s\" for importing. "
                                u"Please check that file exists." % 
                                self.file_path)
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
                ok_fldnames = ods_reader.get_ok_fldnames(tbl, has_header=False, 
                                                rows_to_sample=ROWS_TO_SAMPLE, 
                                                headless=self.headless)
                if not ok_fldnames:
                    raise Exception(_("Unable to extract or generate field "
                                      "names"))
                rows = ods_reader.get_rows(tbl, inc_empty=False)
                lib.safe_end_cursor()
                strdata = []
                for i, row in enumerate(rows):
                    strrow = ods_reader.get_vals_from_row(row, len(ok_fldnames))
                    strdata.append(strrow)
                    if i > 3:
                        break
                try:
                    prob_has_hdr = self.has_header_row(strdata)
                except Exception:
                    prob_has_hdr = False
                dlg = importer.HasHeaderGivenDataDlg(self.parent, self.ext, 
                                                     strdata, prob_has_hdr)
                ret = dlg.ShowModal()
                if debug: print(unicode(ret))
                if ret == wx.ID_CANCEL:
                    return False
                else:
                    self.has_header = (ret == mg.HAS_HEADER)
                    return True
    
    def import_content(self, progbar, import_status, lbl_feedback):
        """
        Get field types dict. Use it to test each and every item before they 
            are added to database (after adding the records already tested).
        Add to disposable table first and if completely successful, rename
            table to final name.
        """
        debug = False
        faulty2missing_fld_list = []
        large = True
        if not self.headless:
            wx.BeginBusyCursor()
        # Use up 2/3rds of the progress bar in initial step (parsing html and  
        # then extracting data from it) and 1/3rd adding to the SQLite database.
        prog_steps_for_xml_steps = importer.GAUGE_STEPS*(2.0/3.0)
        prog_step1 = prog_steps_for_xml_steps/5.0 # to encourage them ;-)
        prog_step2 = prog_steps_for_xml_steps/2.0
        tree = ods_reader.get_contents_xml_tree(self.file_path, lbl_feedback, 
                                                progbar, prog_step1, prog_step2)
        tbl = ods_reader.get_tbl(tree)
        ok_fldnames = ods_reader.get_ok_fldnames(tbl, self.has_header, 
                                                 ROWS_TO_SAMPLE, self.headless)
        if not ok_fldnames:
            raise Exception(_("Unable to extract or generate field names"))
        # Will expect exactly the same number of fields as we have names for.
        # Have to process twice as much before it will add another step on bar.
        fldtypes, rows = ods_reader.get_ods_dets(lbl_feedback, progbar, tbl,
                                        ok_fldnames, faulty2missing_fld_list, 
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
                default_dd.cur, self.file_path, self.tblname, self.has_header, 
                ok_fldnames, fldtypes, faulty2missing_fld_list, rows, 
                progbar, steps_per_item, gauge_start)
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                                      self.tblname, self.file_path,
                                      progbar, feedback[mg.NULLED_DOTS],
                                      self.headless)
        except Exception:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        lib.safe_end_cursor()
