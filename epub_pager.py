import sys
from subprocess import PIPE, run
import time
from pathlib import Path
import urllib.parse

import xmltodict
import json
import zipfile

CR = '\n'
opf_dictkey = 'package'
# epubns = 'xmlns:epub="http://www.idpf.org/2011/epub"'
pglnk = 'pagetb'
epubns = 'xmlns:epub="http://www.idpf.org/2007/ops"'


class epub_paginator:
    """
    Paginate an ePub3 using page-list navigation and/or inserting page
    information footers and/or superscripts into the text.

    **Release Notes**

    **Version 2.97**
    1. Added chk_orig property to allow epubcheck to be run on original
    file. Provide stats on errors for both original and paged epub file
    results from epubcheck.
    1. Added finding id="page-7" to searching for a page value in a
    pagebreak element. A lot of books don't have a 'title' or
    'aria-label' specification, or a displayable page number. 
    1. Changed epubcheck to not report warnings to simplify testing.
    1. Made the page link id's more unique so we don't inadvertently get
    duplicate ids of form id='page7' for example. I use pagetb as the
    prefix now.
    1. Added a fix for figuring out the relative href for page links
    when opf_file and nav file are not at the same directory level.
    1. Fixed books that have file names or paths that contain spaces,
    commas, etc, which result in invalid URI in pagelists. 
    1. If a file in the spine contains 'toc' or 'contents', skip
    counting words and inserting pagebreaks. This avoids lots of
    epubcheck errors, even though those errors are benign.
    1. Added chk_xmlns to fix namespace errors when we are adding a
    page-list

    **Version 2.96**
    1. fixed a bug with calculating words per page when not matching and
    total pages is provided.

    **Version 2.95**
    Fixing bugs and doing extensive testing with hundreds of epubs.

    1. Fixed a problem with removing existing pagebreaks in a converted
    epub2 book.
    1. Parsed the epubcheck stdout to find Messages and report fatal and
    other errors.
    1. Fixed a problem where matching missed pages because it was
    looking for a </span> after the epub:type="pagebreak" element.
    Should look for '/>' instead.
    1. Additional fixes that allow proper identification and handling of
    epubs that use 'aria' features and don't have epub:type in
    pagebreaks.
    1. Major fix--we no longer scan and word count anything before
    <body. Then, no pagelinks appear outside of <body and this makes
    epubcheck happier.
    1. When the epub:type page-list is added, also add the namespace
    because it is not there sometimes and being repetitive doesn't
    matter.
    1. Fixed a bug where <span> was not removed correctly. Now checks
    for /> as end of span rather than assuming </span> is the element
    terminator.

    **Version 2.94**

    PEP8 compliant.

    **Version 2.93**

    1. Update Doc strings.
    1. Refactor to eliminate globals--essentially move the class
       statement to the top of the file and reference globals with self.
    1. Fixed a bug that was looking for '/>' as the end of the pagebreak
       element in scan and match routine. Should have been looking for
       </span>.

    **Version 2.92**

    1. Can now match the superscript and footer insertions to existing
       page numbering. This is automatically done if a page-list exists
       in the nav file.

    **Version 2.91**

    1. Lots of refactoring of code.
    1. Added ebpub_info dictionary to consolidate data about the epub
       file.
    1. Added get_nav_pagecount() which determines the maximum page
       number in an already paginated file.

    **Version 2.9**

    1. Add the role="doc-pagebreak" to the page links. This appears to
       fix the bug that resulted in iBooks not showing all the page
       numbers in the margin.

    **Version 2.8**

    1. Fixed a bug where the </span> was not removed when removing
       existingn page links from a converted epub.

    **Version 2.7**

    1. Added rdict to return a set of data to the calling program,
       including what used to go to stdout

    **Version 2.6**

    1. Fixed a bug in logic that removes pagebreak elements from
       converted epub2 books.

    **Version 2.5**

    1. Implemented conversion of epub2 to epub3 using calibre
       ebook-converter.  epub_paginator contains command line switches
       for all options to epub_pager.

    **Version 2.4**

    1. Implement configuration file.

    **Version 2.3**

    1. Add log file. Program produces minimal output, but puts data in
       log file.
    2. If running epubcheck, echo stdout to stdout, but echo stderr only
       to the log file.
    3. If DEBUG is False, remove the unzipped epub directory when done.

    **Version 2.2**

    1. Add epub_version exposed command to the class.

    1. Fixed bug that mispositioned the footer inside italic or other
       textual html elements and caused epubcheck errors. footers are
       now properly positioned after the <div> or <p> active element
       when the page limit is reached.

    1. Refactored some of the code. Uses f strings for formatting;
       cleaned up printing.

    **Version 2.1**

    1. Made a Github repository with a local copy.
    1. Rewrote the scanning algorithm. Scans character by character
       after <body> element in spine files. Doesn't care about <p>
       elements or anything else. Still places footer before paragraph
       where the page ends. Other page numbering is at precise word
       location.
    1. Note that nested <div> elements are created by the placement of
       footers and this creates errors in epubcheck. However, these
       errors do not affect Calibre book reader, nor Apple Books.

    **Version 2.0**

    1. Includes Docstrings that are compatible with creating
       documentation using pdoc.
    1. Lot's of refactoring has been done.
    1. Verifies epub3 version.
    1. Verifies nav file exists.
    1. Doesn't generate page-list if it already exists.
    1. Adds chapter page numbering.
    """

    version = '2.97'
    bkinfo = {
        "version": "",
        "converted": False,
        "title": "",
        "unzip_path": "",
        "nav_file": "None",
        "nav_item": "None",
        "opf_file": "None",
        "has_plist": False,
        "has_pbreaks": False,
        "spine_lst": [],
        "words": 0,
        "match": False,
        "genplist": True,
        "pgwords": 0,
        "pages": 0
    }
    curpg = 1        # current page number
    tot_wcnt = 0     # count of total words in the book
    pg_wcnt = 0      # word count per page
    plist = ''       # the page-list element for the nav file
    bk_flist = []    # list of all files in the epub
    logpath = ''     # path for the logfile
    epub_file = ''   # this will be the epub to paginate

    rdict = {                  # data to return to calling program
        "logfile": "",         # logfile location and name
        "bk_outfile": "",      # modified epub file name and location
        "errors": [],          # list of errors that occurred
        "fatal": False,        # Was there a fatal error?
        "error": False,        # epub_pager error
        "warn": False,         # epub_pager warning
        "orig`_fatal": 0,      # epubcheck fatal error original file
        "orig`_error": 0,      # epubcheck error original file
        "orig`_warn": 0,       # epubcheck warning original file
        "echk_fatal": 0,       # epubcheck fatal error
        "echk_error": 0,       # epubcheck error
        "echk_warn": 0,        # epubcheck warning
        "messages": ""         # list of messages generated.
    }

    def __init__(self):
        """
        **Instance Variables**

        **_outdir_**

        full os path for placement of the paginated ePub file.

        **_match_**

        Boolean, if book is paginated, match super and footer insertion
        to existing page numbering. Default True

        **_genplist_**

        Create the page_list element in the navigation file.

        **_pgwords_**

        Number of words per page.

        **_pages__**

        Number of pages in the book.

        **_footer_**

        Boolean, if True, insert the page footers, otherwise do not.

        **_ft_align_**

        left, right, or center, alignment of the page numbers in the
        footer.

        **_ft_color_**

        Optional color for the footer--if not set, then no color is
        used.

        **_ft_bkt_**

        Character (e.g. '<' or '(' ) used to bracket page numbers in
        page footer.

        **_ft_fntsz_**

        A percentage value for the relative font size used for the
        footer.

        **_ft_pgtot_**

        Present the book page number with a total (34/190) in the
        footer.

        **_superscript_**

        Insert a superscripted page entry

        **_super_color_**

        Optional color for the superscript--if not set, then no color is
        used.

        **_super_fntsz_**

        A percentage value for the relative font size used for
        superscript.

        **_super_total_**

        Present the book page number with a total (34/190) in
        superscript.

        **_chap_pgtot_**

        Present the chapter page number and chapter page number total in
        the footer and/or superscript.

        **_chap_bkt_**

        Character (e.g. '<' or '(' ) used to bracket page numbers in
        footer and/or superscript.

        **_ebookconvert_**

        The OS path of the ebook conversion program. If present, epub2
        books are converted to epub3 before pagination.

        **_epubcheck_**

        The OS path of epubcheck. If present, epubcheck is run on the
        created file.

        **_chk_orig_**

        Run epubcheck on the file before pagination

        **_DEBUG_**

        Boolean. If True, print status and debug information to logile
        while running.

        """
        self.outdir = ("/Users/tbrown/Documents/projects/"
                       "BookTally/paged_epubs")
        self.match = True
        self.genplist = True
        self.pgwords = 300
        self.pages = 0
        self.footer = False
        self.ft_align = 'center'
        self.ft_color = 'red'
        self.ft_bkt = '<'
        self.ft_fntsz = '75%'
        self.ft_pgtot = True
        self.superscript = False
        self.super_color = 'red'
        self.super_fntsz = '60%'
        self.super_total = True
        self.chap_pgtot = True
        self.chap_bkt = '<'
        self.ebookconvert = None
        self.epubcheck = None
        self.chk_orig = False
        self.DEBUG = False

