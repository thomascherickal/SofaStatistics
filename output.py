#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is mostly concerned with the html displayed as output, the scripts 
written to produce it, and the display of it.
    
For any given item of output, e.g. a report table or a dojo chart, there is a
snippet of code specific to that item, and other, potentially shared code, that 
might be needed to display that item e.g. css, or javascript. 

The snippet is needed in potentially two contexts - for standalone display in 
the GUI and as part of a larger external html output file. If the snippet is in 
a larger html file, with the snippets of many other items, the overall html must 
have the shared resources (css, js) it requires. This shared code should only 
appear once in the external html.

If the item is being added to an external html report, any images will need to 
be stored in an appropriate subfolder of the report so that it can be 
distributed complete with visible images.  In this case, the standalone GUI 
version of the snippet should link to these same images. To do this it will need 
a full path to the report images. The snippet inside the external html report 
should have a relative link to make the output portable. It shouldn't matter 
where the external html file is as long as the appropriate subfolders (images, 
js) are below it.

If the item is only being used for standalone GUI display, without being added 
to an external html report, there will be no report to store the images under. 
Instead, any images it links to can be stored in the _internal folder.

The snippet is produced by a script. It is created with an html header and 
footer so that it can be displayed with the appropriate styles and js (without 
the right js, the dojo charts would not exist at all).

The initial snippet has a header containing the embedded css for the selected
style e.g. lucid spirals. Embedding is bulkier than linking so why do that? In 
its initial state, any background images in this css have relative links. The 
full path will vary by installation so it must start this way and be modified to 
become absolute. Instead of having duplicate copies of the background images for 
the standalone snippet (in _internal) an absolute path to the existing images is 
needed. This is achieved, when converting the raw snippet into the internal 
standalone GUI version by including the css in embedded form in the snippet 
header and editing the css in a simple search and replace looking for url(...).
  
The initial snippet also has all the js it needs for dojo in the html header as
well as its special css.  There is no obstacle to linking to these resources 
rather than embedding them so they are linked.

When being added to an html report, the header is completely removed and 
replaced.

HTML output is used in different places with different needs. Which all adds
complexity, unfortunately.

1) GUI display
2) When adding to an existing html report
3) When turning most recent output displayed in GUI into a PDF

Issues:

* Include or exclude title content. Leave title out when just displaying on the
GUI. As title or subtitle typed in, just change that part of the html rather 
than recalculating everything fresh. Stops flicker or other changes when using 
random data (when too many records to just use real data).
* Absolute or relative image pathways (GUI requires absolute). Export output?
"""

from __future__ import print_function
import codecs
import os
import time
import traceback
import urllib
import wx

import basic_lib as b
import my_globals as mg
import config_globals
import lib
import my_exceptions

# do not use os.linesep for anything going to be read and exec'd
# in Windows the \r\n makes it fail.

def update_var_dets(dlg):
    """
    Update all variable details, including those already displayed.
    Even if errors etc will set something, even if empty dicts.
    """
    cc = get_cc()
    (dlg.var_labels, dlg.var_notes, 
     dlg.var_types, dlg.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
     
def ensure_imgs_path(report_path, ext=mg.RPT_SUBFOLDER_SUFFIX):
    debug = False
    imgs_path = os.path.join(os.path.splitext(report_path)[0] + ext, u"")
    if debug: print("imgs_path: %s" % imgs_path)
    try:
        os.mkdir(imgs_path)
    except OSError:
        pass # already there
    return imgs_path

def append_divider(html, title, indiv_title=u"", item_type=u""):
    """
    indiv_title -- so we can use a general title but have separate parts e.g. 
    separate histograms under a single analysis e.g. ANOVA.
    
    Must immediately follow image or table item that it refers to.
    """
    item_title = get_item_title(title, indiv_title, item_type)
    html.append(u"%s<!--%s-->%s" % (mg.ITEM_TITLE_START, item_title, 
        mg.OUTPUT_ITEM_DIVIDER))

def get_part_dets(part, ideal):
    len_part = min(len(part), ideal)
    extra = ideal - len_part
    return len_part, extra 

def get_item_title(title, indiv_title=u"", item_type=u""):
    """
    Limits maximum characters for title - plus the split if needed.
    A separate process adds a number at the start and the image extension at the 
        end.
    """
    debug = False
    ideal_a = 35
    ideal_b = 15
    len_a, extra4b = get_part_dets(part=title, ideal=ideal_a)
    len_b, extra4a = get_part_dets(part=indiv_title, ideal=ideal_b)
    len_a += extra4a
    len_b += extra4b
    parts = []
    if item_type:
        parts.append(item_type)
    title_part = title[:len_a]
    if title_part:
        parts.append(title[:len_a])
    indiv_title_part = indiv_title[:len_b]
    if indiv_title_part:
        parts.append(indiv_title_part)
    item_title = u"_".join(parts)
    if debug: print(item_title)
    return item_title

def colour_mappings_to_item_colours(colour_mappings):
    """
    str() so no u"" in front of strings - needs to be ready for Javascript to 
        read in Dojo.
    """
    item_colours = [str(x[0]) for x in colour_mappings] + mg.DOJO_COLOURS
    return item_colours

def get_stats_chart_colours(css_fil):
    (unused, grid_bg, unused, major_gridline_colour, unused, 
     unused, unused, colour_mappings, unused) = lib.extract_dojo_style(css_fil)
    item_colours = colour_mappings_to_item_colours(colour_mappings)
    line_colour = major_gridline_colour
    return grid_bg, item_colours, line_colour

def get_fallback_css():
    """
    Get fallback CSS. The "constants" are used so that we can guarantee the 
        class names we use later on are the same as used here. Keep aligned 
        with default.css.
    """
    default_css = u"""
        body{
            font-size: 12px;
        }
        h1, h2{
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
            font-weight: bold;
        }
        h1{
            font-size: 18px;
        }
        h2{
            font-size: 16px;
        }
        tr, td, th{
            margin: 0;
        }
        .%s{""" % mg.CSS_TBL_TITLE_CELL + u"""
            border: none;
            padding: 0;
            margin: 0;
            color: red;
        }
        .%s{""" % mg.CSS_TBL_TITLE + u"""
            padding: 0;
            margin: 0;
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
            font-weight: bold;
            font-size: 18px;
        }
        .%s{ """ % mg.CSS_TBL_SUBTITLE + u"""
            padding: 12px 0px 0px 0px;
            margin: 0;
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        th, .%s, .%s, .%s, .%s {""" % (mg.CSS_ROW_VAR, mg.CSS_ROW_VAL, 
                                mg.CSS_DATACELL, mg.CSS_FIRST_DATACELL) + u"""
            border: solid 1px #A1A1A1;
        }
        th{
            margin: 0;
            padding: 0px 6px;
        }
        td{
            padding: 2px 6px;
        }
        .%s{""" % mg.CSS_ROW_VAL + u"""
            margin: 0;
        }
        .%s, .%s{ """ % (mg.CSS_DATACELL, mg.CSS_FIRST_DATACELL) + u"""
            text-align: right;
            margin: 0;
        }
        .%s, .%s, .%s {""" % (mg.CSS_FIRST_COL_VAR, mg.CSS_FIRST_ROW_VAR, 
                              mg.CSS_SPACEHOLDER) + u"""
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: white;
        }
        .%s, .%s { """ % (mg.CSS_FIRST_COL_VAR, mg.CSS_FIRST_ROW_VAR) + u"""
            background-color: #333435;
        }
        .%s{ """ % mg.CSS_TOPLINE + u"""
            border-top: 2px solid #c0c0c0;
        }
        .%s {""" % mg.CSS_SPACEHOLDER + u"""
            background-color: #CCD9D7;
        }
        .%s{ """ % mg.CSS_FIRST_COL_VAR + u"""
            padding: 9px 6px;
            vertical-align: top;
        }
        .%s, .%s{""" % (mg.CSS_ROW_VAR, mg.CSS_COL_VAR) + u"""
            font-family: Ubuntu, Helvetica, Arial, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: #000146;
            background-color: white;
        }
        .%s{""" % mg.CSS_COL_VAR + u"""
            padding: 6px 0px;
        }            
        .%s{""" % mg.CSS_COL_VAL + u"""
            font-size: 12px;
            vertical-align: top;
        }
        tr.%s td{""" % mg.CSS_TOTAL_ROW + u"""
            font-weight: bold;
            border-top: solid 2px black;
            border-bottom: double 3px black;
        }
        .%s{""" % mg.CSS_PAGE_BREAK_BEFORE + u"""
            page-break-before: always;
            border-bottom: none; /*3px dotted #AFAFAF;*/
            width: auto;
            height: 18px;
        }
        th.%s{""" % mg.CSS_MEASURE + u"""
            background-color: white;
        }"""
    default_css += u"\n    td.%s{\n        text-align: left;\n        "  % \
        mg.CSS_LBL + \
        u"background-color: #F5F5F5;\n    }"
    default_css += u"\n    td.%s{\n        text-align: right;\n    }" % \
        mg.CSS_ALIGN_RIGHT
    return default_css
    
def get_html_hdr(hdr_title, css_fils, has_dojo=False, new_js_n_charts=None,
                 default_if_prob=False, grey=False, abs_pth=False):
    """
    Get HTML header.
    
    Add suffixes to each of the main classes so can have multiple styles in a
    single HTML file.
    
    has_dojo -- so can include all required css and javascript links plus direct
    css and js.
    
    new_js_n_charts -- the number of dojo chart objects in the final version of 
    this report including anything just being added.
    
    default_if_prob -- if True, will use the default css if the specified css 
    fails.  Otherwise will raise a css-specific exception (which will probably 
    be handled to give the user some feedback).
    
    grey -- make the text in the cells grey instead of black so it is more
    clearly an example rather than real data.
    
    abs_pth -- absolute paths to background images in css.
    """
    debug = False
    if debug: print(css_fils[0])
    if css_fils:
        css_lst = []
        for i, css_fil in enumerate(css_fils):
            try:
                f = codecs.open(css_fil, "r", "utf-8")
            except IOError:
                if default_if_prob:
                    f = codecs.open(mg.DEFAULT_CSS_PATH, "r", "utf-8")
                else:
                    raise my_exceptions.MissingCss(css_fil)
            css_txt = f.read()
            for css_class in mg.CSS_ELEMENTS:
                # suffix all report-relevant css entities so distinct
                old_class = u"." + css_class
                new_class = u"." + mg.CSS_SUFFIX_TEMPLATE % (css_class, i)
                if debug: print(old_class, new_class)
                css_txt = css_txt.replace(old_class, new_class)
            css_lst.append(css_txt)
            f.close()
        css = (os.linesep + os.linesep).join(css_lst)
    else:
        if debug: print("\n\nUsing default css")
        css = get_fallback_css()
    if grey: # appending it will override whatever else it is set to
        css += u"\ntd, th {\n    color: #5f5f5f;\n}"
    css = u"""
body {
    background-color: %s;
}
td, th {
    background-color: white;
}
""" % mg.BODY_BACKGROUND_COLOUR + css
    if has_dojo:
        """
        zero padding so that when we search and replace, and we go to replace 
            Renumber1 with Renumber15, we don't change Renumber16 to 
            Renumber156 ;-)
        """
        if new_js_n_charts is None:
            make_objs_func_str = u"""
    for(var i=0;i<%s;i++){
        try{
            window["makechartRenumber" + String('00'+i).slice(-2)]();
        } catch(exceptionObject) {
            var keepGoing = true;
        }
    }
    """ % mg.MAX_CHARTS_IN_SET
        else:
            make_objs_func_str = u"""
    //n_charts_start
    %s%s;
    //n_charts_end
    for(var i=0;i<n_charts;i++){
        try{
            window["makechart" + String('00'+i).slice(-2)]();
        } catch(exceptionObject) {
            var keepGoing = true;
        }
    }""" % (mg.JS_N_CHARTS_STR, new_js_n_charts)
        dojo_debug = False
        dojo_js_source = (
            u"file:///home/g/sofastats/reports/sofastats_report_extras"
            u"/sofalayer.js.uncompressed.js") if dojo_debug \
            else u"sofastats_report_extras/sofastatsdojo_minified.js"
        dojo_insert = u"""
