#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
GENERAL ********************
export2imgs() does the real work and can be scripted outside the GUI. Set
headless = True when calling. export2imgs has the best doc string to read.

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
import os
import shutil
import subprocess

import wx

import basic_lib as b
import my_globals as mg
import lib
import my_exceptions
import export_output
import export_output_pdfs
import output

HTML4PDF_FILE = u"html4pdf.html"
PDF2IMG_FILE = u"pdf2img.pdf"
PDF2IMG_PATH = os.path.join(mg.INT_PATH, PDF2IMG_FILE)

img_creation_problem = False

def copy_existing_img(item, report_path, imgs_path, headless=False, 
        progbar=None):
    """
    Merely copying an existing image
    """
    export_report = not (report_path == mg.INT_REPORT_PATH)
    src, dst = lib.OutputLib.get_src_dst_preexisting_img(export_report,
        imgs_path, item.content)
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
    export_output_pdfs.html2pdf(html_path=html4pdf_path, pdf_path=PDF2IMG_PATH, 
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
    img_name_no_ext = "%04i_%s" % (i, lib.get_safer_name(item.title))
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
        progbar = export_output.Prog2console()
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    output_dpi = 60 if debug else output_dpi
    if save2report_path:
        imgs_path = output.ensure_imgs_path(report_path, 
            ext=u"_exported_images")
    else:
        imgs_path = alternative_path
    if mg.OVERRIDE_FOLDER:
        imgs_path = mg.OVERRIDE_FOLDER
    if debug: print(imgs_path)
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
    gauge2show = min(gauge_start_imgs, mg.EXPORT_IMG_GAUGE_STEPS)
    if progbar: progbar.SetValue(gauge2show)
    ftr = u"</body></html>"
    for i, item in enumerate(img_items, 1): # the core - where images are actually exported
        export2img(i, item, hdr, ftr, report_path, imgs_path, html4pdf_path, 
            output_dpi, headless, export_status, progbar)
        gauge2show += steps_per_img
        if progbar: progbar.SetValue(gauge2show)
    if save2report_path:
        img_saved_msg = (_(u"Images have been saved to: \"%s\".") % imgs_path)
    else:
        foldername = os.path.split(alternative_path)[1]
        img_saved_msg = (u"Images have been saved to your desktop in the "
            u"\"%s\" folder." % foldername)
    if img_creation_problem:
        img_saved_msg += (u"\n\nThere may have been a problem making some of "
            u"the images - please contact the developer at %s for assistance" %
            mg.CONTACT)
    if not headless:
        msgs.append(img_saved_msg)
    
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
        u'-dLastPage=%(pg)s "%(pdf_path)s"' % 
        {u"exe_tmp": export_output.EXE_TMP, u"png2make": png2read_path,
         u"dpi": dpi, u"pg": i+1, u"pdf_path": pdf_path})
    try:
        export_output.shellit(cmd_pdf2png)
    except Exception, e:
        raise Exception(u"pdf2png_ghostscript command failed: %s. "
            u"Orig error: %s" % (cmd_pdf2png, b.ue(e)))
    
def try_pdf_page_to_img_pythonmagick(pdf_path, i, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    If a single-page PDF will always be an exception when trying to make a non-
    existent page 2 into an image. But we (apparently) need to try and fail to
    know when to stop. Failing to make a first page, on the other hand, is
    always an error. Clearly, we don't return an image_made string if we didn't
    actually make an image so we return None instead.
    
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

def check_img_made(img_path):
    """
    Needed because call to make image can fail silently. We want to capture any
    failures so we can alter message to user about success of making images.
    """
    global img_creation_problem
    if not os.path.exists(img_path):
        img_creation_problem = True
        

def pdf2img_pythonmagick(pdf_path, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Can use python-pythonmagick.
    Windows may crash with higher output_dpis e.g. 1200.
    """
    debug = False
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    imgs_made = []
    n_pages = export_output_pdfs.get_pdf_page_count(pdf_path) # may include blank page at end
    for i in range(n_pages):
        try:
            img_made = try_pdf_page_to_img_pythonmagick(pdf_path, i, 
                img_pth_no_ext, bgcolour, output_dpi)
            if img_made is None:
                break # not a content page - just a trailing empty page
        except Exception, e:
            raise Exception(u"Failed to convert PDF into image using "
                u"PythonMagick. Orig error: %s" % b.ue(e))
        if debug: print(u"img_made: %s" % img_made)
        check_img_made(img_path=img_made)
        imgs_made.append(img_made)
    return imgs_made

def pdf2img_imagemagick(pdf_path, img_pth_no_ext, 
        bgcolour=mg.BODY_BACKGROUND_COLOUR, output_dpi=300):
    """
    Use ImageMagick directly side-stepping the Python wrapper.
    """
    debug = False # not used at present but all wired up ready
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
    if debug: pass
    verbose = False
    imgs_made = []
    n_pages = export_output_pdfs.get_pdf_page_count(pdf_path)
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
                    % {"framework_path": mg.MAC_FRAMEWORK_PATH})
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
        check_img_made(img_path=img_made)
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
    hdr, img_items, unused = export_output.get_hdr_and_items(mg.INT_REPORT_PATH, 
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
    lib.GuiLib.safe_end_cursor()
