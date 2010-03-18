
import wx
import xml.etree.ElementTree as etree
import zipfile

import my_globals as mg
import importer

"""
NB need to handle ods from OpenOffice Calc, and Gnumeric at least.  Some 
    differences.
NB some internal xml files are mainly empty yet they still have to be parsed.
    They may even be very large e.g. 54MB!  Extremely inefficient under these 
    circumstances.
Example of date cell:
<table:table-cell table:style-name="ce1" office:value-type="date" 
    office:date-value="2010-02-01">
<text:p>01/02/10</text:p>
</table:table-cell>
Example of empty cell:
<table:table-cell/>
Example of string cell:
<table:table-cell office:value-type="string">
<text:p>col2</text:p>
</table:table-cell>
Example of float cell:
<table:table-cell office:value-type="float" office:value="1">
<text:p>1</text:p>
</table:table-cell>
"""

xml_type_to_val_type = {"string": mg.VAL_STRING, "float": mg.VAL_NUMERIC}

def add_type_to_coltypes(coltypes, col_idx, type):
    try:
        coltypes[col_idx].add(type)
    except IndexError:
        coltypes.append(set([type]))    

def after_end_brace(text):
    try:
        idx_end = text.index(u"}") + 1
        endtext = text[idx_end:]
        return endtext
    except ValueError:
        return Exception, "No curly brace in text: %s" % text

def get_new_attrib_dict(items):
    """
    Get new dictionary with xml verbiage removed from front
    """
    debug = False
    large = False
    if debug and not large: print("items: %s" % items)
    new_attrib_dict = {}
    for item in items:
        key, value = item
        newkey = after_end_brace(key)
        new_attrib_dict[newkey] = value
    return new_attrib_dict
            
def get_fld_names_from_header_row(row):
    debug = False
    orig_fld_names = []
    for i, el in enumerate(row):
        if debug: 
            print(u"\nChild element of a table-row: " + etree.tostring(el))
        items = el.attrib.items()
        new_attrib_dict = get_new_attrib_dict(items)
        # stays None unless there is a date-value or value-type attrib
        fld_name = None
        type = None
        if new_attrib_dict:
            if u"date-value" in new_attrib_dict.keys():
                fld_name = new_attrib_dict[u"date-value"] # take proper date 
                    # val e.g. 2010-02-01 rather than orig text of 01/02/10
            elif u"value-type" in new_attrib_dict.keys():
                fld_name = el[0].text # take val from inner text element
            else: # not a data cell
                pass
                # e.g. <table:table-cell table:number-columns-repeated="254" 
                # table:style-name="ACELL-0x88a3bc8"/>
        else:
            fld_name = lib.get_next_fld_name(existing_var_names=orig_fld_names)
        if fld_name is not None:
            if fld_name in orig_fld_names:
                raise Exception, _("Field name \"%s\" has been repeated") % \
                    fld_name
            orig_fld_names.append(fld_name)
    return orig_fld_names

def dets_from_row(orig_fld_names, coltypes, row):
    """
    Update coltypes and return dict of values in row (using orig fld names).
    """
    debug = False
    large = False
    val_dict = {}
    next_fld_name_idx = 0
    for i, el in enumerate(row):
        if debug: 
            print(u"\nChild element of a table-row: " + etree.tostring(el))
        items = el.attrib.items()
        new_attrib_dict = get_new_attrib_dict(items)
        if debug and not large: print("items: %s" % items)
        # stays None unless there is a date-value or value-type attrib
        val2use = None
        type = None
        if new_attrib_dict:
            if u"date-value" in new_attrib_dict.keys():
                type = mg.VAL_DATETIME
                val2use = new_attrib_dict[u"date-value"] # take proper date 
                    # val e.g. 2010-02-01 rather than orig text of 01/02/10
            elif u"value-type" in new_attrib_dict.keys():
                xml_type = new_attrib_dict[u"value-type"]
                try:
                    type = xml_type_to_val_type[xml_type]
                except KeyError:
                    raise Exception, ("Unknown value-type. Update "
                                      "ods_reader.xml_type_to_val_type")
                val2use = el[0].text # take val from inner text element
            else: # not a data cell
                pass
        else: # el has no attribs - empty cell
            type = mg.VAL_EMPTY_STRING
            val2use = u""
        if type is not None:
            add_type_to_coltypes(coltypes, col_idx=i, type=type)
            orig_fld_name = orig_fld_names[next_fld_name_idx]
            next_fld_name_idx += 1
            val_dict[orig_fld_name] = val2use
    return coltypes, val_dict