<link rel='stylesheet' type='text/css' 
href="sofastats_report_extras/tundra.css" />
<script src="sofastats_report_extras/dojo.xd.js"></script>
<script src="%(dojo_js_source)s"></script>
<script src="sofastats_report_extras/sofastats_charts.js"></script>
<script type="text/javascript">
get_ie_script = function(mysrc){
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = mysrc;
    document.getElementsByTagName('head')[0].appendChild(script); 
}
if(dojo.isIE){
    get_ie_script("sofastats_report_extras/arc.xd.js");
    get_ie_script("sofastats_report_extras/gradient.xd.js");
    get_ie_script("sofastats_report_extras/vml.xd.js");
}
makeObjects = function(){
%(make_objs_func_str)s
};
dojo.addOnLoad(makeObjects);

var DEFAULT_SATURATION  = 100,
DEFAULT_LUMINOSITY1 = 75,
DEFAULT_LUMINOSITY2 = 50,

c = dojox.color,

cc = function(colour){
    return function(){ return colour; };
},

hl = function(colour){

    var a = new c.Color(colour),
        x = a.toHsl();
    if(x.s == 0){
        x.l = x.l < 50 ? 100 : 0;
    }else{
        x.s = DEFAULT_SATURATION;
        if(x.l < DEFAULT_LUMINOSITY2){
            x.l = DEFAULT_LUMINOSITY1;
        }else if(x.l > DEFAULT_LUMINOSITY1){
            x.l = DEFAULT_LUMINOSITY2;
        }else{
            x.l = x.l - DEFAULT_LUMINOSITY2 > DEFAULT_LUMINOSITY1 - x.l 
                ? DEFAULT_LUMINOSITY2 : DEFAULT_LUMINOSITY1;
        }
    }
    return c.fromHsl(x);
}

getfainthex = function(hexcolour){
    var a = new c.Color(hexcolour)
    x = a.toHsl();
    x.s = x.s * 1.5;
    x.l = x.l * 1.25;
    return c.fromHsl(x);
}

makefaint = function(colour){
    var fainthex = getfainthex(colour.toHex());
    return new dojox.color.Color(fainthex);
}

%(label_line_break_js)s

</script>

<style type="text/css">
<!--
    .dojoxLegendNode {
        border: 1px solid #ccc; 
        margin: 5px 10px 5px 10px; 
        padding: 3px
    }
    .dojoxLegendText {
        vertical-align: text-top; 
        padding-right: 10px
    }
    @media print {
        .screen-float-only{
        float: none;
        }
    }
    
    @media screen {
        .screen-float-only{
        float: left;
        }
    }
