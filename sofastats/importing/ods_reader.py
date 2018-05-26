
import wx
import xml.etree.ElementTree as etree
import zipfile

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import importer

"""
NB need to handle ods from OpenOffice Calc, and Gnumeric at least. Some 
differences.

NB some internal xml files are mainly empty yet they still have to be parsed.
They may even be very large e.g. 100MB! Extremely inefficient under these 
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
    
get_ods_dets() is the most main starting point. It is supplied with fldnames 
already by get_ok_fldnames() which uses get_tbl() as an input and gets and
processes the first data_row.

get_ods_dets gets data rows (actually table-row elements) with get_rows().

Then we loop through rows (table-row elements) and for each row get a list of 
field types (as identified in the actual row) and a values dictionary using the 
fldnames as keys using dets_from_row().

For each cell element in the row, we use process_cells() to process individual 
cell (or cells if col repeating). Update types and valdict.

There is a problem if the number of data cells exceed the number of fldnames 
identified.
"""

XML_TYPE_STR = u"string"
XML_TYPE_FLOAT = u"float"
XML_TYPE_PERC = u"percentage"
XML_TYPE_CURRENCY = u"currency"
XML_TYPE_FRACTION = u"fraction"
XML_TYPE_BOOL = u"boolean"
XML_TYPE_TIME = u"time"
XML_TYPE_DATE = u"date"
XML_TYPE_SCIENTIFIC = u"scientific"
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

def get_contents_xml_tree(filename, lbl_feedback=None, progbar=None, 
        prog_step1=None, prog_step2=None):
    debug = False
    myzip = zipfile.ZipFile(filename)
    cont = myzip.open("content.xml")
    myzip.close()
    if debug: print("Starting parse process ...")
    if progbar is not None: progbar.SetValue(min(prog_step1, mg.IMPORT_GAUGE_STEPS))
    if lbl_feedback is not None:
        lbl_feedback.SetLabel(_("Please be patient. The next step may take a "
            "few minutes ..."))
    wx.Yield()
    tree = etree.parse(cont) # the most time-intensive bit
    if lbl_feedback is not None: lbl_feedback.SetLabel(u"")
    wx.Yield()
    if progbar is not None: progbar.SetValue(min(prog_step2, mg.IMPORT_GAUGE_STEPS))
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
    if body is None:
        raise Exception("No body found in for XML")
    sheet = None
    for el in body:
        if el.tag.endswith("spreadsheet"):
            sheet = el
            break
    if sheet is None:
        raise Exception("No sheet found in for XML")
    tbl = None
    for el in sheet:
        if el.tag.endswith("table"):
            tbl = el
            break
    if tbl is None:
        raise Exception(u"Unable to get tree from xml")
    return tbl

def get_has_data_cells(el):
    """
    Checks to see if this table-row element has a table-cell child with data.
    """
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

def get_rows(tbl, inc_empty=True, n=None):
    """
    Note - not rows of values but element rows. Need special processing to work 
    with.
    
    Even if empty rows are included, they are only included if there is a 
    non-empty row afterwards (eventually).

    n -- usually None meaning that all rows are extracted. Only non-empty rows
    are included in collected rows and thus the count if inc_empty=False.
    """
    datarows = []
    prev_empty_rows_to_add = []
    for el in tbl:
        is_datarow = el.tag.endswith("table-row")
        if not is_datarow:
            continue
        el_attribs = get_streamlined_attrib_dict(el.attrib.items())
        repeated = ROWS_REP in el_attribs
        has_data = get_has_data_cells(el)
        deemed_end = (not has_data and repeated)
        empty_row = (not has_data and not repeated)
        ## Process data row
        if has_data:  ## put empty rows in first (if any there to add) then the data row
            datarows.extend(prev_empty_rows_to_add)  ## only something there if inc_empty
            prev_empty_rows_to_add = []  ## refresh
            if repeated:
                n_same_rows = int(el_attribs[ROWS_REP])
                for unused in range(n_same_rows):
                    datarows.append(el)
            else:
                datarows.append(el)            
        elif deemed_end:
            break
        elif empty_row and inc_empty:
            prev_empty_rows_to_add.append(el)
        else:
            continue
        ## Stop if enough data
        if n is not None:
            if len(datarows) >= n:
                datarows = datarows[:n]  ## May have repeated rows added which bring total rows to more than allowed n
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

