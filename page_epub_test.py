import json
import datetime
from subprocess import PIPE, run
import time
import sys
from pathlib import Path
import argparse

from epub_pager import epub_paginator

BookFileName = Path('/Users/tbrown/Documents/projects/BookTally/Books.json')
BookArray = []     # the entire set of dictionaries from the master file
booklist = []      # the list of titles in the BookArray
CR = '\n'


def build_booklist(bookarray):
    global booklist

    booklist = []
    for book in bookarray:
        booklist.append(book['Title'])
    return booklist


def save_book_dictionary(BookArray):

    with BookFileName.open('w') as outfile:
        json.dump(BookArray, outfile, indent=4)
        outfile.close()


def load_book_data():

    # get all dictionaries from the master file
    with BookFileName.open('r') as infile:
        jsondata = infile.read()
    bookdata = json.loads(jsondata)
    return bookdata


def get_config(cfg_file):
    if cfg_file.exists():
        print(f'Using config file {cfg_file}')
        with cfg_file.open('r') as config_file:
            return(json.loads(config_file.read()))
    else:
        if DEBUG:
            print('Configuration file {cfg_file} not found!')

# setup and parse command line arguments
parser = argparse.ArgumentParser(description=(f'Paginate Calibre ePub '
                                              f'files.'))
parser.add_argument(
        '-c',
        '--count',
        type=int,
        default=5,
        help='count of books to paginate')
parser.add_argument(
        '-s',
        '--start',
        type=int,
        default=0,
        help='first book to paginate')
parser.add_argument(
        '-q',
        '--quiet',
        help='Only print when errors occurred.',
        action=argparse.BooleanOptionalAction,
        default=False)
args = parser.parse_args()

BookArray = load_book_data()
booklist = build_booklist(BookArray)

cfile = Path('./epub_pager.cfg')
config = get_config(cfile)

paginator = epub_paginator()
paginator.outdir = config['outdir']
paginator.match = config['match']
paginator.genplist = config['genplist']
paginator.pgwords = config['pgwords']
paginator.pages = config['pages']
paginator.footer = config['footer']
paginator.ft_align = config['ft_align']
paginator.ft_color = config['ft_color']
paginator.ft_bkt = config['ft_bkt']
paginator.ft_fntsz = config['ft_fntsz']
paginator.ft_pgtot = config['ft_pgtot']
paginator.superscript = config['superscript']
paginator.super_color = config['super_color']
paginator.super_fntsz = config['super_fntsz']
paginator.super_total = config['super_total']
paginator.chap_pgtot = config['chap_pgtot']
paginator.chap_bkt = config['chap_bkt']
paginator.ebookconvert = config['ebookconvert']
paginator.epubcheck = config['epubcheck']
paginator.DEBUG = config['DEBUG']

# an error database for books converted
edb = {
        "title": '',
        "fatal": False,
        "error": False,
        "warn": False

      }
# and a list of results
edb_list = []
epub_count = 0
fatal_errcnt = 0
error_errcnt = 0
warn_errcnt = 0
start = args.start
max_count = args.start + args.count
if not args.quiet:
    print((f'ready to paginate books from '
           f'{args.start} to {max_count}'))

for book in BookArray:
    if epub_count < start:
        epub_count += 1
        continue
    if epub_count == max_count:
        break
    b_edb = {}
    b_edb['title'] = book['Title']
    b_edb['fatal'] = False
    b_edb['error'] = False
    b_edb['warn'] = False
    format_list = book['formats']
    for booktype in format_list:
        booksplit = booktype.split('/')
        filename = booksplit[len(booksplit)-1]
        ext = filename.split('.')
        if ext[len(ext)-1] == 'epub':
            if not args.quiet:
                print('\n--------------------')
            if epub_count % 2:
                paginator.footer = False
                paginator.superscript = True
            else:
                paginator.footer = True
                paginator.superscript = False
            if epub_count % 3:
                paginator.genplist = True
            else:
                paginator.genplist = False
            if epub_count % 4:
                paginator.match = True
            else:
                paginator.match = False
            if not args.quiet:
                print(f"Paginating {booktype}")
                print(f"footer: {paginator.footer}; super: {paginator.superscript}")
                print(f"genplist: {paginator.genplist}; match: {paginator.match}")
            else:
                if not epub_count % 5:
                    # print(f'Book {epub_count}; ',end='\r')
                    print(f'Book {epub_count}; ')
            t1 = time.perf_counter()
            rdict = paginator.paginate_epub(booktype)
            if rdict['fatal'] or rdict['echk_fatal']:
                b_edb['fatal'] = True
                fatal_errcnt += 1
                print(f"--> Fatal errors occurred in book {booktype}; book"
                        f' number:{epub_count}:')
            elif rdict['error'] or rdict['echk_error']:
                b_edb['error'] = True
                error_errcnt += 1
                print(f"--> Errors occurred in book {booktype}; book"
                        f' number:{epub_count}:')
            elif rdict['warn'] or rdict['echk_warn']:
                b_edb['warn'] = True
                warn_errcnt += 1
                print(f"--> Warnings occurred in book {booktype}; book"
                        f' number:{epub_count}:')
            else:
                if not args.quiet:
                    print('No errors or warnings detected.')
            epub_count += 1
            edb_list.append(b_edb)
            t2 = time.perf_counter()
print(f'Completed {max_count} paginations: ')
print(f'---> {fatal_errcnt} books had fatal errors.')
print(f'---> {error_errcnt} books had errors.')
print(f'---> {warn_errcnt} books had warnings.')
print('--------------------')
print()

print('--------Summary-----')
print("Books with fatal errors:")
for book in edb_list:
    if book['fatal']:
        print(f' - {book["title"]}')
print('--------------------')
print('--------------------')
print("Books with errors:")
for book in edb_list:
    if book['error']:
        print(f" - {book['title']}")
print('--------------------')
print('--------------------')
print("Books with warnings")
for book in edb_list:
    if book['warn']:
        print(f' - {book["title"]}')
print('--------------------')