-->
</style>""" % {u"make_objs_func_str": make_objs_func_str,
               u"label_line_break_js": mg.LBL_LINE_BREAK_JS,
               u"dojo_js_source": dojo_js_source}
    else:
        dojo_insert = u""
    hdr = mg.DEFAULT_HDR % {u"title": hdr_title, u"css": css, 
        u"dojo_insert": dojo_insert}
    if abs_pth:
        hdr = rel2abs_css_bg_imgs(hdr)
    if debug: print(hdr)
    return hdr

def get_html_ftr():
    "Close HTML off cleanly"
    return u"</body></html>"

def get_js_n_charts(html):
    """
    Read from report html. 3 in this example.  None if not there or an error.
    //n_charts_start
    var n_charts = 3; # must be same as mg.JS_N_CHARTS_STR
    //n_charts_end
    Get the 3.
    """
    debug = False
    try:
        idx_start = (html.index(mg.N_CHARTS_TAG_START) +
            len(mg.N_CHARTS_TAG_START))
        idx_end = html.index(mg.N_CHARTS_TAG_END)
        raw_n_charts_str = html[idx_start: idx_end]
        if debug: print(raw_n_charts_str)
        js_n_charts = int(raw_n_charts_str.strip().lstrip(mg.JS_N_CHARTS_STR)
            .rstrip(u";"))
        if debug: print(js_n_charts)
    except Exception:
        js_n_charts = None
    return js_n_charts

def get_makechartRenumbers_n(html):
    """
    Count occurrences of makechartRenumber.
    """
    makechartRenumbers_n = html.count(u"makechartRenumber") - 1 # one in header
    return makechartRenumbers_n

def get_css_dets():
    """
    Returns css_fils, css_idx.
    css_fils - list of full paths to css files.
    Knowing the current report and the current css what is the full list of css 
        files used by the report and what is the index for the current one in
        that list?
    Try reading from report file first.
    If not there (empty report or manually broken by user?) make and use a new
        one using cc[mg.CURRENT_CSS_PATH].
    """
    cc = get_cc()
    if not os.path.exists(cc[mg.CURRENT_CSS_PATH]):
        ret = wx.MessageBox(_("The CSS style file '%s' doesn't exist. "
            "Continue using the default style instead?") % 
            cc[mg.CURRENT_CSS_PATH], _("Needs CSS Style"), 
            style=wx.YES_NO|wx.ICON_QUESTION)
        if ret == wx.YES:
            cc[mg.CURRENT_CSS_PATH] = mg.DEFAULT_CSS_PATH
        else:
            raise my_exceptions.MissingCss(cc[mg.CURRENT_CSS_PATH])
    css_fils = None
    # read from report
    if os.path.exists(cc[mg.CURRENT_REPORT_PATH]):
        f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "U", "utf-8")
        content = b.clean_boms(f.read())
        f.close()
        if content:
            try:
                idx_start = content.index(mg.CSS_FILS_START_TAG) + len("<!--")
                idx_end = content.index("-->")
                css_fils_str = content[idx_start: idx_end]
                css_fils_str = b.get_exec_ready_text(text=css_fils_str)
                css_dets_dic = {}
                exec css_fils_str in css_dets_dic
                css_fils = css_dets_dic[u"css_fils"]
            except Exception:
                pass # Don't let css failuer stop report production.
    if not css_fils:
        css_fils = [cc[mg.CURRENT_CSS_PATH]]
    else:
        if cc[mg.CURRENT_CSS_PATH] not in css_fils:
            css_fils.append(cc[mg.CURRENT_CSS_PATH])
    #mg.OUTPUT_CSS_DIC[cc[mg.CURRENT_REPORT_PATH]] = css_fils
    css_idx = css_fils.index(cc[mg.CURRENT_CSS_PATH])
    return css_fils, css_idx

def get_title_dets_html(titles, subtitles, css_idx, istable=False):
    """
    Table title and subtitle html ready to display.
    
    If title and/or subtitle are empty, want minimal display height. But have to 
    have stable html. Solution - have cells table containing spans. But make 
    separate table from main table so wide title !- wide table ;-)
    """
    (CSS_TBL_TITLE, 
     CSS_TBL_SUBTITLE, CSS_TBL_TITLE_CELL) = get_title_css(css_idx)
    title_dets_html_lst = []
    # titles
    title_dets_html_lst.append(u"<table cellspacing='0'><thead><tr>"
        u"<th class='%s'>" % CSS_TBL_TITLE_CELL)
    title_dets_html_lst.append(u"<span class='%s'>" % CSS_TBL_TITLE)
    if istable:
        title_dets_html_lst.append(mg.TBL_TITLE_START) # so we can refresh content
    if titles:
        title_dets_html_lst.append(get_titles_inner_html(titles))
    if istable:
        title_dets_html_lst.append(mg.TBL_TITLE_END)
    title_dets_html_lst.append(u"</span>")
    # subtitles
    if titles and subtitles:
        title_dets_html_lst.append(u"<br>")
    title_dets_html_lst.append(u"<span class='%s'>" % CSS_TBL_SUBTITLE)
    if istable:
        title_dets_html_lst.append(mg.TBL_SUBTITLE_START) # so we can refresh content
    if subtitles:
        title_dets_html_lst.append(get_subtitles_inner_html(subtitles))
    if istable:
        title_dets_html_lst.append(mg.TBL_SUBTITLE_END)
    title_dets_html_lst.append(u"</span>")
    title_dets_html_lst.append(u"</th></tr></thead></table>")
    # combine
    title_dets_html = u"\n".join(title_dets_html_lst)
    return title_dets_html    
    
def get_titles_inner_html(titles):
    """
    Just the bits within the tags, css etc.
    """
    return u"<br>".join(titles)

def get_subtitles_inner_html(subtitles):
    """
    Just the bits within the tags, css etc.
    """
    return u"<br>".join(subtitles)

def percent_encode(url2esc):
    """
    http://kbyanc.blogspot.co.nz/2010_07_01_archive.html
    http://stackoverflow.com/questions/2742852/unicode-characters-in-urls
    """
    try:
        url2esc_str = url2esc.encode("utf-8") #essential to encode first
        perc_url = urllib.quote(url2esc_str)
    except Exception, e:
        raise Exception(u"Unable to percent encode \"%s\". Orig error: %s" % 
            (url2esc, b.ue(e)))
    return perc_url

def fix_perc_encodings_for_win(mystr):
    """
    IE6 at least chokes on C%3A%5CDocuments but is OK with 
    C:/Documents.
    
    IE6 can't cope with non-English text percent encoded or otherwise. See 
    http://ihateinternetexplorer.com/. The IE widget on Windows 7 is fine though 
    so time will fix this problem.
    
    These steps made a difference in the wxPython IE-based window on XP. Crazy.
    """
    fixed_str = (mystr.replace(mg.PERC_ENCODED_BACKSLASH, u"/").
        replace(mg.PERC_ENCODED_COLON, u":"))
    return fixed_str

def extract_title_subtitle(txt):
    debug = False
    try:
        title_start_idx = (txt.index(mg.TBL_TITLE_START) 
            + len(mg.TBL_TITLE_START))
        title_end_idx = txt.index(mg.TBL_TITLE_END)
        title = txt[title_start_idx: title_end_idx].strip()
        subtitle_start_idx = (txt.index(mg.TBL_SUBTITLE_START) 
            + len(mg.TBL_SUBTITLE_START))
        subtitle_end_idx = txt.index(mg.TBL_SUBTITLE_END)
        subtitle = txt[subtitle_start_idx: subtitle_end_idx].strip()
        return title, subtitle
    except Exception, e:
        if debug:
            print(txt)
        raise Exception(u"Unable to extract title and subtitle. Orig error: %s" 
            % b.ue(e))

def extract_tbl_only(tbl_item):
    """
    Assumes certain placeholders exist from which titles can be extracted.
    Assumes only one report start and end.
    """
    debug = False
    try:
        split_report = tbl_item.split(mg.REPORT_TABLE_START)
        try:
            mystart, post_start = split_report
        except ValueError:
            if debug: print(tbl_item)
            raise Exception(u"Unable to split by report table start (%s)."
                u"\n\nOrig item: %s\n...\n%s" % (mg.REPORT_TABLE_START, 
                tbl_item[:400], tbl_item[-400:]))
        title, subtitle = extract_title_subtitle(mystart)
        tbl_html, unused = post_start.split(mg.REPORT_TABLE_END)
        tbl_only = u"<h2>%s</h2>\n<h2>%s</h2>\n%s" % (title, subtitle, tbl_html)
    except Exception, e:
        msg = (u"Unable to extract report table html and title from "
            u"input. Orig error: %s" % b.ue(e))
        if debug: print(msg)
        raise Exception(msg)
    return tbl_only

def rel2abs_rpt_img_links(str_html):
    """
    Linked images in external HTML reports are in different locations from those 
    in internal standalone GUI output. 
    
    The former are in subfolders of the reports folder ready to be shared with 
    other people alongside the report file which refers to them. The latter are 
    in the internal folder only.
    
    The internal-only images/js can be referred to by the GUI with reference to 
    their absolute path.
    
    The report-associated images/js, can be referred to by their report in a 
    relative sense, but not by the GUI which has a different relative location 
    than the report. That is why it must use an absolute path to the images/js 
    (stored in a particular report's subfolder).
    
    So this functionality is only needed for GUI display of report-associated 
    images/js.
    
    Turn my_report_name/001.png to e.g. 
    file:///home/g/Documents/sofastats/reports/my_report_name/001.png so 
    that the html can be written to, and read from, anywhere (and still show the 
    images!) in the temporary GUI displays.
    """
    debug = False
    verbose = False
    cc = get_cc()
    report_path = os.path.split(cc[mg.CURRENT_REPORT_PATH])[0]
    report_path = os.path.join(report_path, u"")
    report_path = percent_encode(report_path)
    if mg.PLATFORM == mg.WINDOWS:
        report_path = fix_perc_encodings_for_win(report_path)
    if debug: print(u"report_path: %s" % report_path)
    file_url_start = (mg.FILE_URL_START_WIN if mg.PLATFORM == mg.WINDOWS 
        else mg.FILE_URL_START_GEN)
    abs_display_content = (str_html.replace(u"%s" % mg.IMG_SRC_START, 
        u"%s%s%s" % (mg.IMG_SRC_START, file_url_start, report_path)))
    if debug and verbose: 
        print(u"From \n\n%s\n\nto\n\n%s" % (str_html, abs_display_content))
    return abs_display_content

def path2url(path):
    """
    http://en.wikipedia.org/wiki/File_URI_scheme
    Two slashes after file:
    then either host and a slash or just a slash
    then the full path e.g. /home/g/etc
    *nix platforms start with a forward slash
    """
    if mg.PLATFORM == mg.WINDOWS:
        url = u"%s%s" % (mg.FILE_URL_START_WIN, path)
    else:
        url = u"%s%s" % (mg.FILE_URL_START_GEN, path)
    return url

def rel2abs_rpt_extras(strhtml, tpl):
    """
    Make all links work off absolute rather than relative paths.
    Will run OK when displayed internally in GUI.
    """ 
    debug = False
    url = path2url(mg.REPORT_EXTRAS_PATH)
    abs_display_content = strhtml.replace(tpl % mg.REPORT_EXTRAS_FOLDER, 
        tpl % url) 
    if debug: print("From \n\n%s\n\nto\n\n%s" % (strhtml, abs_display_content))
    return abs_display_content

def rel2abs_extra_js_links(strhtml):
    return rel2abs_rpt_extras(strhtml, tpl=u"get_ie_script(\"%s")

def rel2abs_css_bg_imgs(strhtml):
    """
    Make all css background images work off absolute rather than relative paths.  
    
    Turn url("sofastats_report_extras/tile.gif"); to 
    url("file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tile.gif");.
    """
    return rel2abs_rpt_extras(strhtml, tpl=u"url(\"%s")

def rel2abs_js_links(strhtml):
    """
    Make all js links work off absolute rather than relative paths.
    
    Turn <script src="sofastats_report_extras/sofalayer.js"> to 
    <script src="file:////home/g/sofastats/reports/sofastats_report_extras/
        sofalayer.js">.
    """
    return rel2abs_rpt_extras(strhtml, tpl=u"<script src=\"%s")

def rel2abs_css_links(strhtml):
    """
    Make all css links work off absolute rather than relative paths.
    
    Turn href="sofastats_report_extras/tundra.css" to 
    href="file:///home/g/sofastats/reports/sofastats_report_extras/tundra.css".
    """
    return rel2abs_rpt_extras(strhtml, tpl=u"href=\"%s")

def get_divider(source, tbl_filt_label, tbl_filt, page_break_before=False):
    """
    Get the HTML divider between content -includes source e.g. database, table 
    and time stamp; and a filter description.
    """
    debug = False
    filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
    pagebreak = u" page-break-before: always " if page_break_before else u""
    div = (u"""\n<br><br>\n<hr style="clear: both; %s">\n%s\n<p>%s</p>\n%s""" %
        (pagebreak, source, filt_msg, mg.VISUAL_DIVIDER_BEFORE_THIS))
    if debug: print(div)
    return div

def get_source(db, tblname):
    full_datestamp = u"on %s" % lib.get_unicode_datestamp()
    source = u"\n<p>From %s.%s %s</p>" % (db, tblname, full_datestamp)
    return source

def get_title_css(css_idx):
    CSS_TBL_TITLE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_TITLE, css_idx)
    CSS_TBL_SUBTITLE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_SUBTITLE, 
        css_idx)
    CSS_TBL_TITLE_CELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_TITLE_CELL, 
        css_idx)
    return CSS_TBL_TITLE, CSS_TBL_SUBTITLE, CSS_TBL_TITLE_CELL

def extract_html_hdr(html):
    """
    Get html between the head tags. The start tag must be present.
    """
    html_hdr = extract_html_content(html, start_tag=u"<head>", 
        end_tag=u"</head>")
    return html_hdr

def extract_html_body(html):
    """
    Get html between the body tags. The start tag must be present.
    """
    html_body = extract_html_content(html, start_tag=mg.BODY_START, 
        end_tag=u"</body>")
    return html_body

def hdr_has_dojo(html):
    html_hdr = extract_html_hdr(html)
    try:
        unused = html_hdr.index(u"dojo.addOnLoad")
        hdr_has_dojo = True
    except ValueError:
        hdr_has_dojo = False
    return hdr_has_dojo

def extract_html_content(html, start_tag, end_tag):
    """
    Get html between the supplied tags.  The start tag must be present.
    """
    try:
        start_idx = html.index(start_tag) + len(start_tag)
    except ValueError:
        if not html:
            msg = (u"Empty report file. Please delete it. SOFA builds report "
                u"files as needed if you enter a report name to add output to "
                u"that doesn't yet exist.")
        else:
            msg = u"Start of broken file: %s ..." % html[:60]
        raise my_exceptions.MalformedHtml(msg)
    try:
        end_idx = html.index(end_tag)
        extracted = html[start_idx:end_idx]
    except ValueError:
        extracted = html[start_idx:]
    return extracted

def save_to_report(css_fils, source, tbl_filt_label, tbl_filt, new_has_dojo, 
        new_html):
    """
    If report doesn't exist, make it.
    
    If it does exist, extract existing content and then create empty version.
    
    Add to empty file, new header, existing content, and new content.
    
    A new header is required each time because there may be new css included 
    plus new js functions to make new charts.
    
    New content is everything between the body tags.
    
    new_has_dojo -- does the new html being added have Dojo. NB the report may 
    have other results which have dojo, whether or not the latest output has.

    If report has dojo, change from makechartRenumber0 etc, to next available 
    integers.
    """
    debug = False
    cc = get_cc()
    new_no_hdr = extract_html_body(new_html)
    new_js_n_charts = None # init
    n_charts_in_new = get_makechartRenumbers_n(new_html)
    existing_report = os.path.exists(cc[mg.CURRENT_REPORT_PATH])
    if existing_report:
        f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "U", "utf-8")
        existing_html = b.clean_boms(f.read())
        existing_has_dojo = hdr_has_dojo(existing_html)
        has_dojo = (new_has_dojo or existing_has_dojo)
        if has_dojo:
            js_n_charts = get_js_n_charts(existing_html)
            if js_n_charts is None:
                new_js_n_charts = n_charts_in_new
            else:
                new_js_n_charts = js_n_charts
                if new_has_dojo:
                    new_js_n_charts += n_charts_in_new
            if debug: print("n_charts: %s, new_n_charts: %s" % (js_n_charts, 
                new_js_n_charts))
        existing_no_ends = extract_html_body(existing_html)
        f.close()        
    else:
        has_dojo = new_has_dojo
        if has_dojo:
            new_js_n_charts = n_charts_in_new
        existing_no_ends = None
    if has_dojo:
        """
        May be a set of charts e.g. Renumber0, Renumber1 etc
        
        zero padding chart_idx so that when we search and replace, and go to 
        replace Renumber1 with Renumber15, we don't change Renumber16 to 
        Renumber156 ;-)
        """
        for i in range(n_charts_in_new):
            orig_n_charts = new_js_n_charts - n_charts_in_new
            new_n = (orig_n_charts) + i
            replacement = u"%02d" % new_n
            i_zero_padded = u"%02d" % i
            new_no_hdr = new_no_hdr.replace(u"Renumber%s" % i_zero_padded, 
                replacement)
    hdr_title = time.strftime(_("SOFA Statistics Report") 
        + " %Y-%m-%d_%H:%M:%S")
    hdr = get_html_hdr(hdr_title, css_fils, has_dojo, new_js_n_charts)
    try:
        f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "w", "utf-8")
    except IOError:
        if not os.path.exists(path=cc[mg.CURRENT_REPORT_PATH]):
            raise Exception(u"Unable to save to report. You might need to "
                u"check and correct the path to the report.")
    except Exception, e:
        raise Exception(u"Unable to save to report. Orig error: %s" % b.ue(e))
    css_fils_str = '[u"' + u'",\nu"'.join(css_fils) + u'"]'
    f.write(u"%s = %s-->\n\n" % (mg.CSS_FILS_START_TAG, css_fils_str))
    f.write(hdr)
    if existing_no_ends:
        f.write(existing_no_ends)
    pagebreak = existing_report
    f.write(u"\n"*4) # Won't change output but make it easier to shift infdividual outputs around or delete them manually
    f.write(get_divider(source, tbl_filt_label, tbl_filt, pagebreak))
    f.write(new_no_hdr)
    f.write(u"\n"*4)
    f.write(get_html_ftr())
    f.close()

def _strip_script(script):
    """
    Get script up till #sofa_script_end ...
    """
    try:
        end_idx = script.index(mg.SCRIPT_END)
        stripped = script[:end_idx]
    except ValueError:
        stripped = script
    return stripped
        
def get_cc():
    debug = False
    if not mg.CURRENT_CONFIG:
        proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
            fil_name=mg.DEFAULT_PROJ)
        mg.CURRENT_CONFIG = {mg.CURRENT_REPORT_PATH: proj_dic[mg.PROJ_FIL_RPT],
            mg.CURRENT_CSS_PATH: proj_dic[mg.PROJ_FIL_CSS],
            mg.CURRENT_VDTS_PATH: proj_dic[mg.PROJ_FIL_VDTS],
            mg.CURRENT_SCRIPT_PATH: proj_dic[mg.PROJ_FIL_SCRIPT]}
        if debug: print("Updated mg.CURRENT_CONFIG")
    return mg.CURRENT_CONFIG

def export_script(script, css_fils, new_has_dojo=False):
    dd = mg.DATADETS_OBJ
    cc = get_cc()
    modules = ["my_globals as mg", "core_stats", "dimtables", "getdata", 
        "output", "rawtables", "stats_output"]
    if os.path.exists(cc[mg.CURRENT_SCRIPT_PATH]):
        f = codecs.open(cc[mg.CURRENT_SCRIPT_PATH], "U", "utf-8")
        existing_script = b.clean_boms(f.read())             
        f.close()
    else:
        existing_script = None
    try:
        f = codecs.open(cc[mg.CURRENT_SCRIPT_PATH], "w", "utf-8")
    except IOError:
        wx.MessageBox(_("Problem making script file named \"%s\". Please try "
            "another name.") % cc[mg.CURRENT_SCRIPT_PATH])
        return
    if existing_script:
        f.write(_strip_script(existing_script))
    else:
        insert_prelim_code(modules, f, cc[mg.CURRENT_REPORT_PATH], css_fils, 
            new_has_dojo)
    tbl_filt_label, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
    append_exported_script(f, script, tbl_filt_label, tbl_filt, 
        inc_divider=True)
    add_end_script_code(f)
    f.close()
    wx.MessageBox(_("Script added to end of \"%s\" ready for reuse and "
        "automation") % cc[mg.CURRENT_SCRIPT_PATH])

def add_divider_code(f, tbl_filt_label, tbl_filt):
    """
    Adds divider code to a script file.
    """
    dd = mg.DATADETS_OBJ
    f.write(u"\nsource = output.get_source(u\"%s\", u\"%s\")" % (dd.db, dd.tbl))
    f.write(u"\ndivider = output.get_divider(source, "
        u" u\"\"\" %s \"\"\", u\"\"\" %s \"\"\")" % (tbl_filt_label, tbl_filt))
    f.write(u"\nfil.write(divider)\n")

def insert_prelim_code(modules, f, fil_report, css_fils, new_has_dojo):
    """
    Insert preliminary code at top of file.  Needed for making output
    f - open file handle ready for writing.
    
    NB only one output file per script irrespective of selection as each script
    exported.
    """
    debug = False
    if debug: print(css_fils)
    # NB the encoding declaration added must be removed before we try to run the 
    # script as a unicode string else "encoding declaration in Unicode string".
    f.write(mg.PYTHON_ENCODING_DECLARATION)
    f.write(u"\n" + mg.MAIN_SCRIPT_START)
    f.write(u"\nimport codecs")
    f.write(u"\nimport gettext")
    f.write(u"\nimport numpy as np")
    f.write(u"\nimport os")
    f.write(u"\nimport sys")
    f.write(u"\ngettext.install(domain='sofastats', localedir=\"%s\", "
        u"unicode=False)" % lib.escape_pre_write(mg.LOCALEDIR))
    f.write(u"\n" + lib.get_gettext_setup_txt())
    f.write(u"\nsys.path.append(u'%s')" % lib.escape_pre_write(mg.SCRIPT_PATH))
    for module in modules:
        f.write(u"\nimport %s" % module)
    f.write(u"\nimport my_exceptions")
    f.write(u"\n\n#Uncomment next block to use this script stand-alone:")
    f.write(u"\n#import config_globals")
    f.write(u"\n#config_globals.set_SCRIPT_PATH()")
    f.write(u"\n#config_globals.set_ok_date_formats()")
    f.write(u"\n#config_globals.set_DEFAULT_LEVEL()")
    f.write(u"\n#config_globals.import_dbe_plugins() # as late as possible because uses local modules e.g. my_exceptions, lib")
    f.write(u"""\n\nfil = codecs.open(u"%s",""" %
        lib.escape_pre_write(fil_report) + u""" "w", "utf-8")""")
    css_fils_esc = [lib.escape_pre_write(x) for x in css_fils]
    css_fils_str = u'[u"' + u'",\nu"'.join(css_fils_esc) + u'"]'
    f.write(u"\ncss_fils=%s" % css_fils_str)
    has_dojo = new_has_dojo # always for making single output item e.g. chart
    has_dojo_str = u"True" if has_dojo else u"False"
    f.write(u"\nfil.write(output.get_html_hdr(\"Report(s)\", css_fils, "
        u"has_dojo=%s, new_js_n_charts=None, default_if_prob=True))" % 
        has_dojo_str)
    f.write(u"\n\n# end of script 'header'" + u"\n" + u"\n")

def append_exported_script(f, inner_script, tbl_filt_label, tbl_filt, 
        inc_divider=False):
    """
    Append exported script onto existing script file.
    f - open file handle ready for writing
    """
    dd = mg.DATADETS_OBJ
    full_datestamp = u"\n# Script exported %s" % lib.get_unicode_datestamp()
    # Fresh connection for each in case it changes in between tables
    f.write(u"#%s" % (u"-"*65))
    f.write(full_datestamp)
    if inc_divider:
        add_divider_code(f, tbl_filt_label, tbl_filt)
    con_dets_str = lib.dic2unicode(dd.con_dets)
    f.write(u"\n" + u"con_dets = %s" % con_dets_str.replace(u"\\", u"\\\\"))
    default_dbs_str = lib.dic2unicode(dd.default_dbs)
    f.write(u"\n" + u"default_dbs = %s" % default_dbs_str)
    default_tbls_str = lib.dic2unicode(dd.default_tbls)
    f.write(u"\ndefault_tbls = %s" % default_tbls_str)
    f.write(u"\ndbe =\"%s\"" % dd.dbe)
    f.write(u"\ndbe_resources = getdata.get_dbe_resources(dbe,")
    f.write(u"\n    con_dets=con_dets, default_dbs=default_dbs, "
        u"\n    default_tbls=default_tbls, ")
    f.write(u"\n    db=u\"%s\", tbl=u\"%s\")" % (dd.db, dd.tbl))
    f.write(u"\ncon = dbe_resources[mg.DBE_CON]")
    f.write(u"\ncur = dbe_resources[mg.DBE_CUR]")
    f.write(u"\ndbs = dbe_resources[mg.DBE_DBS]")
    f.write(u"\ndb = dbe_resources[mg.DBE_DB]")
    f.write(u"\ntbls = dbe_resources[mg.DBE_TBLS]")
    f.write(u"\ntbl = dbe_resources[mg.DBE_TBL]")
    f.write(u"\nflds = dbe_resources[mg.DBE_FLDS]")
    f.write(u"\nidxs = dbe_resources[mg.DBE_IDXS]")
    f.write(u"\nhas_unique = dbe_resources[mg.DBE_HAS_UNIQUE]")
    f.write(u"\n%s" % inner_script)
    f.write(u"\ncon.close()")

def add_end_script_code(f):
    "Add ending code to script. NB leaves open file."
    f.write(u"\n" + u"\n" + mg.SCRIPT_END + \
        u"-"*(65 - len(mg.SCRIPT_END)) + u"\n")
    f.write(u"\n" + u"fil.write(output.get_html_ftr())")
    f.write(u"\n" + u"fil.close()")

def generate_script(modules, css_fils, new_has_dojo, inner_script,
        tbl_filt_label, tbl_filt):
    debug = False
    verbose = False
    try:
        f = codecs.open(mg.INT_SCRIPT_PATH, "w", "utf-8")
        if debug and verbose: print(css_fils)
        insert_prelim_code(modules, f, mg.INT_REPORT_PATH, css_fils, 
            new_has_dojo)
        append_exported_script(f, inner_script, tbl_filt_label, tbl_filt, 
            inc_divider=False)
        add_end_script_code(f)
        f.close()
    except Exception, e:
        raise Exception(u"Unable to make the script needed to make the output."
            u"\nOrig error: %s" % b.ue(e))

def run_script():
    try:
        f = codecs.open(mg.INT_SCRIPT_PATH, "r", "utf-8")
        script_txt = f.read()
        f.close()
        script_txt = b.get_exec_ready_text(text=script_txt)
        script = b.clean_boms(script_txt)    
        script = script[script.index(mg.MAIN_SCRIPT_START):]
    except Exception, e:
        raise Exception(u"Unable to read part of script for execution."
            u"\nOrig error: %s" % b.ue(e))
    dd = mg.DATADETS_OBJ
    if dd.dbe == mg.DBE_MS_ACCESS:
        orig_projdic = dd.proj_dic
        orig_db = dd.db
        orig_tbl = dd.tbl
        dd.con.close() # close it - or else have to wait till it times out and closes self before script will get data back ;-)
    try:
        dummy_dic = {}
        exec script in dummy_dic
    except my_exceptions.OutputException, e:
        wx.MessageBox(b.ue(e))
        raise my_exceptions.NeedViableInput
    except Exception, e:
        print("Unable to run report: %s" % traceback.format_exc())
        raise Exception(_(u"Unable to run script to generate report. Caused by "
            u"error: %s") % b.ue(e))
    finally:
        if dd.dbe == mg.DBE_MS_ACCESS: 
            dd.set_proj_dic(orig_projdic)
            dd.set_dbe(dbe=mg.DBE_MS_ACCESS, db=orig_db, tbl=orig_tbl)

def get_raw_results():
    """
    Raw results will have a html header with embedded css referencing relative
    background images, and in the body either relative image links (if added to
    report) or absolute images links (if standalone GUI only). 
    
    If it has dojo, will have relative dojo js and css in the header, a 
    makeObjects function, also in the header, which only runs from 0 to N
    makechartsRenumber0(), and in the body, a function called 
    makechartRenumber0, a chart called mychartRenumber0, and a legend called 
    legendMychartRenumber0, and makechartsRenumber1 etc.
    """
    debug = False
    verbose = False
    try:
        with codecs.open(mg.INT_REPORT_PATH, "U", "utf-8") as f:
            raw_results = b.clean_boms(f.read())
            f.close()
        if debug and verbose: print(raw_results)
    except Exception, e:
        raise Exception(u"Unable to read local copy of output report."
            u"\nOrig error: %s" % b.ue(e))
    return raw_results

def append_onto_report(css_fils, source, tbl_filt_label, tbl_filt, new_has_dojo, 
        raw_results):
    """
    Append into html file. 
    
    Handles source and filter desc internally when making divider between 
    output.
    
    Ignores snippet html header and modifies report header if required.
    """
    try:
        save_to_report(css_fils, source, tbl_filt_label, tbl_filt, new_has_dojo, 
            raw_results)
    except my_exceptions.MalformedHtml, e:
        raise Exception(_("Problems with the content of the report you are "
            u"saving to. Please fix, or delete report and start again. Caused "
            u"by error: %s") % b.ue(e))
    except Exception, e:
        raise Exception(u"Problem running report.\n"
            u"Caused by error: %s" % b.ue(e))

def get_abs_content(raw_display_content, add_to_report):
    """
    Relative references are good for a portable html file but no good for local
    display in SOFA or extracting paths suitable for copying images. Need
    absolute paths.
    """
    debug = False
    verbose = True
    if debug and verbose:
        print(u"\nrel\n" + 100*u"*" + u"\n\n" + raw_display_content)
    css_links_fixed = rel2abs_css_links(raw_display_content)
    if debug and verbose: 
        print(u"\ncss\n" + 100*u"*" + u"\n\n" + css_links_fixed)
    js_fixed = rel2abs_js_links(css_links_fixed)
    if debug and verbose: 
        print(u"\njs\n" + 100*u"*" + u"\n\n" + js_fixed)
    ie_js_fixed = rel2abs_extra_js_links(js_fixed)
    if debug and verbose: 
        print(u"\nie\n" + 100*u"*" + u"\n\n" + ie_js_fixed)
    abs_content = rel2abs_css_bg_imgs(ie_js_fixed)
    if debug and verbose: 
        print(u"\ngui\n" + 100*u"*" + u"\n\n" + abs_content)
    if add_to_report:
        # Has to deal with local GUI version to display as well.
        # Make relative image links absolute so GUI viewers can display images.
        # If not add_to_report, already has absolute link to internal imgs.
        # If in real report, will need a relative version for actual report.
        # Make relative js absolute so dojo charts can display.
        abs_content = rel2abs_rpt_img_links(abs_content)
        if debug and verbose: 
            print(u"\nimgs\n" + 100*u"*" + u"\n\n" + abs_content)
    return abs_content

def run_report(modules, add_to_report, css_fils, new_has_dojo, inner_script):
    """
    Runs report and returns bolran_report, and HTML representation of report 
    (or of the error) for GUI display. Report includes HTML header.
    
    add_to_report -- also append result to current report.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    cc = get_cc()
    source = get_source(dd.db, dd.tbl)
    tbl_filt_label, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
    filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
    try:
        generate_script(modules, css_fils, new_has_dojo, inner_script,
            tbl_filt_label, tbl_filt)
        run_script()
        raw_results = get_raw_results()
        if add_to_report:
            append_onto_report(css_fils, source, tbl_filt_label, tbl_filt, 
                new_has_dojo, raw_results)
        # Split raw_results so can insert messages re filters etc AFTER header
        above_inner_body, inner_body = raw_results.split(mg.BODY_START)
        try:
            abs_above_inner_body = get_abs_content(above_inner_body, 
                add_to_report)
            abs_inner_body = get_abs_content(inner_body, add_to_report)
        except Exception, e:
            if add_to_report:
                raise Exception(u"Problems getting copy of output to display."
                    u"\nOrig error: %s" % b.ue(e))
            else:
                raise Exception(u"Problems getting content to display on "
                    u"screen.\nOrig error: %s" % b.ue(e))
        if add_to_report:
            esc_rpt_path = lib.escape_pre_write(cc[mg.CURRENT_REPORT_PATH])
            gui_display_content = (abs_above_inner_body + mg.BODY_START + 
                u"\n<p>Output also saved to '%s'</p>" % esc_rpt_path 
                + u"<p>%s</p>" % filt_msg + abs_inner_body)
        else:
            gui_display_content = (abs_above_inner_body + mg.BODY_START + source 
                + u"<p>%s</p>" % filt_msg + abs_inner_body)
        if debug: print(abs_inner_body)
    except my_exceptions.NeedViableInput, e:
        return False, u"<p>%s</p>" % b.ue(e)
    except Exception, e:
        return False, u"<h1>Ooops!</h1><p>%s</p>" % b.ue(e)
    if debug: 
        print(u"\n\n\n\nAdd2report: %s\n%s" % (add_to_report, 
            gui_display_content))
    try: # makes it much easier to extract absolute chart paths for linked 
            # images (as opposed to SVG/Javascript images (Dojo).
        with codecs.open(mg.INT_REPORT_PATH, "w", "utf-8") as f:
            f.write(abs_above_inner_body + mg.BODY_START + abs_inner_body)
            f.close()
    except Exception:
        pass # will stuff up exporting images in some cases but not worth 
            # halting otherwise-successful analysis.
    return True, gui_display_content

