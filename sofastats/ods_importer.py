from __future__ import print_function
import os
import wx

from sofastats import my_globals as mg
from sofastats import lib
from sofastats import ods_reader
from sofastats import getdata
from sofastats import importer

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
            headless_has_header, force_quickcheck=False):
        importer.FileImporter.__init__(self, parent, file_path, tblname,
            headless, headless_has_header)
        self.ext = u"ODS"
        self.force_quickcheck = force_quickcheck

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
        row1_types = [lib.get_val_type(val, comma_dec_sep_ok) 
            for val in strdata[0]]
        row2_types = [lib.get_val_type(val, comma_dec_sep_ok) 
            for val in strdata[1]]
        str_type = mg.VAL_STRING
        empty_type = mg.VAL_EMPTY_STRING
        non_str_types = [mg.VAL_DATE, mg.VAL_NUMERIC]
        return importer.has_header_row(row1_types, row2_types, str_type, 
            empty_type, non_str_types)
        
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
                # much less efficient if no header supplied
                ok_fldnames = ods_reader.get_ok_fldnames(tbl, has_header=False, 
                    rows_to_sample=ROWS_TO_SAMPLE, headless=self.headless,
                    force_quickcheck=self.force_quickcheck)
                if not ok_fldnames:
                    raise Exception(_("Unable to extract or generate field "
                        "names"))
                rows = ods_reader.get_rows(tbl, inc_empty=False, 
                    n=importer.ROWS_TO_SHOW_USER)
                lib.GuiLib.safe_end_cursor()
                strdata = []
                for i, row in enumerate(rows, 1):
                    strrow = ods_reader.get_vals_from_row(row, len(ok_fldnames))
                    if debug: print(strrow)
                    strdata.append(strrow)
                    if i >= importer.ROWS_TO_SHOW_USER:
                        break
                try:
                    prob_has_hdr = self.has_header_row(strdata)
                except Exception:
                    prob_has_hdr = False
                dlg = importer.DlgHasHeaderGivenData(self.parent, self.ext, 
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
        prog_steps_for_xml_steps = mg.IMPORT_GAUGE_STEPS*(2.0/3.0)
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
            ok_fldnames, faulty2missing_fld_list, prog_steps_for_xml_steps, 
            next_prog_val=prog_step2, has_header=self.has_header,
            headless=self.headless)
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
                progbar, steps_per_item, gauge_start, headless=self.headless)
            importer.tmp_to_named_tbl(default_dd.con, default_dd.cur, 
                self.tblname, self.file_path, progbar, feedback[mg.NULLED_DOTS],
                self.headless)
        except Exception:
            importer.post_fail_tidy(progbar, default_dd.con, default_dd.cur)
            raise
        default_dd.cur.close()
        default_dd.con.commit()
        default_dd.con.close()
        progbar.SetValue(0)
        lib.GuiLib.safe_end_cursor()
