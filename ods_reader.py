
import re
import time
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

XML_TYPE_FLOAT = u"float"
xml_type_to_val_type = {"string": mg.VAL_STRING, 
                        XML_TYPE_FLOAT: mg.VAL_NUMERIC}
RAW_EL = u"raw element"
ATTRIBS = u"attribs"
COLS_REP = u"number-columns-repeated"
ROWS_REP = u"number-rows-repeated"
VAL_TYPE = u"value-type"
VALUE = u"value"
DATE_VAL = u"date-value"
FORMULA = u"formula"

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
    lbl_feedback.SetLabel(_("Please be patient. The next step may take a few "
                            "minutes ..."))
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
        raise Exception(u"Unable to get tree from xml")
    return tbl

def get_has_data_cells(el):
    """
    Checks to see if this table-row element has a table-cell child with data.
    """
    has_data_cells = False
    if not el.tag.endswith("table-row"):
        raise Exception(u"Trying to check for data cells but not a table-row")
    for sub_el in el: # only interested in table cells.  Look in them for data
            # value.
        if not sub_el.tag.endswith("table-cell"):
            continue
        sub_el_attribs = get_streamlined_attrib_dict(sub_el.attrib.items())
        if VAL_TYPE in sub_el_attribs:
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
        if ROWS_REP in el_attribs:
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

def get_col_rep(el_attribs):
    """
    Returns number of times to display column. number-columns-repeated="2" means 
        display twice (not really repeating twice but repeating once).
    Cells with or without value content can repeat.
    With data: 
        <table:table-cell table:number-columns-repeated="2" 
                office:value-type="float" office:value="1">
            <text:p>1</text:p>
        </table:table-cell>
    will be 1, 1
    Without data:
        <table:table-cell table:number-columns-repeated="4"/>
    will be ,,,
    """
    if COLS_REP in el_attribs:
        colrep = int(el_attribs[COLS_REP])
    else:
        colrep = 1
    return colrep

def get_fld_names(tbl, has_header, rows_to_sample):
    """
    Get cleaned field names.  Will be used to create row dicts as required by
        importer.add_to_tmp_tbl().
    """
    debug = False
    if has_header:
        datarows = get_data_rows(tbl, inc_empty=False, n=1)
        try:
            row = datarows[0]
            fldnames = get_fld_names_from_header_row(row)
        except IndexError:
            raise Exception(_("Need at least one row to import"))
    else:
        max_row_cells = 0
        # Must assess a sample, get max row cells, and auto-build fldnames
        #     stops counting width at last data cell.
        # Colspanning between datacells is counted. 
        # e.g. 1,2,colspan=3,4 is 6 wide
        # e.g. 1,2,colspan=3,4, colspan=12 is still 6 wide
        # If all the rows in the sample have an empty final col (NB we have no 
        #     header row) then we will mistakenly leave that column out. Users
        #     have the option of adding a header and trying again.
        datarows = get_data_rows(tbl, inc_empty=False)
        for i, datarow in enumerate(datarows):
            if (i+1) > rows_to_sample:
                break
            # get number of data elements
            cells_n = 0
            prev_empty_cells_to_add = 0
            for el in datarow:
                # Count every cell - only count empty cells (inc repeated empty
                #     cells if followed by a value-type cell.
                # Only interested in table cells.
                if not el.tag.endswith("table-cell"):
                    continue
                el_attribs = get_streamlined_attrib_dict(el.attrib.items())
                if VAL_TYPE in el_attribs: # real data value(s)
                    # prev ns are counted iff followed by data cell(s) 
                    if prev_empty_cells_to_add:
                        cells_n += prev_empty_cells_to_add
                    prev_empty_cells_to_add = 0
                    cells_n += get_col_rep(el_attribs)
                elif len(el) == 0: # just an an empty cell (possibly repeated)
                    prev_empty_cells_to_add += get_col_rep(el_attribs)
                # other
                else:
                    pass
            if cells_n > max_row_cells:
                max_row_cells = cells_n
        fldnames = lib.get_n_fld_names(max_row_cells)
        if debug: print(fldnames)
    return fldnames

def get_el_inner_val(el):
    """
    Sometimes the value is not in the first item in el
    """
    debug = False
    text2return = []
    i = 0
    while True:
        try:
            item_text = el[i].text
            if item_text is not None:
                text2return.append(item_text)
        except IndexError, e:
           break
        i += 1
    if text2return:
        if debug: print(etree.tostring(el))
        return u"\n".join(text2return)
    else:
        if debug: print("NO TEXT in el - " + etree.tostring(el))
        return u""

def get_fld_names_from_header_row(row):
    """
    As soon as hits an empty cell, stops collecting field names.  This is the
        intended behaviour.
    If a header cell is repeated, raise an exception.
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
            if COLS_REP in attrib_dict and VAL_TYPE in attrib_dict:
                raise Exception(_("Field name \"%s\" cannot be repeated")
                                % get_el_inner_val(el))
            elif DATE_VAL in attrib_dict:
                fldname = attrib_dict[DATE_VAL] # take proper date 
                    # val e.g. 2010-02-01 rather than orig text of 01/02/10
            elif VAL_TYPE in attrib_dict:
                fldname = get_el_inner_val(el) #take val from inner text element
            else: # not a data cell
                pass # fail to set fldname
                # e.g. <table:table-cell table:number-columns-repeated="254" 
                # table:style-name="ACELL-0x88a3bc8"/>
        if fldname is None:
            break # just hit an empty cell - we're done.
        else:
            if fldname in orig_fld_names:
                raise Exception(_("Field name \"%s\" has been repeated")
                                % fldname)
            orig_fld_names.append(fldname)
    return importer.process_fld_names(orig_fld_names)

def get_ods_dets(lbl_feedback, progbar, tbl, fldnames, faulty2missing_fld_list,
                 prog_steps_for_xml_steps, next_prog_val, has_header=True):
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
            raise Exception(u"Error getting details from row idx %s."
                            u"\nCaused by error: %s" % (i, lib.ue(e)))
    for fldname, type_set in zip(fldnames, coltypes):
        fld_type = importer.get_best_fld_type(fldname, type_set,
                                              faulty2missing_fld_list)
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
    empty - <table:table-cell/>
    """
    debug = False
    tbl_cell_el_dets = []
    for el in row:
        if debug: print(el.tag)
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

