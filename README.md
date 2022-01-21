# epubpaginator

epubpaginator is a Python script that generates pagination for ePub
books. 

## ePub2 Support

For ePub2books, epubpaginator can embed formatted lines (called
pagelines) in the text with pagination information both for the entire
book as well as chapter by chapter progress. It can also generate
pagination information formatted as superscripts in the text. These
pagelines and superscripts are displayed by all ereaders.

For ePub3 books, in addition to pagelines and superscripts,
epubpaginator can generate epub3 compliant embedded pagination that
capable ereaders honor (there are few of these, see below). 

## Features

* For ePub3 files, epubpaginator can generate a page-list table in the
  navigation document, and corresponding page links in the epub text.
* epubpaginator can generate "pagelines"--information lines in text of
  an ePub2 or ePub3 document. These are placed at the end of the
  paragraph where the page break occurs and appear as separate
  paragraphs in the book.
* epubpaginator can generate superscripted page information lines in
  text of an ePub2 or ePub3 document. These superscripts are placed
  after the word where the page break occurs.
* If an ePub3 document has existing pagination, epubpaginator can
  match the pagelines or superscripts to the existing pagination. This
  allows epub readers that do not support epub3 pagination to still show
  the publisher's page numbering.
* Font size, color and alignment (right, left, or center) are selectable
  for pagelines.
* Font size and color are selectable for superscripts.
* Total pages may optionally be included in pagelines and superscripts
  for the book and the current chapter.
* For ebooks without existing pagination, the page size may be defined
  by specifying words per page, or by specifying total pages for the
  book in which case words per page is calculated as:

> (words per page) = (words in the book) / (total pages).

## Requirements

1. Python 3.8 or greater. 
2. The library xmltodict. 

## Installation

1. Download epubpaginator.zip and unzip to your chosen location.
2. For your system run: `pip install xmltodict`. If xmltodict is already
installed, pip will inform you of that, otherwise it will be installed.
3. In the installation directory run: `python epubpaginator
--options`. You should see the help message show below.


## Usage

```
epubpaginator --help

usage: epub_paginator.py [-h] [-c CFG] [--outdir OUTDIR] [--match] [--genplist] [--pgwords PGWORDS]
                         [--pages PAGES] [--pageline] [--pl_align PL_ALIGN]
                         [--pl_color {red,blue,green,none}] [--pl_bkt {<,(,none}] [--pl_fntsz PL_FNTSZ]
                         [--pl_pgtot] [--superscript] [--super_color {red,blue,green,none}]
                         [--super_fntsz SUPER_FNTSZ] [--super_total] [--chap_pgtot]
                         [--chap_bkt CHAP_BKT] [--epubcheck EPUBCHECK] [--chk_orig] [--chk_warn]
                         [--ebookconvert EBOOKCONVERT] [--DEBUG]
                         ePub_file

Paginate ePub file.

positional arguments:
  ePub_file             The ePub file to be paginated.

optional arguments:
  -h, --help            show this help message and exit
  -c CFG, --cfg CFG     path to configuration file
  --outdir OUTDIR       location for output ePub files
  --match               If pagination exists, match it.
  --genplist            generate the navigation page list and page links for page numbers
  --pgwords PGWORDS     define words per page; if 0, use pages
  --pages PAGES         if = 0 use pgwords; else pgwords=(wordcount/pages)
  --pageline            generate and insert page pagelinesinto the ePub text
  --pl_align PL_ALIGN   'right', 'left' or 'center'; specify alignment of the pageline
  --pl_color {red,blue,green,none}
                        html color for the inserted pageline
  --pl_bkt {<,(,none}   character to use to bracket page number
  --pl_fntsz PL_FNTSZ   font size as percentage of book font for the pageline
  --pl_pgtot            include total pages in the pageline
  --superscript         generate superscripted page numbers
  --super_color {red,blue,green,none}
                        html color for the inserted page pagelinee.g. 'red'
  --super_fntsz SUPER_FNTSZ
                        font size as percentage of book font for the pageline
  --super_total         include total pages in the pageline
  --chap_pgtot          include chapter page and total in the pagelineand/or superscript
  --chap_bkt CHAP_BKT   '<', '(' or nothing; character to use to bracket page number
  --epubcheck EPUBCHECK
                        location of epubcheck executable
  --chk_orig            Run epubcheck on original file
  --chk_warn            Enable warnings in epubcheck
  --ebookconvert EBOOKCONVERT
                        location of ebook conversion executable
  --DEBUG               print additional debug information to the log file
```

