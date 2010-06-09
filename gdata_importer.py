#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
http://code.google.com/apis/documents/docs/1.0/developers_guide_python.html...
    ...#DownloadingSpreadsheets
http://code.google.com/apis/documents/docs/2.0/developers_guide_protocol.html...
    ...#DownloadingSpreadsheets
"""

import googleapi.gdata.docs.service as gservice
import googleapi.gdata.spreadsheet.service as sservice
import googleapi.gdata.spreadsheet as gdata_spreadsheet
import string

debug = True

# get a docs client
gd_client = gservice.DocsService()
gd_client.ClientLogin('grant@p-s.co.nz', 'beatmss00n')

# setup a spreadsheets service for downloading spreadsheets
gs_client = sservice.SpreadsheetsService()
gs_client.ClientLogin('grant@p-s.co.nz', 'beatmss00n')
feed = gs_client.GetSpreadsheetsFeed()

def PrintFeed(feed):
  for i, entry in enumerate(feed.entry):
    if isinstance(feed, gdata_spreadsheet.SpreadsheetsCellsFeed):
      print '%s %s\n' % (entry.title.text, entry.content.text)
    elif isinstance(feed, gdata_spreadsheet.SpreadsheetsListFeed):
      print '%s %s %s' % (i, entry.title.text, entry.content.text)
      # Print this row's value for each column (the custom dictionary is
      # built from the gsx: elements in the entry.) See the description of
      # gsx elements in the protocol guide.
      print 'Contents:'
      for key in entry.custom:
        print '  %s: %s' % (key, entry.custom[key].text)
      print '\n',
    else:
      print '%s %s\n' % (i, entry.title.text)

PrintFeed(feed)
input = raw_input('\nSelection: ')
key = feed.entry[string.atoi(input)].id.text.rsplit('/', 1)[1]
print key
url = (u"http://spreadsheets.google.com/feeds/download/spreadsheets/Export?"
       u"key=%(example_spreadsheet_id)s&exportFormat=%(example_format)s") % \
       {"example_spreadsheet_id": key,
        "example_format": "csv"}
file_path = '/home/g/Desktop/your_spreadsheets.csv'
docs_token = gd_client.GetClientLoginToken()
gd_client.SetClientLoginToken(gs_client.GetClientLoginToken())
wksheet_idx = 0
gd_client.Export(url, file_path, gid=wksheet_idx)
gd_client.SetClientLoginToken(docs_token)
raw_input("Stop?: ") 
