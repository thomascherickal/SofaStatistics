#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
GENERAL ********************
export2pdf(), export2spreadsheet(), and export2imgs() do the real work and can 
be scripted outside the GUI. Set headless = True when calling. export2imgs has 
the best doc string to read.

The starting point is always HTML. If a report, will have lots of individual 
items to extract and convert into images/pdfs and/or spreadsheet tables.

Splits HTML by divider SOFA puts between all chunks of content. Namely 
mg.OUTPUT_ITEM_DIVIDER.

IMAGES *********************

For images, there are two situations:

1) images that were created by matplotlib that are already created and were only 
linked to by the HTML. We just need to relocate a copy and rename these.

2) images which only exist when rendered by a web browser which can handle 
javascript and SVG.

For each split item, a separate HTML file must be made, rendered within 
wkhtmltopdf, and the PDF converted into an image.

Because we don't know the final size of the output image we have to start with 
an oversized version which is then autocropped down to the correct size. If we 
did this on the full-resolution image it would take far too long (cropping is a 
very computer-intensive process) so we use a different approach to get a cropped 
high-resolution image output. We make the very low-resolution version and then
read its dimension properties. We can use these to make a final output instead 
of having to crop down from an oversized version. Even though we are not using
autocropping to get the dimensions anymore we still need to use it. Because we 
are reading our dimensions from a low-resolution image there is a margin of 
error when translating to the high-resolution version so it is safest to add a 
slight bit of padding to the outside of our dimensions and then autocrop from 
there. Note - more padding required than might be expected for some reason. 
Anyway, still an expensive process but we are doing very little of it. 

SPLITTING OUTPUT ************

Use SOFA Python code to split output into individual HTML items (if a chart 
series we split these into individual charts). Each will have the massive HTML 
header (css and javascript etc) plus a tiny end bit (close body and html tags). 
Store the temp HTML output in the _internal folder.

Also split out any text in same order so that numbering can be sequential. Store 
names inside html original so we can name “001 - Gender by Ethnicity.png” etc.

http://www.imagemagick.org/Magick++/Image.html#Image%20Manipulation%20Methods
http://www.imagemagick.org/Usage/crop/#trim. A trick that works is to add a 
border of the colour you want to trim, then_ trim.

trim() -- Trim edges that are the background color from the image.

trimming is very slow at higher dpis so we can do a quick, dirty version at a 
lower dpi, get dimensions, and multiply by the PDF dpi/cheap dpi to get rough 
dimensions to crop.

For multipage images, use [idx] notation after .pdf
http://stackoverflow.com/questions/4809314/...
    ...imagemagick-is-converting-only-the-first-page-of-the-pdf
