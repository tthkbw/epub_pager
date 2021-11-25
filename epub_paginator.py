#!/opt/homebrew/bin/python3

import os
import rpyc
import json
import sys
import argparse
from epub_pager import epub_paginator

Version = '1.0'
# Version 1.0
# Added argparse for parsing command line options. There are options to set and
# default values for every option that epub_pager supports.  Left in the
# read_config routine, but it is not currently used. Nor is default.cfg

# version 0.7 includes configuration stuff

# to rebuild the zip file, use Finder and simply compress the file and rename to epub. Open using Sigil.
# use zip from command line:
# zip -r SourceDirectory Zipname
# mv Zipname.zip Zipname.epub

pagenum = 1
total_wordcount = 0
page_wordcount = 0
DEBUG = False
BookID = 973

default_cfg = {
    "paged_epub_library": "/Users/tbrown/data_store/paged_epubs",
    "words_per_page": 300,
    "total_pages": 0,
    "page_footer": False,
    "footer_align": "right",
    "footer_color": "red",
    "footer_bracket": "<",
    "footer_fontsize": "75%",
    "footer_total": True,
    "superscript": True,
    "super_color": "red",
    "super_fontsize": "60%",
    "super_total": True,
    "chapter_pages": True,
    "chapter_bracket": "",
    "nav_pagelist": True,
    "epubcheck": "/opt/homebrew/bin/epubcheck",
    "DEBUG": False
}

# setup and parse command line arguments
parser = argparse.ArgumentParser(description='Paginate ePub file.')
parser.add_argument('-c', '--cfg', help='path to configuration file')
parser.add_argument('ePub_file', help='The ePub file to be paginated.')
parser.add_argument('--paged_epub_library', help='location for output ePub files',default='./')
parser.add_argument('--words_per_page', help='define words per page',type=int, default=300)
parser.add_argument('--total_pages', help='if = 0 then use words_per_page; else words_per_page=(wordcount/total_pages)',type=int, default=0)
parser.add_argument('--page_footer', help='generate and insert page footers into the ePub text',action=argparse.BooleanOptionalAction,default=False)
parser.add_argument('--footer_align', help="'right', 'left' or 'center'; specify alignment of the page footer",default='right')
parser.add_argument('--footer_color', choices=['red', 'blue', 'green', 'none'],help="html color for the inserted page footer",default='none')
parser.add_argument('--footer_bracket', choices=['<','(','none'], help="character to use to bracket page number",default='<')
parser.add_argument('--footer_fontsize', help='font size as percentage of book font for the footer',default='75%')
parser.add_argument('--footer_total', help='include total pages in the footer',action=argparse.BooleanOptionalAction,default=False)
parser.add_argument('--superscript', help='generate superscripted page numbers',action=argparse.BooleanOptionalAction,default=False)
parser.add_argument('--super_color', choices=['red', 'blue', 'green', 'none'],help="html color for the inserted page footer e.g. 'red'")
parser.add_argument('--super_fontsize', help='font size as percentage of book font for the footer',default='60%')
parser.add_argument('--super_total', help='include total pages in the footer',action=argparse.BooleanOptionalAction,default=False)
parser.add_argument('--chapter_pages', help='include chapter page and total in the footer and/or superscript',action=argparse.BooleanOptionalAction,default=True)
parser.add_argument('--chapter_bracket', help="'<', '(' or nothing; character to use to bracket page number",default='')
parser.add_argument('--nav_pagelist', help='generate the navigation page list and page links for page numbers',action=argparse.BooleanOptionalAction,default=True)
parser.add_argument('--epubcheck', help='location of epubcheck executable',default='none')
parser.add_argument('--ebookconvert', help='location of ebook conversion executable',default='none')
parser.add_argument('--DEBUG', help='print additional debug information to the log file',action=argparse.BooleanOptionalAction,default=False)
args = parser.parse_args()
# the config file may be local, which has precedence, or in the ~/.config/BookTally directory
def get_config(args):
    if len(args.cfg) > 0:
        if os.path.exists(args.cfg):
            if DEBUG:
                print(f'config file is {cfg_file}')
            with open(args.cfg, 'r') as config_file:
                return(json.loads(config_file.read()))
        else:
            if DEBUG:
                print('Configuration file {cfg_file} not found!')
    else:
        # no config file, build the config from the parameters
        config["paged_epub_library"] = args.paged_epub_library
        config["words_per_page"] = args.words_per_page
        config["total_pages"] = args.total_pages
        config["page_footer"] = args.page_footer
        config["footer_align"] = args.footer_align
        config["footer_color"] = args.footer_color
        config["footer_bracket"] = args.footer_bracket
        config["footer_fontsize"] = args.footer_fontsize
        config["footer_total"] = args.footer_total
        config["superscript"] = args.superscript
        config["super_color"] = args.super_color
        config["super_fontsize"] = args.super_fontsize
        config["super_total"] = args.super_total
        config["chapter_pages"] = args.chapter_pages
        config["chapter_bracket"] = args.chapter_bracket
        config["nav_pagelist"] = args.nav_pagelist
        config["ebookconvert"] = args.ebookconvert
        config["epubcheck"] = args.epubcheck
        config["DEBUG"] = args.DEBUG
        return(config)

