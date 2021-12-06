import os
import sys
from subprocess import PIPE, run
import time

import xmltodict
import json
import zipfile

CR = '\n'
opf_dictkey = 'package'


class epub_paginator:
    """
    Paginate an ePub3 using page-list navigation and/or inserting page
    information footers and/or superscripts into the text.

    **Release Notes**

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
    1. Doesn't generated page-list if it already exists.
    1. Adds chapter page numbering.
    """

    version = '2.94'
    bkinfo = {
        "version": "",
        "converted": False,
        "title": "",
        "unzip_path": "",
        "has_plist": False,
        "match": False,
        "has_pbreaks": False,
        "nav_file": "None",
        "spine_lst": [],
        "words": 0,
        "pages": 0
    }
    curpg = 1        # current page number
    tot_wcnt = 0     # count of total words in the book
    pg_wcnt = 0      # word count per page
    plist = ''       # the page-list element for the nav file
    bk_flist = []    # list of all files in the epub
    logpath = ''     # path for the logfile

    rdict = {              # data to return to calling program
        "logfile": "",     # logfile location and name
        "bk_outfile": "",  # modified epub file name and location
        "errors": [],      # list of errors that occurred
        "fatal": False,    # Was there a fatal error?
        "messages": ""     # list of messages generated.
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
        self.ebookconvert = 'none'
        self.epubcheck = 'none'
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
                sys.exit()
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

    def get_bkinfo(self, epub_file):
        """
        Gather useful information about the ebub file and put it in the
        bkinfo dictionary.

        **Instance Variables**

        **_epub_file_**  -- ePub file to return version of

        """

        # The epub name is the book file name with spaces removed and '.epub'
        # removed.
        dirsplit = epub_file.split('/')
        stem_name = dirsplit[len(dirsplit)-1].replace(' ', '')
        self.bkinfo['title'] = stem_name.replace('.epub', '')
        self.logpath = (f"{self.outdir}/"
                        f"{self.bkinfo['title']}")
        self.rdict['logfile'] = f'{self.logpath}.log'
        self.rdict['bk_outfile'] = f'{self.logpath}.epub'
        with open(self.logpath+'.log', 'w') as logfile:
            logfile.write(''+'\n')
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
        self.bkinfo['version'] = self.get_epub_version(epub_file)
        if self.bkinfo['version'] == 'no_version':
            estr = 'Version was not found in the ePub file.'
            self.rdict['errors'].append(estr)
            self.rdict['fatal'] = True
            return
        vnum = float(self.bkinfo['version'])
        if vnum < 3.0:
            if self.DEBUG:
                self.wrlog(True, 'Handling epub 2')
            # if convert is set, then convert to epub3 first
            if self.ebookconvert != 'none':
                self.wrlog(True,
                           (f'    Converting to epub3 using '
                            f'{self.ebookconvert}'))
                epub3_file = epub_file.replace('.epub', '_epub3.epub')
                ebkcvrt_cmd = [self.ebookconvert,
                               epub_file,
                               epub3_file,
                               '--epub-version',
                               '3']
                result = run(ebkcnvrt_cmd,
                             stdout=PIPE,
                             stderr=PIPE,
                             universal_newlines=True)
                if result.returncode == 0:
                    self.wrlog(False, 'Conversion log:')
                    self.wrlog(False, result.stdout)
                    epub_file = epub3_file
                    lstr = f'Paginating epub3 file: {epub_file}'
                    self.wrlog(True, lstr)
                    plstr = ('<nav epub:type="page-list" id="page-list" '
                             'hidden="hidden"><ol>') + CR
                    self.plist = plstr
                    self.bkinfo['converted'] = True
                    self.bkinfo['version'] = '3.0'
                else:
                    lstr = 'Conversion to epub3 failed. Conversion reported:'
                    self.wrlog(True, lstr)
                    self.wrlog(True, result.stderr)
                    astr = 'Conversion to epub3 failed.'
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
            self.plist = ('<nav epub:type="page-list" '
                          'id="page-list" hidden="hidden"><ol>' + CR)
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

        with open(self.bkinfo['nav_file'], 'r') as nav_r:
            nav_data = nav_r.read()
        loc = nav_data.find('<nav epub:type="page-list"')
        if loc == -1:
            # this should never happen since we get here only after the entry
            # was found
            print('Error! oops, the page-list entry was not found!')
            sys.exit(0)
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
        if (stdout):
            print(message)
            self.rdict['messages'] += '\n' + message
        with open(self.logpath+'.log', 'a') as logfile:
            logfile.write(message + '\n')

    def update_navfile(self):
        """
        Add generated page-list element to the ePub navigation file
        """

        with open(self.bkinfo['nav_file'], 'r') as nav_file_read:
            nav_data = nav_file_read.read()
        pagelist_loc = nav_data.find('</body>')
        new_nav_data = nav_data[:pagelist_loc]
        new_nav_data += self.plist
        with open(self.bkinfo['nav_file'], 'w') as nav_file_write:
            nav_file_write.write(new_nav_data)
            nav_file_write.write(nav_data[pagelist_loc:])

    def add_genplist_target(self, curpg, href):
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

        self.plist += f'  <li><a href="{href}#page{curpg}">{curpg}</a></li>'
        self.plist += CR
        return

    def bld_foot(self, curpg, sct_pg, sct_pgcnt, href):
        """
        Format and return page footer.

        **Keyword arguments:**
        **_curpg_**

        The current page number of the book.

        **_sct_pg_**

        The current section page number.

        **_sct_pgcnt_**

        The pagecount of the section.

        **_href_**

        The relative path and filename for the pagelink.

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
        with open(f"{path}/META-INF/container.xml", 'r') as container_file:
            xd = xmltodict.parse(container_file.read())
            opf_file = xd['container']['rootfiles']['rootfile']['@full-path']
            opf_path = opf_file.split('/')
            disk_path = ''
            if len(opf_path) > 1:
                for index in range(0, len(opf_path)-1):
                    disk_path += f"{opf_path[index]}/"
            opf_filename = f"{path}/{opf_file}"

        # read the opf file and find nav file
        with open(opf_filename, 'r') as opf_file:
            opf_dict = xmltodict.parse(opf_file.read())
        # be sure we find a nav file
            if self.genplist:
                for item in opf_dict[opf_dictkey]['manifest']['item']:
                        if item.get('@properties') == 'nav':
                            lstr = f"{path}/{disk_path}{item['@href']}"
                            self.bkinfo['nav_file'] = lstr
                if self.bkinfo['nav_file'] == 'None':
                    self.wrlog(True,
                               ('Fatal error - did not find navigation file'))
                    self.rdict['fatal'] = True
                    return
                else:
                    if self.DEBUG:
                        lstr = f"nav_file found: {self.bkinfo['nav_file']}"
                        self.wrlog(False, lstr)
                # we have a nav file, verify there is no existing page_list
                # element
                    if self.genplist:
                        with open(self.bkinfo['nav_file'], 'r') as nav_r:
                            nav_data = nav_r.read()
                            lstr = '<nav epub:type="page-list"'
                            if nav_data.find(lstr) != -1:
                                self.wrlog(True,
                                           ('    ->INFO<- This epub file '
                                            'already has a page-list '
                                            'navigation element.'))
                                self.wrlog(True,
                                           ('   ->INFO<- page-list navigation '
                                            'was selected but will not '
                                            'be created.'))
                                self.genplist = False
                                if self.match:
                                    self.bkinfo['match'] = True
                                    # count the total number of pages in the
                                    # nav pagelist
                                    pgs = self.get_nav_pagecount()
                                    self.bkinfo['pages'] = pgs
                                    if self.rdict['fatal']:
                                        self.wrlog(True, 'Fatal error.')
                                        return(self.rdict)
                                else:
                                    self.bkinfo['match'] = False
                            else:
                                # there is no pagelist, unset match
                                self.match = False
                                self.bkinfo['match'] = False

        # we're good to go
        spine_lst = []
        for spine_item in opf_dict[opf_dictkey]['spine']['itemref']:
            if self.DEBUG:
                lstr = f"spine_item idref: {spine_item['@idref']}"
                self.wrlog(False, lstr)
            for manifest_item in opf_dict[opf_dictkey]['manifest']['item']:
                if spine_item['@idref'] == manifest_item['@id']:
                    fdict = {}
                    fdict['disk_file'] = f"{disk_path}{manifest_item['@href']}"
                    fdict['href'] = manifest_item['@href']
                    spine_lst.append(fdict)
        self.bkinfo['spine_lst'] = spine_lst
        return()

    def scan_sections(self):
        """
        Scan book contents, count words, pages, and section pages.

        This is an informational scan only, data is gathered, but no
        changes are made

        **Keyword arguments:**

        """

        book_wordcount = 0
        page_words = 0
        book_curpg = 1
        idx = 0
        # scan until we find '<body' and just copy all the header stuff.
        for chapter in self.bkinfo['spine_lst']:
            sct_pgcnt = 0
            with open(f"{self.bkinfo['unzip_path']}/"
                      f"{chapter['disk_file']}", 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
                if self.DEBUG:
                    self.wrlog(False,
                               f'The word count is {book_wordcount:,} .')
                    self.wrlog(False, f'The page count is {book_curpg:,}')
            if self.bkinfo['match']:
                lstr = 'epub:type="pagebreak"'
                chapter['sct_pgcnt'] = ebook_data.count(lstr)
                book_curpg += chapter['sct_pgcnt']
            # we always do this loop to count words.  But if we are matching
            # pages, do not change chapter nor book_curpg
            body1 = ebook_data.find('<body')
            if body1 == -1:
                self.rdict['errors'].append(f"No <body> element found. "
                                            f"File: {chapter['disk_file']}")
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
                    book_wordcount += 1
                    if page_words > self.pgwords:
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
        self.bkinfo['words'] = book_wordcount
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
        body1 = ebook_data.find('<body')
        if body1 == -1:
            pgbook += ebook_data
#             print('No <body> element found.')
            estr = f"No <body> element found. File: {chapter['disk_file']}"
            self.rdict['errors'].append(estr)
            return pgbook
        else:
            pgbook += ebook_data[:body1]
            idx = body1
        while idx < len(ebook_data)-1:
            # we found an html element, just copy it and don't count words
            if ebook_data[idx] == '<':
                # if the element is </div> or </p>, after we scan past it,
                # insert any footers
                html_element = ebook_data[idx]
                idx += 1
                while ebook_data[idx] != '>':
                    html_element += ebook_data[idx]
                    idx += 1
                html_element += ebook_data[idx]
                idx += 1
                # if span element with pagebreak and a converted book, then
                # don't put in the book, remove it.
                # TODO
                # Fix to allow keeping these and matching, while creating a
                # page-list in the nav file.
                rm_pbreak = (self.bkinfo['converted'] and
                             html_element.find('span') != -1 and
                             html_element.find('pagebreak') != -1)
                if rm_pbreak:
                    self.wrlog(True, f'Removing html element: {html_element}')
                    # but we must also remove the </span>
                    if ebook_data[idx] == '<':
                        html_element = ebook_data[idx]
                        while ebook_data[idx] != '>':
                            idx += 1
                            html_element += ebook_data[idx]
                        self.wrlog(True,
                                   f'Removing html element: {html_element}')
                        idx += 1
                pgbook += html_element
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
                    if self.genplist:
                        pstr = (f'<span epub:type="pagebreak" '
                                f'id="page{self.curpg}" '
                                f' role="doc-pagebreak" '
                                f'title="{self.curpg}"/>'
                                )
                        pgbook += pstr
                        self.add_genplist_target(
                                self.curpg,
                                chapter['href']
                            )
                    if self.footer:
                        ft_lst.append(self.bld_foot(self.curpg,
                                                    sct_pg,
                                                    chapter['sct_pgcnt'],
                                                    chapter['href']))
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
            if plink_loc == -1:
                pgbook += ebook_data
                not_done = False
            else:
                pgbook += ebook_data[:plink_loc]
                # update the string
                ebook_data = ebook_data[plink_loc:]
                # find the curpgber
                loc = ebook_data.find('title=')
                if loc == -1:
                    self.wrlog(True, 'Did not find title for page link')
                else:
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    qlist = ebook_data.split('"')
                    thispage = qlist[1]
                    # now find the end of this element </span>
                    loc = ebook_data.find('</span>')
                    loc += 7
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
                                                    chapter['sct_pgcnt'],
                                                    chapter['href'])
                    sct_pg += 1
        return (pgbook)  # }}}

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
        self.get_bkinfo(source_epub)
        if self.rdict['fatal']:
            self.wrlog(True, 'Fatal error.')
            return(self.rdict)
        self.ePubUnZip(source_epub, self.bkinfo['unzip_path'])
        # figure out where everything is and the order they are in.
        self.scan_spine(self.bkinfo['unzip_path'])
        if self.rdict['fatal']:
            self.wrlog(True, 'Fatal error.')
            return(self.rdict)
        # now check we have what we need for paging
        if not self.bkinfo['match']:
            if self.pgwords == 0 and self.pages == 0:
                self.wrlog(True, 'Fatal error:')
                self.wrlog(True, f"match: {self.bkinfo['match']}")
                self.wrlog(True, f"pgwords: {self.pgwords}")
                self.wrlog(True, f"pages: {self.pages}")
                self.wrlog(True, f"cannot determine how to paginate.")
                rdict['fatal'] = True
                return(self.rdict)
        # scan the book to count words, section pages and total pages based on
        # words/page
        self.scan_sections()
        # this is the working loop. Scan each file, locate pages and insert
        # page-links and/or footers or superscripts
        self.curpg = 1
        for chapter in self.bkinfo['spine_lst']:
            # must reset things from the previous scan
            total_word_count = 0
            if self.DEBUG:
                lstr = (f"file: {self.bkinfo['unzip_path']}/"
                        f"{chapter['disk_file']}")
                self.wrlog(False, lstr)
            erfile = (f"{self.bkinfo['unzip_path']}/"
                      f"{chapter['disk_file']}")
            with open(erfile, 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
            ewfile = (f"{self.bkinfo['unzip_path']}/"
                      f"{chapter['disk_file']}")
            with open(ewfile, 'w') as ebook_wfile:
                start_total = self.tot_wcnt
                if self.DEBUG:
                    lstr = (f"Scanning {chapter['disk_file']}; "
                            f"start_total: {start_total} "
                            f"self.tot_wcnt: "
                            f"{self.tot_wcnt}")
                    self.wrlog(False, lstr)
                if self.bkinfo['match']:
                    if self.DEBUG:
                        lstr = (f"file: "
                                f"{self.bkinfo['unzip_path']}/"
                                f"{chapter['disk_file']}")
                        self.wrlog(False, lstr)
                    new_ebook = self.scan_match_file(ebook_data, chapter)
                else:
                    new_ebook = self.scan_file(ebook_data, chapter)
                if self.DEBUG:
                    lstr = (f"chapter has "
                            f"{self.tot_wcnt-start_total:,} "
                            f"words")
                    self.wrlog(False, lstr)
                ebook_wfile.write(new_ebook)
        if self.bkinfo['match']:
            w_per_page = self.bkinfo['words']/self.bkinfo['pages']
            lstr = (f"    {self.bkinfo['words']:,} words; "
                    f"{self.bkinfo['pages']:,} pages; "
                    f"{int(w_per_page)} words per page")
            self.wrlog(True, lstr)
        else:
            self.wrlog(True,
                       (f"    {self.tot_wcnt:,} words;"
                        f"{self.curpg:,} pages"))
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
        self.wrlog(True, f"    Paginated in {t2-t1:.2f} seconds.")
        t1 = time.perf_counter()
        if self.epubcheck != 'none':
            self.wrlog(True, '---------------------------')
            self.wrlog(True, 'Running epubcheck:' + CR)
            epubcheck_cmd = [self.epubcheck,
                             (f"{self.outdir}/"
                              f"{self.bkinfo['title']}.epub")]
            result = run(epubcheck_cmd,
                         stdout=PIPE,
                         stderr=PIPE,
                         universal_newlines=True)
            # check and log the errors from epubcheck
            stdout_lines = result.stdout.splitlines()
            self.wrlog(True, result.stdout)
            if len(result.stderr) > 0:
                self.wrlog(False, result.stderr)
            self.wrlog(True, '---------------------------')
            self.wrlog(True, '\n')
        t2 = time.perf_counter()
        self.wrlog(True, f"    epubcheck took {t2-t1:.2f} seconds.")
        return(self.rdict)
