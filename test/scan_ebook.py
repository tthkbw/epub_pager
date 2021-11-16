#!/opt/homebrew/bin/python3

import os
import sys
from subprocess import PIPE, run

import xmltodict
import json

CR = '\n'
pagenum = 1
total_wordcount = 0
page_wordcount = 0
pagelist_element = ''
epub_filelist = []
nav_file = 'None'
href_path = []
words_per_page = 100

datafile = './Dune_c20.xhtml'
paged_book = './paged_dunec20.xhtml'

with open(datafile,'r') as rfile:
    ebook_data = rfile.read()

idx = 0
paginated_book = ''
section_pagenum = 1
superscript = True
nav_pagelist = True
page_number_color = 'red'
page_footer = True
chapter = {"href": 'xxxx', "section_pagecount": 21}
# scan until we find '<body>' and just copy all the header stuff.
body1 = ebook_data.find('<body>')
if body1==-1:
    paginated_book += ebook_data
    print('No body element found')
else:
    paginated_book += ebook_data[:body1]
    idx = body1
while idx < len(ebook_data)-1:
    if ebook_data[idx]=='<': # we found an html element, just copy it and don't count words
        paginated_book += ebook_data[idx]
        idx += 1
        while ebook_data[idx]!='>':
            paginated_book += ebook_data[idx]
            idx += 1
        paginated_book += ebook_data[idx]
        idx += 1 
    elif ebook_data[idx]==' ': # we found a word boundary
        page_wordcount += 1
        total_wordcount += 1
        if page_wordcount>words_per_page: # if page boundary, add a page
            # insert the superscripted page number
            if superscript:
                paginated_book += '<span style="font-size:75%;vertical-align:super;color:' + page_number_color + '">' + str(pagenum) + '</span>'
            # insert the page-link entry
            if nav_pagelist:
                paginated_book += '<span epub:type="pagebreak" id="page' + str(pagenum) + '"'  + ' title="' + str(pagenum) + '"/>'
                print('insert nav_pagelist')

#                 add_nav_pagelist_target(pagenum, chapter['href'])
            if page_footer:
                print('insert footer')
#                 create_pagefooter(pagenum, section_pagenum, chapter['section_pagecount'], chapter['href'])
            section_pagenum += 1
            pagenum += 1
            page_wordcount = 0
        while ebook_data[idx]==' ': #skip additional whitespace
            paginated_book += ebook_data[idx]
            idx += 1
    else: # just copy non-white space and non-element stuff
        paginated_book += ebook_data[idx]
        idx += 1
print(paginated_book)
