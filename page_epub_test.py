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
    paginator.DEBUG = config['DEBUG']

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
        "pager_fatal": False,
        "pager_error": False,
        "pager_warn": False,
        "orig_fatal": False,
        "orig_error": False,
        "orig_warn": False,
        "echk_fatal": False,
        "echk_error": False,
        "echk_warn": False

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
    b_edb['pager_fatal'] = False
    b_edb['pager_error'] = False
    b_edb['pager_warn'] = False
    b_edb['orig_fatal'] = False
    b_edb['orig_error'] = False
    b_edb['orig_warn'] = False
    b_edb['echk_fatal'] = False
    b_edb['echk_error'] = False
    b_edb['echk_warn'] = False
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
                print(f"Paginating {booktype:.72}")
                # print(f"footer: {paginator.footer}; super: {paginator.superscript}")
                # print(f"genplist: {paginator.genplist}; match: {paginator.match}")
            else:
                if not epub_count % 5:
                    print(f'Book {epub_count}; ')
            rdict = paginator.paginate_epub(booktype)
            # run epubcheck on original for comparisons
            # if conversion, be sure to get the converted file
            epubcheck_cmd = [epubcheck,booktype]
            result = run(epubcheck_cmd,
                            stdout=PIPE,
                            stderr=PIPE,
                            universal_newlines=True)
            # check and log the errors from epubcheck
            for line in result.stdout.splitlines():
                # Messages: 0 fatals / 0 errors / 0 warnings
                # 0         1 2      3 4  5     6    7
                if line.find('Messages:') != -1:
                    w = line.split(' ')
                    if w[1] != '0':
                        print(f'  --> Fatal error reported in original epubcheck')
                        b_edb['orig_fatal'] = True
                        orig_fatal_errcnt += 1
                    if w[4] != '0':
                        print('  --> Errors reported in original epubcheck')
                        b_edb['orig_error'] = True
                        orig_error_errcnt += 1
                    if w[7] != '0':
                        print('  --> Warnings reported in original epubcheck')
                        b_edb['orig_warn'] = True
                        orig_warn_errcnt += 1
            t1 = time.perf_counter()
            with Path(return_dict['logfile']).open('a') as logfile:
                logfile.write('Appending original epubcheck output:')
                logfile.write(result.stdout)
                logfile.write(result.stderr)
            b_edb['pager_fatal'] = rdict['fatal']
            b_edb['pager_error'] = rdict['error']
            b_edb['pager_warn'] = rdict['warn']
            b_edb['echk_fatal'] = rdict['echk_fatal']
            b_edb['echk_error'] = rdict['echk_error']
            b_edb['echk_warn'] = rdict['echk_warn']
            if b_edb['pager_fatal']:
                pager_fatal_errcnt += 1
                print(f"--> Pager Fatal errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['pager_error']:
                pager_error_errcnt += 1
                print(f"--> Pager Errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['pager_warn']:
                pager_warn_errcnt += 1
                print(f"--> Pager Warnings occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_fatal']:
                echk_fatal_errcnt += 1
                print(f"--> echk Fatal errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_error']:
                echk_error_errcnt += 1
                print(f"--> echk Errors occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            if b_edb['echk_warn']:
                echk_warn_errcnt += 1
                print(f"--> echk Warnings occurred in book {booktype:.50}; book"
                      f' number:{epub_count}:')
            else:
                if not args.quiet:
                    print('No errors or warnings detected.')
            epub_count += 1
            edb_list.append(b_edb)
            t2 = time.perf_counter()
print()
print(f'Completed {max_count} paginations: ')
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
print('------epubcheck Comparison-----')
for book in edb_list:
    if book['orig_fatal'] != book['echk_fatal']:
        if book['orig_fatal']:
            print(f' - {book["title"]:.65}: Original has fatal; paged does not.')
        else:
            print(f' - {book["title"]:.65}: Paged has fatal; original does not.')
    if book['orig_error'] != book['echk_error']:
        if book['orig_error']:
            print(f' - {book["title"]:.65}: Original has error; paged does not.')
        else:
            print(f' - {book["title"]:.65}: Paged has error; original does not.')
    if book['orig_warn'] != book['echk_warn']:
        if book['orig_warn']:
            print(f' - {book["title"]:.65}: Original has warning; paged does not.')
        else:
            print(f' - {book["title"]:.65}: Paged has warning; original does not.')

print()
print('--------Epubcheck Original Summary-----')
print("Original books with epubcheck fatal errors:")
for book in edb_list:
    if book['orig_fatal']:
        print(f' - {book["title"]:.65}')
print('--------------------')
print("Original books with epubcheck errors:")
for book in edb_list:
    if book['orig_error']:
        print(f" - {book['title']:.65}")
print('--------------------')
print("Original books with epubcheck warnings")
for book in edb_list:
    if book['orig_warn']:
        print(f' - {book["title"]:.65}')
print()
print('--------Epubcheck Summary-----')
print("Books with epubcheck fatal errors:")
for book in edb_list:
    if book['echk_fatal']:
        print(f' - {book["title"]:.65}')
print('--------------------')
print("Books with epubcheck errors:")
for book in edb_list:
    if book['echk_error']:
        print(f" - {book['title']:.65}")
print('--------------------')
print("Books with epubcheck warnings")
for book in edb_list:
    if book['echk_warn']:
        print(f' - {book["title"]:.65}')
print()
print('--------Epubpager Summary-----')
print("Books with pager fatal errors:")
for book in edb_list:
    if book['pager_fatal']:
        print(f' - {book["title"]:.65}')
print('--------------------')
print("Books with pager errors:")
for book in edb_list:
    if book['pager_error']:
        print(f" - {book['title']:.65}")
print('--------------------')
print("Books with pager warnings")
for book in edb_list:
    if book['pager_warn']:
        print(f' - {book["title"]:.65}')
print('--------------------')
