import json
import datetime
from subprocess import PIPE, run
import time
import sys

from packages.epub_pagination import epub_pager

BookFileName = 'Books.json'
BookArray = []     # the entire set of dictionaries from the master file
ActiveBook = 0     # an index into BookArray for the currently active book
booklist = []      # the list of titles in the BookArray
CR = '\n'

def build_booklist(bookarray):
    global booklist

    booklist = []
    for book in bookarray:
        booklist.append(book['Title'])
    return booklist

def save_book_dictionary(BookArray):

    with open(BookFileName, 'w') as outfile:
        json.dump(BookArray, outfile, indent=4)
        outfile.close()

def load_book_data():

    # get all dictionaries from the master file
    with open(BookFileName, 'r') as infile:
        jsondata = infile.read()
    bookdata = json.loads(jsondata)
    return bookdata

# this is the main line

BookArray = load_book_data()
booklist = build_booklist(BookArray)

# put your test code here
# now measure time for finding the index in BookArray of a BookID after generating the booklist
# t1 = time.perf_counter()
# for i in range(1,101):
#     for BookID in booklist:
#         Book = GetBook(BookID)
# t2 = time.perf_counter()

paginator = epub_pager.epub_paginator()
paginator.paged_epub_library = '/Users/tbrown/data_store/paged_epubs'
paginator.words_per_page = 300
paginator.page_number_total = True
paginator.page_footer = True,
paginator.page_number_align = 'right'
paginator.page_number_color = 'red'
paginator.page_number_bracket = '<'
paginator.page_number_total = True
paginator.chapter_pages = True
paginator.total_pages = 0
paginator.nav_pagelist = True
paginator.superscript = False
paginator.epubcheck = '/opt/homebrew/bin/epubcheck'
# paginator.epubcheck = ''
paginator.DEBUG = False

# paginator.paginate_epub('/Users/tbrown/Documents/projects/BookTally/dev/test/LeGuinBirthday.epub')
# paginator.paginate_epub('/Users/tbrown/Documents/projects/BookTally/dev/test/Birthday_epub3.epub')
# sys.exit(0)
max_count = 5
epub_count = 0
for book in BookArray:
    format_list = book['formats']
    for booktype in format_list:
#         print('epub location: ' + booktype)
#         print(f"Paginating {booktype}")
        booksplit = booktype.split('/')
        filename = booksplit[len(booksplit)-1]
#         print('filename: ' + filename)
        if 'epub' in filename:
            epub_count += 1
            t1 = time.perf_counter()
            paginator.total_pages = 0
            returncode = paginator.paginate_epub(booktype)
            t2 = time.perf_counter()
#             if returncode!=0:
#                 print(f'{booktype} was not paginated, error {returncode} occurred.')
#             else:
#                 print(f"{book['Title']} has been paginated. ePub file created at: {paginator.paged_epub_library}  in  {t2-t1:.2f} seconds.")
            if epub_count > max_count:
                sys.exit(0)
