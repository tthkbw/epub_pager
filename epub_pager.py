import os
import sys
from subprocess import PIPE, run
import time

import xmltodict
import json
import zipfile
import re

version = '2.1'
CR = '\n'
pagenum = 1
total_wordcount = 0
page_wordcount = 0
pagelist_element = ''
epub_filelist = []
nav_file = 'None'
href_path = []

# the following two routines are modified from those on GitHub: https://github.com/MJAnand/epub/commit/8980928a74d2f761b2abdb8ef82a951be11b26d5

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
            print('Fatal error, no mimetype file was found.')
            sys.exit()
    with zipfile.ZipFile(epub_path, 'a', zipfile.ZIP_DEFLATED) as myzip:
        for ifile in epub_filelist:
            myzip.write(srcfiles_path + '/' + ifile, ifile, zipfile.ZIP_DEFLATED)

def ePubUnZip(fileName, path):
    """
    Unzip ePub file into a directory

    **Keyword arguments:**

    fileName -- the ePub file name

    path     -- path for the unzipped files.

    """
    global epub_filelist
    z = zipfile.ZipFile(fileName)
    epub_filelist = z.namelist()
    for name in epub_filelist:
        output = str(path+'/'+fileName.replace('.epub', ''))
        z.extract(name, output)
    z.close()

class epub_paginator:
    """
    Paginate an ePub3 using page-list navigation and/or inserting page information footers into the text.

    **Release Notes**

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

        **_page_number_bracket_** -- Character (e.g. '<' or '(' ) used to bracket page numbers in page footer. 

        **_page_number_total_**   -- Present the book page number with a total (34/190) in the footer.

        **_chapter_pages_**       -- Present the chapter page number and chapter page number total in the footer.

        **_chapter_fontsize_**    -- A percentage value for the relative font size used for the footer.

        **_nav_pagelist_**        -- Create the page_list element in the navigation file.

        **_superscript_**               -- Insert a superscripted page entry

        **_epubcheck_**           -- The OS path of epubcheck. If present, epubcheck is run on the created file.

        **_DEBUG_**               -- Boolean. If True, print status and debug information while running.

        """
        self.paged_epub_library = "/Users/tbrown/Documents/projects/BookTally/paged_epubs"
        self.words_per_page = 300
        self.total_pages = 0
        self.page_footer = False
        self.page_number_align = 'center'
        self.page_number_color = 'red'
        self.page_number_bracket = '<'
        self.page_number_total = True
        self.chapter_pages = True
        self.chapter_fontsize = '75%'
        self.nav_pagelist = True
        self.superscript = False
        self.epubcheck = '/opt/homebrew/bin/epubcheck'
        self.DEBUG = False

    def get_version():
        """
        Return version of epub_pager.
        """

        return(version)

    def update_navfile(self):
        """
        Add generated page-list element to the ePub navigation file
        """
        global nav_file
        global pagelist_element

        with open(nav_file,'r') as nav_file_read:
            nav_data = nav_file_read.read()
        pagelist_loc = nav_data.find('</body>')
        new_nav_data = nav_data[:pagelist_loc]
        new_nav_data += pagelist_element
        with open(nav_file,'w') as nav_file_write:
            nav_file_write.write(new_nav_data)
            nav_file_write.write(nav_data[pagelist_loc:])

    def add_nav_pagelist_target(self, pagenum, href):
        """
        Generate page-list entry and page footer

        **Keyword arguments:**

        pagenum -- the page number in the book

        href    -- the filename and path for the internal page link in the book

        """
        global pagelist_element

        pagelist_element += '  <li><a href="' + href + '#page' + str(pagenum) + '">' + str(pagenum) + '</a></li>' + CR
        return 

    def create_pagefooter(self,pagenum,section_pagenum, section_pagecount, href):
        """# {{{
        Create pagelinks for navigation and add to page-list element. 
        Format and return page footer.

        **Keyword arguments:**
        pagenum           -- the current page number of the book

        section_pagenum   -- the current section page number

        section_pagecount -- the pagecount of the section

        href              -- the relative path and filename for the pagelink

        """# }}}

        # construct the page footer based on formatting selections
        # brackets
        if self.page_number_bracket=='<':
            lb = '&lt;'
            rb = '&gt;'
        elif self.page_number_bracket=='-':
            lb = '-'
            rb = '-'
        else:
            lb = ''
            rb = ''
        #book pages format
        if self.page_number_total==True:
            pagestr_bookpages = lb + str(pagenum) + '/' + str(self.total_pages) + rb
        else:
            pagestr_bookpages = lb + str(pagenum) + rb

        #chapter pages format
        if self.chapter_pages==True:
            pagestr_chapterpages = ' ' + lb + str(section_pagenum) + '/' + str(section_pagecount) + ' in chapter' + rb
        else:
            pagestr_chapterpages = ''

        pagestr = pagestr_bookpages + pagestr_chapterpages

        if self.page_number_color=='none':
            page_footer = '<div style="font-size:' + self.chapter_fontsize + '; text-align: ' + self.page_number_align + ';margin: 0 0 0 0">' + pagestr + '</div>'
