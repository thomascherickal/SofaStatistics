"""
Some general functions with no scope for circular dependencies (unlike lib)
"""

import codecs

def ue(e):
    """
    Return unicode string version of error reason

    unicode(e) handles "找不到指定的模块。" & "I \u2665 unicode"

    str(e).decode("utf8", ...) handles "找不到指定的模块。"
    """
    return str(e)

def _clean_BOM_UTF8_from_bytestring(bytestr):
    """
    From codecs: BOM_UTF8 = '\xef\xbb\xbf'

    No need to strip any other BOMs off - in fact they're needed.
    """
    if bytestr.startswith(codecs.BOM_UTF8):  ## '\xef\xbb\xbf'
        len2rem = len(codecs.BOM_UTF8)  ## 3 long in byte str, 1 in unicode str
        bom_stripped = bytestr[len2rem:]  ## strip it off 
    else:
        bom_stripped = bytestr
    return bom_stripped

def get_bom_free_contents(fpath):
    """
    Particularly trying to cope with what Windows users manually do to text
    files when editing them e.g. Notepad inserting a BOM in a utf-8 encoded
    file. Intended for SOFA internal files e.g. reports, css files, proj files
    etc.
    """
    try:
        with open(fpath, 'rb') as f:
            bytestr = f.read()
    except OSError as e:
        raise Exception(f'Unable to read non-existent file {fpath}')
    except Exception as e:
        raise Exception(f'Unable to read from file "{fpath}". Orig error {ue(e)}')
    bom_utf8_stripped = _clean_BOM_UTF8_from_bytestring(bytestr)
    try:
        fixed = bom_utf8_stripped.decode('utf-8')
    except Exception:
        raise Exception(f"Unable to convert text from '{fpath}' into unicode")
    return fixed

def get_exec_ready_text(text):
    """
    exec can't handle some Windows scripts e.g. print("Hello world")\r\n
    you can see

    :param str text: often the result of f.read()
    """
    debug = False
    if debug: print(repr(text))  ## look for terminating \r\n on Windows sometimes
    exec_ready_text = text.replace('\r', '')
    return exec_ready_text