"""
import codecs
from collections import namedtuple
import os
import shutil
import subprocess
import sys

import pyPdf
import wx

import basic_lib as b
import my_globals as mg
import lib
import my_exceptions
import output

MAC_FRAMEWORK_PATH = os.path.join(os.path.split(os.path.dirname(__file__))[0],
    u"Frameworks") # where misc libraries will be (even if via soft link)
#print(MAC_FRAMEWORK_PATH)
HTML4PDF_FILE = u"html4pdf.html"
RAWPDF_FILE = u"raw.pdf"
PDF2IMG_FILE = u"pdf2img.pdf"
RAWPDF_PATH = os.path.join(mg.INT_PATH, RAWPDF_FILE)
PDF2IMG_PATH = os.path.join(mg.INT_PATH, PDF2IMG_FILE)
PDF_SIDE_MM = u"420" # any larger and they won't be able to display anywhere in one go anyway
try:
    EXE_TMP = sys._MEIPASS #@UndefinedVariable
except AttributeError:
    EXE_TMP = u""

output_item = namedtuple('output_item', 'title, content')


class Prog2console(object):
    def SetValue(self, value):
        print(u"Current progress: %s ..." % str(value).rjust(3))


def get_raw_html(report_path):
    """
    Get the BOM-cleaned HTML text for the specified report.
    """
    try:
        with codecs.open(report_path, "U", "utf-8") as f:
            raw_html = b.clean_boms(f.read())
            f.close()
    except IOError:
        raise Exception(u"Unable to get items from report file - it doesn't "
            u"exist yet.") # should only see this when running headless via a script - otherwise should be picked up by GUI-level validation.
    return raw_html

def get_split_html(report_path):
    """
    Get the report HTML text split by the standard divider 
    (e.g. <!-- _SOFASTATS_ITEM_DIVIDER -->).
    """
    raw_html = get_raw_html(report_path)
    if not raw_html:
        raise Exception(u"No raw html found in report file.")
    split_html = raw_html.split(mg.OUTPUT_ITEM_DIVIDER)
    return split_html

def get_hdr_and_items(report_path, diagnostic=False):
    """
    Read (presumably) HTML text from report. Split by main output divider, 
    discarding the first (assumed to be the html header).
    
    Within each item, split off the content above the item (if any) e.g. a 
    visual line divider, comments on filtering applied etc.
    
    Then split by title splitter - chunk 0 = actual content, chunk 1 = title to 
    use when saving the item. Items are item.title, item.content.
    
    All items can be turned into images. 
    
    Only table reports can be turned into spreadsheet tables.
    
    Called once, even if exporting 
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
        if mg.REPORT_TABLE_START in item.content: # only some items can become table items
            tbl_items.append(item)
    if hdr is None:
        raise Exception(u"Unable to extract hdr from report file.")
    return hdr, img_items, tbl_items

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
        progbar = Prog2console()
    if mg.OVERRIDE_FOLDER:
        pdf_root = mg.OVERRIDE_FOLDER
    pdf_path = os.path.join(pdf_root, pdf_name)
    html2pdf(html_path=report_path, pdf_path=pdf_path, as_pre_img=False)
    gauge2show = gauge_start_pdf + steps_per_pdf
    progbar.SetValue(gauge2show)
    return pdf_path

def copy_existing_img(item, report_path, imgs_path, headless=False, 
        progbar=None):
    """
    Merely copying an existing image
    """
    export_report = not (report_path == mg.INT_REPORT_PATH)
    src, dst = lib.get_src_dst_preexisting_img(export_report, imgs_path, 
        item.content)
    try:
        shutil.copyfile(src, dst)
    except Exception, e:
        msg = (u"Unable to copy existing image file. Orig error: %s" % 
            b.ue(e))
        if not headless:
            wx.MessageBox(msg)
        else:
            print(msg)
        if progbar: progbar.SetValue(0)
        raise my_exceptions.ExportCancel