def get_ok_fldnames(tbl, has_header, rows_to_sample, headless, 
        force_quickcheck=False):
    """
    Get cleaned field names. Will be used to create row dicts as required by
        importer.add_to_tmp_tbl().
    Much more efficient if has a header. Otherwise need to sample as many as 
        500 rows to confidently establish number of cols.
    """
    debug = False
    if has_header:
        rows = get_rows(tbl, inc_empty=False, n=1)
        try:
            row = rows[0]
            ok_fldnames = get_fldnames_from_header_row(row, headless,
                force_quickcheck)
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
        rows = get_rows(tbl, inc_empty=False)
        for i, row in enumerate(rows):
            if (i+1) > rows_to_sample:
                break
            # get number of data elements
            cells_n = 0
            prev_empty_cells_to_add = 0
            for el in row:
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
        ok_fldnames = lib.get_n_fldnames(max_row_cells)
        if debug: print(ok_fldnames)
    return ok_fldnames

def get_el_inner_val(el):
    """
    Sometimes the value is not in the first item in el.
    Need to handle cells with multiple lines. Each is an indiv subel.
    Each line may have subelement with text.
    Each element may have a tail as well.
    """
    debug = False
    if debug: print(len(el))
    text2return = []
    subels = list(el)
    for subel in subels:
        line_text = ""
        subel_text = subel.text
        if subel_text is not None:
            line_text += subel_text
        else:
            continue
        subel_tail = subel.tail
        if subel_tail is not None:
            line_text += subel_tail
        innermost_els = list(subel)
        for innermost_el in innermost_els:
            innermost_el_text = innermost_el.text
            if innermost_el_text is not None:
                line_text += innermost_el_text
            innermost_el_tail = innermost_el.tail
            if innermost_el_tail is not None:
                line_text += innermost_el_tail
        text2return.append(line_text)
    if text2return:
        if debug: print("Element as string - " + etree.tostring(el))
        return u"\n".join(text2return)
    else:
        if debug: print("NO TEXT in el - " + etree.tostring(el))
        return u""

def get_fldnames_from_header_row(row, headless=False, force_quickcheck=False):
    """
    Work across row collecting fldnames. Stop when hit end of data columns. NB 
    an empty cell is allowed as part of a dataset if deemed to be a divider.

    Only single column dividers are allowed.

    Sometimes grab one cell too many (empty cell may have been a divider but 
    turned out not to be) so need to remove last fldname.

    An empty cell is deemed to be a divider unless a column-repeating empty 
    cell, or two empty cells in a row). 

    OK to grab an empty string for a field name if a divider column (empty field 
    names will be autofilled later). 

    Only empty string field names are allowed to be repeated (they will be made 
    distinct when autofilled later).

    One oddity of this approach is that a csv or xls version of the same file 
    which has a blank field label as the final col will have that col autonamed 
    whereas here it and all its data will be ignored. 
    """
    debug = False
    orig_fldnames = []
    last_was_empty = False # init
    for el in row:
        if debug: print(u"\nChild element of table-row: " + etree.tostring(el))
        el_attribs = get_streamlined_attrib_dict(el.attrib.items())
        colrep = get_col_rep(el_attribs)
        if debug: print(el_attribs)
        if DATE_VAL in el_attribs:
            if debug: print("Getting fldname(s) from DATE_VAL")
            fldnames = [el_attribs[DATE_VAL], ]*colrep # take proper date 
                # val e.g. 2010-02-01 rather than orig text of 01/02/10
            last_was_empty = False
        elif VAL_TYPE in el_attribs:
            if debug: print("Getting fldname(s) from inner val")
            fldnames = [get_el_inner_val(el), ]*colrep  ## take val from inner text element
            last_was_empty = False
        else: 
            if debug: print("No fldname provided by cell")
            """
            No data in cell but still may be needed as part of data e.g. if a
            divider column. Unless it is the last column (defined as second in a
            row or the start of multiple empty).

            Set fldnames to empty string if not last column.
            """
            if last_was_empty:
                break
            elif colrep > 1:  ## i.e. not just a single empty divider column
                break
            fldnames = [u"", ]
            last_was_empty = True
        if debug: print(fldnames)
        orig_fldnames.extend(fldnames)
    # If last fldname is empty, remove it. We had to give it a chance as a 
    # potential divider column but it clearly wasn't.
    if orig_fldnames[-1] == u"":
        orig_fldnames.pop()
    if debug: print(orig_fldnames)
    processed_fldnames = importer.process_fldnames(orig_fldnames, headless,
        force_quickcheck)
    if debug: print(processed_fldnames)
    return processed_fldnames