# the following two routines are modified from those on GitHub:
# https://github.com/MJAnand/epub/commit/8980928a74d2f761b2abdb8ef82a951be11b26d5

    def ePubZip(self, epub_path, srcfiles_path, bk_flist):
        """
        Zip files from a directory into an epub file

        **Keyword arguments:**

        **_epub_path_** -- os path for saving creating epub file

        **_srcfiles_path_** -- path of the directory containing epub
        files

        **_bk_flist_** -- the list of files to zip into the epub file

        """
        with zipfile.ZipFile(epub_path, 'w') as myzip:
            if 'mimetype' in bk_flist:
                myzip.write(srcfiles_path + '/' + 'mimetype', 'mimetype')
                bk_flist.remove('mimetype')
            else:
                self.wrlog(True,
                           'Fatal error, no mimetype file was found.')
                if self.DEBUG:
                    self.wrlog(False, 'bk_flist: ')
                    self.wrlog(False, bk_flist)
                sys.exit('Fatal error, no mimetype file was found.')
        with zipfile.ZipFile(epub_path, 'a', zipfile.ZIP_DEFLATED) as myzip:
            for ifile in bk_flist:
                myzip.write(f"{srcfiles_path}/{ifile}",
                            ifile,
                            zipfile.ZIP_DEFLATED)

    def ePubUnZip(self, fileName, unzip_path):
        """
        Unzip ePub file into a directory

        **Keyword arguments:**

        **_fileName_** -- the ePub file name

        **_path_**     -- path for the unzipped files.

        """

        z = zipfile.ZipFile(fileName)
        self.bk_flist = z.namelist()
        z.extractall(unzip_path)
        z.close()

    def get_version(self):
        """
        Return version of epub_pager.
        """

        return(self.version)

    def get_bkinfo(self):
        """
        Gather useful information about the epub file and put it in the
        bkinfo dictionary.

        **Instance Variables**

        **_epub_file_**  -- ePub file to return version of

        """

        self.bkinfo = {
            "version": "",
            "converted": False,
            "title": "",
            "unzip_path": "",
            "nav_file": "None",
            "opf_file": "None",
            "has_plist": False,
            "match": False,
            "has_pbreaks": False,
            "spine_lst": [],
            "words": 0,
            "pgwords": 0,
            "pages": 0
        }
        # The epub name is the book file name with spaces removed and '.epub'
        # removed.
        dirsplit = self.epub_file.split('/')
        stem_name = dirsplit[len(dirsplit)-1].replace(' ', '')
        self.bkinfo['title'] = stem_name.replace('.epub', '')
        self.logpath = Path(f"{self.outdir}/" f"{self.bkinfo['title']}.log")
        self.rdict['logfile'] = self.logpath
        bkout = f"{self.outdir}/{self.bkinfo['title']}.epub"
        self.rdict['bk_outfile'] = bkout
        with self.logpath.open('w') as logfile:
            logfile.write(''+'\n')
        if not Path(self.epub_file).is_file():
            self.wrlog(True, 'Source epub not found.')
            self.rdict['errors'].append("Fatal error: Source epub not found.")
            self.rdict['fatal'] = True
            return(self.rdict)
        self.wrlog(True, '---------------------------')
        self.wrlog(True,  f"epub_paginator version {self.get_version()}")
        self.wrlog(True,  f'Paginating {dirsplit[len(dirsplit)-1]}')
        # dump configuration
        self.wrlog(False, f'Configuration:')
        self.wrlog(False, f'  outdir: {self.outdir}')
        self.wrlog(False, f'  match: {self.match}')
        self.wrlog(False, f'  genplist: {self.genplist}')
        self.wrlog(False, f'  pgwords: {self.pgwords}')
        self.wrlog(False, f'  pages: {self.pages}')
        self.wrlog(False, f'  footer: {self.footer}')
        self.wrlog(False, f'  ft_align: {self.ft_align}')
        self.wrlog(False, f'  ft_color: {self.ft_color}')
        self.wrlog(False, f'  ft_bkt: {self.ft_bkt}')
        self.wrlog(False, f'  ft_fntsz: {self.ft_fntsz}')
        self.wrlog(False, f'  ft_pgtot: {self.ft_pgtot}')
        self.wrlog(False, f'  superscript: {self.superscript}')
        self.wrlog(False, f'  super_color: {self.super_color}')
        self.wrlog(False, f'  super_fntsz: {self.super_fntsz}')
        self.wrlog(False, f'  super_total: {self.super_total}')
        self.wrlog(False, f'  chap_pgtot: {self.chap_pgtot}')
        self.wrlog(False, f'  chap_bkt: {self.chap_bkt}')
        self.wrlog(False, f'  ebookconvert: {self.ebookconvert}')
        self.wrlog(False, f'  epubcheck: {self.epubcheck}')
        self.wrlog(False, f'  DEBUG: {self.DEBUG}')

        # first get the epub_version
        self.bkinfo['version'] = self.get_epub_version(self.epub_file)
        if self.bkinfo['version'] == 'no_version':
            estr = 'Fatal error: Version was not found in the ePub file.'
            self.rdict['errors'].append(estr)
            self.rdict['fatal'] = True
            return
        vnum = float(self.bkinfo['version'])
        if vnum < 3.0:
            if self.DEBUG:
                self.wrlog(True, 'Handling epub 2')
            # if convert is set, then convert to epub3 first
            if self.ebookconvert != None:
                self.wrlog(True,
                           (f'    Converting to epub3 using '
                            f'{self.ebookconvert}'))
                epub3_file = self.epub_file.replace('.epub', '_epub3.epub')
                ebkcnvrt_cmd = [self.ebookconvert,
                                self.epub_file,
                                epub3_file,
                                '--epub-version',
                                '3']
                result = run(ebkcnvrt_cmd,
                             stdout=PIPE,
                             stderr=PIPE,
                             universal_newlines=True)
                if result.returncode == 0:
                    # now try again on version
                    v = self.get_epub_version(self.epub_file)
                    self.bkinfo['version'] = v
                    if self.bkinfo['version'] == 'no_version':
                        estr = ('Fatal error: After conversion, version was '
                                'not found in the ePub file.')
                        self.rdict['errors'].append(estr)
                        self.rdict['fatal'] = True
                        return
                    self.wrlog(False, 'Conversion log:')
                    self.wrlog(False, result.stdout)
                    self.epub_file = epub3_file
                    self.wrlog(True,
                               f'epub converted - now paginating new file.')
                    lstr = f'Paginating epub3 file: {self.epub_file}'
                    self.wrlog(True, lstr)
                    plstr = (f'<nav epub:type="page-list" id="page-list" '
                             'hidden="hidden"><ol>') + CR
                    self.plist = plstr
                    self.bkinfo['converted'] = True
                else:
                    lstr = 'Conversion to epub3 failed. Conversion reported:'
                    self.wrlog(True, lstr)
                    self.wrlog(True, result.stderr)
                    astr = 'Fatal error: Conversion to epub3 failed.'
                    self.rdict['errors'].append(astr)
                    self.rdict['fatal'] = True
                    return
            else:
                lstr = ("    --> WARNING <-- Epub version is not 3 or newer,"
                        "page-link navigation disabled.")
                self.wrlog(False, lstr)
                lstr = ("    --> WARNING <-- To enable page-link "
                        "navigation, convert to Epub3 and try again.")
                self.wrlog(False, lstr)
                self.genplist = False
                self.match = False
        else:
            self.plist = (f'<nav epub:type="page-list" '
                          f'id="page-list" hidden="hidden"><ol>'
                          '\n')
        self.bkinfo['unzip_path'] = f"{self.outdir}/{self.bkinfo['title']}"

    def get_epub_version(self, epub_file):
        """
        Return ePub version of ePub file

        If ePub does not store the version information in the standard
        location, return 'no version'

        **Instance Variables**

        **_epub_file_**

        ePub file to return version of

        """

        zfile = zipfile.ZipFile(epub_file)
        # find the opf file, which contains the version information
        x_dct = xmltodict.parse(zfile.read('META-INF/container.xml'))
        opf_file = x_dct['container']['rootfiles']['rootfile']['@full-path']
        opf_dict = xmltodict.parse(zfile.read(opf_file))
        if opf_dict.get('package', 'badkey') == 'badkey':
            lstr = ('ABORTING: Error parsing opf file, '
                    'this is probably an ePub2 file.')
            self.wrlog(True, lstr)
            self.wrlog(True, 'Convert to ePub3 and try again.')
            return('no_version')
        else:
            version = opf_dict['package']['@version']
        return (version)

    def get_nav_pagecount(self):
        """
        Read the nav file and parse the page-list entries to find the
        total pages in the book

        **Instance Variables**

        **_navfile_**  -- ePub navigation file

        """

        with self.bkinfo['nav_file'].open('r') as nav_r:
            nav_data = nav_r.read()
        loc = nav_data.find('epub:type="page-list"')
        if loc == -1:
            # this should never happen since we get here only after the entry
            # was found
            sys.exit(('Error! oops, the page-list entry was not found '
                      'after having been initially found.'))
        nav_data = nav_data[loc:]
        not_done = True
        max_page = 0
        while not_done:
            loc = nav_data.find('<a href')
            if loc == -1:
                not_done = False
                continue
            nav_data = nav_data[loc:]
            loc = nav_data.find('">')
            if loc == -1:
                self.wrlog(True, "Unclosed '<a href' element in nav file.")
                self.wrlog(True, 'Does this file pass epubcheck?')
                self.rdict['fatal'] = True
                return (0)
            loc += 2
            nav_data = nav_data[loc:]
            loc2 = nav_data.find('</a>')
            if loc2 == -1:
                self.wrlog(True, "'</a>' element not found in nav file.")
                self.wrlog(True, 'Does this file pass epubcheck?')
                self.rdict['fatal'] = True
                return (0)
            if nav_data[:loc2].isdigit():
                if int(nav_data[:loc2]) > max_page:
                    max_page = int(nav_data[:loc2])
        self.wrlog(True, f'Nav pagelist page count is: {max_page}')
        return(max_page)

    def wrlog(self, stdout, message):
        """
        Write a message to the log file.

        **Instance Variables**

        **_stdout_**

        If True, then echo the message to stdout.

        **_message_**

        The message to print

        """
        '''
        if (stdout):
            print(message)
            self.rdict['messages'] += '\n' + message
        '''
        with self.logpath.open('a') as logfile:
            logfile.write(message + '\n')

    def update_navfile(self):
        """
        Add generated page-list element to the ePub navigation file
        Verify that nav file has proper xmlns. If not fix it.
        """

        with self.bkinfo['nav_file'].open('r') as nav_file_read:
            nav_datar = nav_file_read.read()
            nav_data = self.chk_xmlns(nav_datar)
        pagelist_loc = nav_data.find('</body>')
        new_nav_data = nav_data[:pagelist_loc]
        new_nav_data += self.plist
        with self.bkinfo['nav_file'].open('w') as nav_file_write:
            nav_file_write.write(new_nav_data)
            nav_file_write.write(nav_data[pagelist_loc:])

    def add_plist_target(self, curpg, href):
        """
        Generate page-list entry and page footer and add them to a
        string that accumulates them for placement in the navigation
        file.

        **Keyword arguments:**

        **_curpg_**

        The page number in the book.

        **_href_**

        The filename and path for the internal page link in the book.

        """

        self.plist += f'  <li><a href="{href}#{pglnk}{curpg}">{curpg}</a></li>'
        self.plist += CR
        return

    def bld_foot(self, curpg, sct_pg, sct_pgcnt):
        """
        Format and return page footer.

        **Keyword arguments:**
        **_curpg_**

        The current page number of the book.

        **_sct_pg_**

        The current section page number.

        **_sct_pgcnt_**

        The pagecount of the section.

        """

        # construct the page footer based on formatting selections
        # brackets
        if self.ft_bkt == '<':
            flb = '&lt;'
            frb = '&gt;'
        elif self.ft_bkt == '-':
            flb = '-'
            frb = '-'
        else:
            flb = ''
            frb = ''
        if self.chap_bkt == '<':
            clb = '&lt;'
            crb = '&gt;'
        elif self.chap_bkt == '-':
            clb = '-'
            crb = '-'
        else:
            clb = ''
            crb = ''
        # book pages format
        if self.ft_pgtot:
            pagestr_bookpages = f"{flb}{curpg}/{self.bkinfo['pages']}{frb}"
        else:
            pagestr_bookpages = f"{flb}{curpg}{frb}"
        # chapter pages format
        if self.chap_pgtot:
            pagestr_chapterpages = f" {clb}{sct_pg}/{sct_pgcnt}{crb}"
        else:
            pagestr_chapterpages = ''
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.ft_color == 'none':
            if self.ft_align == 'float':
                # the following creates center justified bookpages and right
                # justified chapter pages.
                footer = (f'<div> <p style="font-size:75%; '
                          f'float: left;margin: 0 0 0 0">{pagestr_bookpages}'
                          f'</p><p style="font-size:75%; float: right;'
                          f'margin: 0 0 0 0">{pagestr_chapterpages}</p>'
                          f'</div><div style="clear: both;"></div>')
            else:
                footer = (f'<div style="font-size:{self.ft_fntsz}; '
                          f'text-align: self.ft_align;margin: 0 0 0 0">'
                          f'{pagestr}</div>')

        else:
            if self.ft_align == 'float':
                # the following creates center justified bookpages and right
                # justified chapter pages.
                footer = (f'<div> <p style="font-size:75%; float: left; '
                          f'color: {self.ft_color};margin: 0 0 0 0">'
                          f'{pagestr_bookpages}</p><p style="font-size:75%; '
                          f'float: right; color: {self.ft_color};'
                          f'margin: 0 0 0 0">{pagestr_chapterpages}</p>'
                          f'</div><div style="clear: both;"></div>')
            else:
                footer = (f'<div style="font-size:{self.ft_fntsz}; '
                          f'text-align:{self.ft_align}; '
                          f'color: {self.ft_color};margin: 0 0 0 0">'
                          f'{pagestr}</div>')
        return (footer)

    def new_super(self, curpg, sct_pg, sct_pgcnt):
        """
        Format and return a <span> element for superscripted page
        numbering.

        **Keyword arguments:**
        **_curpg_**

        The current page number of the book.

        **_sct_pg_**

        The current section page number.

        **_sct_pgcnt_**

        The pagecount of the section.

        """

        # construct the page footer based on formatting selections
        # brackets
        if self.ft_bkt == '<':
            flb = '&lt;'
            frb = '&gt;'
        elif self.ft_bkt == '-':
            flb = '-'
            frb = '-'
        else:
            flb = ''
            frb = ''
        if self.chap_bkt == '<':
            clb = '&lt;'
            crb = '&gt;'
        elif self.chap_bkt == '-':
            clb = '-'
            crb = '-'
        else:
            clb = ''
            crb = ''
        # book pages format
        if self.super_total:
            pagestr_bookpages = f"{flb}{curpg}/{self.bkinfo['pages']}{frb}"
        else:
            pagestr_bookpages = f"{flb}{curpg}{frb}"
        # chapter pages format
        if self.chap_pgtot:
            pagestr_chapterpages = f" {clb}{sct_pg}/{sct_pgcnt}{crb}"
        else:
            pagestr_chapterpages = ''
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.super_color == 'none':
            page_superscript = (f'<span style="font-size:{self.super_fntsz};'
                                f'vertical-align:super">{pagestr}</span>')

        else:
            page_superscript = (f'<span style="font-size:{self.super_fntsz};'
                                f'vertical-align:super '
                                f'color:{self.super_color}">{pagestr}</span>')
        return (page_superscript)

    def bld_href(self, manifest_item):
        """
        If the opf file and the nav file are at different directory
        levels in the epub structure, the hrefs in the page_list cannot
        be identical to the href's in the manifest. Fix this

        Returns: the href for the pagelink

        **Keyword arguments:**

        **_manifest_item_**

        The href for the file in the manifest of the opf_file

        """

        opf_list = self.bkinfo['opf_file'].split('/')
        nav_list = str(self.bkinfo['nav_item']).split('/')
        manifest_list = manifest_item['@href'].split('/')
        manifest_fnm = manifest_list[len(manifest_list)-1]
        if len(opf_list) == 1:
            opf_path = []
        else:
            opf_path = opf_list[:len(opf_list)-1]
        if self.DEBUG:
            lstr = f"opf_path: {opf_path}"
            self.wrlog(True,lstr)
        if len(nav_list) == 1:
            # this means nav and opf are same level, so use manifest
            # paths
            if self.DEBUG:
                lstr = (f"nav file at same level as opf/manifest, "
                        f"use manifest href.")
                self.wrlog(True, lstr)
            href = urllib.parse.quote(manifest_item['@href'])
            return(href)
        np = nav_list[:len(nav_list)-1]
        nav_path = opf_path + np
        if self.DEBUG:
            lstr = f"nav_path: {nav_path}"
            self.wrlog(True,lstr)
        if len(manifest_list) == 1:
            manifest_path = []
        else:
            manifest_path = manifest_list[:len(manifest_list)-1]
        if self.DEBUG:
            lstr = f"manifest_path: {manifest_path}"
            self.wrlog(True,lstr)
        nn = opf_path + manifest_path
        if self.DEBUG:
            lstr = f"opf_path+manifest_path: {nn}"
            self.wrlog(True, lstr)
        if nn == nav_path:
            if self.DEBUG:
                lstr = (f"nav file at same level as opf/manifest, "
                        f"remove subdirectories from href.")
                self.wrlog(True, lstr)
            href = urllib.parse.quote(manifest_fnm)
        else:
            if self.DEBUG:
                lstr = (f"Oops, opf_path: {opf_path}; manifest_path: "
                        f"{manifest_path}")
                self.wrlog(True, lstr)
            href = urllib.parse.quote(manifest_item['@href'])
        return(href)

    def scan_spine(self, path):
        """
        Verify ePub has a navigation file.

        Check for existing page-list element in the nav file.  Abort as
        necessary.

        Create a list of file_list dictionaries from the spine element
        in the opf file:

            Dictionary keys:

                filename: the full system path of the filename in the
                unzipped epub

                href: the href value from the manifest--used to create
                the page links

                sct_pgcnt: added later when the section is pre-scanned

        **Keyword arguments:**

        **_path_**

        The os path to the unzipped ePub files.

        returns spine_lst
        """

        # find the opf file using the META-INF/container.xml file
        confile = Path(f"{path}/META-INF/container.xml")
        with confile.open('r') as container_file:
            xd = xmltodict.parse(container_file.read())
            opf_file = xd['container']['rootfiles']['rootfile']['@full-path']
            self.bkinfo['opf_file'] = opf_file
            opf_path = opf_file.split('/')
            disk_path = ''
            if opf_path:
                for index in range(0, len(opf_path)-1):
                    disk_path += f"{opf_path[index]}/"
            else:
                self.rdict['fatal'] = True
                self.wrlog(True, 'Fatal error: opf file not found')
                return
            opf_filep = Path(f"{path}/{opf_file}")

        # read the opf file and find nav file
        with opf_filep.open('r') as opf_file:
            opf_dict = xmltodict.parse(opf_file.read())
        # be sure we find a nav file
            if self.genplist:
                for item in opf_dict[opf_dictkey]['manifest']['item']:
                    if item.get('@properties') == 'nav':
                        navf = Path(f"{path}/{disk_path}{item['@href']}")
                        self.bkinfo['nav_item'] = item['@href']
                        self.bkinfo['nav_file'] = navf
                if self.bkinfo['nav_file'] == 'None':
                    self.wrlog(True,
                               ('Fatal error - did not find navigation file'))
                    self.rdict['fatal'] = True
                    return
                else:
                    lstr = f"nav_file found: {self.bkinfo['nav_file']}"
                    self.wrlog(False, lstr)
                # we have a nav file, verify there is no existing page_list
                # element
                    if self.genplist:
                        with self.bkinfo['nav_file'].open('r') as nav_r:
                            nav_data = nav_r.read()
                            lstr = 'epub:type="page-list"'
                            if nav_data.find(lstr) != -1:
                                self.genplist = False
                                self.bkinfo['has_plist'] = True
                                self.wrlog(True,
                                           ('    ->INFO<- This epub file '
                                            'already has a page-list '
                                            'navigation element.'))
                                self.wrlog(True,
                                           ('   ->INFO<- page-list navigation '
                                            'was selected but will not '
                                            'be created.'))
                                if self.match:
                                    self.bkinfo['match'] = True
                                    # count the total number of pages in the
                                    # nav pagelist
                                    pgs = self.get_nav_pagecount()
                                    self.bkinfo['pages'] = pgs
                                else:
                                    self.bkinfo['match'] = False
                            else:
                                # there is no pagelist, unset match
                                self.match = False
                                self.bkinfo['has_plist'] = False
                                self.bkinfo['match'] = False

        # we're good to go
        spine_lst = []
        for spine_item in opf_dict[opf_dictkey]['spine']['itemref']:
            if self.DEBUG:
                lstr = f"spine_item idref: {spine_item['@idref']}"
                self.wrlog(False, lstr)
            for manifest_item in opf_dict[opf_dictkey]['manifest']['item']:
                if spine_item['@idref'] == manifest_item['@id']:
                    if ('toc' in manifest_item['@href'].casefold() or
                        'contents' in manifest_item['@href'].casefold()):
                        self.wrlog(True, (f"Skipping file "
                                            f"{manifest_item['@href']} "
                                            f"because TOC."))
                    else:
                        fdict = {}
                        fdict['disk_file'] = f"{disk_path}{manifest_item['@href']}"
                        # take care of books structured with opf file and
                        # nav file at different directory levels
                        fdict['href'] = self.bld_href(manifest_item)
                        spine_lst.append(fdict)
        self.bkinfo['spine_lst'] = spine_lst
        return()

    def count_words(self):
        """
        Scan book contents and count words

        This is an informational scan only, data is gathered, but no
        changes are made
        """

        book_wordcount = 0
        idx = 0
        for chapter in self.bkinfo['spine_lst']:
            efile = Path((f"{self.bkinfo['unzip_path']}/"
                          f"{chapter['disk_file']}"))
            with efile.open('r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
                if self.DEBUG:
                    self.wrlog(False,
                               f'The word count is {book_wordcount:,} .')
                    self.wrlog(False, f'The page count is {book_curpg:,}')
            # we always do this loop to count words.  But if we are matching
            # pages, do not change chapter nor book_curpg
            body1 = ebook_data.find('<body')
            if body1 == -1:
                self.rdict['errors'].append(f"Fatal error: No <body> found. "
                                            f"File: {chapter['disk_file']}")
                self.rdict['fatal'] = True
                return 0
            else:
                idx = body1
            while idx < len(ebook_data)-1:
                if ebook_data[idx] == '<':
                    # we found an html element, just scan past it and don't
                    # count words
                    idx += 1
                    while ebook_data[idx] != '>':
                        idx += 1
                    idx += 1
                elif ebook_data[idx] == ' ':  # we found a word boundary
                    book_wordcount += 1
                    while ebook_data[idx] == ' ':  # skip additional whitespace
                        idx += 1
                else:  # just copy non-white space and non-element stuff
                    idx += 1
        self.bkinfo['words'] = book_wordcount
        if self.bkinfo['has_plist'] and self.bkinfo['match']:
            wc = int(self.bkinfo['words'] / self.bkinfo['pages'])
            self.bkinfo['pgwords'] = wc
        else:
            self.bkinfo['pgwords'] = self.pgwords
        return

    def chk_xmlns(self, ebook_data):
        """
        Verify that ebook_data has proper xmlns:epub statement. If not,
        insert it.

        **Keyword arguments:**
        ebook_data - complete data from an xhtml file.
        """
        dct = xmltodict.parse(ebook_data)
        # print(f"xmlns: {dct['html']['@xmlns']}")
        d = dct['html']
        if d.get('@xmlns:epub', False):
            # self.wrlog(True, f"xmlns:epub namespace is found.")
            return(ebook_data)
        else:
            if self.DEBUG:
                self.wrlog(True, f"Adding xmlns:epub namespace.")
            loc = ebook_data.find('<html')
            newbk = ebook_data[:loc]
            ebook_data = ebook_data[loc:]
            loc2 = ebook_data.find('>')
            newbk += ebook_data[:loc2]
            newbk += ' '
            newbk += epubns
            newbk += ebook_data[loc2:]
            return (newbk)

    def scan_sections(self):
        """
        Scan book contents, book pages, and section pages.

        This is an informational scan only, data is gathered, but no
        changes are made

        **Keyword arguments:**

        """

        page_words = 0
        book_curpg = 1
        idx = 0
        # scan until we find '<body' and just copy all the header stuff.
        for chapter in self.bkinfo['spine_lst']:
            sct_pgcnt = 0
            efile = Path((f"{self.bkinfo['unzip_path']}/"
                          f"{chapter['disk_file']}"))
            with efile.open('r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
            if self.bkinfo['match']:
                lstr = 'epub:type="pagebreak"'
                ep_typcnt = ebook_data.count(lstr)
                # in case this is an aria file
                lstr = 'role="doc-pagebreak"'
                aria_typcnt = ebook_data.count(lstr)
                if aria_typcnt:
                    # book_curpg += aria_typcnt
                    chapter['sct_pgcnt'] = aria_typcnt
                else:
                    # book_curpg += ep_typcnt
                    chapter['sct_pgcnt'] = ep_typcnt
            # we always do this loop to count words.  But if we are matching
            # pages, do not change chapter nor book_curpg
            body1 = ebook_data.find('<body')
            if body1 == -1:
                self.rdict['errors'].append(f"Fatal error: No <body> found. "
                                            f"File: {chapter['disk_file']}")
                self.rdict['fatal'] = True
                return 0
            else:
                idx = body1
            while idx < len(ebook_data)-1:
                if ebook_data[idx] == '<':
                    # we found an html element, just scan past it and don't
                    # count words
                    idx += 1
                    while ebook_data[idx] != '>':
                        idx += 1
                    idx += 1
                elif ebook_data[idx] == ' ':  # we found a word boundary
                    page_words += 1
                    if self.bkinfo['pgwords'] and not self.bkinfo['match']:
                        if page_words > self.bkinfo['pgwords']:
                            if not self.bkinfo['match']:
                                sct_pgcnt += 1
                                book_curpg += 1
                            page_words = 0
                    while ebook_data[idx] == ' ':  # skip additional whitespace
                        idx += 1
                else:  # just copy non-white space and non-element stuff
                    idx += 1
            if self.DEBUG:
                lstr = f'Section page count is: {sct_pgcnt}'
                self.wrlog(False, lstr)
            # store the section pagecount in the dictionary.
            if not self.bkinfo['match']:
                chapter['sct_pgcnt'] = sct_pgcnt
        if self.bkinfo['pgwords'] and not self.bkinfo['match']:
            self.bkinfo['pages'] = book_curpg
        return

    def scan_file(self, ebook_data, chapter):
        """
        Scan a section file and place page-links, page footers,
        superscripts as appropriate.

        This function is very similar to scan_section, but this one adds
        the pagelinks and page footers.

        If this is a converted ebook, then remove existing pagebreak
        links.

        **Keyword arguments:**

        **_ebook_data_**

        The data read from the section file.

        **_chapter_**

        Dictionary containing the href for use in pagelinks and pages in
        the section.

        """

        idx = 0
        pgbook = ''
        sct_pg = 1
        ft_lst = []
        # scan until we find '<body' and just copy all the header stuff.
        # we only scan for <body since calibre conversion makes the body
        # element '<body class=calibre>
        body1 = ebook_data.find('<body')
        if body1 == -1:
            pgbook += ebook_data
#             print('No <body> element found.')
            estr = f"Fatal error: No <body> found in {chapter['disk_file']}"
            self.rdict['errors'].append(estr)
            self.rdict['fatal'] = True
            return pgbook
        else:
            pgbook += ebook_data[:body1]
            ebook_data = ebook_data[body1:]
        while idx < len(ebook_data)-1:
            # If we find an html element, just copy it and don't count
            # words
            if ebook_data[idx] == '<':
                html_element = ebook_data[idx]
                idx += 1
                # note this doesn't work for comments! We must search
                # for '-->'
                # check for comment (this caused an error in Cordwainer
                # Smith's The Rediscovery of Man.
                if ebook_data[idx]=='!':
                    # self.wrlog(True, f"Found a comment when scanning.")
                    loc = ebook_data.find('-->')
                    if loc == -1:
                        estr = f"Comment end not found."
                        self.wrlog(True, estr)
                        self.rdict['errors'].append(estr)
                    else:
                        end = idx + loc + 3
                        html_element += ebook_data[idx:end]
                        self.wrlog(True, f"html_element: {html_element}")
                        # pgbook += ebook_data[idx:idx + loc]
                        idx += loc + 3
                else:
                    while ebook_data[idx] != '>':
                        html_element += ebook_data[idx]
                        idx += 1
                    html_element += ebook_data[idx]
                    idx += 1
                # if we found </body>, we're done with this file.
                if html_element == '</body>':
                    pgbook += html_element
                    pgbook += ebook_data[idx:]
                    break
                # if span element with pagebreak and a converted book,
                # then don't put in the book, remove it.
                # TODO Fix this to allow keeping these and matching,
                # while creating a page-list in the nav file.
                rm_pbreak = (self.bkinfo['converted'] and
                             html_element.find('span') != -1 and
                             html_element.find('pagebreak') != -1)
                if rm_pbreak:
                    # but we must be sure we remove the closing span.
                    # This is either /> or </span>
                    # a </span>
                    if html_element.find('/>') == -1:
                        # we must look for </span> and extend removal
                        svidx = idx
                        if ebook_data[idx] == '<':
                            html_element = ebook_data[idx]
                            while ebook_data[idx] != '>':
                                idx += 1
                                html_element += ebook_data[idx]
                            idx += 1
                            if html_element.find('</span>') != -1:
                                htstr = (f"file {chapter['disk_file']}: "
                                         f'Removing <span>..</span>')
                                self.wrlog(True, htstr)
                            else:
                                idx = svidx
                    else:
                        htstr = (f"file {chapter['disk_file']}: "
                                 f'Removing html element: {html_element}')
                        self.wrlog(True, htstr)
                        # pgbook += html_element
                else:
                    pgbook += html_element
                # if the element is </div> or </p>, after we scan past
                # it, insert any footers
                if html_element == '</div>' or html_element == '</p>':
                    if self.footer:
                        if ft_lst:
                            for ft in ft_lst:
                                pgbook += ft
                        ft_lst = []
            elif ebook_data[idx] == ' ':  # we found a word boundary
                self.pg_wcnt += 1
                self.tot_wcnt += 1
                if self.pg_wcnt > self.pgwords:
                    # insert the superscripted page number
                    if self.superscript:
                        pgbook += self.new_super(self.curpg,
                                                 sct_pg,
                                                 chapter['sct_pgcnt'])
                    # insert the page-link entry
                    # note that we make a unique (we hope!) id for the
                    # pagelink
                    if self.genplist:
                        pstr = (f'<span epub:type="pagebreak" '
                                f'id="{pglnk}{self.curpg}" '
                                f' role="doc-pagebreak" '
                                f'title="{self.curpg}"/>'
                                )
                        pgbook += pstr
                        self.add_plist_target(
                                self.curpg,
                                chapter['href']
                            )
                    if self.footer:
                        ft_lst.append(self.bld_foot(self.curpg,
                                                    sct_pg,
                                                    chapter['sct_pgcnt']))
                    sct_pg += 1
                    self.curpg += 1
                    self.pg_wcnt = 0
                # skip additional whitespace
                while ebook_data[idx] == ' ':
                    pgbook += ebook_data[idx]
                    idx += 1
            else:  # just copy non-white space and non-element stuff
                pgbook += ebook_data[idx]
                idx += 1
        return (pgbook)  # }}}

    def scan_match_file(self, ebook_data, chapter):
        """
        Called when the ebook already has page links and we are told to
        insert footers/superscripts matching existing paging.

        Scan a section file and place page footers, superscripts based
        on existing pagebreaks.

        **Keyword arguments:**

        **_ebook_data_**

        The data read from the section file.

        **_chapter_**

        Dict with href for pagelinks; section pages.

        """

        idx = 0
        pgbook = ''
        sct_pg = 1
        ft_lst = []
        # just find existing pagebreak entries
        not_done = True
        while not_done:
            plink_loc = ebook_data.find('epub:type="pagebreak"')
            # some aria type files don't have epub:type="pagebreak"
            plink_loc1 = ebook_data.find('role="doc-pagebreak"')
            if plink_loc == -1 and plink_loc1 == -1:
                pgbook += ebook_data
                not_done = False
            else:
                if plink_loc == -1:
                    plink_loc = plink_loc1
                # find the start of the <span because sometimes
                # aria-label is before the epub:type
                spanst = ebook_data[:plink_loc].rfind('<span')
                pgbook += ebook_data[:spanst]
                ebook_data = ebook_data[spanst:]
                # Find the page number. Could be title or aria-label
                loctitle = ebook_data.find('title=')
                loclabel = ebook_data.find('aria-label=')
                locid = ebook_data.find('id=')
                if loctitle == -1 and loclabel == -1 and locid == -1:
                    estr = (f"Error: {chapter['disk_file']}: "
                            f"Did not find title or aria-label or id "
                            f"for pagebreak")
                    self.wrlog(False, estr)
                    self.rdict['errors'].append(estr)
                    self.rdict['error'] = True
                    pgbook += ebook_data
                    not_done = False
                else:
                    if loctitle != -1:
                        loc = loctitle
                        loc += len('title=')
                    elif loclabel != -1:
                        loc = loclabel
                        loc += len('aria-title')
                    elif locid != -1:
                        loc = locid
                        loc += len('id')
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    qlist = ebook_data.split('"')
                    thispage = qlist[1]
                    if locid != -1:
                        newpage = ''
                        for c in thispage:
                            if c.isdigit():
                                newpage += c
                        if newpage:
                            thispage = newpage
                    # now find the end of this element '/'
                    loc = ebook_data.find('/')
                    loc += 1
                    if ebook_data[loc] == '>':
                        # if next char is a >, found it
                        loc += 1
                    else:
                        # otherwise must find 'span>'
                        if ebook_data.find('span>') == -1:
                            estr = (f"Error: {chapter['disk_file']}: "
                                    f"In match mode did not find "
                                    f"closing span for pagebreak")
                            self.wrlog(False, estr)
                            self.rdict['errors'].append(estr)
                            self.rdict['error'] = True
                        else:
                            loc += len('span>')
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    # insert superscript here
                    if self.superscript:
                        sstr = self.new_super(thispage,
                                              sct_pg,
                                              chapter['sct_pgcnt'])
                        pgbook += sstr
                    # scan for next paragraph start or end and insert footer.
                    # Could miss a page if a paragraph contains two page links
                    loc = ebook_data.find('</p>')
                    if loc == -1:
                        self.rdict['warn'] = True
                        lstr = ('Did not find paragraph end to '
                                'insert matched footer.')
                        self.wrlog(True, lstr)
                        lstr = (f'--> thispage: {thispage}; '
                                f'sct_pg: {sct_pg}')
                        self.wrlog(True, lstr)
                    else:
                        loc += 4
                        pgbook += ebook_data[:loc]
                        ebook_data = ebook_data[loc:]
                        if self.footer:
                            pgbook += self.bld_foot(thispage,
                                                    sct_pg,
                                                    chapter['sct_pgcnt'])
                    sct_pg += 1
        return (pgbook)  # }}}

    def run_chk(self, original):
        """
        Run epubcheck on the epub source file. Copy results to log file.
        Save error counts to global rdict.

        **Instance Variables**

        **_original_** -- Original file or paged output file to be
        checked
        """
        t1 = time.perf_counter()
        self.wrlog(True, '---------------------------')
        if original:
            self.wrlog(True, 'Running epubcheck on original epub file:' + CR)
            epubcheck_cmd = [self.epubcheck, '-e', self.epub_file]
        else:
            self.wrlog(True, 'Running epubcheck on paged epub file:' + CR)
            epubcheck_cmd = [self.epubcheck, '-e',
                                (f"{self.outdir}/"
                                f"{self.bkinfo['title']}.epub")]
        result = run(epubcheck_cmd,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True)
        # check and log the errors from epubcheck
        for line in result.stdout.splitlines():
            # Messages: 0 fatals / 0 errors / 0 warnings
            # 0         1 2      3 4
            # with -e ignoring warnings
            # Messages: 0 fatals / 0 errors
            if line.find('Messages:') != -1:
                w = line.split(' ')
                if original:
                    self.rdict['orig_fatal'] = int(w[1])
                    self.rdict['orig_error'] = int(w[4])
                    # self.rdict['orig_warn'] = int(w[7])
                    if self.rdict['orig_fatal']:
                        self.wrlog(True,
                                    (f"--> {self.rdict['orig_fatal']} fatal "
                                    f"errors reported in epubcheck."))
                    if self.rdict['orig_error']:
                        self.wrlog(True,
                                    (f"--> {self.rdict['orig_error']} "
                                    f"errors reported in epubcheck."))
                    if self.rdict['orig_warn']:
                        self.wrlog(True,
                                    (f"--> {self.rdict['orig_warn']} warnings "
                                    f"reported in epubcheck."))
                else:
                    self.rdict['echk_fatal'] = int(w[1])
                    self.rdict['echk_error'] = int(w[4])
                    # self.rdict['echk_warn'] = int(w[7])
                    if self.rdict['echk_fatal']:
                        self.wrlog(True,
                                    (f"--> {self.rdict['echk_fatal']} fatal "
                                    f"errors reported in epubcheck."))
                    if self.rdict['echk_error']:
                        self.wrlog(True,
                                    (f"--> {self.rdict['echk_error']} "
                                    f"errors reported in epubcheck."))
                    # if self.rdict['echk_warn']:
                    #     self.wrlog(True,
                    #                 (f"--> {self.rdict['echk_warn']} warnings "
                    #                 f"reported in epubcheck."))
        if original:
            self.wrlog(True, '-------Epubcheck Original Output------')
        else:
            self.wrlog(True, '-------Epubcheck Paged Output---------')
        self.wrlog(True,'')
        stdout_lines = result.stdout.splitlines()
        self.wrlog(True, result.stdout)
        if len(result.stderr) > 0:
            self.wrlog(False, result.stderr)
        t2 = time.perf_counter()
        self.wrlog(True, f"    epubcheck took {t2-t1:.2f} seconds.")
        self.wrlog(True, '--End Epubcheck Output-----')
        self.wrlog(True, '\n')
        return

# directory structures and names
# self.outdir/
#   book1/: unzipped source epub--modified in place
#   book1.epub: paginated book1
#   book2/: unzipped source epub--modified in place
#   book2.epub: paginated book1

# source_epub: full path to source epub file--the file to paginate. This is
# unzipped to self.outdir/book_name
# book_name: the source_epub with spaces removed from everything, and .epub
# removed.

# Parameters:
# source_epub: full path to source epub file--the file to paginate
    def paginate_epub(self, source_epub):
        """
        **paginate_epub**

        Unzip *source_epub*.

        Verify ePub version, navigation capable, navigation exists.

        Generate list of files to scan and their order.

        Scan each file and add page links and page footers as requested.

        Build a page-list element while scanning.

        Update the navigation file with the page-list element.

        Save the modified files a a paginated ePub.

        **Keyword arguments:**

        **_source_epub_** -- The original ePub file to modify.

        """

        t1 = time.perf_counter()
        # re-initialize on each call
        self.curpg = 1
        self.tot_wcnt = 0
        self.pg_wcnt = 0
        self.plist = ''
        self.bk_flist = []
        self.epub_file = source_epub
        self.rdict["logfile"]: ""
        self.rdict["bk_outfile"] = ""
        self.rdict["logfile"] = ''
        self.rdict["errors"] = []
        self.rdict["fatal"] = False
        self.rdict["error"] = False
        self.rdict["warn"] = False
        self.rdict['orig_fatal'] = 0
        self.rdict['orig_error'] = 0
        self.rdict['orig_warn'] = 0
        self.rdict["echk_fatal"] = 0
        self.rdict["echk_error"] = 0
        self.rdict["echk_warn"] = 0
        self.rdict["messages"] = ""
        self.get_bkinfo()
        if self.rdict['fatal']:
            self.wrlog(True, 'Fatal error.')
            return(self.rdict)
        # run epubcheck on the file to be paged if requested
        if self.chk_orig:
            self.run_chk(True)
        self.ePubUnZip(self.epub_file, self.bkinfo['unzip_path'])
        # figure out where everything is and the order they are in.
        self.scan_spine(self.bkinfo['unzip_path'])
        if self.rdict['fatal']:
            self.wrlog(True, 'Fatal error.')
            return(self.rdict)

        # scan the book to count words, section pages and total pages based on
        # words/page
        self.count_words()
        self.scan_sections()
        for key in self.bkinfo:
            if key != 'spine_lst':
                self.wrlog(True, f"bkinfo[{key}]: {self.bkinfo[key]}")

        # report what we are doing
        if self.bkinfo['has_plist'] and self.bkinfo['match']:
            self.wrlog(True, f'Matching existing pagination.')
            self.wrlog(True, (f"Approximately {self.bkinfo['pgwords']}"
                              f" words per page."))
        elif self.genplist:
            inline = self.footer or self.superscript
            if self.pgwords == 0 and self.pages == 0:
                self.wrlog(True, 'Fatal error:')
                self.wrlog(True, f"match: {self.bkinfo['match']}")
                self.wrlog(True, f"pgwords: {self.pgwords}")
                self.wrlog(True, f"pages: {self.pages}")
                self.wrlog(True, f"cannot determine how to paginate.")
                self.rdict['fatal'] = True
                return(self.rdict)
            elif self.pgwords:
                self.wrlog(True, (f'Generating pagelist with '
                                  f"{self.bkinfo['pgwords']} words per page."))
            else:
                self.pgwords = int(self.bkinfo['words'] / self.pages)
                self.wrlog(True, (f'Generating pagelist with calculated'
                                  f" {bkinfo['pgwords']} words per page."))
        else:
            if self.footer:
                self.wrlog(True, (f'Generating page footer with '
                                  f"{self.bkinfo['pgwords']} words per page."))
            if self.superscript:
                self.wrlog(True, (f'Generating page superscripts with '
                                  f"{self.bkinfo['pgwords']} words per page."))
        # this is the working loop. Scan each file, locate pages and insert
        # page-links and/or footers or superscripts
        self.curpg = 1
        for chapter in self.bkinfo['spine_lst']:
            if self.DEBUG:
                lstr = (f"file: {self.bkinfo['unzip_path']}/"
                        f"{chapter['disk_file']}")
                self.wrlog(False, lstr)
            erfile = Path((f"{self.bkinfo['unzip_path']}/"
                           f"{chapter['disk_file']}"))
            with erfile.open('r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
            ewfile = Path((f"{self.bkinfo['unzip_path']}/"
                           f"{chapter['disk_file']}"))
            with ewfile.open('w') as ebook_wfile:
                start_total = self.tot_wcnt
                lstr = (f"Scanning {chapter['disk_file']}; "
                        f"start_total: {start_total} "
                        f"self.tot_wcnt: "
                        f"{self.tot_wcnt}")
                self.wrlog(True, lstr)
                if self.bkinfo['match']:
                    if self.DEBUG:
                        lstr = (f"file: "
                                f"{self.bkinfo['unzip_path']}/"
                                f"{chapter['disk_file']}")
                        self.wrlog(False, lstr)
                    new_ebook = self.scan_match_file(ebook_data, chapter)
                else:
                    new_ebook = self.scan_file(ebook_data, chapter)
                xebook_data = self.chk_xmlns(new_ebook)
                ebook_wfile.write(xebook_data)
        if self.bkinfo['match']:
            w_per_page = self.bkinfo['words']/self.bkinfo['pages']
            lstr = (f"    {self.bkinfo['words']:,} words; "
                    f"    {self.bkinfo['pages']:,} pages; "
                    f"    {int(w_per_page)} words per page")
            self.wrlog(True, lstr)
        else:
            self.wrlog(True,
                       (f"    {self.bkinfo['words']:,} words;"
                        f"    {self.bkinfo['pages']:,} pages"))
        # modify the nav_file to add the pagelist
        if self.genplist:
            self.plist += '  </ol></nav>' + CR
            self.update_navfile()
        # build the epub file
        self.ePubZip((f"{self.outdir}/"
                      f"{self.bkinfo['title']}.epub"),
                     (f"{self.outdir}/"
                      f"{self.bkinfo['title']}"),
                     self.bk_flist)
        # and if DEBUG is not set, we remove the unzipped epub directory
        if not self.DEBUG:
            rm_cmd = ['rm',
                      '-rf',
                      (f"{self.outdir}/"
                       f"{self.bkinfo['title']}")]
            result = run(rm_cmd,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
        t2 = time.perf_counter()
        self.wrlog(True, f"{self.bkinfo['title']}.epub")
        self.wrlog(True, f"    Paginated in {t2-t1:.2f} seconds.")
        if self.epubcheck != None:
            self.run_chk(False)
        return(self.rdict)
