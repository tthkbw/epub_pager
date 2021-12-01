import os
import sys
from subprocess import PIPE, run
import time

import xmltodict
import json
import zipfile
import re

version = '2.92'
CR = '\n'
pagenum = 1
total_wordcount = 0
page_wordcount = 0
pagelist_element = ''
epub_filelist = []
# the dictionary key in the opf file. Usually it is 'package', but some old files use 'opf:package'
opf_dictkey = 'package'
logfile_path = ''

epub_info = {
    "epub_version_orig": "",
    "epub_version_conv": "",
    "converted": False,
    "book_name": "",
    "unzipped_epub_path": "",
    "has_pagelist": False,
    "match_pages": False,
    "has_pagebreaks": False,
    "nav_file": "None",
    "spine_filelist": [],
    "words": 0,
    "pages": 0,
    "spine": []
}

return_dict = {
    "logfile": "",
    "paged_epub_file": "",
    "errors": [],
    "fatal": False,
    "messages": "",
}

# the following two routines are modified from those on GitHub:
# https://github.com/MJAnand/epub/commit/8980928a74d2f761b2abdb8ef82a951be11b26d5

def ePubZip(epub_path,srcfiles_path,epub_filelist):
    """
    Zip files from a directory into an epub file

    **Keyword arguments:**

    epub_path -- os path for saving creating epub file

    srcfiles_path -- os path of the directory containing files for the epub

    epub_filelist -- the list of files to zip into the epub file

    """
    with zipfile.ZipFile(epub_path,'w') as myzip:
        if 'mimetype' in epub_filelist:
            myzip.write(srcfiles_path + '/' + 'mimetype', 'mimetype')
            epub_filelist.remove('mimetype')
        else:
            self.write_log(True,'Fatal error, no mimetype file was found.')
            if self.DEBUG:
                self.write_log(False, 'epub_filelist: ')
                self.write_log(False, epub_filelist)
            sys.exit()
    with zipfile.ZipFile(epub_path, 'a', zipfile.ZIP_DEFLATED) as myzip:
        for ifile in epub_filelist:
            myzip.write(srcfiles_path + '/' + ifile, ifile, zipfile.ZIP_DEFLATED)

def ePubUnZip(fileName, unzip_path):
    """
    Unzip ePub file into a directory

    **Keyword arguments:**

    fileName -- the ePub file name

    path     -- path for the unzipped files.

    """
    global epub_filelist

    z = zipfile.ZipFile(fileName)
    epub_filelist = z.namelist()
    z.extractall(unzip_path)
    z.close()

