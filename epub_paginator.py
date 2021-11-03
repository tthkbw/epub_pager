#!/opt/homebrew/bin/python3

import os
import rpyc
import json
from epub_pager import epub_paginator

Version = '0.7'
# version 0.7 includes configuration stuff

# to rebuild the zip file, use Finder and simply compress the file and rename to epub. Open using Sigil.
# use zip from command line:
# zip -r SourceDirectory Zipname
# mv Zipname.zip Zipname.epub

# ebook_file = './Dune_nopara.epub'
ebook_file = './FarmBoy.epub'
cfg_directory = '/Users/tbrown/.config/BookTally/'
pagenum = 1
total_wordcount = 0
page_wordcount = 0
DEBUG = False
BookID = 973

default_config = {
    "rpyc_port": 12345,
    "tally_json_file": "/Users/tbrown/Documents/projects/BookTally/Books.json",
    "calibre_library": "/Users/tbrown/Documents/Calibre Library/",
    "paged_epub_library": "./paged_epubs",
    "words_per_page": 300,
    "page_footer": True,
    "page_number_align": 'right',
    "page_number_color": 'red',
    "page_number_bracket": '<',
    "page_number_total": True,
    "chapter_pages": True,
    "total_pages": 0,
    "nav_pagelist": True,
    "superscript": False,
    "epubcheck": '/opt/homebrew/bin/epubcheck',
    "DEBUG": False
}

# the config file may be local, which has precedence, or in the ~/.config/BookTally directory
def read_config():
    return(default_config)
    if os.path.exists('./BookTally.cfg'):
        cfg_file = './BookTally.cfg'
    if DEBUG:
        print('config file is ./BookTally.cfg')
    elif os.path.exists('/Users/tbrown/.config/BookTally/BookTally.cfg'):
        cfg_file = '/Users/tbrown/.config/BookTally/BookTally.cfg'
    if DEBUG:
        print('/Users/tbrown/.config/BookTally/BookTally.cfg')
    else:
        if DEBUG:
            print('No config file found!')
        return(default_config)
    with open(cfg_file, 'r') as config_file:
        return(json.loads(config_file.read()))

# get the config file to set things up
config = read_config()
# connect to server to find files
# conn = rpyc.connect('m1mini', config['rpyc_port'])
# current_book = conn.root.GetBookJson(BookID)
# if current_book['GoodReadsPages']!=0 and current_book['CalibreWordcount']!=0:
#     words_per_page = int(current_book['CalibreWordcount']/current_book['GoodReadsPages'])
# else:
words_per_page = config['words_per_page']

print('Words per page is: ' + str(words_per_page))

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
paginator.paged_epub_library = config['paged_epub_library']
paginator.words_per_page = words_per_page
paginator.page_number_align = config['page_number_align']
paginator.page_number_color = config['page_number_color']
paginator.total_pages = config['total_pages']
paginator.chapter_pages = config['chapter_pages']
paginator.superscript = config['superscript']
paginator.page_footer = config['page_footer']
paginator.DEBUG = True

paginator.paginate_epub(ebook_file)
