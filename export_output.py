#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sorry - I haven't been able to get exporting to work on Macs yet. Please contact 
the project if you would like details or if you are a Python developer and can 
help.

export2pdf(), export2spreadsheet(), and export2imgs() do the real work and can 
be scripted outside the GUI. Set headless = True when calling. export2imgs has 
the best doc string to read.

When creating images, splits by divider SOFA puts between all chunks of content.
Namely mg.OUTPUT_ITEM_DIVIDER.
"""

import codecs
from collections import namedtuple
import datetime
import os
import shutil
import subprocess
import sys

import pyPdf
import wx

import my_globals as mg
import lib
import my_exceptions
import output

OVERRIDE_FOLDER = None

EXTNAME = "Export output"
GAUGE_STEPS = 100
HTML4PDF_FILE = u"html4pdf.html"
RAWPDF_FILE = u"raw.pdf"
PDF2IMG_FILE = u"pdf2img.pdf"
RAWPDF_PATH = os.path.join(mg.INT_PATH, RAWPDF_FILE)
PDF2IMG_PATH = os.path.join(mg.INT_PATH, PDF2IMG_FILE)
PDF_SIDE_MM = u"420" # any larger and they won't be able to display anywhere in one go anyway
DRAFT_DPI = 72
SCREEN_DPI = 150
PRINT_DPI = 300
HIGH_QUAL_DPI = 600
TOP_DPI = 1200 #1000 if mg.PLATFORM == mg.WINDOWS else 1200 # Windows XP crashes with a message about
# PostscriptDelegateFailed '...\_internal\pdf2img.pdf'. No such file or directory
PDF_ITEM_TAKES = 4
IMG_ITEM_TAKES_72 = 2
IMG_ITEM_TAKES_150 = 4
IMG_ITEM_TAKES_300 = 8
IMG_ITEM_TAKES_600 = 20
IMG_ITEM_TAKES_1200 = 50
TBL_ITEM_TAKES = 1
try:
    EXE_TMP = sys._MEIPASS #@UndefinedVariable
except AttributeError:
    EXE_TMP = u""

DIAGNOSTIC = False
if DIAGNOSTIC:
    wx.MessageBox("Diagnostic mode is on :-). Be ready to take screen-shots.")

"""
Idea - put into large pages, then use PythonMagick to auto-crop. Then I don't 
    have to know exact dimensions.
Use SOFA Python code to split output into individual images (split chart series 
    into individual charts). Each will have the massive html header (css and 
    javascript etc) plus a tiny end bit (close body and html tags). Store in 
    _internal folder.
Also split out any text in same order so that numbering can be sequential. Store 
    names inside html original so we can name “001 - Gender by Ethnicity.png” 
    etc.

http://www.imagemagick.org/Magick++/Image.html#Image%20Manipulation%20Methods
http://www.imagemagick.org/Usage/crop/#trim
A trick that works is to add a border of the colour you want to trim,
    _then_ trim.
trim() -- Trim edges that are the background color from the image.

trimming is very slow at higher dpis so we can do a quick, dirty version
    at a lower dpi, get dimensions, and multiply by the PDF dpi/cheap dpi
    to get rough dimensions to crop.
We can (approximately) translate from size at lower dpi to larger
    based on quick job done at lower dpi. Add a few pixels around
    to be safe. [update - for some reason, takes more, best to add a fair
    few and then trim the final]
20 130x138
40 261x277
80 518x550
160 1038x1100

For multipage images, use [idx] notation after .pdf
http://stackoverflow.com/questions/4809314/...
    ...imagemagick-is-converting-only-the-first-page-of-the-pdf

Packaging Notes:
Wkhtmltopdf - Packaged for Ubuntu and cross-platform. An active projects but 
    some tricky bugs too: Problems with space between characters
    wkhtmltopdf > 0.9.0
ImageMagick - Packaged for Ubuntu and cross-platform.
    imagemagick > 8.0.0
PythonMagick - http://www.imagemagick.org/download/python/
    python-pythonmagick > 0.9.0