def get_ods_dets(lbl_feedback, progbar, tbl, fldnames, faulty2missing_fld_list,
        prog_steps_for_xml_steps, next_prog_val, has_header=True, 
        headless=False):
    """
    Returns fldtypes (dict with field names as keys) and rows (list of dicts).
    
    Re: fldtypes, given that there may be data mismatches within fields, need to 
    get user decision when there is more than one option. Do this by collecting 
    all types (e.g. date, number) within col and an example of the first 
    mismatch per col.
    
    Limited value in further optimising my code. The xml parsing stage takes up 
    most of the time. Using the SAX approach would significantly reduce memory 
    usage but would it save any time overall? Harder code and may even be 
    slower.
    
    BTW, XML is a terrible way to store lots of data ;-).
    """
    debug = False
    for (key, value) in tbl.attrib.items():
        if key[-5:].endswith("}name"):
            if debug: print("The sheet is named \"%s\"" % value)
    datarows = []
    col_type_sets = [] # one set per column containing all types in column
    fldtypes = {}
    if debug:
        print("prog_steps_for_xml_steps: %s" % prog_steps_for_xml_steps)
        print("next_prog_val: %s" % next_prog_val)
    prog_steps_left = prog_steps_for_xml_steps - next_prog_val
    rows = get_rows(tbl, inc_empty=True)
    row_n = len(rows)*1.0
    if (has_header and row_n == 1) or (not has_header and row_n == 0):
        raise Exception(u"No data rows identified. Either there were no "
            u"data rows at all or there were too many empty rows before the "
            u"first data row.")
    steps_per_item = prog_steps_left/row_n
    if debug: print("Has %s rows including any headers" % row_n)
    fld_first_mismatches = [None,]*len(fldnames) # init
    """
    1) Process all rows and cols to get data (datarows), the field types found 
    in each col (col_type_sets), and information required to enable user to be
    confident that there are in fact mismatches (fld_first_mismatches).
    """
    for row_num, row in enumerate(rows, 1):
        try:
            if has_header and row_num == 1:
                continue
            col_type_sets, valdict = dets_from_row(fldnames, col_type_sets, 
                fld_first_mismatches, row, row_num)
            if valdict:
                datarows.append(valdict)
            gauge_val = min(next_prog_val + ((row_num-1)*steps_per_item),
                mg.IMPORT_GAUGE_STEPS)
            progbar.SetValue(gauge_val)
            wx.Yield()
        except Exception as e:
            raise Exception(u"Error getting details from row %s."
                u"\nCaused by error: %s" % (row_num, b.ue(e)))
    """
    2) Get user decisions on each field where there are potentially more than 
    one data type.
    """
    for fldname, type_set, first_mismatch in zip(fldnames, col_type_sets, 
            fld_first_mismatches):
        fldtype = importer.get_best_fldtype(fldname, type_set,
            faulty2missing_fld_list, first_mismatch, headless)
        fldtypes[fldname] = fldtype
    return fldtypes, datarows

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

def add_type_to_coltypes(coltypes, col_idx, coltype):
    try:
        coltypes[col_idx].add(coltype)
    except IndexError:
        coltypes.append(set([coltype]))    

def update_types_and_valdict(col_type_sets, col_idx, fldnames, valdict, coltype, 
        val2use):
    """
    col_type_sets -- list of sets - each set is coltypes for given col
    """
    add_type_to_coltypes(col_type_sets, col_idx, coltype)
    try:
        fldname = fldnames[col_idx]
    except IndexError:
        raise Exception(u"Didn't get enough field names to cover "
            u"all the data cells.")
    valdict[fldname] = val2use

def process_cells(attrib_dict, col_type_sets, fld_first_mismatches, col_idx, 
        fldnames, valdict, coltype, val2use, row_num):
    """
    Process cell (or cells if col repeating) in row. Update types and valdict.
    Sniff for data type mismatches to pass back out.
    Return next col_idx to process.
    """
    # If col is repeated, will loop through multiple times. Usually just once.
    # This single el is repeated if col-repeat.
    for unused in range(get_col_rep(attrib_dict)):
        update_types_and_valdict(col_type_sets, col_idx, fldnames, valdict, 
            coltype, val2use)
        col_type_set = col_type_sets[col_idx]
        mismatch_in_col = (fld_first_mismatches[col_idx] is not None) # initialised with Nones
        if not mismatch_in_col: # sniff for the first (not interested in subsequent)
            main_type_set = col_type_set.copy()
            main_type_set.discard(mg.VAL_EMPTY_STRING)
            n_types_in_col = len(main_type_set) # we don't count missing as a separate type
            if n_types_in_col == 2: # can't all match - now more than one type
                main_type_set.discard(coltype) # leaving only the expected type
                    # given we have the one just added and the previous which we 
                    # can treat as the expected type.
                expected_fldtype = list(main_type_set)[0]
                mismatch_in_col = (importer.FIRST_MISMATCH_TPL %
                    {u"row": row_num, u"value": val2use, 
                    u"fldtype": expected_fldtype})
                fld_first_mismatches[col_idx] = mismatch_in_col # will never collect mismatch for this col again
            elif n_types_in_col > 2:
                raise Exception(u"Should have identified first mismatch when "
                    u"reached two non-missing col types but here we are with "
                    u"three. Something must be wrong.")
        idx_final_col = len(fldnames) - 1
        col_idx += 1
        if col_idx > idx_final_col:
            break
    return col_idx