class epub_paginator:
    """
    Paginate an ePub3 using page-list navigation and/or inserting page information footers into the text.

    **Release Notes**

    Version 2.92
    Can now match the superscript and footer insertions to existing page
    numbering. This is automatically done if a page-list exists in the nav
    file.

    Version 2.91
    Lots of refactoring of code.
    Added ebpub_info dictionary to consolidate data about the epub file
    Added get_nav_pagecount() which determines the maximum page number in an already paginated file.

    Version 2.9
    Add the role="doc-pagebreak" to the page links. This appears to fix the bug
    that resulted in iBooks not showing all the page numbers in the margin.

    Version 2.8
    Fixed a bug where the </span> was not removed when removing existingn page links from a converted epub.

    Version 2.7
    Added return_dict to return a set of data to the calling program, including what used to go to stdout

    Version 2.6
    Fixed a bug in logic that removes pagebreak elements from converted epub2 books.

    Version 2.5
    Implemented conversion of epub2 to epub3 using calibre ebook-converter.
    epub_paginator contains command line switches for all options to epub_pager.

    Version 2.4
    Implement configuration file.

    Version 2.3
    Add log file. Program produces minimal output, but puts data in log file.
    If running epubcheck, echo stdout to stdout, but echo stderr only to the log file.
    If DEBUG is False, remove the unzipped epub directory when done.

    Version 2.2

    Add epub_version exposed command to the class.

    Fixed bug that mispositioned the page_footer inside italic or other textual
    html elements and caused epubcheck errors. Page_footers are now properly
    positioned after the <div> or <p> active element when the page limit is
    reached.

    Refactored some of the code. Uses f strings for formatting; cleaned up printing.

    Version 2.1

    1. Now set up as a Github repository with a local copy.
    2. Rewrote the scanning algorithm. Scans character by character after
    <body> element in spine files. Doesn't care about <p> elements or anything
    else. Still places footer before paragraph where the page ends. Other page
    numbering is at precise word location. 
    3. Note that nested <div> elements are created by the placement of footers
    and this creates errors in epubcheck. However, these errors do not affect
    Calibre book reader, nor Apple Books.

    Version 2.0

    1. Includes Docstrings that are compatible with creating documentation using pdoc.
    2. Lot's of refactoring has been done.
    3. Verifies epub3 version.
    3. Verifies nav file exists.
    4. Doesn't generated page-list if it already exists.
    5. Adds chapter page numbering.
    """
    def __init__(self):
        """
        **Instance Variables**

        **_paged_epub_library_**  -- full os path for placement of the paginated ePub file.

        **_words_per_page_**      -- Number of words per page.

        **_total_pages_**         -- Number of pages in the book.

        **_page_footer_**         -- Boolean, if True, insert the page footers, otherwise do not.

        **_page_number_align_**   -- left, right, or center, alignment of the page numbers in the footer.

        **_page_number_color_**   -- Optional color for the footer--if not set, then no color is used.

        **_footer_bracket_** -- Character (e.g. '<' or '(' ) used to bracket page numbers in page footer. 

        **_page_number_total_**   -- Present the book page number with a total (34/190) in the footer.

        **_chapter_pages_**       -- Present the chapter page number and chapter page number total in the footer.

        **_chapter_fontsize_**    -- A percentage value for the relative font size used for the footer.

        **_nav_pagelist_**        -- Create the page_list element in the navigation file.

        **_superscript_**         -- Insert a superscripted page entry

        **_ebookconvert_**        -- The OS path of the ebook conversion program. If present, epub2 books are converted to epub3 before pagination.

        **_epubcheck_**           -- The OS path of epubcheck. If present, epubcheck is run on the created file.

        **_DEBUG_**               -- Boolean. If True, print status and debug information while running.

        """
        self.paged_epub_library = "/Users/tbrown/Documents/projects/BookTally/paged_epubs"
        self.words_per_page = 300
        self.total_pages = 0
        self.page_footer = False
        self.footer_align = 'right'
        self.footer_color = 'red'
        self.footer_bracket = '<'
        self.footer_fontsize = '75%'
        self.footer_total = True
        self.superscript = False
        self.super_color = 'red'
        self.super_fontsize = '60%'
        self.super_total = True
        self.chapter_pages = True
        self.chapter_bracket = '<'
        self.nav_pagelist = True
        self.ebookconvert = 'none'
        self.epubcheck = 'none'
        self.DEBUG = False

    def get_version(self):
        """
        Return version of epub_pager.
        """

        return(version)

    def get_epub_info(self, epub_file):
        """
        gather useful information about the ebub file and put it in the epub_info dictionary.

        **Instance Variables**

        **_epub_file_**  -- ePub file to return version of

        """
        global epub_info
        global return_dict
        global pagelist_element
        global logfile_path

        # the epub name is the book file name with spaces removed and '.epub' removed
        dirsplit = epub_file.split('/')
        stem_name = dirsplit[len(dirsplit)-1].replace(' ','')
        epub_info['book_name'] = stem_name.replace('.epub','')
        logfile_path = f"{self.paged_epub_library}/{epub_info['book_name']}"
        return_dict['logfile'] = f'{logfile_path}.log'
        return_dict['paged_epub_file'] = f'{logfile_path}.epub'
        with open(logfile_path+'.log','w') as logfile:
            logfile.write(''+'\n')
        self.write_log(True,'---------------------------')
        self.write_log(True,f"epub_paginator version {self.get_version()}")
        self.write_log(True,dirsplit[len(dirsplit)-1])
        # first get the epub_version
        epub_info['epub_version_orig'] = self.get_epub_version(epub_file)
        if epub_info['epub_version_orig']=='no_version':
            return_dict['errors'].append('Version was not found in the ePub file.')
            return_dict['fatal'] = True
            return 
        vnum = float(epub_info['epub_version_orig'])
        if vnum < 3.0:
            if self.DEBUG:
                self.write_log(True,'Handling epub 2')
            # if convert is set, then convert to epub3 first
            if self.ebookconvert!='none':
                self.write_log(True,'    Converting to epub3 using {self.ebookconvert}')
                epub3_file = epub_file.replace('.epub','_epub3.epub')
                ebookconvert_cmd = [self.ebookconvert,epub_file,epub3_file, '--epub-version', '3']
                result = run(ebookconvert_cmd, stdout=PIPE, stderr=PIPE,universal_newlines=True)
                if result.returncode==0:
                    self.write_log(False, 'Conversion log:')
                    self.write_log(False, result.stdout)
                    epub_file = epub3_file
                    self.write_log(True, f'Paginating epub3 file: {epub_file}')
                    pagelist_element = '<nav epub:type="page-list" id="page-list" hidden="hidden"><ol>' + CR
                    epub_info['converted'] = True
                    epub_info['epub_version_conv'] = '3.0'
                else:
                    self.write_log(True, 'Conversion to epub3 failed. Conversion reported:')
                    self.write_log(True, result.stderr)
                    return_dict['errors'].append('Conversion to epub3 failed.')
                    return_dict['fatal'] = True
                    return
            else:
                self.write_log(False, "    --> WARNING <-- Epub version is not 3 or newer, page-link navigation disabled.")
                self.write_log(False, "    --> WARNING <-- To enable page-link navigation, convert to Epub3 and try again.")
                self.nav_pagelist = False
        else:
            pagelist_element = '<nav epub:type="page-list" id="page-list" hidden="hidden"><ol>' + CR
        epub_info['unzipped_epub_path'] = f"{self.paged_epub_library}/{epub_info['book_name']}"

    def get_epub_version(self, epub_file):
        """
        Return ePub version of ePub file
        If ePub does not store the version information in the standard location, return 'no version'

        **Instance Variables**

        **_epub_file_**  -- ePub file to return version of

        """

        zfile = zipfile.ZipFile(epub_file)
        # find the opf file, which contains the version information
        container_dict = xmltodict.parse(zfile.read('META-INF/container.xml'))
        opf_file = container_dict['container']['rootfiles']['rootfile']['@full-path']
        opf_dict = xmltodict.parse(zfile.read(opf_file))
        if opf_dict.get('package','badkey') == 'badkey':
            self.write_log(True,'ABORTING: Error parsing opf file, this is probably an ePub2 file.')
            self.write_log(True,'Convert to ePub3 and try again.')
            return('no_version')
        else:
            version = opf_dict['package']['@version']
        return (version)

    def get_nav_pagecount(self):
        """
        Read the nav file and parse the page-list entries to find the total pages in the book

        **Instance Variables**

        **_navfile_**  -- ePub navigation file

        """

        with open(epub_info['nav_file'],'r') as nav_r:
            nav_data = nav_r.read()
        loc = nav_data.find('<nav epub:type="page-list"')
        if loc==-1:
            #this should never happen since we get here only after the entry was found
            print('Error! oops, this time the page-list entry was not found!')
            sys.exit(0)
        nav_data = nav_data[loc:]
        not_done = True
        max_page = 0
        while not_done:
            loc = nav_data.find('<a href')
            if loc==-1:
                not_done = False
                continue
            nav_data = nav_data[loc:]
            loc = nav_data.find('">')
            if loc==-1:
                self.write_log(True,"Unclosed '<a href' element in nav file.")
                self.write_log(True,'Does this file pass epubcheck?')
                return_dict['fatal'] = True
                return (0)
            loc += 2
            nav_data = nav_data[loc:]
            loc2 = nav_data.find('</a>')
            if loc2==-1:
                self.write_log(True,"'</a>' element not found in nav file.")
                self.write_log(True,'Does this file pass epubcheck?')
                return_dict['fatal'] = True
                return (0)
            if nav_data[:loc2].isdigit():
                if int(nav_data[:loc2])>max_page:
                    max_page = int(nav_data[:loc2])
        self.write_log(True,f'The page count from nav pagelist is: {max_page}')
        return(max_page)

    def write_log(self,stdout,message):
        """
        Write a message to the log file.

        **Instance Variables**

        **_stdout_file_**  -- if True, then echo the message to stdout
        **_message_**      -- the message to print

        """
        global logfile_path
        global return_dict
        if (stdout):