def get_ods_xml_size(filename):
    myzip = zipfile.ZipFile(filename)
    size = myzip.getinfo("content.xml").file_size
    return size

def get_ods_dets(lbl_feedback, progbar, prog_steps_for_xml_steps, filename, 
                 has_header=True):
    """
    Returns fld_names, fld_types (dict with field names as keys) and rows 
        (list of lists).
    Limited value in further optimising my code.  The xml parsing stage takes up 
        most of the time.  Using the SAX approach would significantly reduce 
        memory usage but would it save any time overall?  Harder code and may 
        even be slower.
    BTW, XML is a terrible way to store lots of data ;-).
    """
    debug = False
    large = True
    myzip = zipfile.ZipFile(filename)
    cont = myzip.open("content.xml")
    if debug: print("Starting parse process ...")
    progbar.SetValue(prog_steps_for_xml_steps/5.0) # to encourage them ;-)
    lbl_feedback.SetLabel(_("Please be patient. This step may take a couple of "
                            "minutes ..."))
    wx.Yield()
    tree = etree.parse(cont) # the most time-intensive bit
    lbl_feedback.SetLabel(u"")
    wx.Yield()
    next_prog_val = prog_steps_for_xml_steps/2.0
    progbar.SetValue(next_prog_val)
    wx.Yield()
    if debug: print("Finishing parse process.")
    myzip.close()
    root = tree.getroot()
    if debug and not large: print(etree.tostring(root))
    body = None
    for el in root:
        if el.tag.endswith("body"):
            body = el
            break
    if not body:
        exit
    sheet = None
    for el in body:
        if el.tag.endswith("spreadsheet"):
            sheet = el
            break
    if not sheet:
        exit
    tbl = None
    for el in sheet:
        if el.tag.endswith("table"):
            tbl = el
            break
    if not tbl:
        exit
    name = None
    for (key, value) in tbl.attrib.items():
        if key[-5:].endswith("}name"):
            if debug: print("The sheet is named \"%s\"" % value)
    if debug: print("No. rows: %s" % len(tbl))
    rows = []
    orig_fld_names = []
    coltypes = [] # one set per column containing all types
    fld_types = {}
    done_header = False
    if debug:
        print("prog_steps_for_xml_steps: %s" % prog_steps_for_xml_steps)
        print("next_prog_val: %s" % next_prog_val)
    prog_steps_left = prog_steps_for_xml_steps - next_prog_val
    row_n = len(tbl)*1.0
    steps_per_item = prog_steps_left/row_n
    for i, el in enumerate(tbl):
        if el.tag.endswith("table-row"): # should always be one per el
            if has_header and not done_header:
                orig_fld_names = get_fld_names_from_header_row(row=el)
                done_header = True
            else:
                coltypes, val_dicts = dets_from_row(orig_fld_names, coltypes, 
                                                    row=el)
                if val_dicts:
                    rows.append(val_dicts)
        gauge_val = next_prog_val + (i*steps_per_item)
        progbar.SetValue(gauge_val)
        wx.Yield()
    for fld_name, type_set in zip(orig_fld_names, coltypes):
        fld_type = importer.get_overall_fld_type(type_set)
        fld_types[fld_name] = fld_type
    return orig_fld_names, fld_types, rows
