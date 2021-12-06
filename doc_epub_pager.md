Module epub_pager
=================

Classes
-------

`epub_paginator()`
:   Paginate an ePub3 using page-list navigation and/or inserting page
    information footers and/or superscripts into the text.
    
    **Release Notes**
    
    **Version 2.94**
    
    PEP8 compliant.
    
    **Version 2.93**
    
    1. Update Doc strings.
    1. Refactor to eliminate globals--essentially move the class statement to
    the top of the file and reference globals with self.
    1. Fixed a bug that was looking for '/>' as the end of the pagebreak
    element in scan and match routine. Should have been looking for </span>.
    
    **Version 2.92**
    
    1. Can now match the superscript and footer insertions to existing page
    numbering. This is automatically done if a page-list exists in the nav
    file.
    
    **Version 2.91**
    
    1. Lots of refactoring of code.
    1. Added ebpub_info dictionary to consolidate data about the epub file.
    1. Added get_nav_pagecount() which determines the maximum page number in an
    already paginated file.
    
    **Version 2.9**
    
    1. Add the role="doc-pagebreak" to the page links. This appears to fix the
    bug that resulted in iBooks not showing all the page numbers in the margin.
    
    **Version 2.8**
    
    1. Fixed a bug where the </span> was not removed when removing existingn
    page links from a converted epub.
    
    **Version 2.7**
    
    1. Added rdict to return a set of data to the calling program, including
    what used to go to stdout
    
    **Version 2.6**
    
    1. Fixed a bug in logic that removes pagebreak elements from converted
    epub2 books.
    
    **Version 2.5**
    
    1. Implemented conversion of epub2 to epub3 using calibre ebook-converter.
    epub_paginator contains command line switches for all options to
    epub_pager.
    
    **Version 2.4**
    
    1. Implement configuration file.
    
    **Version 2.3**
    
    1. Add log file. Program produces minimal output, but puts data in log
    file.
    2. If running epubcheck, echo stdout to stdout, but echo stderr only to the
    log file.
    3. If DEBUG is False, remove the unzipped epub directory when done.
    
    **Version 2.2**
    
    1. Add epub_version exposed command to the class.
    
    1. Fixed bug that mispositioned the footer inside italic or other
    textual html elements and caused epubcheck errors. footers are now
    properly positioned after the <div> or <p> active element when the page
    limit is reached.
    
    1. Refactored some of the code. Uses f strings for formatting; cleaned up
    printing.
    
    **Version 2.1**
    
    1. Made a Github repository with a local copy.
    1. Rewrote the scanning algorithm. Scans character by character after
    <body> element in spine files. Doesn't care about <p> elements or anything
    else. Still places footer before paragraph where the page ends. Other page
    numbering is at precise word location.
    1. Note that nested <div> elements are created by the placement of footers
    and this creates errors in epubcheck. However, these errors do not affect
    Calibre book reader, nor Apple Books.
    
    **Version 2.0**
    
    1. Includes Docstrings that are compatible with creating documentation
    using pdoc.
    1. Lot's of refactoring has been done.
    1. Verifies epub3 version.
    1. Verifies nav file exists.
    1. Doesn't generated page-list if it already exists.
    1. Adds chapter page numbering.
    
    **Instance Variables**
    
    **_outdir_**
    
    full os path for placement of the paginated ePub file.
    
    **_match_**
    
    Boolean, if book is paginated, match super and footer insertion to
    existing page numbering. Default True
    
    **_genplist_**
    
    Create the page_list element in the navigation file.
    
    **_pgwords_**
    
    Number of words per page.
    
    **_pages__**
    
    Number of pages in the book.
    
    **_footer_**
    
    Boolean, if True, insert the page footers, otherwise do not.
    
    **_ft_align_**
    
    left, right, or center, alignment of the page numbers in the footer.
    
    **_ft_color_**
    
    Optional color for the footer--if not set, then no color is used.
    
    **_ft_bkt_**
    
    Character (e.g. '<' or '(' ) used to bracket page numbers in page
    footer.
    
    **_ft_fntsz_**
    
    A percentage value for the relative font size used for the footer.
    
    **_ft_pgtot_**
    
    Present the book page number with a total (34/190) in the footer.
    
    **_superscript_**
    
    Insert a superscripted page entry
    
    **_super_color_**
    
    Optional color for the superscript--if not set, then no color is used.
    
    **_super_fntsz_**
    
    A percentage value for the relative font size used for superscript.
    
    **_super_total_**
    
    Present the book page number with a total (34/190) in superscript.
    
    **_chap_pgtot_**
    
    Present the chapter page number and chapter page number total in the
    footer and/or superscript.
    
    **_chap_bkt_**
    
    Character (e.g. '<' or '(' ) used to bracket page numbers in footer
    and/or superscript.
    
    **_ebookconvert_**
    
    The OS path of the ebook conversion program. If present, epub2 books
    are converted to epub3 before pagination.
    
    **_epubcheck_**
    
    The OS path of epubcheck. If present, epubcheck is run on the created
    file.
    
    **_DEBUG_**
    
    Boolean. If True, print status and debug information to logile while
    running.

    ### Class variables

    `bk_flist`
    :

    `bkinfo`
    :

    `curpg`
    :

    `logpath`
    :

    `pg_wcnt`
    :

    `plist`
    :

    `rdict`
    :

    `tot_wcnt`
    :

    `version`
    :

    ### Methods

    `add_genplist_target(self, curpg, href)`
    :   Generate page-list entry and page footer and add them to a string that
        accumulates them for placement in the navigation file.
        
        **Keyword arguments:**
        
        **_curpg_**
        
        The page number in the book.
        
        **_href_**
        
        The filename and path for the internal page link in the book.

    `bld_foot(self, curpg, sct_pg, sct_pgcnt, href)`
    :   # {{{
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

    `ePubUnZip(self, fileName, unzip_path)`
    :   Unzip ePub file into a directory
        
        **Keyword arguments:**
        
        **_fileName_** -- the ePub file name
        
        **_path_**     -- path for the unzipped files.

    `ePubZip(self, epub_path, srcfiles_path, bk_flist)`
    :   Zip files from a directory into an epub file
        
        **Keyword arguments:**
        
        **_epub_path_** -- os path for saving creating epub file
        
        **_srcfiles_path_** -- path of the directory containing epub files
        
        **_bk_flist_** -- the list of files to zip into the epub file

    `get_bkinfo(self, epub_file)`
    :   Gather useful information about the ebub file and put it in the
        bkinfo dictionary.
        
        **Instance Variables**
        
        **_epub_file_**  -- ePub file to return version of

    `get_epub_version(self, epub_file)`
    :   Return ePub version of ePub file
        
        If ePub does not store the version information in the standard
        location, return 'no version'
        
        **Instance Variables**
        
        **_epub_file_**
        
        ePub file to return version of

    `get_nav_pagecount(self)`
    :   Read the nav file and parse the page-list entries to find the total
        pages in the book
        
        **Instance Variables**
        
        **_navfile_**  -- ePub navigation file

    `get_version(self)`
    :   Return version of epub_pager.

    `new_super(curpg, sct_pg, sct_pgcnt)`
    :   Format and return a <span> element for superscripted page numbering.
        
        **Keyword arguments:**
        **_curpg_**
        
        The current page number of the book.
        
        **_sct_pg_**
        
        The current section page number.
        
        **_sct_pgcnt_**
        
        The pagecount of the section.

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

    `scan_file(self, ebook_data, chapter)`
    :   Scan a section file and place page-links, page footers, superscripts as
        appropriate.
        
        This function is very similar to scan_section, but this one adds the
        pagelinks and page footers.
        
        If this is a converted ebook, then remove existing pagebreak links.
        
        **Keyword arguments:**
        
        **_ebook_data_**
        
        The data read from the section file.
        
        **_chapter_**
        
        Dictionary containing the href for use in pagelinks and pages in the
        section.

    `scan_match_file(self, ebook_data, chapter)`
    :   Called when the ebook already has page links and we are told to insert
        footers/superscripts matching existing paging.
        
        Scan a section file and place page footers, superscripts based on
        existing pagebreaks.
        
        **Keyword arguments:**
        
        **_ebook_data_**
        
        The data read from the section file.
        
        **_chapter_**
        
        Dict with href for pagelinks; section pages.

    `scan_sections(self)`
    :   Scan book contents, count words, pages, and section pages.
        
        This is an informational scan only, data is gathered, but no changes
        are made
        
        **Keyword arguments:**

    `scan_spine(self, path)`
    :   Verify ePub has a navigation file.
        
        Check for existing page-list element in the nav file.  Abort as
        necessary.
        
        Create a list of file_list dictionaries from the spine element in the
        opf file:
        
            Dictionary keys:
        
                filename: the full system path of the filename in the unzipped
                epub
        
                href: the href value from the manifest--used to create the page
                links
        
                sct_pgcnt: added later when the section is pre-scanned
        
        **Keyword arguments:**
        
        **_path_**
        
        The os path to the unzipped ePub files.
        
        returns spine_lst

    `update_navfile(self)`
    :   Add generated page-list element to the ePub navigation file

    `wrlog(self, stdout, message)`
    :   Write a message to the log file.
        
        **Instance Variables**
        
        **_stdout_**       -- if True, then echo the message to stdout
        **_message_**      -- the message to print
