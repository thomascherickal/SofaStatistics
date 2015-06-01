#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Some general functions with no scope for circular dependencies (unlike lib)
"""

from __future__ import absolute_import
import codecs
import locale

def ue(e):
    """
    Return unicode string version of error reason
    
    unicode(e) handles u"找不到指定的模块。" & u"I \u2665 unicode"
    
    str(e).decode("utf8", ...) handles "找不到指定的模块。"
    """
    debug = False
    try:
        unicode_e = unicode(e)
    except UnicodeDecodeError:
        try:
            unicode_e = str(e).decode(locale.getpreferredencoding())
        except UnicodeDecodeError:
            try:
                unicode_e = str(e).decode("utf8", "replace")
            except UnicodeDecodeError:
                unicode_e = u"Problem getting error reason"
    if debug: 
        print("unicode_e has type %s" % type(unicode_e))
        print(repr(u"unicode_e is %s" % unicode_e))
    return unicode_e

def guess_possible_encodings(bytestr):
    """
    Order matters. '\xff\xfe' starts utf-16 BOM but also starts 
    '\xff\xfe\x00\x00' the utf-32 BOM. Do the larger one first.
    
    From codecs:
    
    BOM_UTF8 = '\xef\xbb\xbf'

    BOM_UTF32 = '\xff\xfe\x00\x00'
    BOM64_LE = '\xff\xfe\x00\x00'
    BOM_UTF32_LE = '\xff\xfe\x00\x00'
    
    BOM_UTF16_BE = '\xfe\xff'
    BOM32_BE = '\xfe\xff'
    BOM_BE = '\xfe\xff'
    
    BOM_UTF16 = '\xff\xfe'
    BOM = '\xff\xfe'
    BOM_LE = '\xff\xfe'
    BOM_UTF16_LE = '\xff\xfe'
    BOM32_LE = '\xff\xfe'
    
    BOM_UTF32_BE = '\x00\x00\xfe\xff'
    BOM64_BE = '\x00\x00\xfe\xff'
    """
    possible_encodings = []
    if bytestr.startswith(codecs.BOM_UTF32): # '\xff\xfe\x00\x00'
        extra_encodings = ["utf-32", ]
    elif bytestr.startswith(codecs.BOM_UTF16_BE): # '\xfe\xff'
        extra_encodings = ["utf-16", "utf-32"]
    elif bytestr.startswith(codecs.BOM_UTF16): # '\xff\xfe'
        extra_encodings = ["utf-16", "utf-32"]
    elif bytestr.startswith(codecs.BOM_UTF32_BE): # '\x00\x00\xfe\xff'
        extra_encodings = ["utf-32",]
    else:
        extra_encodings = []
    possible_encodings.extend(extra_encodings)
    possible_encodings.append("utf-8")  ## last
    return possible_encodings

def clean_BOM_UTF8_from_bytestring(bytestr):
    """
    From codecs: BOM_UTF8 = '\xef\xbb\xbf'
    
    No need to strip any other BOMs off - in fact they're needed.
    """
    if bytestr.startswith(codecs.BOM_UTF8): # '\xef\xbb\xbf'
        len2rem = len(codecs.BOM_UTF8)  ## 3 long in byte str, 1 in unicode str
        bom_stripped = bytestr[len2rem:] # strip it off 
    else:
        bom_stripped = bytestr
    return bom_stripped

def get_unicode_from_file(fpath):
    """
    Particularly trying to cope with what Windows users manually do to text
    files when editing them e.g. Notepad inserting a BOM in a utf-8 encoded
    file. Intended for SOFA internal files e.g. reports, css files, proj files
    etc.
    """
    try:
        with open(fpath, "rb") as f:
            bytestr = f.read()
    except IOError, e:
        raise Exception(u"Unable to read non-existent file %s" % fpath)
    except Exception, e:
        raise Exception(u"Unable to read from file '%s'" % (fpath, ue(e)))
    bom_utf8_stripped = clean_BOM_UTF8_from_bytestring(bytestr)
    possible_encodings = guess_possible_encodings(bytestr=bom_utf8_stripped)
    fixed = None
    for possible_encoding in possible_encodings:
        try:
            fixed = bom_utf8_stripped.decode(possible_encoding)
            break
        except Exception:
            pass
    if fixed is None:
        raise Exception("Unable to convert text from '%s' into unicode" % fpath)
    return fixed

def get_exec_ready_text(text):
    """
    test -- often the result of f.read()
    
    exec can't handle some Windows scripts e.g. print("Hello world")\r\n
    you can see
    """
    debug = False
    if debug: print(repr(text)) # look for terminating \r\n on Windows sometimes
    exec_ready_text = text.replace(u"\r", u"")
    return exec_ready_text
