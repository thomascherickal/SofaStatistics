"""
export2pdf() does the real work and can be scripted outside the GUI. Set
headless = True when calling.
"""
import os
import shutil
import sys

import PyPDF2 as pypdf

from .. import basic_lib as b  #@UnresolvedImport
from .. import my_globals as mg  #@UnresolvedImport
from . import export_output  #@UnresolvedImport

RAWPDF_FILE = 'raw.pdf'
RAWPDF_PATH = mg.INT_PATH / RAWPDF_FILE
PDF_SIDE_MM = '420'  ## any larger and they won't be able to display anywhere in one go anyway

def pdf_tasks(report_path, alternative_path,
        gauge_start_pdf, steps_per_pdf, msgs, progbar, *,
        save2report_path, headless):
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception('Report contents cannot be exported. '
                f'No report file "{report_path}" to export.')
        rpt_root, rpt_name = os.path.split(report_path)
        pdf_root = os.path.splitext(rpt_name)[0]
        pdf_name = f'{pdf_root}.pdf'
        pdf_path = export2pdf(rpt_root, pdf_name, report_path,
            gauge_start_pdf, steps_per_pdf, progbar, headless=headless)
        pdf_saved_msg = (_('PDF has been saved to: \"%s\"') % pdf_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        pdf_path = export2pdf(alternative_path, 'SOFA output.pdf',
            report_path, gauge_start_pdf, steps_per_pdf, progbar,
            headless=headless)
        pdf_saved_msg = _('PDF has been saved to your desktop in the '
            '\"%s\" folder' % foldername)
    msgs.append(pdf_saved_msg)

def export2pdf(pdf_root, pdf_name, report_path, gauge_start_pdf=0,
        steps_per_pdf=None, progbar=None, *, headless=False):
    if headless:
        if (steps_per_pdf, progbar) != (None, None):
            raise Exception(
                "If running headless, don't set the GUI-specific settings")
        steps_per_pdf = 1
        progbar = export_output.Prog2console()
    if mg.OVERRIDE_FOLDER:
        pdf_root = mg.OVERRIDE_FOLDER
    pdf_path = pdf_root / pdf_name
    html2pdf(html_path=report_path, pdf_path=pdf_path, as_pre_img=False)
    gauge2show = min(gauge_start_pdf + steps_per_pdf, mg.EXPORT_IMG_GAUGE_STEPS)
    progbar.SetValue(gauge2show)
    return pdf_path

def get_raw_pdf(html_path, pdf_path, width='', height=''):
    """
    Note - PDFs made by wkhtmltopdf might be malformed from a strict point of
    view (ghostscript and Adobe might complain). Best to fix in extra step.
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    try:
        url = html_path.as_uri()
        cmd_make_pdf = 'cmd_make_pdf not successfully generated yet'
        """
        Unless Linux, MUST be in report directory otherwise won't carry across
        internal links.

        Re: http://www.microsoft.com/resources/documentation/windows/xp/all/proddocs/en-us/ntcmds_shelloverview.mspx?mfr=true
        """
        ## clear decks first so we can tell if image made or not
        try:
            os.remove(pdf_path)
        except Exception:
            pass
        rel_url = os.path.split(url)[1]
        cd_path = os.path.split(html_path)[0]
        if mg.PLATFORM == mg.WINDOWS:  ## using Pyinstaller
            cmd_make_pdf = (
                f'cd "{cd_path}" && '
                f'"{export_output.EXE_TMP}\\wkhtmltopdf.exe" '
                f'{width} {height} "{rel_url}" "{pdf_path}"')
        elif mg.PLATFORM == mg.MAC:
            cmd_make_pdf = (
                f'cd "{cd_path}" && '
                f'"{mg.MAC_FRAMEWORK_PATH}/wkhtmltopdf" '
                f'{width} {height} "{rel_url}" "{pdf_path}"')
        elif mg.PLATFORM == mg.LINUX:
            cmd_make_pdf = f'wkhtmltopdf {width} {height} "{url}" "{pdf_path}"'
        else:
            raise Exception('Encountered an unexpected platform!')
        ## wkhtmltopdf uses stdout to actually output the PDF - a good feature but stuffs up reading stdout for message
        if debug: print(f'cmd_make_pdf: {cmd_make_pdf}')
        export_output.shellit(cmd_make_pdf)
        if not os.path.exists(pdf_path):
            raise Exception(
                f"wkhtmltopdf didn't generate error but {pdf_path} not made "
                f'nonetheless. cmd_make_pdf: {cmd_make_pdf}')
        if debug: print(f'Initial processing of {html_path} complete')
    except Exception as e:
        raise Exception(
            f'get_raw_pdf command failed: {cmd_make_pdf}. Orig error: {b.ue(e)}')
    return pdf_path

def get_pdf_page_count(pdf_path):
    try:
        encoding2use = sys.getfilesystemencoding()  ## on win, mbcs
        pdf_im = pypdf.PdfFileReader(open(pdf_path.encode(encoding2use), 'rb'))
    except Exception as e:
        raise Exception(
            f'Problem getting PDF page count. Orig error: {b.ue(e)}')
    n_pages = pdf_im.getNumPages()
    return n_pages

def html2pdf(html_path, pdf_path, *, as_pre_img=False):
    width = f'--page-width {PDF_SIDE_MM}' if as_pre_img else ''
    height = f'--page-height {PDF_SIDE_MM}' if as_pre_img else ''
    try:
        raw_pdf = get_raw_pdf(html_path, RAWPDF_PATH, width, height)
    except Exception as e:
        raise Exception(f'Unable to make raw PDF: Orig error: {b.ue(e)}')
    shutil.copy(raw_pdf, pdf_path)