#             print(message)
            return_dict['messages'] += '\n' + message
        with open(logfile_path+'.log','a') as logfile:
            logfile.write(message + '\n')

    def update_navfile(self):
        """
        Add generated page-list element to the ePub navigation file
        """
        global epub_info
        global pagelist_element

        with open(epub_info['nav_file'],'r') as nav_file_read:
            nav_data = nav_file_read.read()
        pagelist_loc = nav_data.find('</body>')
        new_nav_data = nav_data[:pagelist_loc]
        new_nav_data += pagelist_element
        with open(epub_info['nav_file'],'w') as nav_file_write:
            nav_file_write.write(new_nav_data)
            nav_file_write.write(nav_data[pagelist_loc:])

    def add_nav_pagelist_target(self, pagenum, href):
        """
        Generate page-list entry and page footer and add them to a string that
        accumulates them for placement in the navigation file.

        **Keyword arguments:**

        **_pagenum_** -- the page number in the book

        **_href_**    -- the filename and path for the internal page link in the book

        """
        global pagelist_element

        pagelist_element += '  <li><a href="' + href + '#page' + str(pagenum) + '">' + str(pagenum) + '</a></li>' + CR
        return 

    def create_pagefooter(self, pagenum,section_pagenum, section_pagecount, href):
        """# {{{
        Create pagelinks for navigation and add to page-list element. 
        Format and return page footer.

        **Keyword arguments:**
        **_pagenum_**           -- the current page number of the book

        **_section_pagenum_**   -- the current section page number

        **_section_pagecount_** -- the pagecount of the section

        **_href_**              -- the relative path and filename for the pagelink

        """# }}}

        # construct the page footer based on formatting selections
        # brackets
        if self.footer_bracket=='<':
            flb = '&lt;'
            frb = '&gt;'
        elif self.footer_bracket=='-':
            flb = '-'
            frb = '-'
        else:
            flb = ''
            frb = ''
        if self.chapter_bracket=='<':
            clb = '&lt;'
            crb = '&gt;'
        elif self.chapter_bracket=='-':
            clb = '-'
            crb = '-'
        else:
            clb = ''
            crb = ''
        #book pages format
        if self.footer_total==True:
            pagestr_bookpages = f"{flb}{pagenum}/{self.total_pages}{frb}"
        else:
            pagestr_bookpages = f"{flb}{pagenum}{frb}"
        #chapter pages format
        if self.chapter_pages==True:
#             pagestr_chapterpages = ' ' + clb + str(section_pagenum) + '/' + str(section_pagecount) + ' in chapter' + crb
            pagestr_chapterpages = f" {clb}{section_pagenum}/{section_pagecount}{crb}"
        else:
            pagestr_chapterpages = ''
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.footer_color=='none':
            if self.footer_align=='float':
                # the following creates center justified bookpages and right justified chapter pages.
                page_footer = f'<div> <p style="font-size:75%; float: left;margin: 0 0 0 0">{pagestr_bookpages}</p><p style="font-size:75%; float: right;margin: 0 0 0 0">{pagestr_chapterpages}</p></div><div style="clear: both;"></div>'
            else:
                page_footer = f'<div style="font-size:{self.footer_fontsize}; text-align: self.footer_align;margin: 0 0 0 0">{pagestr}</div>'

        else:
            if self.footer_align=='float':
                # the following creates center justified bookpages and right justified chapter pages.
                page_footer = f'<div> <p style="font-size:75%; float: left; color: {self.footer_color};margin: 0 0 0 0">{pagestr_bookpages}</p><p style="font-size:75%; float: right; color: {self.footer_color};margin: 0 0 0 0">{pagestr_chapterpages}</p></div><div style="clear: both;"></div>'
            else:
                page_footer = f'<div style="font-size:{self.footer_fontsize}; text-align:{self.footer_align}; color: {self.footer_color};margin: 0 0 0 0">{pagestr}</div>'
