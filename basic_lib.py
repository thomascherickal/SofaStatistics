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

def clean_boms(orig_utf8):
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
    try:
        str_orig = orig_utf8.encode("utf-8")
    except UnicodeEncodeError:
        raise Exception("cleans_boms() must be supplied a utf-8 unicode string")
    if str_orig.startswith(codecs.BOM_UTF8): # '\xef\xbb\xbf'
        len2rem = len(unicode(codecs.BOM_UTF8, "utf-8"))# 3 long in byte str, 1 in unicode str
        bom_stripped = orig_utf8[len2rem:] # strip it off 
        return bom_stripped
    # that was the only one we strip BOM off. The rest need it.
    if str_orig.startswith(codecs.BOM_UTF32): # '\xff\xfe\x00\x00'
        possible_encodings = ["utf-32",]
    elif str_orig.startswith(codecs.BOM_UTF16_BE): # '\xfe\xff'
        possible_encodings = ["utf-16", "utf-32"]
    elif str_orig.startswith(codecs.BOM_UTF16): # '\xff\xfe'
        possible_encodings = ["utf-16", "utf-32"]
    elif str_orig.startswith(codecs.BOM_UTF32_BE): # '\x00\x00\xfe\xff'
        possible_encodings = ["utf-32",]
    else:
        return orig_utf8
    # Handle those needing to be decoded
    for possible_encoding in possible_encodings + ["utf-8",]:
        try:
            fixed = orig_utf8.decode(possible_encoding)
            return fixed
        except Exception:
            pass
    return u"" # last ditch attempt to return something

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