def get_val_and_type(attrib_dict, el_det):
    """
    Not straight forward - the value we want is in different places depending on
    value type.
    """
    debug = False
    xml_type = attrib_dict[VAL_TYPE]
    xml_value = attrib_dict.get(VALUE)
    text = get_el_inner_val(el_det[RAW_EL]) # get val from inner txt el
    if debug: print(xml_type, xml_value, text)
    if xml_type == XML_TYPE_STR:
        val2use = text
        coltype = mg.VAL_STRING
    elif xml_type == XML_TYPE_FLOAT:
        """
        For Scientific, Fraction, and Date etc always safest to use xml_value 
        rather than text.
        
        NB need to treat as datetime if it really is even though not
        properly tagged as a date-value (e.g. Google Docs spreadsheets).
        
        Needed because Google Docs spreadsheets return timestamp as a float with 
        a text format e.g. 40347.8271296296 and 6/18/2010 19:51:04. If a float, 
        check to see if a valid datetime anyway. NB date text might be invalid 
        and not align with float value e.g. 
        <table:table-cell table:style-name="ce22" office:value-type="float" 
            office:value="40413.743425925924">
        <text:p>50/23/2010 17:50:32</text:p>
        """
        # unless a date
        val2use = xml_value
        coltype = mg.VAL_NUMERIC
        try:
            # is it really a date even though not formally formatted as a date?
            # see if text contains multiple /s
            google_docs_default_date = u"%m/%d/%Y" # OK if already in list
            probable_date_formats = mg.OK_DATE_FORMATS[:]
            probable_date_formats.append(google_docs_default_date)
            try: # so we don't assume 2136 is a year
                probable_date_formats.remove(u"%Y")
            except ValueError:
                pass # If not there, OK that removing it failed
            usable_datetime = lib.DateLib.is_usable_datetime_str(
                raw_datetime_str=text, ok_date_formats=probable_date_formats)
            # OK for this purpose to accept invalid dates - we calculate the 
            # datetime from the number anyway - this is just an indicator that 
            # this is meant to be a date e.g. 50/23/2010 17:50:32.
            attempted_date = text.count(u"/") > 1
            if usable_datetime or attempted_date:
                days_since_1900 = xml_value
                if days_since_1900:
                    val2use = lib.DateLib.dates_1900_to_datetime_str(
                        days_since_1900)
                    coltype = mg.VAL_DATE
                    if debug: print(xml_value, val2use)
        except Exception:
            pass # Unable to detect if date or not so will fall back to string.
    elif xml_type == XML_TYPE_PERC:
        """
        <table:table-cell table:style-name="ce2" office:value-type="percentage" 
                office:value="23">
            <text:p>2300.00%</text:p>
        </table:table-cell>
        """
        try:
            val2use = str(100*float(xml_value))
            coltype = mg.VAL_NUMERIC
        except Exception:
            val2use = text
            coltype = mg.VAL_STRING
    elif xml_type == XML_TYPE_CURRENCY:
        """
        <table:table-cell table:style-name="ce3" office:value-type="currency" 
                office:currency="NZD" office:value="24">
            <text:p>$24.00</text:p>
        </table:table-cell>
        """
        val2use = xml_value
        coltype = mg.VAL_NUMERIC
    elif xml_type == XML_TYPE_TIME:
        """
        <table:table-cell table:style-name="ce6" office:value-type="time" 
                office:time-value="PT672H00M00S">
            <text:p>00:00:00</text:p>
        </table:table-cell>
        """
        val2use = text
        coltype = mg.VAL_DATE
    elif xml_type == XML_TYPE_BOOL:
        """
        <table:table-cell table:style-name="ce8" office:value-type="boolean" 
                office:boolean-value="31">
            <text:p>TRUE</text:p>
        </table:table-cell>
        """
        val2use = text
        coltype = mg.VAL_STRING
    else:
        if debug: print(attrib_dict)
        val2use = text
        coltype = mg.VAL_STRING
    return val2use, coltype