#         if self.nav_pagelist:
#             self.add_nav_pagelist_target(pagenum, href)
        return (page_footer)

    def create_superscript(pagenum,section_pagenum, section_pagecount):
        """# {{{
        Format and return a <span> element for superscripted page numbering

        **Keyword arguments:**
        **_pagenum_**           -- the current page number of the book

        **_section_pagenum_**   -- the current section page number

        **_section_pagecount_** -- the pagecount of the section

        """# }}}

        # construct the page footer based on formatting selections
        # brackets
        if self.footer_bracket=='<':
            flb = '&lt;'
            frb = '&gt;'
        elif self.footer_bracket=='-':
            flb = '-'
            frb = '-'
        else:
            flb = ''
            frb = ''
        if self.chapter_bracket=='<':
            clb = '&lt;'
            crb = '&gt;'
        elif self.chapter_bracket=='-':
            clb = '-'
            crb = '-'
        else:
            clb = ''
            crb = ''
        #book pages format
        if self.super_total==True:
            pagestr_bookpages = f"{flb}{pagenum}/{self.total_pages}{frb}"
        else:
            pagestr_bookpages = f"{flb}{pagenum}{frb}"
        #chapter pages format
        if self.chapter_pages==True:
            pagestr_chapterpages = f" {clb}{section_pagenum}/{section_pagecount}{crb}"
        else:
            pagestr_chapterpages = ''
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.super_color=='none':
            page_superscript = f'<span style="font-size:{self.super_fontsize};vertical-align:super">{pagestr}</span>'

        else:
            page_superscript = f'<span style="font-size:{self.super_fontsize};vertical-align:super color:{self.super_color}">{pagestr}</span>'
