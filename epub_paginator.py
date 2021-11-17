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
    "paged_epub_library": "/Users/tbrown/data_store/paged_epubs",
    "words_per_page": 300,
    "total_pages": 0,
    "page_footer": True,
    "footer_align": 'right',
    "footer_color": 'red',
    "footer_bracket": '<',
    "footer_fontsize": '75%',
    "footer_total": True,
    "superscript": True,
    "super_color": 'red',
    "super_fontsize": '60%',
    "super_total": True,
    "chapter_pages": True,
    "chapter_bracket": '',
    "nav_pagelist": True,
    "epubcheck": '/opt/homebrew/bin/epubcheck',
    "DEBUG": False
}

# the config file may be local, which has precedence, or in the ~/.config/BookTally directory
def read_config():
    if os.path.exists('./epub_pager.cfg'):
        cfg_file = './epub_pager.cfg'
        if DEBUG:
            print(f'config file is {cfg_file}')
    else:
        if DEBUG:
            print('No config file found!')
        return(default_config)
    with open(cfg_file, 'r') as config_file:
        return(json.loads(config_file.read()))

# get the config file to set things up
config = read_config()
print('Config file read')
for dkey in config.keys():
    print(f'{dkey}: {config[dkey]}; Type: {type(config[dkey])}')
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
paginator.words_per_page = config['words_per_page']
paginator.total_pages = config['total_pages']
paginator.page_footer = config['page_footer']
paginator.footer_align = config['footer_align']
paginator.footer_color = config['footer_color']
paginator.footer_bracket = config['footer_bracket']
paginator.footer_fontsize = config['footer_fontsize']
paginator.footer_total = config['footer_total']
paginator.superscript = config['superscript']
paginator.super_color = config['super_color']
paginator.super_fontsize = config['super_fontsize']
paginator.super_total = config['super_total']
paginator.chapter_pages = config['chapter_pages']
paginator.chapter_bracket = config['chapter_bracket']
paginator.nav_pagelist = config['nav_pagelist']
paginator.epubcheck = config['epubcheck']
paginator.DEBUG = config['DEBUG']

paginator.paginate_epub(ebook_file)
