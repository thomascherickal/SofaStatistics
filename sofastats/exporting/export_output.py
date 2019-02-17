from collections import namedtuple
import subprocess
import sys

import wx

from .. import basic_lib as b
from .. import my_globals as mg

try:
    EXE_TMP = sys._MEIPASS #@UndefinedVariable
except AttributeError:
    EXE_TMP = ''

output_item = namedtuple('output_item', 'title, content')


class Prog2console:
    def SetValue(self, value):
        print(f'Current progress: {value:>3} ...')


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
    if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = False
    verbose = False
    if debug: 
        if verbose:
            try:
                wx.MessageBox(cmd)
            except Exception:  ## e.g. headless
                print(cmd)
        else:
            print(cmd)
    encoding2use = sys.getfilesystemencoding()  ## on win, mbcs
    retcode = subprocess.call(cmd.encode(encoding2use), shell=shell)
    if retcode < 0:
        msg = f'{cmd} was terminated by signal {retcode}'
        if debug: print(msg)
        raise Exception(msg)
    else:
        if debug and verbose: print(f'{cmd} returned {retcode}')

def get_split_html(report_path):
    """
    Get the report HTML text split by the standard divider
    (e.g. <!-- _SOFASTATS_ITEM_DIVIDER -->).
    """
    raw_html = b.get_bom_free_contents(fpath=report_path)  ## should only see an exception here when running headless via a script - otherwise should be picked up by GUI-level validation.
    if not raw_html:
        raise Exception('No raw html found in report file.')
    split_html = raw_html.split(mg.OUTPUT_ITEM_DIVIDER)
    return split_html

def get_hdr_and_items(report_path, *, diagnostic=False):
    """
    Read (presumably) HTML text from report. Split by main output divider,
    discarding the first (assumed to be the html header).

    Within each item, split off the content above the item (if any) e.g. a
    visual line divider, comments on filtering applied etc.

    Then split by title splitter - chunk 0 = actual content, chunk 1 = title to
    use when saving the item. Items are item.title, item.content.

    All items can be turned into images.

    Only table reports can be turned into spreadsheet tables.

    Called once, even if exporting.
    """
    debug = False
    if diagnostic: debug = True
    verbose = False
    img_items = []
    tbl_items = []
    split_html = get_split_html(report_path)
    if not split_html:
        raise Exception('No split html')
    n_items = len(split_html) - 1  ## never content at end - just html footer
    if n_items == 0: n_items = 1  ## the normality chart is a special case where there is only one item
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
            break  ## never content at end - just html footer
        split_by_div = html.split(mg.VISUAL_DIVIDER_BEFORE_THIS)
        if debug and verbose: print(split_by_div)
        if len(split_by_div) == 1:
            ex_vis_div = split_by_div[0]
        else:
            ex_vis_div = split_by_div[1]
        if i == 1:  ## get the header
            hdr = (split_by_div[0].split('<body ')[0] + f'\n{mg.BODY_START}')
            if debug: print('\nEnd of hdr:\n' + hdr[-60:])
        if debug and verbose: print(ex_vis_div)
        full_content = ex_vis_div.split(mg.ITEM_TITLE_START)
        n_content = len(full_content)
        if n_content == 2:
            content, title_comment = full_content
        else:
            raise Exception('Should split into two parts - content and title '
                f'comment. Instead split into {n_content} parts. Did you forget'
                ' to use append_divider?')
        if debug and verbose:
            print(f'\n\n{title_comment}\n{content[:30]} ...\n{content[-30:]}')
        title = title_comment[4:-3]
        if debug: print(title)
        item = output_item(title, content)
        img_items.append(item)  ## all items can be turned into images (whether a chart or a table etc.
        if mg.REPORT_TABLE_START in item.content:  ## only some items can become table items
            tbl_items.append(item)
    if hdr is None:
        raise Exception('Unable to extract hdr from report file.')
    return hdr, img_items, tbl_items