def html2img(i, item, hdr, ftr, imgs_path, html4pdf_path, img_pth_no_ext,
        output_dpi):
    """
    Key bits htmltopdf() and pdf2img()
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    full_content_html = u"\n".join([hdr, item.content, ftr])
    with codecs.open(html4pdf_path, "w", "utf-8") as f:
        f.write(full_content_html)
        f.close()
    html2pdf(html_path=html4pdf_path, pdf_path=PDF2IMG_PATH, 
        as_pre_img=True)
    #wx.MessageBox(img_pth_no_ext)
    if debug: print(img_pth_no_ext)
    imgs_made = pdf2img(pdf_path=PDF2IMG_PATH, 
        img_pth_no_ext=img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=output_dpi)
    if debug: print(u"Just made image(s) %s:\n%s" % 
        (i, u",\n".join(imgs_made)))

def export2img(i, item, hdr, ftr, report_path, imgs_path, html4pdf_path, 
        output_dpi, headless=False, export_status=None, progbar=None):
    # give option of backing out
    if not headless: wx.Yield()
    if export_status[mg.CANCEL_EXPORT]:
        if progbar: progbar.SetValue(0)
        raise my_exceptions.ExportCancel
    img_name_no_ext = "%04i_%s" % (i, item.title.replace(u" - ", u"_").
        replace(u" ", u"_").replace(u":", u"_"))
    img_pth_no_ext = os.path.join(imgs_path, img_name_no_ext)
    if mg.IMG_SRC_START in item.content:
        copy_existing_img(item, report_path, imgs_path, headless, progbar)
    else:
        html2img(i, item, hdr, ftr, imgs_path, html4pdf_path, img_pth_no_ext,
            output_dpi)

def export2imgs(hdr, img_items, save2report_path, report_path, 
        alternative_path, output_dpi, gauge_start_imgs=0, headless=False, 
        export_status=None, steps_per_img=None, msgs=None, progbar=None):
    """
    hdr -- HTML header with css, javascript etc. Make hdr (and img_items) with 
    get_hdr_and_items()
    
    img_items -- list of data about images. Make img_items (and hdr) with a call 
    to get_hdr_and_items()
    
    save2report_path -- boolean. True when exporting a report; False 
    when exporting or coping current output.
    
    report_path -- needed whether or not exporting entire report. Need to know
    location so can make pdf in report folder - our html relies on the 
    Javascript files and images being in the correct relative location.
    e.g. /home/g/Documents/sofastats/reports/sofa_use_only_report.htm
    
    Will put images here if save2report_path is True (and there is no 
    OVERRIDE_FOLDER set).
    
    alternative_path -- images will only go here if save2report_path is False 
    (and there is no OVERRIDE_FOLDER set). Don't include a trailing slash.
    
    output_dpi -- e.g. 300
    
    gauge_start_imgs -- used when in non-headless mode so the progress bar can 
    show progress through exporting images, tables, and as pdf as a single total 
    job. Can also be used when in headless mode.
    
    headless -- Set to True to run from a script without GUI input.
    
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
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    output_dpi = 60 if debug else output_dpi
    if save2report_path:
        imgs_path = output.ensure_imgs_path(report_path, 
            ext=u"_exported_images")
    else:
        imgs_path = alternative_path
    if mg.OVERRIDE_FOLDER:
        imgs_path = mg.OVERRIDE_FOLDER
    rpt_root = os.path.split(report_path)[0]
    html4pdf_path = os.path.join(rpt_root, HTML4PDF_FILE) # must be in reports path so JS etc all available
    n_imgs = len(img_items)
    long_time = ((n_imgs > 30 and output_dpi == mg.SCREEN_DPI) 
        or (n_imgs > 10 and output_dpi == mg.PRINT_DPI) 
        or (n_imgs > 2 and output_dpi == mg.HIGH_QUAL_DPI))
    if long_time and not headless:
        if wx.MessageBox(_("The report has %s images to export at %s dpi. "
                "Do you wish to export at this time?") % (n_imgs, output_dpi), 
                caption=_("SLOW EXPORT PREDICTED"), style=wx.YES_NO) == wx.NO:
            if progbar: progbar.SetValue(0)
            raise my_exceptions.ExportCancel
    gauge2show = gauge_start_imgs
    if progbar: progbar.SetValue(gauge2show)
    ftr = u"</body></html>"
    for i, item in enumerate(img_items, 1): # the core - where images are actually exported
        export2img(i, item, hdr, ftr, report_path, imgs_path, html4pdf_path, 
            output_dpi, headless, export_status, progbar)
        gauge2show += steps_per_img
        if progbar: progbar.SetValue(gauge2show)
    if save2report_path:
        img_saved_msg = (_(u"Images have been saved to: \"%s\"") % imgs_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        img_saved_msg = (u"Images have been saved to your desktop in the "
            u"\"%s\" folder" % foldername)
    if not headless:
        msgs.append(img_saved_msg)

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
    that e.g. wkhtmltopdf. Not tested myself (the real cause was the frozen vs 
    popen issue) but see http://code.google.com/p/wkhtmltopdf/issues/...
    ...detail?id=825. It uses stdout to actually output the PDF - a good feature 
    but possibly stuffs up reading stdout for message? And pdftk the same?
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
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
                EXE_TMP, width, height, rel_url, pdf_path))
        elif mg.PLATFORM == mg.MAC:
            cmd_make_pdf = (u'cd "%s" && "%s/wkhtmltopdf" %s %s "%s" "%s"'
                % (cd_path, MAC_FRAMEWORK_PATH, width, height, rel_url, pdf_path))
        elif mg.PLATFORM == mg.LINUX:
            cmd_make_pdf = (u'wkhtmltopdf %s %s "%s" "%s" ' % (width, height, 
                url, pdf_path))
        else:
            raise Exception(u"Encountered an unexpected platform!")
        # wkhtmltopdf uses stdout to actually output the PDF - a good feature but stuffs up reading stdout for message
        if debug: print(u"cmd_make_pdf: %s" % cmd_make_pdf)
        shellit(cmd_make_pdf)
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
                (final_pdf_root, EXE_TMP, raw_pdf, final_pdf_file))
        elif mg.PLATFORM == mg.MAC:
            cmd_fix_pdf = (u'"%s/pdftk" "%s" output "%s" ' % (MAC_FRAMEWORK_PATH, 
                raw_pdf, final_pdf))
        elif mg.PLATFORM == mg.LINUX:
            cmd_fix_pdf = (u'pdftk "%s" output "%s" ' % (raw_pdf, final_pdf))
        else:
            raise Exception(u"Encountered an unexpected platform!")
        if debug: print(u"cmd_fix_pdf: %s" % cmd_fix_pdf)
        shellit(cmd_fix_pdf)
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
    
