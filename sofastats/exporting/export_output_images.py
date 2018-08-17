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
import os
import shutil
from subprocess import Popen, PIPE

from PIL import Image, ImageChops
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from sofastats.exporting import export_output
from sofastats.exporting import export_output_pdfs
from sofastats import output

HTML4PDF_FILE = 'html4pdf.html'
PDF2IMG_FILE = 'pdf2img.pdf'
PDF2IMG_PATH = os.path.join(mg.INT_PATH, PDF2IMG_FILE)

img_creation_problem = False


class ExportImage:

    @staticmethod
    def export2imgs(hdr, img_items, report_path,
            alternative_path, output_dpi, gauge_start_imgs=0,
            export_status=None, steps_per_img=None, msgs=None, progbar=None,
            save2report_path=True, headless=False, multi_page_items=True):
        """
        hdr -- HTML header with css, javascript etc. Make hdr (and img_items)
        with get_hdr_and_items()

        img_items -- list of data about images. Make img_items (and hdr) with a
        call to get_hdr_and_items()

        save2report_path -- boolean. True when exporting a report; False
        when exporting or coping current output.

        report_path -- needed whether or not exporting entire report. Need to
        know location so can make pdf in report folder - our html relies on the
        Javascript files and images being in the correct relative location. e.g.
        /home/g/Documents/sofastats/reports/sofa_use_only_report.htm

        Will put images here if save2report_path is True (and there is no
        OVERRIDE_FOLDER set).

        alternative_path -- images will only go here if save2report_path is
        False (and there is no OVERRIDE_FOLDER set). Don't include a trailing
        slash.

        output_dpi -- e.g. 300

        gauge_start_imgs -- used when in non-headless mode so the progress bar
        can show progress through exporting images, tables, and as pdf as a
        single total job. Can also be used when in headless mode.

        headless -- Set to True to run from a script without GUI input.

        export_status -- only used to check if a user has cancelled the export
        via the GUI.

        steps_per_img -- relevant to GUI progress bar.

        msgs -- list of messages to display in GUI later.

        progbar -- so we can display progress as we go in GUI. If set to None,
        will send progress to stdout instead.
        """
        debug = False
        if headless:
            if ((export_status, steps_per_img, msgs, progbar)
                    != (None, None, None, None)):
                raise Exception(
                    "If running headless, don't set the GUI-specific settings")
            export_status = {mg.CANCEL_EXPORT: False}
            steps_per_img = 1  ## leave msgs as default of None
            progbar = export_output.Prog2console()
        if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
        output_dpi = 60 if debug else output_dpi
        if save2report_path:
            imgs_path = output.ensure_imgs_path(
                report_path, ext='_exported_images')
        else:
            imgs_path = alternative_path
        if mg.OVERRIDE_FOLDER:
            imgs_path = mg.OVERRIDE_FOLDER
        if debug: print(imgs_path)
        rpt_root = os.path.split(report_path)[0]
        html4pdf_path = os.path.join(rpt_root, HTML4PDF_FILE)  ## must be in reports path so JS etc all available
        n_imgs = len(img_items)
        long_time = ((n_imgs > 30 and output_dpi == mg.SCREEN_DPI) 
            or (n_imgs > 10 and output_dpi == mg.PRINT_DPI) 
            or (n_imgs > 2 and output_dpi == mg.HIGH_QUAL_DPI))
        if long_time and not headless:
            msg = _('The report has %s images to export at %s dpi. '
                'Do you wish to export at this time?') % (n_imgs, output_dpi)
            if wx.MessageBox(msg, caption=_('SLOW EXPORT PREDICTED'),
                    style=wx.YES_NO) == wx.NO:
                if progbar: progbar.SetValue(0)
                raise my_exceptions.ExportCancel
        gauge2show = min(gauge_start_imgs, mg.EXPORT_IMG_GAUGE_STEPS)
        if progbar: progbar.SetValue(gauge2show)
        ftr = '</body></html>'
        for i, item in enumerate(img_items, 1):  ## the core - where images are actually exported
            ExportImage._export2img(i, item, hdr, ftr, report_path, imgs_path,
                html4pdf_path, output_dpi, export_status, progbar,
                headless=headless, multi_page_items=multi_page_items)
            gauge2show += steps_per_img
            if progbar: progbar.SetValue(gauge2show)
        if save2report_path:
            img_saved_msg = (
                _('Images have been saved to: \"%s\".') % imgs_path)
        else:
            foldername = os.path.split(alternative_path)[1]
            img_saved_msg = ('Images have been saved to your desktop in the '
                '\'%s\' folder.' % foldername)
        if img_creation_problem:
            img_saved_msg += (('\n\nThere may have been a problem making some '
                'of the images - please contact the developer at %s for '
                'assistance') % mg.CONTACT)
        if not headless:
            msgs.append(img_saved_msg)

    @staticmethod
    def _copy_existing_img(item, report_path, imgs_path, progbar=None, *,
            headless=False):
        """
        Merely copying an existing image
        """
        export_report = not (report_path == mg.INT_REPORT_PATH)
        src, dst = lib.OutputLib.get_src_dst_preexisting_img(
            export_report, imgs_path, item.content)
        try:
            shutil.copyfile(src, dst)
        except Exception as e:
            msg = (f'Unable to copy existing image file. Orig error: {b.ue(e)}')
            if not headless:
                wx.MessageBox(msg)
            else:
                print(msg)
            if progbar: progbar.SetValue(0)
            raise my_exceptions.ExportCancel

    @staticmethod
    def _html2img(i, item, hdr, ftr, html4pdf_path, img_pth_no_ext, output_dpi,
            *, multi_page_items=True):
        """
        Key bits htmltopdf() and pdf2img()
        """
        debug = False
        if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
        full_content_html = '\n'.join([hdr, item.content, ftr])
        with open(html4pdf_path, 'w', encoding='utf-8') as f:
            f.write(full_content_html)
        export_output_pdfs.html2pdf(
            html_path=html4pdf_path, pdf_path=PDF2IMG_PATH, as_pre_img=True)
        #wx.MessageBox(img_pth_no_ext)
        if debug: print(img_pth_no_ext)
        imgs_made = Pdf2Img.pdf2img(pdf_path=PDF2IMG_PATH,
            img_pth_no_ext=img_pth_no_ext, bgcolour=mg.BODY_BACKGROUND_COLOUR,
            output_dpi=output_dpi, multi_page_items=multi_page_items)
        if debug:
            list_imgs_made = ',\n'.join(imgs_made)
            print(f'Just made image(s) {i}\n{list_imgs_made}')

    @staticmethod
    def _export2img(i, item, hdr, ftr, report_path, imgs_path, html4pdf_path,
            output_dpi, export_status=None, progbar=None, *,
            headless=False, multi_page_items=True):
        ## give option of backing out
        if not headless: wx.Yield()
        if export_status[mg.CANCEL_EXPORT]:
            if progbar: progbar.SetValue(0)
            raise my_exceptions.ExportCancel
        title = lib.get_safer_name(item.title)
        img_name_no_ext = f'{i:04}_{title}'
        img_pth_no_ext = os.path.join(imgs_path, img_name_no_ext)
        if mg.IMG_SRC_START in item.content:
            ExportImage._copy_existing_img(item, report_path, imgs_path,
                progbar, headless=headless)
        else:
            ExportImage._html2img(i, item, hdr, ftr, html4pdf_path,
                img_pth_no_ext, output_dpi, multi_page_items=multi_page_items)