``` bash
    epubpaginator --options epub_file
```

epubpaginator is a command-line tool that can be configured with
command line options, or by referencing a configuration file. The
configuration file is in json format. An example configuration file
"epub_pager.cfg" is provided: 

``` json
{
    "outdir": "/Your/path/for/epubs",
    "match": true,
    "genplist": true,
    "pgwords": 300,
    "pages": 0,
    "pageline": true,
    "pl_align": "center",
    "pl_color": "red",
    "pl_bkt": "<",
    "pl_fntsz": "75%",
    "pl_pgtot": true,
    "superscript": false,
    "super_color": "red",
    "super_fntsz": "60%",
    "super_total": false,
    "chap_pgtot": true,
    "chap_bkt": "",
    "ebookconvert": "none",
    "epubcheck": "none",
    "chk_orig": true,
    "chk_warn": false,
    "DEBUG": false
}
```

Note that the configuration file is in json and must use json syntax,
not python syntax. 

## Why Paginate?

Most ereaders display page numbers that are based on what fits on the
display of your device based on its size and the font size you have
chosen. When you switch devices (say, from your iPhone to your iPad) or
change the font size, the page size and total number of pages in your
book changes. This means you can't use page numbers as bookmarks. It
also means you don't have consistent page lengths, so you don't have a
feel for how much is left in a chapter or in the book. Percentages don't
help much. 20% of a book with 75,000 words is quite different from 20%
of a book with 200,000 words.

Consistent paging can be useful to solve these problems. If an epub book
contains paging information that matches the paging of a physical book,
displaying that information in an ereader that does not support epub3
paging can also be useful.

epubpaginator provides all of these features.

## Epub Reader Support

Most epub readers simply ignore epub3 page-lists. Some read the
page-lists and provide the ability to go to a particular page, but
little else. 

Apple Books on iOS uses epub3 pagination as an option. You must select
"Tap to show print edition page numbers' at the bottom of the Table of
Contents for epub3 pagination to be used. If the ebook does not contain
a page-list element in the navigation file, this option will not be
displayed. When print edition page numbering is enabled, the page
numbering in the displayed footer reflects the page as specified in the
page-list. In addition, Books will display the page number in the margin
beside the location where the actual page break occurred (this could be
in the middle of a paragraph). 

All ereaders support epubpaginator since it simply adds the pagination
to the display text of the book.

### Pagination in epub Readers Without epub3 Pagination Support

Since most epub readers do not support displaying epub3 page-list
information, epubpaginator provides two alternatives for custom
pagination of epub files, pagination that will be displayed by all
ereaders.

#### Pagelines

The 'pagelines' option directs epubpaginator to place formatted lines
containing pagination information in the text. These pagelines are
placed at the end of the paragraph in which the page break occurred.

#### Superscripts

The 'superscript' option directs epubpaginator to place page
information in the text of the book as a superscript placed after the
word where the page break occurs. 

## Examples

The following image is the Calibre ebook-viewer app display a page of a
book paginated with epubpaginator. The superscript page information is
in the second line of the displayed page. The superscript is placed just
after the word at which the page break occurred. The pageline is placed
at the end of the paragraph in which the page break occurred. In each
case, both current page and page totals for the book and the chapter are
presented.

Note that Calibre ebook-viewer does not display information from the
page-list of this ebook in its footer. The footer page numbering is
generated by ebook-viewer and is in about 200 words per page.

<img src="./epub_paginator_super_pageline.png" alt="ebook-viewer"
width="600" >

By contrast, Apple Books shows the page-list page numbers in its footer
line (where a page that contains a page break will show, as in this
example, 2-3), and also shows the exact location of the page break with
a number in the margin. 

One can now see that the superscript inserted by epubpaginator appears
in the same line as the page break, and the pageline inserted by
epubpaginator appears at the end of the paragraph in which the page
break occurred. 

<img src="./FarmBoy_pl_super.png" alt="Apple Books" width="600" >

## The Details

### Color Formatting

epubpaginator allows setting the color of the pageline and the
superscript. However, depending on the ereader used, and the theme used
in the ereader, the colors may not be visible, or may be ignored by the
ereader.

