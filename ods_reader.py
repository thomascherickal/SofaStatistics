
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
    """
    Slightly strange approach to dict is because I only want to work with the
        end of the key, not the whole thing including the namespaces.
    """
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
                        break
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
            else: # el has no attribs - empty cell
                type = u"string"
                val2use = u""
            add_type_to_coltypes(coltypes, col_idx=i, type=type)
            vals.append(val2use)
    return coltypes, vals

def get_ods_dets(filename):
    """
    Not worth optimising my code.  The xml parsing stage takes up most of the 
        time.  Using the SAX approach would significantly reduce memory usage 
        but would it save any time overall?  Harder code and may even be slower.
    XML is a terrible way to store lots of data ;-).
    """
    debug = True
    large = True
    coltypes = [] # one set per column containing all types
    myzip = zipfile.ZipFile
    myzip = zipfile.ZipFile(filename)
    cont = myzip.open("content.xml")
    if debug: print("Starting parse process ...")
    tree = etree.parse(cont) # the most time-intensive bit
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
            print "The sheet is named \"%s\"" % value
    rows = []
    first = True
    if debug: print(len(tbl))
    for el in tbl:
        if el.tag.endswith("table-row"): # should always be one per el
            coltypes, vals = dets_from_row(coltypes, el, first=first)
            rows.append(vals)
            first = False
    return coltypes, rows

debug = False
import time
import os
t1 = time.time() # clock is CPU time which might be zero while this process waits!
coltypes, rows = get_ods_dets(filename = u"/home/g/test_ods.ods")
f = open(u"/home/g/test_ods_results.txt", "w")
import pprint
f.write(pprint.pformat(coltypes))
f.write(pprint.pformat(rows))
f.close()
if debug:
    print(coltypes)
    print(rows)
print("FINISHED ODS EXTRACT")
t2 = time.time()
diff = t2 - t1
mins, secs = divmod(diff, 60)
hours, mins = divmod(mins, 60)
dur = "%d hour(s) %d minute(s) %d seconds" % (hours, mins, secs)
print os.linesep + "*"*30 + os.linesep
print "Finished backup.  Time taken: %s" % dur
print os.linesep + "*"*30 + os.linesep