def copy_output():
    wx.BeginBusyCursor()
    bi = wx.BusyInfo('Copying output ...')
    ## act as if user selected print dpi and export as images
    export_status = {mg.CANCEL_EXPORT: False}
    sorted_names = os.listdir(mg.INT_COPY_IMGS_PATH)
    sorted_names.sort()
    for filename in sorted_names:
        delme = os.path.join(mg.INT_COPY_IMGS_PATH, filename)
        os.remove(delme)
    hdr, img_items, unused = export_output.get_hdr_and_items(
        mg.INT_REPORT_PATH, mg.EXPORT_IMAGES_DIAGNOSTIC)
    msgs = []  ## not used in this case
    ExportImage.export2imgs(hdr, img_items=img_items,
        report_path=mg.INT_REPORT_PATH, alternative_path=mg.INT_COPY_IMGS_PATH,
        output_dpi=mg.PRINT_DPI, gauge_start_imgs=0,
        export_status=export_status, steps_per_img=mg.EXPORT_IMG_GAUGE_STEPS,
        msgs=msgs, progbar=None, save2report_path=False, headless=False)
    sorted_names = os.listdir(mg.INT_COPY_IMGS_PATH)
    sorted_names.sort()
    ## http://wiki.wxpython.org/ClipBoard
    wx.TheClipboard.Open()
    do = wx.FileDataObject()
    for filname in sorted_names:
        if filname.endswith('.png'):
            imgname = os.path.join(mg.INT_COPY_IMGS_PATH, filname)
            do.AddFile(imgname)
    wx.TheClipboard.AddData(do)
    wx.TheClipboard.Close()
    bi.Destroy()
    lib.GuiLib.safe_end_cursor()


