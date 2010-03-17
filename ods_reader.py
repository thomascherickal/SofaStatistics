
import xml.etree.ElementTree as etree
import zipfile

"""
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

def add_type_to_coltypes(coltypes, col_idx, type):
    try:
        coltypes[col_idx].add(type)
    except IndexError:
        coltypes.append(set([type]))    

def dets_from_row(coltypes, row, first=False):
    debug = False
    vals = []
    for i, el in enumerate(row):
        if debug: print(etree.tostring(el))
        items = el.attrib.items()
        if first: # only get values, not col types
            if items:
                for (key, value) in el.attrib.items():
                    if key.endswith("date-value"):
                        val2use = value # take proper date val e.g. 2010-02-01
                            # rather than actual text of 01/02/10
                    elif key.endswith("value-type"): # must always be one per el
                        val2use = el[0].text # take val from inner text element
            else:
                val2use = u""
            vals.append(val2use) # take val from inner text element
        else: # get vals and col types
            if items:
                for (key, value) in items:
                    if key.endswith("date-value"):
                        type = u"date"
                        val2use = value
                        break
                    elif key.endswith("value-type"): # must always be one per el
                        type = value
                        val2use = el[0].text
                        # don't break - give chance to go through date-value
            else:
                type = u"string"
                val2use = u""
            add_type_to_coltypes(coltypes, col_idx=i, type=type)
            vals.append(val2use)
    return coltypes, vals

def get_ods_dets(filename):
    debug = False
    coltypes = [] # one set per column containing all types
    myzip = zipfile.ZipFile
    myzip = zipfile.ZipFile(filename)
    cont = myzip.open("content.xml")
    tree = etree.parse(cont)
    myzip.close()
    root = tree.getroot()
    if debug: print(etree.tostring(root))
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
            print "The sheet is named \"%s\"" % value
    rows = []
    first = True
    for el in tbl:
        if el.tag.endswith("table-row"): # should always be one per el
            coltypes, vals = dets_from_row(coltypes, el, first=first)
            rows.append(vals)
            first = False
    return coltypes, rows

coltypes, rows = get_ods_dets(filename = u"/home/g/test_ods.ods")
print coltypes
print rows

