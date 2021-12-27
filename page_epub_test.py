import json
import datetime
from subprocess import PIPE, run
import time
import sys
from pathlib import Path
import argparse

from epub_pager import epub_paginator

epubcheck = "/opt/homebrew/bin/epubcheck"
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

def set_params(paginator):
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
    paginator.chk_orig = config['chk_orig']
    paginator.DEBUG = config['DEBUG']

def p_result(llen, lpad, s):
    rpad = linelen-lpad
    print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")

# setup and parse command line arguments
parser = argparse.ArgumentParser(description=(f'Paginate Calibre ePub '
                                              f'files.'))
parser.add_argument(
        '--cfg',
        default='',
        help='path to configuration file')
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

# cfile = Path('./.cfg')
config = get_config(Path(args.cfg))

paginator = epub_paginator()
set_params(paginator)

# an error database for books converted
edb = {
        "title": '',
        "pager_fatal": 0,
        "pager_error": 0,
        "pager_warn": 0,
        "orig_fatal": 0,
        "orig_error": 0,
        "orig_warn": 0,
        "echk_fatal": 0,
        "echk_error": 0,
        "echk_warn": 0

      }
# and a list of results
edb_list = []
epub_count = 0
pager_fatal_errcnt = 0
pager_error_errcnt = 0
pager_warn_errcnt = 0
orig_fatal_errcnt = 0
orig_error_errcnt = 0
orig_warn_errcnt = 0
echk_fatal_errcnt = 0
echk_error_errcnt = 0
echk_warn_errcnt = 0
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
    b_edb['pager_fatal'] = 0
    b_edb['pager_error'] = 0
    b_edb['pager_warn'] = 0
    b_edb['orig_fatal'] = 0
    b_edb['orig_error'] = 0
    b_edb['orig_warn'] = 0
    b_edb['echk_fatal'] = 0
    b_edb['echk_error'] = 0
    b_edb['echk_warn'] = 0
    format_list = book['formats']
    for booktype in format_list:
        booksplit = booktype.split('/')
        filename = booksplit[len(booksplit)-1]
        ext = filename.split('.')
        set_params(paginator)
        if ext[len(ext)-1] == 'epub':
            if not args.quiet:
                print('\n--------------------')
            '''
            if epub_count % 2:
                paginator.footer = False
                paginator.superscript = True
            else:
                paginator.footer = True
                paginator.superscript = False
            if epub_count % 3:
                paginator.pgwords = 0
                paginator.pages = 300
            else:
                paginator.pgwords = 300
                paginator.pages = 0
            else:
            if epub_count % 3:
                paginator.genplist = True
            else:
                paginator.genplist = False
            if epub_count % 4:
                paginator.match = True
            else:
                paginator.match = False
            '''
            if not args.quiet:
                # print(f"Paginating {booktype:.72}")
                print(f"Paginating {book['Title']:.72}")
                # print(f"footer: {paginator.footer}; super: {paginator.superscript}")
                # print(f"genplist: {paginator.genplist}; match: {paginator.match}")
            else:
                if not epub_count % 5:
                    print(f'Book {epub_count}; ')
            rdict = paginator.paginate_epub(booktype)
            # report the results
            b_edb['pager_fatal'] = rdict['fatal']
            b_edb['pager_error'] = rdict['error']
            b_edb['pager_warn'] = rdict['warn']
            b_edb['echk_fatal'] = rdict['echk_fatal']
            b_edb['echk_error'] = rdict['echk_error']
            b_edb['echk_warn'] = rdict['echk_warn']
            b_edb['orig_fatal'] = rdict['orig_fatal']
            b_edb['orig_error'] = rdict['orig_error']
            b_edb['orig_warn'] = rdict['orig_warn']
            one_fatal = False
            one_error = False
            one_warn = False
            if b_edb['pager_fatal']:
                one_fatal = True
                pager_fatal_errcnt += 1
                print(f"--> Pager Fatal errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['pager_error']:
                one_error = True
                pager_error_errcnt += 1
                print(f"--> Pager Errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['pager_warn']:
                one_warn = True
                pager_warn_errcnt += 1
                print(f"--> Pager Warnings occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_fatal']:
                one_fatal = True
                echk_fatal_errcnt += 1
                print(f"--> echk Fatal errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_error']:
                one_error = True
                echk_error_errcnt += 1
                print(f"--> echk Errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_warn']:
                one_warn = True
                echk_warn_errcnt += 1
                print(f"--> echk Warnings occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['orig_fatal']:
                one_fatal = True
                orig_fatal_errcnt += 1
                print(f"--> orig Fatal errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['orig_error']:
                one_error = True
                orig_error_errcnt += 1
                print(f"--> orig Errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['orig_warn']:
                one_warn = True
                orig_warn_errcnt += 1
                print(f"--> orig Warnings occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if one_fatal or one_error or one_warn:
                print('Errors or warnings detected.')
            else:
                print('No errors or warnings detected.')
            epub_count += 1
            edb_list.append(b_edb)
            t2 = time.perf_counter()
print()
print(f'Completed {args.count} paginations: ')
print(f'---> {pager_fatal_errcnt} books had fatal errors in epub_pager.')
print(f'---> {pager_error_errcnt} books had errors in epub_pager.')
print(f'---> {pager_warn_errcnt} books had warnings in epub_pager.')
print('--------------------')
print(f'---> {orig_fatal_errcnt} original books had fatal errors in epubcheck.')
print(f'---> {orig_error_errcnt} original books had errors in epubcheck.')
print(f'---> {orig_warn_errcnt} original books had warnings in epubcheck.')
print('--------------------')
print(f'---> {echk_fatal_errcnt} paged books had fatal errors in epubcheck.')
print(f'---> {echk_error_errcnt} paged books had errors in epubcheck.')
print(f'---> {echk_warn_errcnt} paged books had warnings in epubcheck.')
print('--------------------')
print()

# compare epubcheck errors for before and after paging.
linelen = 60
p_result(linelen, 3, 'epubcheck Difference Comparison')
for book in edb_list:
    if book['echk_fatal'] != book['orig_fatal']:
        p_result(linelen, 3, book['title'])
        p_result(linelen, 10, 'Fatal Errors')
        print(f"  --> {book['echk_fatal']:3} fatal error(s) in paged book epubcheck.")
        print(f"  --> {book['orig_fatal']:3} fatal error(s) in original book epubcheck.")
        p_result(linelen, 0, '')
    if book['echk_error'] != book['orig_error']:
        p_result(linelen, 3, book['title'])
        p_result(linelen, 10, 'Errors')
        print(f"  --> {book['echk_error']:3} error(s) in paged book epubcheck.")
        print(f"  --> {book['orig_error']:3} error(s) in original book epubcheck.")
        p_result(linelen, 0, '')
    if book['echk_warn'] != book['orig_warn']:
        p_result(linelen, 3, book['title'])
        p_result(linelen, 10, 'Warnings')
        print(f"  --> {book['echk_warn']:3} warning(s) in paged book epubcheck.")
        print(f"  --> {book['orig_warn']:3} warning(s) in original book epubcheck.")
        p_result(linelen, 0, '')