def u2utf8(unicode_txt):
    # http://stackoverflow.com/questions/1815427/...
    #     ...how-to-pass-an-unicode-char-argument-to-imagemagick
    return unicode_txt.encode("utf-8")

def pdf2img(pdf_path, img_pth_no_ext, bgcolour=mg.BODY_BACKGROUND_COLOUR, 
            output_dpi=300):
    if mg.PLATFORM == mg.MAC: # if I have trouble getting pythonmagick installed
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
            u"Orig error: %s" % (cmd_pdf2png, b.ue(e)))
    
def try_pdf_page_to_img_pythonmagick(pdf_path, i, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Return img_made or None. Returning None lets calling function break loop 
        through pages.
    """
    import PythonMagick as pm
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
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
                    u"Orig error: %s" % b.ue(e))
            else:
                # Not a problem if fails to read page 2 etc if not multipage
                if debug: 
                    print(u"Failed to convert page idx %s PDF (%s) into image. "
                        u"Probably not a multipage PDF. Orig error: %s" % (i, 
                        pdf_path, b.ue(e)))
                return None
            
        try: # can read directly from PDF because IM knows where GS is
            im.read(u2utf8(cheap_dpi_png2read_path)) # will fail on page idx 1 if not multipage PDF
        except Exception, e:
            raise Exception(u"Failed to read PDF (%s) into image. "
                u"Orig error: %s" % (pdf_path, b.ue(e)))
    else:
        try: # can read directly from PDF because IM knows where GS is
            im.read(u2utf8(orig_pdf)) # will fail on page idx 1 if not multipage PDF
        except Exception, e:
            if i == 0:
                raise Exception(u"Failed to read PDF (%s) into image. "
                    u"Orig error: %s" % (pdf_path, b.ue(e)))
            else:
                # Not a problem if fails to read page 2 etc if not multipage
                if debug: 
                    print(u"Failed to read page idx %s PDF (%s) into image. "
                        u"Probably not a multipage PDF. Orig error: %s" % (i, 
                        pdf_path, b.ue(e)))
                return None
    if debug: print(u"About to set border colour for image")
    im.borderColor(u2utf8(bgcolour))
    if debug: print(u"Just set border colour for image")
    im.border("1x1")
    try:
        im.trim() # sometimes the PDF has an empty page at the end. Trim hates that and dies even though we don't need that page as an image.
    except Exception, e:
        if debug: print(u"Failed with im.trim(). Orig error: %s" % b.ue(e))
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
        if debug: print(u"Failed with im.trim(). Orig error: %s" % b.ue(e))
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
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    imgs_made = []
    n_pages = get_pdf_page_count(pdf_path)
    for i in range(n_pages):
        try:
            img_made = try_pdf_page_to_img_pythonmagick(pdf_path, i, 
                img_pth_no_ext, bgcolour, output_dpi)
        except Exception, e:
            raise Exception(u"Failed to convert PDF into image using "
                u"PythonMagick. Orig error: %s" % b.ue(e))
        if debug: print(u"img_made: %s" % img_made)
        imgs_made.append(img_made)
    return imgs_made

def pdf2img_imagemagick(pdf_path, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Use ImageMagick directly side-stepping the Python wrapper.
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
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
            if mg.PLATFORM == mg.WINDOWS:
                convert = u"convert.exe"
            elif mg.PLATFORM == mg.MAC:
                """
                Assumes the framework path is the first path in PATH, so we can
                just reference 'gs' in delegates.xml without a fully qualified
                file name, AND that the environment variable
                MAGICK_CONFIGURE_PATH has been set to the framework path so
                that imagemagick convert can find delegates.xml (and colors.xml)
                and thus make use of the largely self-contained gs
                (ghostscript) binary there.

                These changes don't persist it seems so OK to call multiple
                times here.
                """
                #import os
                #print(os.environ["PATH"])
                convert = (u'export PATH="%(framework_path)s:${PATH}" '
                    u'&& export MAGICK_CONFIGURE_PATH="%(framework_path)s" '
                    u'&& "%(framework_path)s/convert"' 
                    % {"framework_path": MAC_FRAMEWORK_PATH})
            elif mg.PLATFORM == mg.LINUX:
                convert = u"convert"
            else:
                raise Exception(u"Encountered an unexpected platform!")
            cmd = ('%s -density %s -borderColor "%s" -border %s -trim '
                '"%s" "%s"' % (convert, output_dpi, u2utf8(bgcolour), "1x1", 
                u2utf8(orig_pdf), img_made))
            retcode = subprocess.call(cmd, shell=True)
            if retcode < 0:
                raise Exception("%s was terminated by signal %s" % (cmd, 
                    retcode))
            else:
                if verbose: print("%s returned %s" % (cmd, retcode))
        except Exception, e:
            wx.MessageBox(u"Unable to convert PDF into image. Please pass on "
                u"this error message to the developer at %s. Orig error: %s" % 
                (mg.CONTACT, b.ue(e)))
            print(u"Failed to read PDF into image. Orig error: %s" % b.ue(e))
            break
        imgs_made.append(img_made)
    return imgs_made

def export2spreadsheet(hdr, tbl_items, save2report_path, report_path, 
        alternative_path, gauge_start_tbls=0, headless=False, 
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
    gauge2show = gauge_start_tbls + (steps_per_tbl*n_tbls)
    progbar.SetValue(gauge2show)

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
    hdr, img_items, unused = get_hdr_and_items(mg.INT_REPORT_PATH, 
        mg.EXPORT_IMAGES_DIAGNOSTIC)
    msgs = [] # not used in this case
    export2imgs(hdr, img_items=img_items, save2report_path=False, 
        report_path=mg.INT_REPORT_PATH, alternative_path=mg.INT_COPY_IMGS_PATH,  
        output_dpi=mg.PRINT_DPI, gauge_start_imgs=0, headless=False, 
        export_status=export_status, steps_per_img=mg.EXPORT_IMG_GAUGE_STEPS, 
        msgs=msgs, progbar=None)
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
