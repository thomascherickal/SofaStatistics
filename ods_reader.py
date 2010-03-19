
import wx
import xml.etree.ElementTree as etree
import zipfile

import my_globals as mg
import lib
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
OR
    <table:table-cell table:number-columns-repeated="236" 
            table:style-name="ACELL-0x95496b8"/>
Example of float cell:
    <table:table-cell office:value-type="float" office:value="1">
    <text:p>1</text:p>
    </table:table-cell>
"""

xml_type_to_val_type = {"string": mg.VAL_STRING, "float": mg.VAL_NUMERIC}
RAW_EL = u"raw element"
ATTRIBS = u"attribs"

def get_ods_xml_size(filename):
    myzip = zipfile.ZipFile(filename)
    size = myzip.getinfo("content.xml").file_size
    return size

def get_contents_xml_tree(lbl_feedback, progbar, prog_step1, prog_step2,
                          filename):
    debug = False
    myzip = zipfile.ZipFile(filename)
    cont = myzip.open("content.xml")
    myzip.close()
    if debug: print("Starting parse process ...")
    progbar.SetValue(prog_step1)
    lbl_feedback.SetLabel(_("Please be patient. The next step may take a "
                            "couple of minutes ..."))
    wx.Yield()
    tree = etree.parse(cont) # the most time-intensive bit
    lbl_feedback.SetLabel(u"")
    wx.Yield()
    progbar.SetValue(prog_step2)
    wx.Yield()
    if debug: print("Finishing parse process.")
    return tree

def after_end_brace(text):
    try:
        idx_end = text.index(u"}") + 1
        endtext = text[idx_end:]
        return endtext
    except ValueError:
        return Exception, u"No curly brace in text: %s" % text

def get_streamlined_attrib_dict(items):
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

def get_tbl(tree):
    debug = False
    large = True
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
        raise Exception, u"Unable to get tree from xml"
    return tbl

def get_has_data_cells(el):
    """
    Checks to see if this table-row element has a table-cell child with data.
    """
    has_data_cells = False
    if not el.tag.endswith("table-row"):
        raise Exception, u"Trying to check for data cells but not a table-row"
    for sub_el in el: # only interested in table cells.  Look in them for data
            # value.
        if not sub_el.tag.endswith("table-cell"):
            continue
        sub_el_attribs = get_streamlined_attrib_dict(sub_el.attrib.items())
        if u"value-type" in sub_el_attribs:
            return True
    return False

def get_data_rows(tbl, inc_empty=True, n=None):
    """
    Even if empty rows are included, they are only included if there is a 
        non-empty row afterwards.
    """
    debug = False
    datarows = []
    prev_empty_rows_to_add = []
    for el in tbl:
        if not el.tag.endswith("table-row"):
            continue
        el_attribs = get_streamlined_attrib_dict(el.attrib.items())
        if u"number-rows-repeated" in el_attribs.keys():
            break
        elif get_has_data_cells(el):
            datarows.extend(prev_empty_rows_to_add)
            prev_empty_rows_to_add = []
            datarows.append(el)            
        else: # empty
            if inc_empty:
                prev_empty_rows_to_add.append(el)
        if n is not None:
            if len(datarows) == n:
                break
    return datarows

def get_fld_names(tbl, has_header, rows_to_sample):
    """
    Get cleaned field names.  Will be used to create row dicts as required by
        importer.add_to_tmp_tbl().
    """
    if has_header:
        datarows = get_data_rows(tbl, inc_empty=False, n=1)
        try:
            row = datarows[0]
            fldnames = get_fld_names_from_header_row(row)
        except IndexError:
            raise Exception, _("Need at least one row to import")
    else:
        max_row_cells = 0
        # Must assess a sample, get max row cells, and auto-build fldnames
        #     stops counting width at last data cell.
        # Colspanning between datacells is counted. 
        # e.g. 1,2,colspan=3,4 is 6 wide
        # e.g. 1,2,colspan=3,4, colspan=12 is still 6 wide
        # If all the rows in the sample have an empty final col (NB we have no 
        #     header row) then we will mistakenly leave that column out. They
        #     have the option of adding a header and trying again.
        datarows = get_data_rows(tbl, inc_empty=False)
        for i, datarow in enumerate(datarows):
            if (i+1) > rows_to_sample:
                break
            # get number of data elements
            cells_n = 0
            prev_empty_cells_to_add = 0
            for el in datarow:
                # Count every cell - look for value-type, empty table cells, 
                #    and number-columns-repeated.  Only count the latter if 
                #    followed by a value-type cell.
                # Only interested in table cells.
                if not el.tag.endswith("table-cell"):
                    continue
                el_attribs = get_streamlined_attrib_dict(el.attrib.items())
                if u"value-type" in el_attribs.keys(): # real data value
                    el_attribs[u"value-type"]
                    cells_n += 1
                    if prev_empty_cells_to_add:
                        cells_n += prev_empty_cells_to_add
                    prev_empty_cells_to_add = 0
                elif len(el) == 0: # an empty cell
                    if prev_empty_cells_to_add:
                        break # if prev not followed by non-empty cell - stop
                    prev_empty_cells_to_add = 1
                elif u"number-columns-repeated" in el_attribs.keys(): # colspans
                    if prev_empty_cells_to_add:
                        break # if prev not followed by non-empty cell - stop
                    prev_empty_cells_to_add = \
                        el_attribs[u"number-columns-repeated"]
                # other
                else:
                    pass
            if cells_n > max_row_cells:
                max_row_cells = cells_n
        fldnames = lib.get_fld_names(max_row_cells)
    return fldnames

def get_fld_names_from_header_row(row):
    """
    As soon as hits an empty cell, stops collecting field names.  This is the
        intended behaviour.
    """
    debug = False
    orig_fld_names = []
    for i, el in enumerate(row):
        if debug: 
            print(u"\nChild element of a table-row: " + etree.tostring(el))
        items = el.attrib.items()
        attrib_dict = get_streamlined_attrib_dict(items)
        # stays None unless there is a date-value or value-type attrib
        fldname = None
        type = None
        if attrib_dict:
            if u"date-value" in attrib_dict.keys():
                fldname = attrib_dict[u"date-value"] # take proper date 
                    # val e.g. 2010-02-01 rather than orig text of 01/02/10
            elif u"value-type" in attrib_dict.keys():
                fldname = el[0].text # take val from inner text element
            else: # not a data cell
                pass
                # e.g. <table:table-cell table:number-columns-repeated="254" 
                # table:style-name="ACELL-0x88a3bc8"/>
        if fldname is not None:
            if fldname in orig_fld_names:
                raise Exception, _("Field name \"%s\" has been repeated") % \
                                 fldname
            orig_fld_names.append(fldname)
        else:
            break # just hit an empty cell - we're done.
    return importer.process_fld_names(orig_fld_names)

def get_ods_dets(lbl_feedback, progbar, tbl, fldnames, prog_steps_for_xml_steps, 
                 next_prog_val, has_header=True):
    """
    Returns fld_types (dict with field names as keys) and rows (list of dicts).
    Limited value in further optimising my code.  The xml parsing stage takes up 
        most of the time.  Using the SAX approach would significantly reduce 
        memory usage but would it save any time overall?  Harder code and may 
        even be slower.
    BTW, XML is a terrible way to store lots of data ;-).
    """
    debug = False
    large = True
    for (key, value) in tbl.attrib.items():
        if key[-5:].endswith("}name"):
            if debug: print("The sheet is named \"%s\"" % value)
    rows = []
    coltypes = [] # one set per column containing all types
    fld_types = {}
    if debug:
        print("prog_steps_for_xml_steps: %s" % prog_steps_for_xml_steps)
        print("next_prog_val: %s" % next_prog_val)
    prog_steps_left = prog_steps_for_xml_steps - next_prog_val
    datarows = get_data_rows(tbl, inc_empty=True)
    row_n = len(datarows)*1.0
    steps_per_item = prog_steps_left/row_n
    if debug: print("Has %s rows including any headers" % row_n)
    for i, datarow in enumerate(datarows):
        try:
            if not (has_header and i == 0):
                coltypes, valdict = dets_from_row(fldnames, coltypes, datarow)
                if valdict:
                    rows.append(valdict)
                gauge_val = next_prog_val + (i*steps_per_item)
                progbar.SetValue(gauge_val)
                wx.Yield()
        except Exception, e:
            raise Exception, (u"Error getting details from row idx %s. "
                              u"Orig err: %s" % (i, e))
    for fldname, type_set in zip(fldnames, coltypes):
        fld_type = importer.get_overall_fld_type(type_set)
        fld_types[fldname] = fld_type
    return fld_types, rows

def get_tbl_cell_el_dets(row):
    """
    Get enough details to filter out non-data cells and for extracting data 
        from the data cells.  Must handle Calc and Gnumeric etc.
    OK - <table:table-cell table:style-name="ACELL-0x95496b8" 
        office:value-type="float" office:value="1">
        <text:p>1</text:p>
        </table:table-cell>
    empty - <table:table-cell table:style-name="ACELL-0x95496b8"/>
    empty - <table:table-cell table:number-columns-repeated="236" 
        table:style-name="ACELL-0x95496b8"/>
    """
    tbl_cell_el_dets = []
    for el in row:
        if not el.tag.endswith(u"table-cell"):
            continue
        attribs = get_streamlined_attrib_dict(el.attrib.items())
        el_dict = {RAW_EL: el, ATTRIBS: attribs}
        tbl_cell_el_dets.append(el_dict)  
    return tbl_cell_el_dets

def add_type_to_coltypes(coltypes, col_idx, type):
    try:
        coltypes[col_idx].add(type)
    except IndexError:
        coltypes.append(set([type]))    

def update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, type, 
                              val2use):
    add_type_to_coltypes(coltypes, col_idx, type)
    fldname = fldnames[col_idx]
    valdict[fldname] = val2use

def dets_from_row(fldnames, coltypes, row):
    """
    Update coltypes and return dict of values in row (using fldnames as keys).
    If there are more cells than fldnames, raise exception.  Suggest user adds
        header row, checks data, and tries again.
    """
    debug = False
    verbose = False
    large = False
    valdict = {}
    tbl_cell_el_dets = get_tbl_cell_el_dets(row)
    col_idx = 0
    for el_det in tbl_cell_el_dets:
        attrib_dict = el_det[ATTRIBS]
        # the defaults unless overridden by actual data
        val2use = u""
        type = mg.VAL_EMPTY_STRING
        if u"date-value" in attrib_dict.keys():
            type = mg.VAL_DATETIME
            val2use = attrib_dict[u"date-value"] # take proper date 
                # val e.g. 2010-02-01 rather than orig text of 01/02/10
            update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, 
                                      type, val2use)
            if col_idx == len(fldnames) - 1:
                break
            col_idx += 1
        elif u"value-type" in attrib_dict.keys():
            xml_type = attrib_dict[u"value-type"]
            try:
                type = xml_type_to_val_type[xml_type]
            except KeyError:
                raise Exception, (u"Unknown value-type. Update "
                                  u"ods_reader.xml_type_to_val_type")
            val2use = el_det[RAW_EL][0].text # take val from inner text element
            update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, 
                                      type, val2use)
            if col_idx == len(fldnames) - 1:
                break
            col_idx += 1
        elif u"number-columns-repeated" in attrib_dict.keys():
            colspan = int(attrib_dict[u"number-columns-repeated"])
            # need an empty cell for each column spanned (until hit max cols)
            for i in range(colspan):
                update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, 
                                          type=mg.VAL_EMPTY_STRING, val2use=u"")
                if col_idx == len(fldnames) - 1:
                    break
                col_idx += 1
        elif len(el_det[RAW_EL]) == 0: # single empty cell
            update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, 
                                      type=mg.VAL_EMPTY_STRING, val2use=u"")
            if col_idx == len(fldnames) - 1:
                break
            col_idx += 1
    if debug: print(unicode(valdict))
    return coltypes, valdict