Note -- enable images saved to be in high resolution for publishing purposes.
Warn users it will take longer (give an estimate) and show progress on a bar.
"""

output_item = namedtuple('output_item', 'title, content')


class Prog2console(object):
    def SetValue(self, value):
        print(u"Current progress: %s ..." % str(value).rjust(3))


class DlgExportOutput(wx.Dialog):
    
    def __init__(self, title, report_path, save2report_path=True):
        """
        save2report_path -- output goes into the report folder. If False, 
        exporting output to a temporary desktop folder for the user to look at. 
        """
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
            pos=(mg.HORIZ_OFFSET+200, 300), style=wx.MINIMIZE_BOX|
            wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU|
            wx.CAPTION|wx.CLIP_CHILDREN)
        self.save2report_path = save2report_path
        if OVERRIDE_FOLDER:
            self.save2report_path = True
        self.report_path = report_path
        szr = wx.BoxSizer(wx.VERTICAL)
        self.export_status = {mg.CANCEL_EXPORT: False} # can change and running script can check on it.
        if self.temp_desktop_report_only:
            msg = u"Export content currently displayed in SOFA"
        else:
            report_name = os.path.split(report_path)[1]
            msg = u"Export \"%s\"" % report_name
        lbl_msg = wx.StaticText(self, -1, msg)
        szr.Add(lbl_msg, 0, wx.ALL, 10)
        szr_pdf_or_tbls = wx.BoxSizer(wx.VERTICAL)
        szr_left_and_right = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_pdf = wx.CheckBox(self, -1, _("Export as PDF"))
        self.chk_pdf.Bind(wx.EVT_CHECKBOX, self.on_chk_pdf)
        self.chk_tbls = wx.CheckBox(self, -1, _("Export to spreadsheet (report "
            u"tables only)"))
        self.chk_tbls.Bind(wx.EVT_CHECKBOX, self.on_chk_tbls)
        szr_pdf_or_tbls.Add(self.chk_pdf, 0, wx.ALL, 10)
        szr_pdf_or_tbls.Add(self.chk_tbls, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        ln_split = wx.StaticLine(self, style=wx.LI_VERTICAL)
        szr_left_and_right.Add(szr_pdf_or_tbls)
        szr_left_and_right.Add(ln_split, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_imgs = wx.BoxSizer(wx.VERTICAL)
        self.chk_imgs = wx.CheckBox(self, -1, _("Export as Images"))
        self.chk_imgs.Bind(wx.EVT_CHECKBOX, self.on_chk_imgs)
        self.choice_dpis = [
            (_(u"Draft Quality (%s dpi)") % DRAFT_DPI, DRAFT_DPI), 
            (_(u"Screen Quality (%s dpi)") % SCREEN_DPI, SCREEN_DPI), 
            (_(u"Print Quality (%s dpi)") % PRINT_DPI, PRINT_DPI),
            (_(u"High Quality (%s dpi)") % HIGH_QUAL_DPI, HIGH_QUAL_DPI),
            (_(u"Top Quality (%s dpi)") % TOP_DPI, TOP_DPI),
        ]
        choices = [x[0] for x in self.choice_dpis]
        self.drop_dpi = wx.Choice(self, -1, choices=choices)
        idx_print = 2
        self.drop_dpi.SetSelection(idx_print)
        self.drop_dpi.SetToolTipString(u"The more dots per inch (dpi) the "
            u"higher the quality but the slower the export process.")
        szr_imgs.Add(self.chk_imgs, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_imgs.Add(self.drop_dpi, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_left_and_right.Add(szr_imgs, 0)
        szr.Add(szr_left_and_right, 0) 
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        self.btn_cancel.Enable(False)
        self.btn_export = wx.Button(self, -1, u"Export")
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
        self.btn_export.Enable(False)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=0)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_export, 0, wx.ALIGN_RIGHT)       
        self.progbar = wx.Gauge(self, -1, GAUGE_STEPS, size=(-1, 20),
            style=wx.GA_PROGRESSBAR)
        self.btn_close = wx.Button(self, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close)
        szr.Add(szr_btns, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr.Add(self.progbar, 0, wx.GROW|wx.ALIGN_RIGHT|wx.ALL, 10)
        szr.Add(self.btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(szr)
        szr.SetSizeHints(self)
        szr.Layout()
    
    def on_btn_export(self, event):
        debug = False
        headless = False
        if DIAGNOSTIC: debug = True
        self.progbar.SetValue(0)
        wx.BeginBusyCursor()
        do_pdf = self.chk_pdf.IsChecked()
        do_imgs = self.chk_imgs.IsChecked()
        do_tbls = self.chk_tbls.IsChecked()
        if not (do_pdf or do_imgs or do_tbls):
            self.align_btns_to_exporting(exporting=False)
            wx.MessageBox(u"Please select a format(s) to export in.")
            return
        self.align_btns_to_exporting(exporting=True)
        msgs = []
        if self.save2report_path:
            foldername = None
            temp_desktop_path = None
        else:
            # save to folder on desktop
            ts = datetime.datetime.now().strftime('%b %d %I-%M %p').strip()
            foldername = u"SOFA export %s" % ts
            desktop = os.path.join(mg.HOME_PATH, u"Desktop")
            temp_desktop_path = os.path.join(desktop, foldername)
            if debug: print(temp_desktop_path)
            try:
                os.mkdir(temp_desktop_path)
            except OSError:
                pass # already there
        hdr, img_items, tbl_items = get_hdr_and_items(self.report_path, 
            DIAGNOSTIC)
        n_imgs = len(img_items)
        n_tbls = len(tbl_items)
        idx_sel = self.drop_dpi.GetSelection()
        idx_dpi = 1
        self.output_dpi = self.choice_dpis[idx_sel][idx_dpi]
        n_pdfs = 1 if do_pdf else 0
        (gauge_start_pdf, steps_per_pdf, 
        gauge_start_imgs, steps_per_img, 
        gauge_start_tbls, steps_per_tbl) = get_start_and_steps(n_pdfs, n_imgs, 
            self.output_dpi, n_tbls)
        if do_pdf:
            try:
                pdf_tasks(self.save2report_path, self.report_path, 
                    temp_desktop_path, headless, gauge_start_pdf, steps_per_pdf, 
                    msgs, self.progbar)
            except Exception, e:
                self.progbar.SetValue(0)
                lib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                wx.MessageBox(u"Unable to export PDF. Orig error: %s" % 
                    lib.ue(e))
                return
        if do_imgs:
            try:
                export2imgs(hdr, img_items, self.save2report_path, 
                    self.report_path, temp_desktop_path, self.output_dpi, 
                    gauge_start_imgs, headless, self.export_status, 
                    steps_per_img, msgs, self.progbar)
            except Exception, e:
                try:
                    raise
                except my_exceptions.ExportCancel:
                    wx.MessageBox(u"Export Cancelled")
                except Exception, e:
                    msg = (u"Problem exporting output. Orig error: %s" % 
                        lib.ue(e))
                    if debug: print(msg)
                    wx.MessageBox(msg)
                self.progbar.SetValue(0)
                lib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                return
        if do_tbls:
            try:
                export2spreadsheet(hdr, tbl_items, self.save2report_path, 
                    self.report_path, temp_desktop_path, gauge_start_tbls, 
                    headless, steps_per_tbl, msgs, self.progbar)
            except Exception, e:
                try:
                    raise
                except my_exceptions.ExportCancel:
                    wx.MessageBox(u"Export Cancelled")
                except Exception, e:
                    msg = (u"Problem exporting output. Orig error: %s" % 
                        lib.ue(e))
                    if debug: print(msg)
                    wx.MessageBox(msg)
                self.progbar.SetValue(0)
                lib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                return
        self.progbar.SetValue(GAUGE_STEPS)
        lib.safe_end_cursor()
        self.align_btns_to_exporting(exporting=False)
        msg = u"\n\n".join(msgs)
        caption = (_(u"EXPORTED CURRENT OUTPUT") 
            if self.temp_desktop_report_only else _(u"EXPORTED REPORT"))
        wx.MessageBox(_(u"Exporting completed.\n\n%s") % msg, caption=caption)
        self.progbar.SetValue(0)
    
    def on_chk_pdf(self, event):
        self.align_btns_to_completeness()
        
    def on_chk_imgs(self, event):
        self.align_btns_to_completeness()
        
    def on_chk_tbls(self, event):
        self.align_btns_to_completeness()
    
    def on_btn_cancel(self, event):
        self.export_status[mg.CANCEL_EXPORT] = True

    def align_btns_to_completeness(self):
        do_pdf = self.chk_pdf.IsChecked()
        do_imgs = self.chk_imgs.IsChecked()
        do_tbls = self.chk_tbls.IsChecked()
        complete = (do_pdf or do_imgs or do_tbls)
        self.btn_export.Enable(complete)

    def align_btns_to_exporting(self, exporting):
        self.btn_close.Enable(not exporting)
        self.btn_cancel.Enable(exporting)
        self.btn_export.Enable(not exporting)
    
    def on_btn_close(self, event):
        self.Destroy()

        
def get_raw_html(report_path):
    try:
        with codecs.open(report_path, "U", "utf-8") as f:
            raw_html = lib.clean_boms(f.read())
            f.close()
    except IOError:
        raise Exception(u"Unable to get items from report file - it doesn't "
            u"exist yet.") # should only see this when running headless via a script - otherwise should be picked up by GUI-level validation.
    return raw_html

def get_split_html(report_path):
    raw_html = get_raw_html(report_path)
    if not raw_html:
        raise Exception(u"No raw html found in report file.")
    split_html = raw_html.split(mg.OUTPUT_ITEM_DIVIDER)
    return split_html

def get_hdr_and_items(report_path, diagnostic=False):
    """
    Read (presumably) html text from report. Split by main output divider, 
    discarding the first (assumed to be the html header).
    
    Within each item, split off the content above the item (if any) e.g. a 
    visual line divider, comments on filtering applied etc.
    
    Then split by title splitter - chunk 0 = actual content, chunk 1 = title to 
    use when saving the item.
    
    All items can be turned into images. Only table reports can be turned into 
    spreadsheet tables.
    """
    debug = False
    if diagnostic: debug = True
    verbose = False
    img_items = []
    tbl_items = []
    split_html = get_split_html(report_path)
    if not split_html:
        raise Exception(u"No split html")
    n_items = len(split_html) - 1 # never content at end - just html footer
    if n_items == 0: n_items = 1 # the normality chart is a special case where there is only one item
    hdr = None
    for i, html in enumerate(split_html, 1):
        """
        Split items might look like this:
        -----------
        Optionally, a Visual Divider (and marker). Indiv charts in stats output
            will not have a visual divider and marker.
        Content
        An Item Title Start
        Title
        -----------
        Strip off visible divider from beginning.
        Grab raw file name from end. Put padded i at start e.g. 0001. Replace 
            spaces with underscores to make web-friendly (build img_name_no_ext).
        Grab raw html from middle
        Put hdr at start and ftr at end
        Save to tmp file (html_name)
        html2pdf()
        imgs_made = pdf2img()
        """
        if i > n_items:
            break # never content at end - just html footer
        split_by_div = html.split(mg.VISUAL_DIVIDER_BEFORE_THIS)
        if debug and verbose: print(split_by_div)
        if len(split_by_div) == 1:
            ex_vis_div = split_by_div[0]
        else:
            ex_vis_div = split_by_div[1]
        if i == 1: # get the header
            hdr = (split_by_div[0].split(u"<body ")[0] + 
                u"\n%s" % mg.BODY_START)
            if debug: print(u"\nEnd of hdr:\n" + hdr[-60:])
        if debug and verbose: print(ex_vis_div)
        full_content = ex_vis_div.split(mg.ITEM_TITLE_START)
        n_content = len(full_content)
        if n_content == 2:
            content, title_comment = full_content
        else:
            raise Exception(u"Should split into two parts - content and title "
                u"comment. Instead split into %s parts. Did you forget to use "
                u"append_divider?" % n_content)
        if debug and verbose: print("\n\n%s\n%s ...\n%s" % (title_comment, 
            content[:30], content[-30:]))
        title = title_comment[4:-3]
        if debug: print(title)
        item = output_item(title, content)
        img_items.append(item) # all items can be turned into images (whether a chart or a table etc.
        if mg.REPORT_TABLE_START in item.content:
            tbl_items.append(item)
    if hdr is None:
        raise Exception(u"Unable to extract hdr from report file.")
    return hdr, img_items, tbl_items

def get_start_and_steps(n_pdfs, n_imgs, output_dpi, n_tbls):
    """
    Where should we start on the progress gauge and how much should each item 
    move us along?
    
    Start by have a basic concept of the relativities for pdf vs images vs 
    tables, and knowing how many items of each sort there are.
    """
    pdf_taken = (n_pdfs*PDF_ITEM_TAKES)
    output_dpi2takes = {72: 1, 150: 2, 300: 4, 600: 10, 1200: 30}
    IMG_ITEM_TAKES = output_dpi2takes[output_dpi]
    imgs_taken = (n_imgs*IMG_ITEM_TAKES)
    tbls_taken = (n_tbls*TBL_ITEM_TAKES)
    tot_taken = pdf_taken + imgs_taken + tbls_taken
    if tot_taken == 0:
        raise Exception(u"Unable to get start and steps - zero items to show "
            u"progress for.")
    pdf_as_prop = pdf_taken/float(tot_taken)
    imgs_as_prop = imgs_taken/float(tot_taken)
    tbls_as_prop = tbls_taken/float(tot_taken)
    steps_for_pdf = GAUGE_STEPS*pdf_as_prop
    steps_for_imgs = GAUGE_STEPS*imgs_as_prop
    steps_for_tbls =  GAUGE_STEPS*tbls_as_prop
    if n_pdfs == 0:
        steps_per_pdf_item = 0 # doesn't matter - should not be used if no items
    else:
        steps_per_pdf_item = steps_for_pdf/float(n_pdfs)
    if n_imgs == 0:
        steps_per_img_item = 0
    else:
        steps_per_img_item = steps_for_imgs/float(n_imgs)
    if n_tbls == 0:
        steps_per_tbl_item = 0
    else:
        steps_per_tbl_item = steps_for_tbls/float(n_tbls)
    gauge_start_pdf = 0
    gauge_start_imgs = steps_for_pdf
    gauge_start_tbls = steps_for_pdf + steps_for_imgs
    return (gauge_start_pdf, steps_per_pdf_item, gauge_start_imgs, 
        steps_per_img_item, gauge_start_tbls, steps_per_tbl_item)

def pdf_tasks(save2report_path, report_path, temp_desktop_path, headless, 
        gauge_start_pdf, steps_per_pdf, msgs, progbar):
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception(u"Report contents cannot be exported. "
                u"No report file \"%s\"to export." % report_path)
        rpt_root, rpt_name = os.path.split(report_path)
        pdf_name = u"%s.pdf" % os.path.splitext(rpt_name)[0]
        """
        Make version which removes class class="screen-float-only" because this 
        printing exercise is really a screen exercise underneath - and we need 
        to manually prevent floating.
        """
        """
        file_src = codecs.open(self.report_path, "r", "utf-8")
        txt2fix = file_src.read()
        file_src.close()
        HTML4PDF_PATH = os.path.join(rpt_root, HTML4PDF_FILE) # must be in reports path so JS etc all available
        file_dest = codecs.open(HTML4PDF_PATH, "w", "utf-8")
        txt2write = txt2fix.replace(u'class="screen-float-only"', 
            u"").replace(u'style="', u'style="page-break-inside: avoid; ')                    
        file_dest.write(txt2write)
        file_dest.close()
        """
        pdf_path = export2pdf(rpt_root, pdf_name, report_path, 
            gauge_start_pdf, headless, steps_per_pdf, progbar)
        pdf_saved_msg = (_(u"PDF has been saved to: \"%s\"") % pdf_path)
    else:
        foldername = os.path.split(temp_desktop_path)[1]
        pdf_path = export2pdf(temp_desktop_path, u"SOFA output.pdf", 
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
        progbar = Prog2console()
    if OVERRIDE_FOLDER:
        pdf_root = OVERRIDE_FOLDER
    pdf_path = os.path.join(pdf_root, pdf_name)
    html2pdf(html_path=report_path, pdf_path=pdf_path, as_pre_img=False)
    gauge2show = gauge_start_pdf + steps_per_pdf
    progbar.SetValue(gauge2show)
    return pdf_path

def export2imgs(hdr, img_items, save2report_path, report_path, 
        temp_desktop_path, output_dpi, gauge_start_imgs=0, headless=False, 
        export_status=None, steps_per_img=None, msgs=None, progbar=None):
    """
    hdr -- HTML header with css, javascript etc. Make hdr (and img_items) with 
    get_hdr_and_items()
    
    img_items -- list of data about images. Make img_items (and hdr) with a call 
    to get_hdr_and_items()
    
    save2report_path -- boolean. True when exporting a report; False 
    when exporting or coping current output.
    
    report_path -- only needed if exporting entire report 
    i.e. save2report_path = True. 
    e.g. /home/g/Documents/sofastats/reports/sofa_use_only_report.htm
    
    temp_desktop_path -- images will only go here if not save2report_path 
    (and if there is no OVERRIDE_FOLDER as well that is).
    
    output_dpi -- e.g. 300
    
    gauge_start_imgs -- used when in non-headless mode so the progress bar can 
    show progress through exporting images, tables, and as pdf as a single total 
    job. Can also be used when in headless mode.
    
    headless -- Set to False to run from a script without GUI input.
    
    export_status -- only used to check if a user has cancelled the export via 
    the GUI.
    
    steps_per_img -- relevant to GUI progress bar.
    
    msgs -- list of messages to display in GUI later.
    
    progbar -- so we can display progress as we go in GUI. If set to None, will 
    send progress to stdout instead.
    """
    debug = False
    if headless:
        if ((export_status, steps_per_img, msgs, progbar) 
                != (None, None, None, None)):
            raise Exception(u"If running headless, don't set the GUI-specific "
                u"settings")
        export_status = {mg.CANCEL_EXPORT: False}
        steps_per_img = 1 # leave msgs as default of None
        progbar = Prog2console()
    if DIAGNOSTIC: debug = True
    output_dpi = 60 if debug else output_dpi
    if temp_desktop_path:
        imgs_path = temp_desktop_path
    else:
        imgs_path = output.ensure_imgs_path(report_path, 
            ext=u"_exported_images")
    if OVERRIDE_FOLDER:
        imgs_path = OVERRIDE_FOLDER
    rpt_root = os.path.split(report_path)[0]
    HTML4PDF_PATH = os.path.join(rpt_root, HTML4PDF_FILE) # must be in reports path so JS etc all available
    n_imgs = len(img_items)
    long_time = ((n_imgs > 30 and output_dpi == SCREEN_DPI) 
        or (n_imgs > 10 and output_dpi == PRINT_DPI) 
        or (n_imgs > 2 and output_dpi == HIGH_QUAL_DPI))
    if long_time and not headless:
        if wx.MessageBox(_("The report has %s images to export at %s dpi. "
                "Do you wish to export at this time?") % (n_imgs, output_dpi), 
                caption=_("SLOW EXPORT PREDICTED"), style=wx.YES_NO) == wx.NO:
            if progbar: progbar.SetValue(0)
            raise my_exceptions.ExportCancel
    gauge2show = gauge_start_imgs
    if progbar: progbar.SetValue(gauge2show)
    ftr = u"</body></html>"
    # give option of backing out
    for i, item in enumerate(img_items, 1):
        if not headless: wx.Yield()
        if export_status[mg.CANCEL_EXPORT]:
            if progbar: progbar.SetValue(0)
            raise my_exceptions.ExportCancel
        img_name_no_ext = "%04i_%s" % (i, item.title.replace(u" - ", u"_").
            replace(u" ", u"_").replace(u":", u"_"))
        img_pth_no_ext = os.path.join(imgs_path, img_name_no_ext)
        if mg.IMG_SRC_START in item.content: # copy existing image
            export_report = not (report_path == mg.INT_REPORT_PATH)
            src, dst = lib.get_src_dst_preexisting_img(export_report, imgs_path, 
                item.content)
            try:
                shutil.copyfile(src, dst)
            except Exception, e:
                msg = (u"Unable to copy existing image file. Orig error: %s" % 
                    lib.ue(e))
                if not headless:
                    wx.MessageBox(msg)
                else:
                    print(msg)
                if progbar: progbar.SetValue(0)
                raise my_exceptions.ExportCancel
        else:
            full_content_html = u"\n".join([hdr, item.content, ftr])
            with codecs.open(HTML4PDF_PATH, "w", "utf-8") as f:
                f.write(full_content_html)
                f.close()
            html2pdf(html_path=HTML4PDF_PATH, pdf_path=PDF2IMG_PATH, 
                as_pre_img=True)
            #wx.MessageBox(img_pth_no_ext)
            if debug: print(img_pth_no_ext)
            imgs_made = pdf2img(pdf_path=PDF2IMG_PATH, 
                img_pth_no_ext=img_pth_no_ext, 
                bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=output_dpi)
            if debug: print(u"Just made image(s) %s:\n%s" % 
                (i, u",\n".join(imgs_made)))
        gauge2show += steps_per_img
        if progbar: progbar.SetValue(gauge2show)
    if save2report_path:
        img_saved_msg = (_(u"Images have been saved to: \"%s\"") % imgs_path)
    else:
        foldername = os.path.split(temp_desktop_path)[1]
        img_saved_msg = (u"Images have been saved to your desktop in the "
            u"\"%s\" folder" % foldername)
    if not headless:
        msgs.append(img_saved_msg)

def export2spreadsheet(hdr, tbl_items, save2report_path, report_path, 
        temp_desktop_path, gauge_start_tbls=0, headless=False, 
        steps_per_tbl=None, msgs=None, progbar=None):
    if headless:
        if (steps_per_tbl, msgs, progbar) != (None, None, None):
            raise Exception(u"If running headless, don't set the GUI-specific "
                u"settings")
        steps_per_tbl = 1 # leave msgs as default of None
        progbar = Prog2console()
    if save2report_path:
        if not os.path.exists(report_path):
            raise Exception(u"Report contents cannot be exported. "
                u"No report file \"%s\"to export." % report_path)
        spreadsheet_root, rpt_name = os.path.split(report_path)
        spreadsheet_name = u"%s.xls" % os.path.splitext(rpt_name)[0]
        progbar = progbar if progbar else Prog2console()
        if OVERRIDE_FOLDER:
            spreadsheet_root = OVERRIDE_FOLDER
        spreadsheet_path = os.path.join(spreadsheet_root, spreadsheet_name)
    else:
        spreadsheet_path = os.path.join(temp_desktop_path, u"SOFA output.xls")
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
        foldername = os.path.split(temp_desktop_path)[1]
        spreadsheet_saved_msg = (u"The spreadsheet has been saved "
            u"to your desktop in the \"%s\" folder" % foldername)
    msgs.append(spreadsheet_saved_msg)
    gauge2show = gauge_start_tbls + (steps_per_tbl*n_tbls)
    progbar.SetValue(gauge2show)

def shellit(cmd, shell=True):
    """
    shell -- on Linux need shell=True
    Avoid stdout from Popen - doesn't work under pyinstaller (my own experiments 
        proved it when the code was run live vs from frozen. Also see 
        http://comments.gmane.org/gmane.comp.python.pyinstaller/3148).
    So avoid this in frozens:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=shell)
        out, err = p.communicate()
        retcode = p.returncode
    Furthermore, there is a possibility that not all programs work well with 
        that e.g. wkhtmltopdf. Not tested myself (the real cause was the frozen 
        vs popen issue) but see http://code.google.com/p/wkhtmltopdf/issues/...
        ...detail?id=825. It uses stdout to actually output the PDF - a good 
        feature but possibly stuffs up reading stdout for message? And pdftk the 
        same?
    """
    debug = False
    if DIAGNOSTIC: debug = True
    verbose = False
    if debug: 
        if verbose:
            try:
                wx.MessageBox(cmd)
            except Exception: # e.g. headless
                print(cmd)
        else:
            print(cmd)
    encoding2use = sys.getfilesystemencoding() # on win, mbcs
    retcode = subprocess.call(cmd.encode(encoding2use), shell=shell)
    if retcode < 0:
        msg = u"%s was terminated by signal %s" % (cmd, retcode)
        if debug: print(msg)
        raise Exception(msg)
    else:
        if debug and verbose: print("%s returned %s" % (cmd, retcode))
    
def get_raw_pdf(html_path, pdf_path, width=u"", height=u""):
    """
    Note - PDFs made by wkhtmltopdf might be malformed from a strict point of 
        view (ghostscript and Adobe might complain). Best to fix in extra step.
    """
    debug = False
    if DIAGNOSTIC: debug = True
    try:
        url = output.path2url(html_path)
        cmd_make_pdf = u"cmd_make_pdf not successfully generated yet"
        if mg.PLATFORM == mg.LINUX:
            cmd_make_pdf = (u'wkhtmltopdf %s %s "%s" "%s" ' % (width, height, 
                url, pdf_path))
        else:
            """
            MUST be in report directory otherwise won't carry across internal 
                links.
            Re: && http://www.microsoft.com/resources/documentation/windows/...
                ...xp/all/proddocs/en-us/ntcmds_shelloverview.mspx?mfr=true
            """
            rel_url = os.path.split(url)[1]
            cd_path = os.path.split(html_path)[0]
            if mg.PLATFORM == mg.WINDOWS: # using Pyinstaller
                cmd_make_pdf = (u'cd "%s" && '
                    u'"%s\\wkhtmltopdf.exe" %s %s "%s" "%s"' % (cd_path, 
                    EXE_TMP, width, height, rel_url, pdf_path))
            elif mg.PLATFORM == mg.MAC:
                cmd_make_pdf = (u'cd "%s" && "%s/wkhtmltopdf" %s %s "%s" "%s"'
                    % (cd_path, os.getcwd(), width, height, rel_url, pdf_path))
        # wkhtmltopdf uses stdout to actually output the PDF - a good feature but stuffs up reading stdout for message
        if debug: print(u"cmd_make_pdf: %s" % cmd_make_pdf)
        shellit(cmd_make_pdf)
        if not os.path.exists(pdf_path):
            raise Exception("wkhtmltopdf didn't generate error but %s not made "
                u"nonetheless. cmd_make_pdf: %s" % (pdf_path, cmd_make_pdf))
        if debug: print("Initial processing of %s complete" % html_path)
    except Exception, e:
        raise Exception(u"get_raw_pdf command failed: %s. Orig error: %s" % 
            (cmd_make_pdf, lib.ue(e)))
    return pdf_path

def fix_pdf(raw_pdf, final_pdf):
    """
    Needed to avoid: http://code.google.com/p/wkhtmltopdf/issues/detail?id=488
    """
    debug = False
    if DIAGNOSTIC: debug = True
    cmd_fix_pdf = "cmd_fix_pdf not successfully built"
    try:
        if mg.PLATFORM == mg.WINDOWS: # using Pyinstaller
            import win32api #@UnresolvedImport
            # http://www.velocityreviews.com/forums/...
            #...t337521-python-utility-convert-windows-long-file-name-into-8-3-dos-format.html
            raw_pdf = win32api.GetShortPathName(raw_pdf)
            final_pdf_root, final_pdf_file = os.path.split(final_pdf)
            cmd_fix_pdf = (u'cd "%s" && "%s\\pdftk.exe" "%s" output "%s"' % 
                (final_pdf_root, EXE_TMP, raw_pdf, final_pdf_file))
        else:
            cmd_fix_pdf = (u'pdftk "%s" output "%s" ' % (raw_pdf, final_pdf))
        if debug: print(u"cmd_fix_pdf: %s" % cmd_fix_pdf)
        shellit(cmd_fix_pdf)
        if not os.path.exists(final_pdf):
            raise Exception("pdftk didn't generate error but %s not made "
                u"nonetheless. cmd_fix_pdf: %s" % (final_pdf, cmd_fix_pdf))
        if debug: print(u"Fixed \"%s\"" % final_pdf)
    except Exception, e:
        raise Exception(u"fix_pdf command for \"%s\" failed: %s. "
            u"Orig error: %s" % (raw_pdf, cmd_fix_pdf, lib.ue(e)))

def get_pdf_page_count(pdf_path):
    try:
        encoding2use = sys.getfilesystemencoding() # on win, mbcs
        pdf_im = pyPdf.PdfFileReader(file(pdf_path.encode(encoding2use), "rb"))
    except Exception, e:
        raise Exception(u"Problem getting PDF page count. Orig error: %s" % 
            lib.ue(e))
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
        raise Exception(u"Unable to make raw PDF: Orig error: %s" % lib.ue(e))
    try:
        fix_pdf(raw_pdf, pdf_path)
    except Exception, e:
        raise Exception(u"Unable to fix raw PDF: Orig error: %s" % lib.ue(e))
    
def u2utf8(unicode_txt):
    # http://stackoverflow.com/questions/1815427/...
    #     ...how-to-pass-an-unicode-char-argument-to-imagemagick
    return unicode_txt.encode("utf-8")

def pdf2img(pdf_path, img_pth_no_ext, bgcolour=mg.BODY_BACKGROUND_COLOUR, 
            output_dpi=300):
    if mg.PLATFORM == mg.MAC: # if I have trouble getting pythonmagick installed
        # Note - requires user to manually install ImageMagick
        return pdf2img_imagemagick(pdf_path, img_pth_no_ext, bgcolour, 
            output_dpi)
    else:
        return pdf2img_pythonmagick(pdf_path, img_pth_no_ext, bgcolour, 
            output_dpi)

def pdf2png_ghostscript(png2read_path, i, pdf_path, dpi):
    """
    http://stackoverflow.com/questions/2598669/...
    ghostscript-whats-are-the-differences-between-linux-and-windows-variants
    
    On Windows you have two executables, gswin32c.exe and gswin32.exe instead of 
    gs only. The first one is to run Ghostscript on the commandline ("DOS box"), 
    the second one will open two GUI windows: one to render the output, another 
    one which is console-like and shows GS stdout/stderr or takes your command 
    input if you run GS in interactive mode.
    
    http://stackoverflow.com/questions/11002982/...
    ...converting-multi-page-pdfs-to-several-jpgs-using-imagemagick-and-or-ghostscript
    
    The png16m device produces 24bit RGB color. You could swap this for pnggray 
    (for pure grayscale output), png256 (for 8-bit color), png16 (4-bit color), 
    pngmono (black and white only) or pngmonod (alternative black-and-white 
    module).
    
    -o not just less explicit -sOutputFile ;-)
    http://ghostscript.com/doc/8.63/Use.htm#PDF_switches
    
    As a convenient shorthand you can use the -o option followed by the output 
    file specification as discussed above. The -o option also sets the -dBATCH 
    and -dNOPAUSE options.
    """
    cmd_pdf2png = (u'"%(exe_tmp)s\\gswin32c.exe" -o "%(png2make)s" '
        u'-sDEVICE=png16m -r%(dpi)s -dFirstPage=%(pg)s '
        u'-dLastPage=%(pg)s "%(pdf_path)s"' % {u"exe_tmp": EXE_TMP, 
        u"png2make": png2read_path, u"dpi": dpi, u"pg": i+1, 
        u"pdf_path": pdf_path})
    try:
        shellit(cmd_pdf2png)
    except Exception, e:
        raise Exception(u"pdf2png_ghostscript command failed: %s. "
            u"Orig error: %s" % (cmd_pdf2png, lib.ue(e)))
    
def try_pdf_page_to_img_pythonmagick(pdf_path, i, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Return img_made or None. Returning None lets calling function break loop 
        through pages.
    """
    import PythonMagick as pm
    debug = False
    if DIAGNOSTIC: debug = True
    im = pm.Image()
    orig_pdf = u"%s[%s]" % (pdf_path, i)
    #wx.MessageBox(orig_pdf)
    cheap_dpi = 30
    # small throwaway version to get size (cheap process to avoid slow process)
    im.density(str(cheap_dpi))
    if mg.PLATFORM == mg.WINDOWS:
        cheap_dpi_png2read_path = os.path.join(mg.INT_PATH, 
            u"cheap_dpi_png2read.png")
        try:
            pdf2png_ghostscript(cheap_dpi_png2read_path, i, pdf_path, cheap_dpi)
        except Exception, e:
            if i == 0:
                raise Exception(u"Unable to convert PDF using ghostscript. "
                    u"Orig error: %s" % lib.ue(e))
            else:
                # Not a problem if fails to read page 2 etc if not multipage
                if debug: 
                    print(u"Failed to convert page idx %s PDF (%s) into image. "
                        u"Probably not a multipage PDF. Orig error: %s" % (i, 
                        pdf_path, lib.ue(e)))
                return None
            
        try: # can read directly from PDF because IM knows where GS is
            im.read(u2utf8(cheap_dpi_png2read_path)) # will fail on page idx 1 if not multipage PDF
        except Exception, e:
            raise Exception(u"Failed to read PDF (%s) into image. "
                u"Orig error: %s" % (pdf_path, lib.ue(e)))
    else:
        try: # can read directly from PDF because IM knows where GS is
            im.read(u2utf8(orig_pdf)) # will fail on page idx 1 if not multipage PDF
        except Exception, e:
            if i == 0:
                raise Exception(u"Failed to read PDF (%s) into image. "
                    u"Orig error: %s" % (pdf_path, lib.ue(e)))
            else:
                # Not a problem if fails to read page 2 etc if not multipage
                if debug: 
                    print(u"Failed to read page idx %s PDF (%s) into image. "
                        u"Probably not a multipage PDF. Orig error: %s" % (i, 
                        pdf_path, lib.ue(e)))
                return None
    if debug: print(u"About to set border colour for image")
    im.borderColor(u2utf8(bgcolour))
    if debug: print(u"Just set border colour for image")
    im.border("1x1")
    try:
        im.trim() # sometimes the PDF has an empty page at the end. Trim hates that and dies even though we don't need that page as an image.
    except Exception, e:
        if debug: print(u"Failed with im.trim(). Orig error: %s" % lib.ue(e))
        return None
    if debug: print(u"Just trimmed image")
    get_dims_only_pth = os.path.join(mg.INT_PATH, u"get_dims_only.png")
    im.write(u2utf8(get_dims_only_pth))
    if debug: print(u"Just written get_dims_only_pth")
    shrunk_width = im.size().width()
    shrunk_height = im.size().height()
    if debug: print(shrunk_width, shrunk_height)
    # apply crop sizes based on small throwaway version
    upscale_by = output_dpi/float(cheap_dpi)
    if debug: print upscale_by
    crop_width = upscale_by*(shrunk_width + 30)
    crop_height = upscale_by*(shrunk_height + 30)
    im.density(str(output_dpi))
    try:
        if mg.PLATFORM == mg.WINDOWS:
            output_dpi_png2read_path = os.path.join(mg.INT_PATH, 
                u"output_dpi_png2read.png")
            #wx.MessageBox(output_dpi_png2read_path)
            pdf2png_ghostscript(output_dpi_png2read_path, i, pdf_path, 
                output_dpi)
            im.read(u2utf8(output_dpi_png2read_path))
        else:
            im.read(u2utf8(orig_pdf))
    except: # Windows XP with 1GB of RAM crashes if 1200 dpi. Note - trying to use e or even Exception may keep crash going.
        raise Exception(u"Unable to process PDF at %s dpi. Please try again "
            u"with a lower output quality if possible." % output_dpi)
    im.crop("%sx%s+50+50" % (crop_width, crop_height))
    # now trim much smaller image (makes big difference if high density/dpi image desired as per output_dpi)
    im.borderColor(u2utf8(bgcolour))
    im.border("1x1")
    if debug: print(u"Just about to trim")
    try:
        im.trim()
    except Exception, e:
        if debug: print(u"Failed with im.trim(). Orig error: %s" % lib.ue(e))
        return None
    if debug: print(u"Just trimmed")
    suffix = "" if i == 0 else "_%02i" % i
    img_made = "%s%s.png" % (img_pth_no_ext, suffix)
    if mg.PLATFORM == mg.WINDOWS:
        img_made = img_made.replace(u'"', u"'")
    if debug: print(u"img_made: %s" % img_made)
    im.write(u2utf8(img_made))
    return img_made