def get_vals_from_row(row, n_flds):
    """
    Get rows back as list of lists of vals (as unicode ready for display).
    
    Based on dets_from_row - which lumps more responsibilities for efficiency 
    reasons.
    
    Note - must handle number-columns-repeated e.g. 
    <table:table-cell table:number-columns-repeated="2" 
            office:value-type="float" office:value="3">
        <text:p>3</text:p>
    </table:table-cell>
    is 3, 3 not just a single 3
    """
    debug = False
    vals = []
    tbl_cell_el_dets = get_tbl_cell_el_dets(row)
    cols = 0
    got_enough = False
    for el_det in tbl_cell_el_dets:
        if got_enough:
            break
        attrib_dict = el_det[ATTRIBS] # already streamlined
        # the defaults unless overridden by actual data
        val2use = None
        if DATE_VAL in attrib_dict:
            val2use = attrib_dict[DATE_VAL] # take proper date value e.g. 2010-02-01 rather than orig text of 01/02/10
        elif VAL_TYPE in attrib_dict:
            val2use, unused = get_val_and_type(attrib_dict, el_det)
        elif len(el_det[RAW_EL]) == 0 or FORMULA in attrib_dict: # empty cell(s) need empty cell for each column spanned (until hit max cols)
            val2use=u""
        else:
            continue
        if debug: print(val2use)
        for unused in range(get_col_rep(attrib_dict)):
            vals.append(val2use)
            cols += 1
            if cols == n_flds:
                got_enough = True
                break
    if debug: print(vals)
    return vals

def dets_from_row(fldnames, col_type_sets, fld_first_mismatches, row, row_num):
    """
    Update col_type_sets and return dict of values in row (using fldnames as 
    keys).
    
    If there are more cells than fldnames, raise exception. Suggest user adds
    header row, checks data, and tries again.
    
    Formula cells with values have a val type attrib as well and will be picked 
    up that way first. It is only if they haven't that they count as an empty 
    cell. Important not to just skip empty formulae cells.
    
    fld_first_mismatches --  list with an item for each fld. Init to None for 
    each. If hit a mismatch, set for that index if not already set (only want 
    the first per fld).
    """
    debug = False
    verbose = False
    valdict = {}
    tbl_cell_el_dets = get_tbl_cell_el_dets(row)
    if debug and verbose:
        print(row)
        print(tbl_cell_el_dets)
    col_idx = 0 # Note may be several tbl_cell_el_dets in a single col so can't 
    # just enumerate. May be incremeneted inside process_cells because of col-repeat
    for el_det in tbl_cell_el_dets: # moving across row through col cells (Note - some cells span multiple cols if col-repeat)
        attrib_dict = el_det[ATTRIBS] # already streamlined
        # the defaults unless overridden by actual data
        val2use = u""
        if DATE_VAL in attrib_dict:
            coltype = mg.VAL_DATE
            val2use = attrib_dict[DATE_VAL] # take proper date value e.g. 2010-02-01 rather than orig text of 01/02/10
            if debug: print(val2use)
            # We pass over to process_cells which handle col-repeats. At the end 
            # of that process we need to know what col_idx we are on. 
            col_idx = process_cells(attrib_dict, col_type_sets, 
                fld_first_mismatches, col_idx, fldnames, valdict, coltype, 
                val2use, row_num)
        elif VAL_TYPE in attrib_dict:
            coltype = mg.VAL_EMPTY_STRING
            val2use, coltype = get_val_and_type(attrib_dict, el_det)
            if debug: print(val2use)
            col_idx = process_cells(attrib_dict, col_type_sets, 
                fld_first_mismatches, col_idx, fldnames, valdict, coltype, 
                val2use, row_num)
        elif len(el_det[RAW_EL]) == 0 or FORMULA in attrib_dict: # empty cell(s)
            # need empty cell for each column spanned (until hit max cols)
            coltype = mg.VAL_EMPTY_STRING
            col_idx = process_cells(attrib_dict, col_type_sets, 
                fld_first_mismatches, col_idx,fldnames, valdict, 
                coltype=mg.VAL_EMPTY_STRING, val2use=u"", row_num=row_num)
        else:
            pass
        idx_final_col = len(fldnames) - 1
        if col_idx > idx_final_col:
            break
    if debug: 
        print(str(valdict))
        print(fld_first_mismatches)
    return col_type_sets, valdict