class Pdf2Img:

    @staticmethod
    def _check_img_made(img_path):
        """
        Needed because call to make image can fail silently. We want to capture
        any failures so we can alter message to user about success of making
        images.
        """
        global img_creation_problem
        img_made = os.path.exists(img_path)
        if not img_made:
            img_creation_problem = True
        return img_made

    @staticmethod
    def _u2utf8(unicode_txt):
        ## http://stackoverflow.com/questions/1815427/...
        ##     ...how-to-pass-an-unicode-char-argument-to-imagemagick
        return unicode_txt.encode('utf-8')

    @staticmethod
    def trim(img_path):
        """
        Assumes starting point has white with a black border and surrounding
        transparency. This is what convert seems to be making from its PDF
        input SOFA supplies it. The goal is to trim through all that as close
        through the white as possible.

        The following settings allow 1200dpi images to be output in
        /etc/ImageMagick-6/policy.xml (Ubuntu Linux):

        <policy domain="resource" name="memory" value="1GiB"/>
        <policy domain="resource" name="map" value="1GiB"/>
        <policy domain="resource" name="width" value="256KP"/>
        <policy domain="resource" name="height" value="256KP"/>
        <policy domain="resource" name="area" value="256MB"/>
        <policy domain="resource" name="disk" value="10GiB"/>
        """
        img_raw = Image.open(img_path, 'r')
        ## crop off transparency first
        img_no_trans = img_raw.crop(img_raw.getbbox())
        ## trim off 1px black boundary "helpfully" added when convert makes png
        bb = img_no_trans.getbbox()
        img_no_border = img_no_trans.crop((1, 1, bb[2]-2, bb[3]-2))  ## l, t, r, b
        img_no_border = img_no_border.convert('RGBA')  ## starts as P but even if both are P doesn't work - both seem to need to be RGBA
        ## trim white off by getting bbox for image which is diff of existing
        ## and one same size but completely of the colour being trimmed
        bg = Image.new('RGBA', img_no_border.size, 'white')
        diff = ImageChops.difference(img_no_border, bg)
        bbox = diff.getbbox()
        img_trimmed = img_no_trans.crop(bbox)
        img_trimmed.save(img_path)

    @staticmethod
    def _get_convert(platform):
        if platform == mg.WINDOWS:
            convert = 'convert.exe'
        elif platform == mg.MAC:
            """
            Assumes the framework path is the first path in PATH, so we
            can just reference 'gs' in delegates.xml without a fully
            qualified file name, AND that the environment variable
            MAGICK_CONFIGURE_PATH has been set to the framework path so
            that imagemagick convert can find delegates.xml (and
            colors.xml) and thus make use of the largely self-contained
            gs (ghostscript) binary there.

            These changes don't persist it seems so OK to call multiple
            times here.
            """
            #import os
            #print(os.environ["PATH"])
            framework_path = mg.MAC_FRAMEWORK_PATH
            convert = (f'export PATH="{framework_path}:${{PATH}}" '
                f'&& export MAGICK_CONFIGURE_PATH="{framework_path}" '
                f'&& "{framework_path}/convert"')
        elif platform == mg.LINUX:
            convert = 'convert'
        else:
            raise Exception('Encountered an unexpected platform!')
        return convert

    @staticmethod
    def pdf2img(pdf_path, img_pth_no_ext, bgcolour=mg.BODY_BACKGROUND_COLOUR,
            output_dpi=300, *, multi_page_items=True):
        """
        Wanted to use pythonmagick wrapper instead of ImageMagick directly but
        too much grief setting up on OSX.
        """
        debug = False
        verbose = False
        if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
        imgs_made = []
        n_pages = export_output_pdfs.get_pdf_page_count(pdf_path)
        for i in range(n_pages):
            if not multi_page_items and i > 0:
                break
            orig_pdf = f'{pdf_path}[{i}]'
            ## Make small throw-away version to get size (cheap process to avoid slow process)
            suffix = '' if i == 0 else f'_{i:02}'
            img_name = f'{img_pth_no_ext}{suffix}.png'
            ## Note - change density before setting input image otherwise 72 dpi
            ## no matter what you subsequently do with -density
            convert = Pdf2Img._get_convert(mg.PLATFORM)
            cmd = (f'{convert} -density {output_dpi} '
                   f'-borderColor "{Pdf2Img._u2utf8(bgcolour)}" -border 1x1 '
                   f'-trim "{Pdf2Img._u2utf8(orig_pdf)}" "{img_name}"')
            if debug: print(cmd)
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
            output, err = p.communicate()
            if err:
                if ('cache resources exhausted' in err
                        or 'Image width exceeds user limit' in err):
                    wx.MessageBox('Unable to make these images at this '
                        f'resolution ({output_dpi} dpi) by converting from PDF '
                        'version. Please try again at a lower resolution.'
                        '\n\nOrig error: {err}')
                else:
                    wx.MessageBox('Unable to make these images successfully.'
                        f'\n\nOrig error: {err}')
                if debug and verbose:
                    print(f'{cmd} returned {p.returncode} with error {err}')
                break
            if Pdf2Img._check_img_made(img_path=img_name):
                Pdf2Img.trim(img_name)
                imgs_made.append(img_name)
            else:
                raise Exception('Unable to make these images at this resolution'
                    f' ({output_dpi} dpi). Please try again at a lower '
                    'resolution.')
        return imgs_made
