#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
export2spreadsheet() can be scripted outside the GUI. Set headless = True when
calling.
"""
import codecs
import os

import my_globals as mg
import export_output
import output
    
def export2spreadsheet(hdr, tbl_items, save2report_path, report_path, 
        alternative_path, gauge_start_tbls=0, headless=False, 
        steps_per_tbl=None, msgs=None, progbar=None):
    if headless:
        if (steps_per_tbl, msgs, progbar) != (None, None, None):
            raise Exception(u"If running headless, don't set the GUI-specific "
                u"settings")
        steps_per_tbl = 1 # leave msgs as default of None
        progbar = export_output.Prog2console()
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception(u"Report contents cannot be exported. "
                u"No report file \"%s\"to export." % report_path)
        spreadsheet_root, rpt_name = os.path.split(report_path)
        spreadsheet_name = u"%s.xls" % os.path.splitext(rpt_name)[0]
        progbar = progbar if progbar else export_output.Prog2console()
        if mg.OVERRIDE_FOLDER:
            spreadsheet_root = mg.OVERRIDE_FOLDER
        spreadsheet_path = os.path.join(spreadsheet_root, spreadsheet_name)
    else:
        spreadsheet_path = os.path.join(alternative_path, u"SOFA output.xls")
    n_tbls = len(tbl_items)
    html = [hdr,] + [output.extract_tbl_only(tbl_item.content) for tbl_item 
        in tbl_items]
    html2save = u"\n".join(html)
    with codecs.open(spreadsheet_path, "w", "utf-8") as f_xls:
        f_xls.write(html2save)
        f_xls.close()
    if save2report_path:
        spreadsheet_saved_msg = (_(u"The spreadsheet has been saved"
            u" to: \"%s\"") % spreadsheet_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        spreadsheet_saved_msg = (u"The spreadsheet has been saved "
            u"to your desktop in the \"%s\" folder" % foldername)
    msgs.append(spreadsheet_saved_msg)
    gauge2show = min(gauge_start_tbls + (steps_per_tbl*n_tbls),
        mg.EXPORT_IMG_GAUGE_STEPS)
    progbar.SetValue(gauge2show)
