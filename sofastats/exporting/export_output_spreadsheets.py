"""
export2spreadsheet() can be scripted outside the GUI. Set headless = True when
calling.
"""
import os

from .. import my_globals as mg
from . import export_output
from .. import output

def export2spreadsheet(hdr, tbl_items,
        report_path, alternative_path,
        gauge_start_tbls=0, steps_per_tbl=None, msgs=None, progbar=None, *,
        save2report_path=True, headless=False):
    if headless:
        if (steps_per_tbl, msgs, progbar) != (None, None, None):
            raise Exception(
                "If running headless, don't set the GUI-specific settings")
        steps_per_tbl = 1  ## leave msgs as default of None
        progbar = export_output.Prog2console()
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception('Report contents cannot be exported. '
                f'No report file "{report_path}"to export.')
        spreadsheet_root, rpt_name = os.path.split(report_path)
        xls_name = os.path.splitext(rpt_name)[0]
        spreadsheet_name = f'{xls_name}.xls'
        progbar = progbar if progbar else export_output.Prog2console()
        if mg.OVERRIDE_FOLDER:
            spreadsheet_root = mg.OVERRIDE_FOLDER
        spreadsheet_path = spreadsheet_root / spreadsheet_name
    else:
        spreadsheet_path = alternative_path / 'SOFA output.xls'
    n_tbls = len(tbl_items)
    html = [hdr,] + [output.extract_tbl_only(tbl_item.content)
        for tbl_item in tbl_items]
    html2save = '\n'.join(html)
    with open(spreadsheet_path, 'w', encoding='utf-8') as f_xls:
        f_xls.write(html2save)
        f_xls.close()
    if save2report_path:
        spreadsheet_saved_msg = (_('The spreadsheet has been saved'
            " to: \"%s\"") % spreadsheet_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        spreadsheet_saved_msg = ('The spreadsheet has been saved '
            "to your desktop in the \"%s\" folder" % foldername)
    msgs.append(spreadsheet_saved_msg)
    gauge2show = min(
        gauge_start_tbls + (steps_per_tbl*n_tbls),
        mg.EXPORT_IMG_GAUGE_STEPS)
    progbar.SetValue(gauge2show)