#             page_superscript = '<span style="font-size:' + self.super_fontsize + ';vertical-align:super;color:' + self.super_color + '">' + pagestr + '</span>'
        return (page_superscript)

    def scan_spine(self, path):
        """
        Verify ePub has a navigation file.
        Check for existing page-list element in the nav file.
        Abort as necessary.
        Create a list of file_list dictionaries from the spine element in the opf file:
            Dictionary keys:
                filename: the full system path of the filename in the unzipped epub
                href: the href value from the manifest--used to create the page links
                section_pagecount: added later when the section scanned

        **Keyword arguments:**

        **_path_** -- the os path to the unzipped ePub files.

        returns spine_filelist
        """

        global epub_info
        # find the opf file using the META-INF/container.xml file
        with open(f"{path}/META-INF/container.xml", 'r') as container_file:
            container_dict = xmltodict.parse(container_file.read())
            opf_file = container_dict['container']['rootfiles']['rootfile']['@full-path']
            opf_path = opf_file.split('/')
            disk_path = ''
            if len(opf_path)>1:
                for index in range(0,len(opf_path)-1):
                    disk_path += f"{opf_path[index]}/"
            opf_filename = f"{path}/{opf_file}"

        with open(opf_filename,'r') as opf_file:
            opf_dict = xmltodict.parse(opf_file.read())
        # be sure we find a nav file
            if self.nav_pagelist:
                for item in opf_dict[opf_dictkey]['manifest']['item']:
                        if item.get('@properties') == 'nav':
                            epub_info['nav_file'] = f"{path}/{disk_path}{item['@href']}"
                if epub_info['nav_file']=='None':
                    self.write_log(True,'Fatal error - did not find navigation file')
                    return_dict['fatal'] = True
                    return
                else:
                    if self.DEBUG:
                        logstring = f"nav_file found: {epub_info['nav_file']}"
                        self.write_log(False, logstring)
                # we have a nav file, verify there is no existing page_list element
                    if self.nav_pagelist:
                        with open(epub_info['nav_file'],'r') as nav_r:
                            nav_data = nav_r.read()
                            if nav_data.find('<nav epub:type="page-list"') != -1:
                                self.write_log(True,'    ->INFO<- This epub file already has a page-list navigation element.')
                                self.write_log(True,'    ->INFO<- page-list navigation was selected but will not be created.')
                                self.nav_pagelist = False
                                epub_info['match_pages'] = True
                                # count the total number of pages in the nav_pagelist
                                epub_info['pages'] = self.get_nav_pagecount()
                                if return_dict['fatal']:
                                    self.write_log(True,'Fatal error.')
                                    return(return_dict)

        # we're good to go
        spine_filelist = []
        for spine_item in opf_dict[opf_dictkey]['spine']['itemref']:
            if self.DEBUG:
                logstring = f"spine_item idref: {spine_item['@idref']}"
                self.write_log(False, logstring)
            for manifest_item in opf_dict[opf_dictkey]['manifest']['item']:
                if self.DEBUG:
                    logstring = f"manifest_item: {manifest_item['@id']}"
                    self.write_log(False, logstring)
                if spine_item['@idref']==manifest_item['@id']:
                    fdict = {}
                    fdict['disk_file'] = f"{disk_path}{manifest_item['@href']}"
                    fdict['href'] = manifest_item['@href']
                    spine_filelist.append(fdict)
        epub_info['spine_filelist'] = spine_filelist
        return()

    def scan_sections(self):
        """
        Scan book contents, count words, pages, and section pages.
        this is an informational scan only, data is gathered, but no changes are made

        **Keyword arguments:**

        """
        global epub_info

        book_wordcount = 0
        page_words = 0
        book_pagenum = 1
        idx = 0
        footer_list = []
        # scan until we find '<body' and just copy all the header stuff.
        for chapter in epub_info['spine_filelist']:
            section_pagecount = 0
            with open(f"{epub_info['unzipped_epub_path']}/{chapter['disk_file']}", 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
                if self.DEBUG:
                    self.write_log(False, f'The word count is {book_wordcount:,} .')
                    self.write_log(False, f'The page count is {book_pagenum:,}')
            if epub_info['match_pages']:
                section_pagecount = ebook_data.count('epub:type="pagebreak"')
                chapter['section_pagecount'] = section_pagecount
                book_pagenum += section_pagecount
            else:
                body1 = ebook_data.find('<body')
                if body1==-1:
#                 print('No <body> element found.')
                    return_dict['errors'].append(f"No <body> element found. File: {chapter['disk_file']}")
                    return 0
                else:
                    idx = body1
                while idx < len(ebook_data)-1:
                    if ebook_data[idx]=='<': # we found an html element, just scan past it and don't count words
                        idx += 1
                        while ebook_data[idx]!='>':
                            idx += 1
                        idx += 1 
                    elif ebook_data[idx]==' ': # we found a word boundary
                        page_words += 1
                        book_wordcount += 1
                        if page_words>self.words_per_page: # if page boundary, add a page
                            section_pagecount += 1
                            book_pagenum += 1
                            page_words = 0
                        while ebook_data[idx]==' ': #skip additional whitespace
                            idx += 1
                    else: # just copy non-white space and non-element stuff
                        idx += 1
                if self.DEBUG:
                    logstring = f'Section page count is: {section_pagecount}'
                    self.write_log(False, logstring)
                #store the section pagecount in the dictionary.
                chapter['section_pagecount'] = section_pagecount
        epub_info['words'] = book_wordcount
        epub_info['pages'] = book_pagenum
        return 

#     Parameters:
#         ebook_data - this is data read from the chapter file
#         chapter - dictionary containing disk path for unzipped epub file, and href for link creation
    def scan_ebook_file(self,ebook_data,chapter):# {{{
        """# {{{
        Scan a section file and place page-links, page footers, superscripts as appropriate.
        This function is very similar to scan_section, but this one adds the pagelinks and page footers.
        If this is a converted ebook, then remove existing pagebreak links.

        **Keyword arguments:**

        **_ebook_data_**      -- the data read from the section file

        **_chapter_**         -- dictionary containing the href for use in pagelinks and pages in the section

        """# }}}

        global epub_info
        global pagenum
        global total_wordcount
        global page_wordcount

        # new version 2.1. 
        # scan the file character by character, allowing us to insert page
        # numbers at the exact word location. For now, put in page-list links
        # and also superscript in the text. Allow footers to be added. They
        # would be added following the paragraph where they occurred.
        idx = 0
        paginated_book = ''
        section_pagenum = 1
        footer_list = []
        # scan until we find '<body' and just copy all the header stuff.
        body1 = ebook_data.find('<body')
        if body1==-1:
            paginated_book += ebook_data
#             print('No <body> element found.')
            return_dict['errors'].append(f"No <body> element found. File: {chapter['disk_file']}")
            return paginated_book
        else:
            paginated_book += ebook_data[:body1]
            idx = body1
        while idx < len(ebook_data)-1:
            if ebook_data[idx]=='<': # we found an html element, just copy it and don't count words
                # if the element is </div> or </p>, after we scan past it, insert any page_footers 
                html_element = ebook_data[idx]
#                 paginated_book += ebook_data[idx]
                idx += 1
                while ebook_data[idx]!='>':
                    html_element += ebook_data[idx]
#                     paginated_book += ebook_data[idx]
                    idx += 1
                html_element += ebook_data[idx]
#                 paginated_book += ebook_data[idx]
                idx += 1 
                # if span element with pagebreak and a converted book, then don't put in the book, remove it.
                if (html_element.find('span') != -1) and (html_element.find('pagebreak') != -1) and (epub_info['converted']==True):
                    self.write_log(True,f'Removing html element: {html_element}')
                    # but we must also remove the </span>
#                     self.write_log(True,f'finding </span>; current char is {idx}')
                    if ebook_data[idx]=='<':
#                         self.write_log(True,f'finding </span>')
                        html_element = ebook_data[idx]
                        while ebook_data[idx]!='>':
                            idx += 1
                            html_element += ebook_data[idx]
                        self.write_log(True,f'Removing html element: {html_element}')
                        idx += 1
                else:
                    paginated_book += html_element

                if html_element=='</div>' or html_element=='</p>':
                    if self.page_footer:
                        if len(footer_list)>0:
                            for ft in footer_list:
                                paginated_book += ft
                        footer_list = []
            elif ebook_data[idx]==' ': # we found a word boundary
                page_wordcount += 1
                total_wordcount += 1
                if page_wordcount>self.words_per_page: # if page boundary, add a page
                    # insert the superscripted page number
                    if self.superscript:
                        paginated_book += self.create_superscript(pagenum,section_pagenum,chapter['section_pagecount'])
                    # insert the page-link entry
                    if self.nav_pagelist:
                        pstr = f'<span epub:type="pagebreak" id="page{pagenum}" '
                        pstr += f' role="doc-pagebreak" title="{pagenum}"/>'
                        paginated_book += pstr
                        self.add_nav_pagelist_target(pagenum, chapter['href'])
                    if self.page_footer:
                        footer_list.append(self.create_pagefooter(pagenum, section_pagenum, chapter['section_pagecount'], chapter['href']))
                    section_pagenum += 1
                    pagenum += 1
                    page_wordcount = 0
                while ebook_data[idx]==' ': #skip additional whitespace
                    paginated_book += ebook_data[idx]
                    idx += 1
            else: # just copy non-white space and non-element stuff
                paginated_book += ebook_data[idx]
                idx += 1
        return (paginated_book)# }}}

    def scan_and_match_ebook_file(self,ebook_data,chapter):# {{{
        """# {{{
        Called when the ebook already has page links and we are told to insert
        footers/superscripts matching existing paging.
        Scan a section file and place page-links, page footers, superscripts as appropriate.
        This function is very similar to scan_section, but this one adds the pagelinks and page footers.

        **Keyword arguments:**

        **_ebook_data_**      -- the data read from the section file

        **_chapter_**         -- dictionary containing the href for use in pagelinks and pages in the section

        **_ebookconverted_**  -- Boolean indicating if this ebook was converted from ePub version 2

        """# }}}

        
        # TODO
        '''
        '''
        idx = 0
        paginated_book = ''
        section_pagenum = 1
        footer_list = []
        # just find existing pagebreak entries
        not_done = True
        while not_done:
            plink_loc = ebook_data.find('epub:type="pagebreak"')
            if plink_loc==-1:
                paginated_book += ebook_data
                not_done = False
            else:
                paginated_book += ebook_data[:plink_loc]
                #update the string
                ebook_data = ebook_data[plink_loc:]
                # find the pagenumber
                loc = ebook_data.find('title=')
                if loc == -1:
                    self.write_log(True,'Did not find title for page link')
                else:
                    paginated_book += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    qlist = ebook_data.split('"')
                    thispage = qlist[1]
                    # now find the end of this element
                    loc = ebook_data.find('/>')
                    loc += 2
                    paginated_book += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    #insert superscript here
                    if self.superscript:
                        paginated_book += self.create_superscript(thispage,section_pagenum,chapter['section_pagecount'])
                    #now scan for next paragraph start or end and insert footer.
                    # note that this could miss a page if a paragraph contains two page links
                    loc = ebook_data.find('</p>')
                    if loc==-1:
                        self.write_log(True,'Did not find paragraph end to insert matched footer')
                    else:
                        loc += 4
                        paginated_book += ebook_data[:loc]
                        ebook_data = ebook_data[loc:]
                        if self.page_footer:
                            paginated_book += self.create_pagefooter(thispage, section_pagenum, chapter['section_pagecount'], chapter['href'])
                    section_pagenum += 1
        return (paginated_book)# }}}

# directory structures and names
# self.paged_epub_library/
#   book1/: unzipped source epub--modified in place
#   book1.epub: paginated book1
#   book2/: unzipped source epub--modified in place
#   book2.epub: paginated book1

# source_epub: full path to source epub file--the file to paginate. This is unzipped to self.paged_epub_library/book_name
# book_name: the source_epub with spaces removed from everything, and .epub removed.

# Parameters:
# source_epub: full path to source epub file--the file to paginate 
    def paginate_epub(self,source_epub):
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
        global epub_info
        global pagenum
        global total_wordcount
        global pagelist_element
        global epub_filelist
        global logfile_path
        global return_dict

        t1 = time.perf_counter()
        # re-initialize on each call
        pagenum = 1
        total_wordcount = 0
        page_wordcount = 0
        pagelist_element = ''
        epub_filelist = []
        book_string = ''
        opf_dictkey = 'package'

        self.get_epub_info(source_epub)
        if return_dict['fatal']:
            self.write_log(True,'Fatal error.')
            return(return_dict)
        ePubUnZip(source_epub,epub_info['unzipped_epub_path']) 
        # figure out where everything is and the order they are in.
        self.scan_spine(epub_info['unzipped_epub_path'])
        if return_dict['fatal']:
            self.write_log(True,'Fatal error.')
            return(return_dict)
        # scan the book to count words, section pages and total pages based on words/page
        self.scan_sections()
        if self.total_pages==0:
            self.total_pages = epub_info['pages']
        # this is the working loop. Scan each file, locate pages and insert page-links and/or footers or superscripts
        pagenum = 1
        for chapter in epub_info['spine_filelist']:
            #must reset things from the previous scan
            total_word_count = 0
            if self.DEBUG:
                logstring = f"file: {epub_info['unzipped_epub_path']}/{chapter['disk_file']}"
                self.write_log(False, logstring)
            with open(f"{epub_info['unzipped_epub_path']}/{chapter['disk_file']}", 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
            with open(f"{epub_info['unzipped_epub_path']}/{chapter['disk_file']}", 'w') as ebook_wfile:
                start_total = total_wordcount
                if self.DEBUG:
                    logstring = f"Scanning {chapter['disk_file']}; start_total: {start_total} total_wordcount: {total_wordcount}"
                    self.write_log(False, logstring)
                if epub_info['match_pages']:
                    new_ebook = self.scan_and_match_ebook_file(ebook_data,chapter)
                else:
                    new_ebook = self.scan_ebook_file(ebook_data,chapter)
                if self.DEBUG:
                    self.write_log(False, f"chapter has {total_wordcount-start_total:,} words")
                ebook_wfile.write(new_ebook)
        book_string += f"    {total_wordcount:,} words; {pagenum:,} pages"
        self.write_log(True,book_string)
        #modify the nav_file to add the pagelist
        if self.nav_pagelist:
            pagelist_element += '  </ol></nav>' + CR
            self.update_navfile()
        # build the epub file 
        ePubZip(f"{self.paged_epub_library}/{epub_info['book_name']}.epub",f"{self.paged_epub_library}/{epub_info['book_name']}", epub_filelist) 
        # and if DEBUG is not set, we remove the unzipped epub directory
        if self.DEBUG==False:
            rm_cmd = ['rm','-rf',f"{self.paged_epub_library}/{epub_info['book_name']}"]
            result = run(rm_cmd, stdout=PIPE, stderr=PIPE,universal_newlines=True)
        t2 = time.perf_counter()
#         self.write_log(True,f"    Paginated in {t2-t1:.6f} seconds.")
        if self.epubcheck!='none':
            self.write_log(True,'---------------------------')
            self.write_log(True,'Running epubcheck:' + CR)
            epubcheck_cmd = [self.epubcheck,f"{self.paged_epub_library}/{epub_info['book_name']}.epub"]
            result = run(epubcheck_cmd, stdout=PIPE, stderr=PIPE,universal_newlines=True)
            # check and log the errors from epubcheck
            stdout_lines = result.stdout.splitlines()
            self.write_log(True, result.stdout)
            if len(result.stderr)>0:
                self.write_log(False, result.stderr)
            self.write_log(True,'---------------------------')
            self.write_log(True,'\n')
        return(return_dict)