def pdf2img_pythonmagick(pdf_path, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Can use python-pythonmagick.
    Windows may crash with higher output_dpis e.g. 1200.
    """
    debug = False
    if DIAGNOSTIC: debug = True
    imgs_made = []
    n_pages = get_pdf_page_count(pdf_path)
    for i in range(n_pages):
        try:
            img_made = try_pdf_page_to_img_pythonmagick(pdf_path, i, 
                img_pth_no_ext, bgcolour, output_dpi)
        except Exception, e:
            raise Exception(u"Failed to convert PDF into image using "
                u"PythonMagick. Orig error: %s" % lib.ue(e))
        if debug: print(u"img_made: %s" % img_made)
        imgs_made.append(img_made)
    return imgs_made

def pdf2img_imagemagick(pdf_path, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Use ImageMagick directly side-stepping the Python wrapper.
    Requires user to have manually installed ImageMagick.
    """
    debug = False
    if DIAGNOSTIC: debug = True
    verbose = False
    imgs_made = []
    n_pages = get_pdf_page_count(pdf_path)
    for i in range(n_pages):
        orig_pdf = "%s[%s]" % (pdf_path, i)
        # Make small throwaway version to get size (cheap process to avoid slow process)
        suffix = "" if i == 0 else "_%02i" % i
        img_made = "%s%s.png" % (img_pth_no_ext, suffix)
        try:
            # Note - change density before setting input image otherwise 72 dpi 
            # no matter what you subsequently do with -density
            cmd = ('convert.exe -density %s -borderColor "%s" -border %s -trim '
                '"%s" "%s"' % (output_dpi, u2utf8(bgcolour), "1x1", 
                u2utf8(orig_pdf), img_made))
            retcode = subprocess.call(cmd, shell=True)
            if retcode < 0:
                raise Exception("%s was terminated by signal %s" % (cmd, 
                    retcode))
            else:
                if verbose: print("%s returned %s" % (cmd, retcode))
        except Exception, e:
            if debug: 
                print(u"Failed to read PDF into image. Did you manually install"
                    u" the ImageMagick package first? Orig error: %s" % 
                    lib.ue(e))
            break
        imgs_made.append(img_made)
    return imgs_made

def copy_output():
    wx.BeginBusyCursor()
    bi = wx.BusyInfo("Copying output ...")
    # act as if user selected print dpi and export as images
    export_status = {mg.CANCEL_EXPORT: False}
    sorted_names = os.listdir(mg.INT_COPY_IMGS_PATH)
    sorted_names.sort()
    for filename in sorted_names:
        delme = os.path.join(mg.INT_COPY_IMGS_PATH, filename)
        os.remove(delme)
    hdr, img_items, unused = get_hdr_and_items(mg.INT_REPORT_PATH, DIAGNOSTIC)
    msgs = [] # not used in this case
    export2imgs(hdr, img_items=img_items, temp_desktop_report_only=False, 
        report_path=mg.INT_REPORT_PATH, temp_desktop_path=mg.INT_COPY_IMGS_PATH,  
        output_dpi=PRINT_DPI, gauge_start_imgs=0, headless=False, 
        export_status=export_status, steps_per_img=GAUGE_STEPS, msgs=msgs, 
        progbar=None)
    sorted_names = os.listdir(mg.INT_COPY_IMGS_PATH)
    sorted_names.sort()
    # http://wiki.wxpython.org/ClipBoard
    wx.TheClipboard.Open()
    do = wx.FileDataObject()
    for filname in sorted_names:
        if filname.endswith(u".png"):
            imgname = os.path.join(mg.INT_COPY_IMGS_PATH, filname)
            do.AddFile(imgname)
    wx.TheClipboard.AddData(do)
    wx.TheClipboard.Close()
    bi.Destroy()
    lib.safe_end_cursor()
    