# the following creates left justified bookpages and right justified chapter pages.
#             page_footer = '<div> <p style="font-size:75%; float: left; ' + ';margin: 0 0 0 0">' + pagestr_bookpages + '</p>' + '<p style="font-size:75%; float: right; ' + ';margin: 0 0 0 0">' + pagestr_chapterpages + '</p></div><div style="clear: both;"></div>'
        else:
            page_footer = '<div style="font-size:' + self.chapter_fontsize + '; text-align: ' + self.page_number_align + '; color: ' + self.page_number_color + ';margin: 0 0 0 0">' + pagestr + '</div>'
        if self.nav_pagelist:
            self.add_nav_pagelist_target(pagenum, href)
        return (page_footer)


# Verify that the pub file is one we can work with:
# - Epub version 3.0 minimum
# - Must have a nav file
# - If the nav file has an existing page-list element, we leave it alone
#

    def scan_spine(self, path):
        """
        Verify ePub is version 3.0 or higher.
        Verify ePub has a navigation file.
        Check for existing page-list element in the nav file.
        Abort as necessary.
        Create a list of file_list dictionaries from the spine element in the opf file:
            Dictionary keys:
                filename: the full system path of the filename in the unzipped epub
                href: the href value from the manifest--used to creted the page links
                section_pagecount: added later

        **Keyword arguments:**

        path -- the os path to the unzipped ePub files.

        """
        global nav_file

        # find the opf file using the META-INF/container.xml file
        with open(path + '/' + 'META-INF/container.xml', 'r') as container_file:
            container_dict = xmltodict.parse(container_file.read())
            opf_file = container_dict['container']['rootfiles']['rootfile']['@full-path']
            opf_path = opf_file.split('/')
            disk_path = ''
            if len(opf_path)>1:
                for index in range(0,len(opf_path)-1):
                    disk_path += opf_path[index] + '/'
            opf_filename = path + '/' + opf_file

        with open(opf_filename,'r') as opf_file:
            opf_dict = xmltodict.parse(opf_file.read())
            # verify we have an epub3, else abort
            version = opf_dict['package']['@version']
            vnum = float(version)
            if vnum < 3.0:
                print('Fatal Error - Epub version is not 3 or newer, cannot paginate.')
                print('Convert to Epub3 and try again.')
                sys.exit()
        # be sure we find a nav file
            for item in opf_dict['package']['manifest']['item']:
                    if item.get('@properties') == 'nav':
                        nav_file = path + '/' + disk_path + '/' + item['@href']
            if nav_file=='None':
                print('Fatal error - did not find navigation file')
                sys.exit()
            else:
                print('nav_file found: ' + nav_file)
            # we have a nav file, verify there is no existing page_list element
            with open(nav_file,'r') as nav_r:
                nav_data = nav_r.read()
                if self.nav_pagelist:
                    if nav_data.find('<nav epub:type="page-list"') != -1:
                        print('This epub file already has a page-list navigation element.')
                        print('page-list navigation was selected but will not be created.')
                        self.nav_pagelist = False
        # we're good to go
        spine_filelist = []
        for spine_item in opf_dict['package']['spine']['itemref']:
#         print('spine_item idref: ' + spine_item['@idref'])
            for manifest_item in opf_dict['package']['manifest']['item']:
#             print('manifest_item: ' + manifest_item['@id'])
                if spine_item['@idref']==manifest_item['@id']:
                    fdict = {}
                    fdict['disk_file'] = disk_path + manifest_item['@href']
                    fdict['href'] = manifest_item['@href']
                    spine_filelist.append(fdict)
        return(spine_filelist)

    def scan_sections(self, unzipped_epub_path, spine_filelist):
        """
        Scan book contents, count words, pages, and section pages.

        **Keyword arguments:**

        unzipped_epub_path -- os path to the unzipped epub file

        spine_filelist     -- list of dictionaries containing os paths and internal href paths

        """
        book_wordcount = 0
        page_words = 0
        book_pagenum = 1
        idx = 0
        footer_list = []
        # scan until we find '<body' and just copy all the header stuff.
        for chapter in spine_filelist:
            section_pagecount = 0
            with open(unzipped_epub_path + '/'  + chapter['disk_file'], 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
                if self.DEBUG:
                    print('The word count is ' + '{:,}'.format(book_wordcount) + '.' + CR + 'The page count is ' + '{:,}'.format(book_pagenum))
            body1 = ebook_data.find('<body')
            if body1==-1:
                print('No <body> element found.')
                return 0
            else:
                idx = body1
            while idx < len(ebook_data)-1:
                if ebook_data[idx]=='<': # we found an html element, just copy it and don't count words
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
            print('Section page count is: ' + str(section_pagecount))
            #store the section pagecount in the dictionary.
            chapter['section_pagecount'] = section_pagecount
        return book_pagenum

#     Parameters:
#         ebook_data - this is data read from the chapter file
#         chapter - dictionary containing disk path for unzipped epub file, and href for link creation
    def scan_ebook_file(self,ebook_data,chapter):# {{{
        """# {{{
        Scan an section file and place page-links and page footers as appropriate.
        This function is very similar to scan_section, but this one adds the pagelinks and page footers.

        **Keyword arguments:**

        ebook_data -- the data read from the section file

        chapter    -- dictionary containing the href for use in pagelinks and pages in the section

        """# }}}
        global pagenum
        global total_wordcount
        global page_wordcount
        global pagelist_element

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
            print('No <body> element found.')
            return paginated_book
        else:
            paginated_book += ebook_data[:body1]
            idx = body1
        while idx < len(ebook_data)-1:
            if ebook_data[idx]=='<': # we found an html element, just copy it and don't count words
                if self.page_footer:
                    if len(footer_list)>0:
                        for ft in footer_list:
                            paginated_book += ft
                    footer_list = []
                paginated_book += ebook_data[idx]
                idx += 1
                while ebook_data[idx]!='>':
                    paginated_book += ebook_data[idx]
                    idx += 1
                paginated_book += ebook_data[idx]
                idx += 1 
            elif ebook_data[idx]==' ': # we found a word boundary
                page_wordcount += 1
                total_wordcount += 1
                if page_wordcount>self.words_per_page: # if page boundary, add a page
                    # insert the superscripted page number
                    if self.superscript:
                        paginated_book += '<span style="font-size:75%;vertical-align:super;color:' + self.page_number_color + '">' + str(pagenum) + '</span>'
                    # insert the page-link entry
                    if self.nav_pagelist:
                        paginated_book += '<span epub:type="pagebreak" id="page' + str(pagenum) + '"'  + ' title="' + str(pagenum) + '"/>'
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

        source_epub -- The original ePub file to modify.

        """
        global pagenum
        global total_wordcount
        global pagelist_element
        global nav_file

        t1 = time.perf_counter()
        pagelist_element = '<nav epub:type="page-list" id="page-list"><ol>' + CR
        dirsplit = source_epub.split('/')
        # the epub name is the book file name with spaces removed and '.epub' removed
        stem_name = dirsplit[len(dirsplit)-1].replace(' ','')
        book_name = stem_name.replace('.epub','')
        ePubUnZip(source_epub,self.paged_epub_library) 
        unzipped_epub_path = self.paged_epub_library + '/' + book_name
        # figure out where everything is and the order they are in.
        spine_filelist = self.scan_spine(unzipped_epub_path)
        # scan the book to count words, section pages and total pages based on words/page
        book_pagecount = self.scan_sections(unzipped_epub_path, spine_filelist)
        if self.total_pages==0:
            self.total_pages = book_pagecount
        pagenum = 1
        for chapter in spine_filelist:
            #must reset things from the previous scan
            total_word_count = 0
            if self.DEBUG:
                print('file: ' + unzipped_epub_path + '/' + chapter['disk_file'])
            with open(unzipped_epub_path + '/'  + chapter['disk_file'], 'r') as ebook_rfile:
                ebook_data = ebook_rfile.read()
            with open(unzipped_epub_path + '/'  + chapter['disk_file'], 'w') as ebook_wfile:
                start_total = total_wordcount
                if self.DEBUG:
                    print('Scanning ' + chapter['disk_file'] + '; start_total: ' + str(start_total) + ' total_wordcount: ' + str(total_wordcount))
                new_ebook = self.scan_ebook_file(ebook_data,chapter)
                if self.DEBUG:
                    print('chapter has ' + '{:,}'.format(total_wordcount-start_total) + ' words')
                ebook_wfile.write(new_ebook)
        print('The word count is ' + '{:,}'.format(total_wordcount) + '.' + CR + 'The page count is ' + '{:,}'.format(pagenum))
        pagelist_element += '  </ol></nav>' + CR
        #modify the nav_file to add the pagelist
        if self.nav_pagelist:
            self.update_navfile()
        t2 = time.perf_counter()
        print('ePub pagination took ' + '{:.6f}'.format(t2-t1) + ' seconds.')
        # Now build the epub file and check it
        ePubZip(self.paged_epub_library + '/' + book_name + '.epub',self.paged_epub_library + '/' + book_name, epub_filelist) 
        epubcheck_cmd = [self.epubcheck,self.paged_epub_library + '/' + book_name + '.epub']
        result = run(epubcheck_cmd, stdout=PIPE, stderr=PIPE,universal_newlines=True)
        print('stdout: ' )
        print(result.stdout)
        if len(result.stderr)>0:
            print('stderr: ' )
            print(result.stderr)
