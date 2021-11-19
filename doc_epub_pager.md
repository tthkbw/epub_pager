Module epub_pager
=================

Functions
---------

    
`ePubUnZip(fileName, unzip_path)`
:   Unzip ePub file into a directory
    
    **Keyword arguments:**
    
    fileName -- the ePub file name
    
    path     -- path for the unzipped files.

    
`ePubZip(epub_path, srcfiles_path, epub_filelist)`
:   Zip files from a directory into an epub file
    
    **Keyword arguments:**
    
    epub_path -- os path for saving creating epub file
    
    srcfiles_path -- os path of the directory containing files for the epub
    
    epub_filelist -- the list of files to zip into the epub file

Classes
-------

`epub_paginator()`
:   Paginate an ePub3 using page-list navigation and/or inserting page information footers into the text.
    
    **Release Notes**
    
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

    ### Methods

    `add_nav_pagelist_target(self, pagenum, href)`
    :   Generate page-list entry and page footer and add them to a string that
        accumulates them for placement in the navigation file.
        
        **Keyword arguments:**
        
        **_pagenum_** -- the page number in the book
        
        **_href_**    -- the filename and path for the internal page link in the book

    `create_pagefooter(self, pagenum, section_pagenum, section_pagecount, href)`
    :   # {{{
        Create pagelinks for navigation and add to page-list element. 
        Format and return page footer.
        
        **Keyword arguments:**
        **_pagenum_**           -- the current page number of the book
        
        **_section_pagenum_**   -- the current section page number
        
        **_section_pagecount_** -- the pagecount of the section
        
        **_href_**              -- the relative path and filename for the pagelink

    `create_superscript(self, pagenum, section_pagenum, section_pagecount)`
    :   # {{{
        Format and return a <span> element for superscripted page numbering
        
        **Keyword arguments:**
        **_pagenum_**           -- the current page number of the book
        
        **_section_pagenum_**   -- the current section page number
        
        **_section_pagecount_** -- the pagecount of the section

    `get_epub_version(self, epub_file)`
    :   Return ePub version of ePub file
        If ePub does not store the version information in the standard location, return 'no version'
        
        **Instance Variables**
        
        **_epub_file_**  -- ePub file to return version of

    `get_version(self)`
    :   Return version of epub_pager.

    `paginate_epub(self, source_epub)`
    :   **paginate_epub** 
        Unzip *source_epub*.
        Verify ePub version, navigation capable, navigation exists.
        Generate list of files to scan and their order.
        Scan each file and add page links and page footers as requested.
        Build a page-list element while scanning.
        Update the navigation file with the page-list element.
        Save the modified files a a paginated ePub.
        
        **Keyword arguments:**
        
        **_source_epub_** -- The original ePub file to modify.

    `scan_ebook_file(self, ebook_data, chapter, ebookconverted)`
    :   # {{{
        Scan a section file and place page-links, page footers, superscripts as appropriate.
        This function is very similar to scan_section, but this one adds the pagelinks and page footers.
        If this is a converted ebook, then remove existing pagebreak links.
        
        **Keyword arguments:**
        
        **_ebook_data_**      -- the data read from the section file
        
        **_chapter_**         -- dictionary containing the href for use in pagelinks and pages in the section
        
        **_ebookconverted_**  -- Boolean indicating if this ebook was converted from ePub version 2

    `scan_sections(self, unzipped_epub_path, spine_filelist)`
    :   Scan book contents, count words, pages, and section pages.
        this is an informational scan only, data is gathered, but no changes are made
        
        **Keyword arguments:**
        
        **_unzipped_epub_path_** -- os path to the unzipped epub file
        
        **_spine_filelist_**     -- list of dictionaries containing os paths and internal href paths

    `scan_spine(self, path)`
    :   Verify ePub has a navigation file.
        Check for existing page-list element in the nav file.
        Abort as necessary.
        Create a list of file_list dictionaries from the spine element in the opf file:
            Dictionary keys:
                filename: the full system path of the filename in the unzipped epub
                href: the href value from the manifest--used to create the page links
                section_pagecount: added later when the section scanned
        
        **Keyword arguments:**
        
        **_path_** -- the os path to the unzipped ePub files.

    `update_navfile(self)`
    :   Add generated page-list element to the ePub navigation file

    `write_log(self, stdout, message)`
    :   Write a message to the log file.
        
        **Instance Variables**
        
        **_stdout_file_**  -- if True, then echo the message to stdout
        **_message_**      -- the message to print