def process_cells(attrib_dict, coltypes, col_idx, fldnames, valdict, type, 
                  val2use):
    """
    Process cell (or cells if col repeating).  Update types and valdict.
    Return bolcontinue, col_idx to use next.
    """
    bolcontinue = True
    for i in range(get_col_rep(attrib_dict)):
        update_types_and_val_dict(coltypes, col_idx, fldnames, valdict, type, 
                                  val2use)
        if col_idx == len(fldnames) - 1:
            bolcontinue = False
            break
        col_idx += 1
    return bolcontinue, col_idx

def extract_date_if_possible(el_det, attrib_dict, xml_type, type):
    """
    Needed because Google Docs spreadsheets return timestamp as a float with a 
        text format e.g. 40347.8271296296 and 6/18/2010 19:51:04.  If a float,
        check to see if a valid datetime anyway.  NB date text might be invalid 
        and not align with float value e.g. 
    <table:table-cell table:style-name="ce22" office:value-type="float" 
        office:value="40413.743425925924">
    <text:p>50/23/2010 17:50:32</text:p>
    """
    debug = False
    text = get_el_inner_val(el_det[RAW_EL]) # get val from inner txt el
    if xml_type == XML_TYPE_FLOAT:
        try:
            # is it really a date even though not formally formatted as a date?
            # see if text contains multiple /s
            google_docs_default_date = u"%m/%d/%Y" # OK if already in list
            mg.OK_DATE_FORMATS.append(google_docs_default_date)
            usable_datetime = lib.is_usable_datetime_str(raw_datetime_str=text)
            # OK for this purpose to accept invalid dates - we calculate the 
            # datetime from the number anyway - this is just an indicator that 
            # this is meant to be a date e.g. 50/23/2010 17:50:32.
            attempted_date = text.count(u"/") > 1
            if usable_datetime or attempted_date:
                str_float = attrib_dict.get(VALUE)
                days_since_1900 = str_float
                if days_since_1900:
                    val2use = lib.dates_1900_to_datetime_str(days_since_1900)
                    type = mg.VAL_DATE
                    if debug: print(str_float, val2use)
            else:
                val2use = text
        except Exception, e:
            val2use = text
        mg.OK_DATE_FORMATS.pop() # back to normal
    else:
        val2use = text
    return val2use, type

def dets_from_row(fldnames, coltypes, row):
    """
    Update coltypes and return dict of values in row (using fldnames as keys).
    If there are more cells than fldnames, raise exception.  Suggest user adds
        header row, checks data, and tries again.
    Formula cells with values have a val type attrib as well and will be picked 
        up that way first.  It is only if they haven't that they count as an 
        empty cell.  Important not to just skip empty formulae cells.
    """
    debug = False
    verbose = False
    large = False
    valdict = {}
    tbl_cell_el_dets = get_tbl_cell_el_dets(row)
    if debug and verbose:
        print(row)
        print(tbl_cell_el_dets)
    col_idx = 0
    for el_det in tbl_cell_el_dets:
        attrib_dict = el_det[ATTRIBS] # already streamlined
        # the defaults unless overridden by actual data
        val2use = u""
        type = mg.VAL_EMPTY_STRING
        if DATE_VAL in attrib_dict:
            type = mg.VAL_DATE
            val2use = attrib_dict[DATE_VAL] # take proper date value
                            # e.g. 2010-02-01 rather than orig text of 01/02/10
            if debug: print(val2use)
            bolcontinue, col_idx = process_cells(attrib_dict, coltypes, col_idx, 
                                               fldnames, valdict, type, val2use)
            if not bolcontinue:
                break
        elif VAL_TYPE in attrib_dict:
            xml_type = attrib_dict[VAL_TYPE]
            try:
                type = xml_type_to_val_type[xml_type]
            except KeyError:
                raise Exception(u"Unknown value-type. Update "
                                u"ods_reader.xml_type_to_val_type")
            # NB need to treat as datetime if it really is even though not
            # properly tagged as a date-value (e.g. Google Docs spreadsheets)
            val2use, type = extract_date_if_possible(el_det, attrib_dict, 
                                                     xml_type, type)
            if debug: print(val2use)
            bolcontinue, col_idx = process_cells(attrib_dict, coltypes, col_idx, 
                                               fldnames, valdict, type, val2use)
            if not bolcontinue:
                break
        elif len(el_det[RAW_EL]) == 0 or FORMULA in attrib_dict: # empty cell(s)
            # need empty cell for each column spanned (until hit max cols)
            bolcontinue, col_idx = process_cells(attrib_dict, coltypes, col_idx, 
                                         fldnames, valdict, 
                                         type=mg.VAL_EMPTY_STRING, val2use=u"")
            if not bolcontinue:
                break
        else:
            pass
    if debug: print(unicode(valdict))
    return coltypes, valdict
