#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
export2pdf() does the real work and can be scripted outside the GUI. Set
headless = True when calling.
"""
import os
import sys

import pyPdf

import basic_lib as b
import my_globals as mg
import export_output
import output

RAWPDF_FILE = u"raw.pdf"
RAWPDF_PATH = os.path.join(mg.INT_PATH, RAWPDF_FILE)
PDF_SIDE_MM = u"420" # any larger and they won't be able to display anywhere in one go anyway

def pdf_tasks(save2report_path, report_path, alternative_path, headless, 
        gauge_start_pdf, steps_per_pdf, msgs, progbar):
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception(u"Report contents cannot be exported. "
                u"No report file \"%s\"to export." % report_path)
        rpt_root, rpt_name = os.path.split(report_path)
        pdf_name = u"%s.pdf" % os.path.splitext(rpt_name)[0]
        pdf_path = export2pdf(rpt_root, pdf_name, report_path, 
            gauge_start_pdf, headless, steps_per_pdf, progbar)
        pdf_saved_msg = (_(u"PDF has been saved to: \"%s\"") % pdf_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        pdf_path = export2pdf(alternative_path, u"SOFA output.pdf", 
            report_path, gauge_start_pdf, headless, steps_per_pdf, progbar)
        pdf_saved_msg = _(u"PDF has been saved to your desktop in the "
            u"\"%s\" folder" % foldername)
    msgs.append(pdf_saved_msg)

def export2pdf(pdf_root, pdf_name, report_path, gauge_start_pdf=0, 
        headless=False, steps_per_pdf=None, progbar=None):
    if headless:
        if (steps_per_pdf, progbar) != (None, None):
            raise Exception(u"If running headless, don't set the GUI-specific "
                u"settings")
        steps_per_pdf = 1
        progbar = export_output.Prog2console()
    if mg.OVERRIDE_FOLDER:
        pdf_root = mg.OVERRIDE_FOLDER
    pdf_path = os.path.join(pdf_root, pdf_name)
    html2pdf(html_path=report_path, pdf_path=pdf_path, as_pre_img=False)
    gauge2show = min(gauge_start_pdf + steps_per_pdf, mg.EXPORT_IMG_GAUGE_STEPS)
    progbar.SetValue(gauge2show)
    return pdf_path

def get_raw_pdf(html_path, pdf_path, width=u"", height=u""):
    """
    Note - PDFs made by wkhtmltopdf might be malformed from a strict point of 
        view (ghostscript and Adobe might complain). Best to fix in extra step.
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    try:
        url = output.path2url(html_path)
        cmd_make_pdf = u"cmd_make_pdf not successfully generated yet"        
        """
        Unless Linux, MUST be in report directory otherwise won't carry across internal 
            links.
        Re: && http://www.microsoft.com/resources/documentation/windows/...
            ...xp/all/proddocs/en-us/ntcmds_shelloverview.mspx?mfr=true
        """
        rel_url = os.path.split(url)[1]
        cd_path = os.path.split(html_path)[0]
        if mg.PLATFORM == mg.WINDOWS: # using Pyinstaller
            cmd_make_pdf = (u'cd "%s" && '
                u'"%s\\wkhtmltopdf.exe" %s %s "%s" "%s"' % (cd_path, 
                export_output.EXE_TMP, width, height, rel_url, pdf_path))
        elif mg.PLATFORM == mg.MAC:
            cmd_make_pdf = (u'cd "%s" && "%s/wkhtmltopdf" %s %s "%s" "%s"'
                % (cd_path, mg.MAC_FRAMEWORK_PATH, width, height, rel_url,
                    pdf_path))
        elif mg.PLATFORM == mg.LINUX:
            cmd_make_pdf = (u'wkhtmltopdf %s %s "%s" "%s" ' % (width, height, 
                url, pdf_path))
        else:
            raise Exception(u"Encountered an unexpected platform!")
        # wkhtmltopdf uses stdout to actually output the PDF - a good feature but stuffs up reading stdout for message
        if debug: print(u"cmd_make_pdf: %s" % cmd_make_pdf)
        export_output.shellit(cmd_make_pdf)
        if not os.path.exists(pdf_path):
            raise Exception("wkhtmltopdf didn't generate error but %s not made "
                u"nonetheless. cmd_make_pdf: %s" % (pdf_path, cmd_make_pdf))
        if debug: print("Initial processing of %s complete" % html_path)
    except Exception, e:
        raise Exception(u"get_raw_pdf command failed: %s. Orig error: %s" % 
            (cmd_make_pdf, b.ue(e)))
    return pdf_path