print('configuration:')
print(f"Output file: {args.ePub_file}")
# print(f"configuration file: {args.cfg}")
print(f"paged_epub_library: {args.paged_epub_library}")
print(f"words_per_page: {args.words_per_page}")
print(f"total_pages: {args.total_pages}")
print(f"page_footer: {args.page_footer}")
print(f"footer_align: {args.footer_align}")
print(f"footer_color: {args.footer_color}")
print(f"footer_bracket: {args.footer_bracket}")
print(f"footer_fontsize: {args.footer_fontsize}")
print(f"footer_total: {args.footer_total}")
print(f"superscript: {args.superscript}")
print(f"super_color: {args.super_color}")
print(f"super_fontsize: {args.super_fontsize}")
print(f"super_total: {args.super_total}")
print(f"chapter_pages: {args.chapter_pages}")
print(f"chapter_bracket: {args.chapter_bracket}")
print(f"nav_pagelist: {args.nav_pagelist}")
print(f"ebookconvert: {args.ebookconvert}")
print(f"epubcheck: {args.epubcheck}")
print(f"DEBUG: {args.DEBUG}")
# get the config file to set things up
# config = get_config(args)
# for dkey in config.keys():
#     print(f'{dkey}: {config[dkey]}')
# connect to server to find files
# conn = rpyc.connect('m1mini', config['rpyc_port'])
# current_book = conn.root.GetBookJson(BookID)
# if current_book['GoodReadsPages']!=0 and current_book['CalibreWordcount']!=0:
#     words_per_page = int(current_book['CalibreWordcount']/current_book['GoodReadsPages'])
# else:

# find and unzip the epub file
# must get book_location from json: current_book['formats'][0] which must contain 'epub'
# format_list = current_book['formats']
# for book in format_list:
#     booksplit = book.split('/')
#     filename = booksplit[len(booksplit)-1]
#     if 'epub' in filename:
#         book_location = book
#         print('epub file is at: ' + book_location)
#         break

paginator = epub_paginator()
paginator.paged_epub_library = args.paged_epub_library
paginator.words_per_page = args.words_per_page
paginator.total_pages = args.total_pages
paginator.page_footer = args.page_footer
paginator.footer_align = args.footer_align
paginator.footer_color = args.footer_color
paginator.footer_bracket = args.footer_bracket
paginator.footer_fontsize = args.footer_fontsize
paginator.footer_total = args.footer_total
paginator.superscript = args.superscript
paginator.super_color = args.super_color
paginator.super_fontsize = args.super_fontsize
paginator.super_total = args.super_total
paginator.chapter_pages = args.chapter_pages
paginator.chapter_bracket = args.chapter_bracket
paginator.nav_pagelist = args.nav_pagelist
paginator.ebookconvert = args.ebookconvert
paginator.epubcheck = args.epubcheck
paginator.DEBUG = args.DEBUG

return_dict = paginator.paginate_epub(args.ePub_file)

print('---> Dumping return_dict')
print()
print(f"Paginated ebook created: {return_dict['paged_epub_file']}")
print(f"Paginated ebook log: {return_dict['logfile']}")
if len(return_dict['errors'])>0:
    print('Errors were reported:')
    for perror in return_dict['errors']:
        print(perror)
else:
    print('No errors reported.')
print(return_dict['messages'])