In Apple Books, for example, colors are acknowledged when the background
selected is white or sepia, but ignored when the background is gray or
black.

### File Handling

epubpaginator creates a copy of the input epub file and operates on
the copy. Although epubpaginator should not corrupt, delete, or
otherwise modify the original epub file, always back up your files!
epubpaginator requires epub files without DRM (Digital Rights
Management) to operate. It outputs the modified file to the directory
specified in 'outdir' with '-paged' appended to the file name.

### Determining the Page Length

If epubpaginator detects an existing page-list element in the
navigation file of the epub (this can only occur when the epub file is
version 3), 'genplist' is forced to false. epubpaginator does not
overwrite or modify an existing page-list and will not generate a second
page-list if one exists.

If 'match' is set and a page-list element is found, then pagination for
pagelines and/or superscripts is matched to the existing pagination.

If 'genplist' or 'pagelines' or 'super' are enabled and no existing
page-list element is found, the pagination will be based on the values
of the options 'pgwords' and 'pages' as follows:

1. If 'pgwords' and 'pages' are zero, this is a fatal error.
   epubpaginator has no way to determine where to place pages.
2. If 'pgwords' is not zero, its value is used to determine the page
   length for the paginated book.
3. if 'pgwords' is zero and 'pages' is not zero, then 'pgwords' is set
   to the integer value of (the book word count) / (pages) and 'pgwords'
   is used to determine the page length for the paginated book.

### epubcheck Usage

[epubcheck
](https://www.w3.org/publishing/epubcheck/docs/getting-started/) may be
used to check the original epub and the paginated epub for errors. Set
the --epubcheck configuration option to the path of your version of
epubcheck. If you want the original epub file to be checked, also set
--chk_orig.

#### epubcheck Comments

1. epubcheck is slow compared to epubpaginator. epubpaginator will
   generally take much less than a second to paginate an epub file.
   epubcheck, even on the smallest files, will usually take two or more
   seconds. 
2. Many epub files, particularly older files, will cause epubcheck to
   generate multiple errors, often dozens or even hundreds of errors.
   epubpaginator simply reports these errors and whether there was a
   difference in the number of warnings, errors, or fatal errors between
   the check of the original book and the paginated book. 
3. Fortunately, most epub readers are very forgiving of warnings, errors
   and fatal errors reported by epubcheck. While it is common for
   epubcheck to report errors and fatal errors, it is relatively
   uncommon for epub readers to improperly render the epub book. 
4. The most common errors that occur in epubpaginator formatted books
   that are not present in the original book have to do with pagelines
   being placed in locations were epubcheck does not allow them. I have
   not seen any of these errors cause issues in the epub readers I have
   tested. 

### epub_converter Usage

[Calibre](https://calibre-ebook.com) provides a command-line ebook
converter program, ebook-convert, which epubpaginator can use to
convert epub2 books to epub3 books to allow page-list generation. If the
option "ebookconvert" contains the path to ebook-convert, epub2 books
will be converted to epub3 and the epub3 book will be paginated.

The use of Calibre ebook-converter for epub2 books is encouraged because
the converted books are more consistent in structure than the originals.
This makes epubpaginator more effective in parsing and changing them. In
a handfull of cases, I have seen epub2 books which epubpaginator does
not handle properly, while it does handle the converted epub3 books.

### So, Does It Really Work?

I think so, but I will probably be surprised by the number of bugs
reported if a lot of folks use it.

I have tested epubpaginator on more than 800 epub books I have
collected over the last ten years. The result was an education in the
variability of epub formats, both in ePub2 and ePub3 books. I have fixed
most of the errors I found, but I am sure there are more out there. 

Some older ePub2 books, have malformed xml or html files that xmltodict
cannot parse. epubpaginator detects these errors and refuses to
paginate these books. In all of my books where I see these problems,
converting the books to ePub3 using Calibre's conversion program results
in ebooks that epubpaginator can properly handle.

If I use Calibre's ebook-convert to convert books from ePub2 to ePub3,
epubpaginator converts all of my books. For testing purposes I assume
that when there are no differences in errors found by epubcheck between
paginated books and the originals, that the books will properly render.
I spot checked a number of these, but not all of them. For books where
there is a difference in epubcheck results between paginated books and
the originals, I have verified the books are rendered properly.