def fix_pdf(raw_pdf, final_pdf):
    """
    Needed to avoid: http://code.google.com/p/wkhtmltopdf/issues/detail?id=488
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    cmd_fix_pdf = "cmd_fix_pdf not successfully built"
    try:
        if mg.PLATFORM == mg.WINDOWS: # using Pyinstaller
            import win32api #@UnresolvedImport
            # http://www.velocityreviews.com/forums/...
            #...t337521-python-utility-convert-windows-long-file-name-into-8-3-dos-format.html
            raw_pdf = win32api.GetShortPathName(raw_pdf)
            final_pdf_root, final_pdf_file = os.path.split(final_pdf)
            cmd_fix_pdf = (u'cd "%s" && "%s\\pdftk.exe" "%s" output "%s"' % 
                (final_pdf_root, export_output.EXE_TMP, raw_pdf, 
                 final_pdf_file))
        elif mg.PLATFORM == mg.MAC:
            cmd_fix_pdf = (u'"%s/pdftk" "%s" output "%s" ' % 
                (mg.MAC_FRAMEWORK_PATH, raw_pdf, final_pdf))
        elif mg.PLATFORM == mg.LINUX:
            cmd_fix_pdf = (u'pdftk "%s" output "%s" ' % (raw_pdf, final_pdf))
        else:
            raise Exception(u"Encountered an unexpected platform!")
        if debug: print(u"cmd_fix_pdf: %s" % cmd_fix_pdf)
        export_output.shellit(cmd_fix_pdf)
        if not os.path.exists(final_pdf):
            raise Exception("pdftk didn't generate error but %s not made "
                u"nonetheless. cmd_fix_pdf: %s" % (final_pdf, cmd_fix_pdf))
        if debug: print(u"Fixed \"%s\"" % final_pdf)
    except Exception, e:
        raise Exception(u"fix_pdf command for \"%s\" failed: %s. "
            u"Orig error: %s" % (raw_pdf, cmd_fix_pdf, b.ue(e)))

def get_pdf_page_count(pdf_path):
    try:
        encoding2use = sys.getfilesystemencoding() # on win, mbcs
        pdf_im = pyPdf.PdfFileReader(file(pdf_path.encode(encoding2use), "rb"))
    except Exception, e:
        raise Exception(u"Problem getting PDF page count. Orig error: %s" % 
            b.ue(e))
    n_pages = pdf_im.getNumPages()
    return n_pages

def html2pdf(html_path, pdf_path, as_pre_img=False):
    """
    PDFs made by wkhtmltopdf might be systematically malformed from a strict 
        point of view (ghostscript and Adobe might complain) so running it 
        through pdftk will fix it.
    """
    width = u"--page-width %s" % PDF_SIDE_MM if as_pre_img else u""
    height = u"--page-height %s" % PDF_SIDE_MM if as_pre_img else u""
    try:
        raw_pdf = get_raw_pdf(html_path, RAWPDF_PATH, width, height)
    except Exception, e:
        raise Exception(u"Unable to make raw PDF: Orig error: %s" % b.ue(e))
    try:
        fix_pdf(raw_pdf, pdf_path)
    except Exception, e:
        raise Exception(u"Unable to fix raw PDF: Orig error: %s" % b.ue(e))
