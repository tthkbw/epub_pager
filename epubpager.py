import sys
import shutil
from subprocess import PIPE, run
import time
from pathlib import Path
import typing
import urllib.parse

import zipfile

CR = "\n"
opf_dictkey = "package"
pglnk = "pagetb"
epubns = 'xmlns:epub="http://www.idpf.org/2007/ops"'
pg_xmlns = f'<nav {epubns} epub:type="page-list" id="page-list" hidden="hidden"><ol> \n'
comment_epubpager ="This epub was modified by epubpager https://github.com/tthkbw/epub_pager "

has_echk = True
try:
    from epubcheck import EpubCheck

    echk_message = "epubcheck module is present."
except ModuleNotFoundError:
    echk_message = "epubcheck module was not found."
    has_echk = False


class epub_paginator:
    """
    Paginate an ePub3 using page-list navigation and/or inserting page
    information pagelines and/or superscripts into the text.

    pagelines appear as separately formatted lines in the text and may contain
    current page, total pages in the book, and current chapter page and total
    chapter pages. Pagelines are placed and the end of the paragraph where the
    page break occurred.

    Superscripts can contain the same information as pagelines, but the
    information is presented at the exact location of the page break as a
    superscript.

    **Release Notes**

    ** Version 3.6**
    1. Metadata added to opf file with words, pages, modified by epubpager notation.
    2. Fixed a bug in logic that caused no pagination under circumstances where
       pagination should have been done.

    TODO

    **Version 3.5** 
    Done
    1. Added a check to do nothing if the book has a plist and pagelines and
    superscripts were not requested.

    **Version 3.4**
    1. Added quiet to the configuration. If set, nothing is echoed to stdout.

    **Version 3.3**
    1. prepare for release on GitHub.

    **Version 3.2**
    1. Added capability of not setting genplist, pageline or superscript and
    epubpager will just convert, count words and count pages.
    1. Refined how pagelinks and lines were inserted to be sure proper page
    location worked. I think it did, but minor change made and operation
    verified.
    1. Generate an error if the original file removal fails.

    **Version 3.1**
    Finding bugs in 3.0
    1. using the shell script to simplify cross-platform compatibility causes
    problems with filenames with spaces. Copy the source_epub to a new filename
    with spaces removed to fix this.
    1. Oops! If the filename doesn't change when spaces are removed, then the
    copy fails. Add '_orig' to the input epub filename.
    1. By default, add xmlns locally to the added page-list element. Some files
    do this locally and I find the naamespace and don't add my own. But since
    the existing one is only local, my added pagelist is not recognized. Fixed
    to scan only <html> element. this works for normal text files, i.e. files
    with text for the book. For the nav file, we no longer use this scan and
    add feature. Instead, just add locally to my page-list element.

    **Version 3.0**
    1. Shoot the engineer and ship the product.
    1. Had the sense wrong on has_echk test. Now check self.epubcheck for
    file.is_file rather than existence (which returns true if the string is
    empty).
    1. To facilitate compatibility across platforms, the epubcheck parameter
    now points to an executable script that runs epubcheck and takes as input a
    epub filename. Examples are included wit the distribution, epubcheck.sh for
    unix and epubcheck.bat for Windows.

    **Version 2.99**
    1. Implement placing pagebreaks and supers at exact word position
    with new scanning algorithm.
    1. Fixed bug with enabling and disabling epubcheck. Must use "none" in the
    config file for this to work properly.
    1. Fixed bug with enabling and disabling epub convert. Without conversion,
    epub2 books are now properly paginated.
    1. Fixed a bug where some files in the manifest were url quoted. Used
    urllib.parse.unquote() to fix this.
    1. Append '_paged' to output file name so we don't inadvertently write over the input file.
    1. Changed name of footer to pageline. Also, ft_ type variable names changed to 'pl'
    1. Fixed a bug where the superscript, if colored, wasn't colored nor
    a superscript. Left out a ';'
    1. epubcheck is run with warnings disabled.
    1. Fixed problems with reporting epubcheck results.
    1. Fixed naming of logfile--appended _paged so it matches epub file name.
    1. File names were changed to remove '_'.
    1. Timing information added to rdict for epubcheck, epubconvert, and pagination times.
    1. Fixed Windows error reading files. changed to read and write with
    pathlib.read_text() and pathlib.write_text(). Although must be careful
    since write_text() has no append mode. also verify that file paths ad opens
    refer to Path objects
    1. Changed from externally referenced epubcheck to the python module
    epubcheck. If the module is not installed, disable checking and report in
    log file.
    1. Removed bkinfo dictionary and put all of the information in rdict.
    1. Removed dependency on xmltodict. I parse all the xml myself.
    1. Somewhere along the line, adding the pagelines with <div> . . . </div>
    at the end of the paragraphs causes the next paragraph to not be indented.
    This is caused by css that uses p+p, or paragraphs that follow paragraphs
    get indentation, while those following headers, for example, do not.
    Putting the pageline divs inside the paragraphs appears to display
    properly, but generates epubcheck errors that they are misplaced. So, I now
    just add '<p></p>' to the end of the pageline. This works, at least in
    Sigil.
    1. Tried various fixes for the problem of spacing after pagelines. The
    obvious fix is now in. Just insert the pageline as a new paragraph with its
    proper style, and margin of 0 0 0 0 specified. Removed the 'float' option in the
    pageline format--too confusing and not worth it. Wasn't implemented in the
    options anyway.

    **Version 2.98**
    1. Begin implmentation of new scanning algorithm. This algorithm
    improves the scan by more than 5x. Same changes to scan_file,
    count_words and scan_sections.
    1. This version generates 750 paged ebooks from the library with no
    fatal errors.

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
    looking for a </span> afterthe epub:type="pagebreak" element.
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

    1. Can now match the superscript and pageline insertions to existing
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

    1. Fixed bug that mispositioned the pageline inside italic or other
       textual html elements and caused epubcheck errors. pagelines are
       now properly positioned apler the <div> or <p> active element
       when the page limit is reached.

    1. Refactored some of the code. Uses f strings for formatting;
       cleaned up printing.

    **Version 2.1**

    1. Made a Github repository with a local copy.
    1. Rewrote the scanning algorithm. Scans character by character
       apler <body> element in spine files. Doesn't care about <p>
       elements or anything else. Still places pagelines before paragraph
       where the page ends. Other page numbering is at precise word
       location.
    1. Note that nested <div> elements are created by the placement of
       pagelines and this creates errors in epubcheck. However, these
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

    version = "3.5"
    curpg = 1  # current page number
    tot_wcnt = 0  # count of total words in the book
    pg_wcnt = 0  # word count per page
    plist = ""  # the page-list element for the nav file
    bk_flist = []  # list of all files in the epub
    logpath = Path()  # path for the logfile
    epub_file = ""  # this will be the epub to paginate

    rdict = {}
    """
    rdict = {  # data to return to calling program
        "logfile": "",  # logfile location and name a Path object
        "bk_outfile": "",  # modified epub file name and location a Path object
        "unzip_path": "",
        "title": "",
        "nav_file": "None",  # Path object pointing to navigation file in unzipped epub
        "nav_item": "None",
        "opf_file": "None",  # path to opf file in zipfile, read with zipfile.read
        "has_plist": False,
        "spine_lst": [],
        "words": 0,
        "match": False,
        "pgwords": 0,
        "version": "no_version",
        "converted": False,  # if True, converted from epub2
        "errors": [],  # list of errors that occurred
        "fatal": False,  # Was there a fatal error?
        "error": False,  # epub_pager error
        "warn": False,  # epub_pager warning
        "orig_fatal": 0,  # epubcheck fatal error original file
        "orig_error": 0,  # epubcheck error original file
        "orig_warn": 0,  # epubcheck warning original file
        "echk_fatal": 0,  # epubcheck fatal error
        "echk_error": 0,  # epubcheck error
        "convert_time": 0,  # time to convert from epub2 to epub3
        "paginate_time": 0,  # time to paginate the epub
        "epubchkpage_time": 0,  # time to run epubcheck on paged epub
        "epubchkorig_time": 0,  # time to run epubcheck on original epub
        "messages": "",  # list of messages generated.
    }
    """

    def __init__(self):
        # Instance Variables 
        """
        **Instance Variables**

        **_outdir_**

        full os path for placement of the paginated ePub file.

        **_match_**

        Boolean, if book is paginated, match super and pageline insertion
        to existing page numbering. Default True

        **_genplist_**

        Create the page_list element in the navigation file.

        **_pgwords_**

        Number of words per page.

        **_pages__**

        Number of pages in the book.

        **_pageline_**

        Boolean, if True, insert the page pagelines, otherwise do not.

        **_pl_align_**

        lepl, right, or center, alignment of the page numbers in the
        pageline.

        **_pl_color_**

        Optional color for the pageline--if not set, then no color is
        used.

        **_pl_bkt_**

        Character (e.g. '<' or '(' ) used to bracket page numbers in
        page pageline.

        **_pl_fntsz_**

        A percentage value for the relative font size used for the
        pageline.

        **_pl_pgtot_**

        Present the book page number with a total (34/190) in the
        pageline.

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
        the pageline and/or superscript.

        **_chap_bkt_**

        Character (e.g. '<' or '(' ) used to bracket page numbers in
        pageline and/or superscript.

        **_ebookconvert_**

        The OS path of the ebook conversion program. If present, epub2
        books are converted to epub3 before pagination.

        **_chk_orig_**

        Run epubcheck on the file before pagination

        **_chk_paged_**

        Run epubcheck on the paged epub after pagination

        **_quiet_**

        Do not print anything to stdout.
        **_DEBUG_**

        Boolean. If True, print status and debug information to logile
        while running.

        """ 
        self.outdir = "/Users/tbrown/Documents/projects/" "BookTally/paged_epubs"
        self.genplist = True
        self.match = True
        self.pgwords = 300
        self.pages = 0
        self.pageline = False
        self.pl_align = "center"
        self.pl_color = "red"
        self.pl_bkt = "<"
        self.pl_fntsz = "75%"
        self.pl_pgtot = True
        self.superscript = False
        self.super_color = "red"
        self.super_fntsz = "60%"
        self.super_total = True
        self.chap_pgtot = True
        self.chap_bkt = "<"
        self.ebookconvert = "none"  # path to conversion executable
        self.chk_orig = False
        self.chk_paged = False
        self.epubcheck = "none"  # path to epubcheck executable
        self.quiet = False
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
        with zipfile.ZipFile(epub_path, "w") as myzip:
            if "mimetype" in bk_flist:
                mpath = srcfiles_path / "mimetype"
                myzip.write(mpath, "mimetype")
                # myzip.write(srcfiles_path + "/" + "mimetype", "mimetype")
                bk_flist.remove("mimetype")
            else:
                self.wrlog(False, "Fatal error, no mimetype file was found.")
                if self.DEBUG:
                    self.wrlog(False, "bk_flist: ")
                    self.wrlog(False, bk_flist)
                sys.exit("Fatal error, no mimetype file was found.")
        with zipfile.ZipFile(epub_path, "a", zipfile.ZIP_DEFLATED) as myzip:
            for ifile in bk_flist:
                myzip.write(f"{srcfiles_path}/{ifile}", ifile, zipfile.ZIP_DEFLATED)

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

        return self.version

    def convert_epub(self):
        """
        Called when epub is not version 3 and we have a convert program. Calls
        convert. If successful points epub_file to the converted file. If
        unsuccessful, throws a fatal error.
        """

        ebconvert = Path(self.ebookconvert)
        cnvrt_t1 = time.perf_counter()
        self.wrlog(
            True,
            (f"    Converting to epub3 using {ebconvert}"),
        )
        epub3_file = self.epub_file.replace(".epub", "_epub3.epub")
        ebkcnvrt_cmd = [
            ebconvert,
            self.epub_file,
            epub3_file,
            "--epub-version",
            "3",
        ]
        result = run(
            ebkcnvrt_cmd,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
        )
        cnvrt_t2 = time.perf_counter()
        self.rdict["convert_time"] = cnvrt_t2 - cnvrt_t1
        self.wrlog(
            True,
            f"    ebook-convert took {self.rdict['convert_time']:.2f} seconds.",
        )
        if result.returncode == 0:
            self.wrlog(False, "Conversion log:")
            self.wrlog(False, result.stdout)
            self.epub_file = epub3_file
            # now try again on version
            v = self.get_epub_version(self.epub_file)
            self.rdict["epub_version"] = v
            if self.rdict["epub_version"] == "no_version":
                estr = (
                    "Fatal error: After conversion, version was "
                    "not found in the ePub file."
                )
                self.wrlog(True, estr)
                self.rdict["error_lst"].append(estr)
                self.rdict["pager_error"] = True
                return
            lstr = f"Paginating epub3 file: {self.epub_file}"
            self.wrlog(True, lstr)
            self.plist = pg_xmlns
            self.rdict["converted"] = True
        else:
            lstr = "Conversion to epub3 failed. Conversion reported:"
            self.wrlog(False, lstr)
            self.wrlog(False, result.stderr)
            astr = "Fatal error: Conversion to epub3 failed."
            self.rdict["error_lst"].append(astr)
            self.rdict["pager_error"] = True
            return

    def initialize(self):
        """
        Gather useful information about the epub file and put it in the
        rdict dictionary.

        **Instance Variables**

        """

        # find the opf file using the META-INF/container.xml file
        # operate from the unzipped epub
        opf_file = self.find_opf(self.rdict["unzip_path"])
        # Watch Out!!
        self.rdict["opf_file"] = opf_file
        if self.rdict["pager_error"]:
            return
        self.rdict["disk_path"] = ""
        opf_path = opf_file.split("/")
        if opf_path:
            for index in range(0, len(opf_path) - 1):
                self.rdict["disk_path"] += f"{opf_path[index]}/"
        else:
            self.rdict["pager_error"] = True
            self.wrlog(False, "Fatal error: opf file not found")
            return
        opf_filep = Path(opf_file)
        opfdata = opf_filep.read_text(encoding="utf-8")
        self.parse_opf(opfdata)

    def simple_epub_version(self) -> str:

        # find the opf file using the META-INF/container.xml file
        # operate from the unzipped epub
        opf_file = self.find_opf(self.rdict["unzip_path"])
        if self.rdict["pager_error"]:
            return "no_version"
        self.rdict["disk_path"] = ""
        opf_path = opf_file.split("/")
        if opf_path:
            for index in range(0, len(opf_path) - 1):
                self.rdict["disk_path"] += f"{opf_path[index]}/"
        else:
            self.rdict["pager_error"] = True
            self.wrlog(False, "Fatal error: opf file not found")
            return "no_version"
        opf_filep = Path(opf_file)
        opfdata = opf_filep.read_text(encoding="utf-8")

        loc = opfdata.find("<package")
        if loc != -1:
            opfdata = opfdata[loc:]
            vloc = opfdata.find("version")
            if vloc != -1:
                vlist = opfdata[vloc : vloc + 15].split('"')
                eversion = vlist[1]
                return eversion
            else:
                estr = "Fatal error: Did not find version string in opf file."
                self.wrlog(False, estr)
                self.rdict["error_lst"].append(estr)
                self.rdict["pager_error"] = True
                return "no version"
        else:
            estr = "Fatal error: Did not find package string in opf file."
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            self.wrlog(False, estr)
            return "no version"

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
        contain_data = zfile.read("META-INF/container.xml")
        contain_str = str(contain_data)
        rloc = contain_str.find("<rootfiles>")
        if rloc == -1:
            self.wrlog(False, f"Did not find <rootfiles> in container.")
            estr = "ABORTING: did not find <rootfiles> in container"
            self.rdict["error_lst"].append(estr)
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return "no_version"
        contain_str = contain_str[rloc + 3 :]
        rloc = contain_str.find("<rootfile")
        if rloc == -1:
            self.wrlog(False, f"Did not find <rootfile in container.")
            estr = "ABORTING: did not find <rootfile in container"
            self.rdict["error_lst"].append(estr)
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return "no_version"
        contain_str = contain_str[rloc + 3 :]
        rloc = contain_str.find("full-path=")
        if rloc == -1:
            self.wrlog(False, f"Did not find full-path in container.")
            estr = "ABORTING: did not find full-path in container"
            self.rdict["error_lst"].append(estr)
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return "no_version"
        contain_str = contain_str[rloc + 3 :]
        opflist = contain_str.split('"')
        opf_file = opflist[1]
        opf = zfile.read(opf_file)
        opf_str = str(opf)

        # first find the <package element
        ploc = opf_str.find("<package")
        if ploc == -1:
            self.wrlog(
                True, "get_epub_version: Did not find package string in opf file"
            )
            return "no version"
        else:
            # find the version= string
            opf_str = opf_str[ploc:]
            vloc = opf_str.find("version=")
            if vloc == -1:
                self.wrlog(
                    True, "get_epub_version: Did not find version string in opf file"
                )
                return "no version"
            else:
                vlist = opf_str[vloc : vloc + 15].split('"')
                eversion = vlist[1]
                return eversion

    def get_nav_pagecount(self):
        """
        Read the nav file and parse the page-list entries to find the
        total pages in the book

        **Instance Variables**

        **_navfile_**  -- ePub navigation file

        """

        with self.rdict["nav_file"].open("r") as nav_r:
            nav_data = nav_r.read()
        loc = nav_data.find('epub:type="page-list"')
        if loc == -1:
            # this should never happen since we get here only after the entry
            # was found
            sys.exit(
                (
                    "Error! oops, the page-list entry was not found "
                    "after having been initially found."
                )
            )
        nav_data = nav_data[loc:]
        not_done = True
        max_page = 0
        while not_done:
            loc = nav_data.find("<a href")
            if loc == -1:
                not_done = False
                continue
            nav_data = nav_data[loc:]
            loc = nav_data.find('">')
            if loc == -1:
                self.wrlog(False, "Unclosed '<a href' element in nav file.")
                self.wrlog(False, "Does this file pass epubcheck?")
                self.rdict["pager_error"] = True
                return 0
            loc += 2
            nav_data = nav_data[loc:]
            loc2 = nav_data.find("</a>")
            if loc2 == -1:
                self.wrlog(False, "'</a>' element not found in nav file.")
                self.wrlog(False, "Does this file pass epubcheck?")
                self.rdict["pager_error"] = True
                return 0
            if nav_data[:loc2].isdigit():
                if int(nav_data[:loc2]) > max_page:
                    max_page = int(nav_data[:loc2])
        self.wrlog(False, f"Nav pagelist page count is: {max_page}")
        return max_page

    def wrlog(self, stdout, message):
        """
        Write a message to the log file.

        **Instance Variables**

        **_stdout_**

        If True, then echo the message to stdout.

        **_message_**

        The message to print

        """
        if stdout and not self.quiet:
            print(message)
            self.rdict["messages"] += "\n" + message
        with self.logpath.open("a") as logfile:
            logfile.write(message + "\n")

    def update_opffile(self):
        """
        add metadata to the opf file if the pagination was successful
            # Add custom metadata to opf file
            # <meta name="tlbepubpager:words" content="57000"/>
            # <meta name="tlbepubpager:pages" content="197"/>
            # <meta name="tlbepubpager:modified" content="True"/>
        """
        with Path(self.rdict["opf_file"]).open("r") as opf_file_read:
            opf_data = opf_file_read.read()
        mloc = opf_data.find("</metadata>")
        if mloc != -1:
            self.wrlog(True,f"Found end of metadata: {opf_data[mloc-20:mloc+20]}")
            new_opf = opf_data[:mloc]
            new_opf += f'''<meta name="tlbepubpager:words" content="{self.rdict['words']}"/>'''
            new_opf += CR
            new_opf += f'''<meta name="tlbepubpager:pages" content="{self.rdict['pages']}"/>'''
            new_opf += CR
            new_opf += f'''<meta name="tlbepubpager:modified" content="True"/>'''
            new_opf += CR
            new_opf += opf_data[mloc:]
            with Path(self.rdict["opf_file"]).open("w") as opf_file_write:
                opf_file_write.write(new_opf)
        else:
            self.wrlog(True,f"Did not find end of metadata")

    def update_navfile(self):
        """
        Add generated page-list element to the ePub navigation file
        Verify that nav file has proper xmlns. If not fix it.
        """

        with self.rdict["nav_file"].open("r") as nav_file_read:
            nav_data = nav_file_read.read()
        pagelist_loc = nav_data.find("</body>")
        new_nav_data = nav_data[:pagelist_loc]
        new_nav_data += self.plist
        with self.rdict["nav_file"].open("w") as nav_file_write:
            nav_file_write.write(new_nav_data)
            nav_file_write.write(nav_data[pagelist_loc:])

    def add_plist_target(self, curpg, href):
        """
        Generate page-list entry and page pageline and add them to a
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
        Format and return page pageline.

        **Keyword arguments:**
        **_curpg_**

        The current page number of the book.

        **_sct_pg_**

        The current section page number.

        **_sct_pgcnt_**

        The pagecount of the section.

        """

        # construct the page pageline based on formatting selections
        # brackets
        # hack_p = '<p style="margin: 0 0 0 0"></p>'
        if self.pl_bkt == "<":
            flb = "&lt;"
            frb = "&gt;"
        elif self.pl_bkt == "-":
            flb = "-"
            frb = "-"
        else:
            flb = ""
            frb = ""
        if self.chap_bkt == "<":
            clb = "&lt;"
            crb = "&gt;"
        elif self.chap_bkt == "-":
            clb = "-"
            crb = "-"
        else:
            clb = ""
            crb = ""
        # book pages format
        if self.pl_pgtot:
            pagestr_bookpages = f"{flb}{curpg}/{self.rdict['pages']}{frb}"
        else:
            pagestr_bookpages = f"{flb}{curpg}{frb}"
        # chapter pages format
        if self.chap_pgtot:
            pagestr_chapterpages = f" {clb}{sct_pg}/{sct_pgcnt}{crb}"
        else:
            pagestr_chapterpages = ""
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.pl_color == "none":
            pageline = (
                f'<p style="font-size:{self.pl_fntsz}; '
                f'text-align: self.pl_align; margin: 0 0 0 0">'
                f"{pagestr}</p>"
            )
        else:
            pageline = (
                f'<p style="font-size:{self.pl_fntsz}; '
                f"text-align:{self.pl_align}; "
                f'color: {self.pl_color}; margin: 0 0 0 0">'
                f"{pagestr}</p>"
            )
        return pageline

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

        # construct the page pageline based on formatting selections
        # brackets
        if self.pl_bkt == "<":
            flb = "&lt;"
            frb = "&gt;"
        elif self.pl_bkt == "-":
            flb = "-"
            frb = "-"
        else:
            flb = ""
            frb = ""
        if self.chap_bkt == "<":
            clb = "&lt;"
            crb = "&gt;"
        elif self.chap_bkt == "-":
            clb = "-"
            crb = "-"
        else:
            clb = ""
            crb = ""
        # book pages format
        if self.super_total:
            pagestr_bookpages = f"{flb}{curpg}/{self.rdict['pages']}{frb}"
        else:
            pagestr_bookpages = f"{flb}{curpg}{frb}"
        # chapter pages format
        if self.chap_pgtot:
            pagestr_chapterpages = f" {clb}{sct_pg}/{sct_pgcnt}{crb}"
        else:
            pagestr_chapterpages = ""
        pagestr = pagestr_bookpages + pagestr_chapterpages
        if self.super_color == "none":
            page_superscript = (
                f'<span style="font-size:{self.super_fntsz};'
                f'vertical-align:super">{pagestr}</span>'
            )

        else:
            page_superscript = (
                f'<span style="font-size:{self.super_fntsz};'
                f"vertical-align:super; "
                f'color:{self.super_color}">{pagestr}</span>'
            )
        return page_superscript

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

        opf_list = self.rdict["opf_file"].split("/")
        nav_list = str(self.rdict["nav_item"]).split("/")
        manifest_list = manifest_item["href"].split("/")
        manifest_fnm = manifest_list[len(manifest_list) - 1]
        if len(opf_list) == 1:
            opf_path = []
        else:
            opf_path = opf_list[: len(opf_list) - 1]
        if self.DEBUG:
            lstr = f"opf_path: {opf_path}"
            self.wrlog(False, lstr)
        if len(nav_list) == 1:
            # this means nav and opf are same level, so use manifest
            # paths
            if self.DEBUG:
                lstr = f"nav file at same level as opf/manifest, " f"use manifest href."
                self.wrlog(False, lstr)
            href = urllib.parse.quote(manifest_item["href"])
            return href
        print(f"nav and opf at different levels")
        np = nav_list[: len(nav_list) - 1]
        nav_path = opf_path + np
        if self.DEBUG:
            lstr = f"nav_path: {nav_path}"
            self.wrlog(False, lstr)
        if len(manifest_list) == 1:
            manifest_path = []
        else:
            manifest_path = manifest_list[: len(manifest_list) - 1]
        if self.DEBUG:
            lstr = f"manifest_path: {manifest_path}"
            self.wrlog(False, lstr)
        nn = opf_path + manifest_path
        if self.DEBUG:
            lstr = f"opf_path+manifest_path: {nn}"
            self.wrlog(False, lstr)
        if nn == nav_path:
            if self.DEBUG:
                lstr = (
                    f"nav file at same level as opf/manifest, "
                    f"remove subdirectories from href."
                )
                self.wrlog(False, lstr)
            href = urllib.parse.quote(manifest_fnm)
        else:
            if self.DEBUG:
                lstr = f"Oops, opf_path: {opf_path}; manifest_path: " f"{manifest_path}"
                self.wrlog(False, lstr)
            href = urllib.parse.quote(manifest_item["href"])
        return href

    def find_opf(self, path):
        """
        Given the path to the unzipped epub file, read the container file and
        return the path to the opf file as a text string.

        **Keyword arguments:**

        **_path_**

        Path to unzipped epub file.

        """
        # TODO
        # Write the comment_epubpager comment to the container file.
        # find the opf file, which contains the version information
        cfile = Path(f"{path}/META-INF/container.xml")
        contain_str = cfile.read_text(encoding="utf-8")
        # contain_str = str(contain_data)
        rloc = contain_str.find("<rootfiles>")
        if rloc == -1:
            estr = "ABORTING: did not find <rootfiles> in container"
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return ""
        contain_str = contain_str[rloc + 3 :]
        rloc = contain_str.find("<rootfile")
        if rloc == -1:
            estr = "ABORTING: did not find <rootfile in container"
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return ""
        contain_str = contain_str[rloc + 3 :]
        rloc = contain_str.find("full-path=")
        if rloc == -1:
            estr = "ABORTING: did not find full-path in container"
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            self.wrlog(False, estr)
            self.wrlog(False, "Convert to ePub3 and try again.")
            return ""
        contain_str = contain_str[rloc + 3 :]
        opflist = contain_str.split('"')
        ofile = f"{self.rdict['unzip_path']}/{opflist[1]}"
        return ofile

    def make_dict(self, item) -> typing.Dict:
        """

        Args:
            item (): string that contains an <item /> from an epub manifest

        items are strings of format:
            <item id="idstring", href="the href of the id", properties="optional properties" />

        This functions turns each left hand side of '=' into a key, and the
        right had side into the value and puts these entries in a dictionary.

        Returns:
            mandict:

        """
        item = item[len("<item ") :]
        mdone = False
        mandict = {}
        while not mdone:
            val = "notfound"
            key = "nokey"
            keyloc = item.find("=")
            if keyloc == -1:
                mdone = True
                continue
            else:
                key = item[:keyloc].strip()
                item = item[keyloc + 2 :]
                q2loc = item.find('"')
                val = item[:q2loc]
                item = item[q2loc + len('"') :]
            mandict[key] = val
            # mdone = True
        return mandict

    def get_manifest(self, man_data):
        """

        Args:
            man_data (): data containing <manifest> through </manifest>

        Returns:
            manifest, a list of dictionaries that are built from each manifest
            entry by make_dict()

        """
        manifest = []
        done = False
        # some documents use opf:manifest instead of manifest
        if man_data.find("<manifest>") != -1:
            man_elmnt = "<manifest>"
        elif man_data.find("<opf:manifest>") != -1:
            man_elmnt = "<opf:manifest>"
        else:
            self.wrlog(
                True, ("Fatal error - did not find manifest element in navigation file")
            )
            self.rdict["pager_error"] = True
            return
        while not done:
            loc = man_data.find(man_elmnt)
            if loc != -1:
                man_data = man_data[loc + len(man_elmnt) :]
                continue
            loc = man_data.find("<item ")  # note 'item ' to avoid matching 'itemref'.
            if loc != -1:
                # get the item to send to make_dict
                man_data = man_data[loc:]
                loc1 = man_data.find("/>")
                if loc1 != -1:
                    item = man_data[:loc1]
                    manifest.append(self.make_dict(item))
                    man_data = man_data[loc1 + len("/>") :]
                    continue
            loc = man_data.find("</manifest>")
            if loc != -1:
                done = True
        return manifest

    def get_spine(self, spine_data):
        """

        Args:
            spine_data (): data from opf file that contains <spine> through </spine>

        Returns:
            splist: a list of the idref entries from the spine

        """
        splist = []
        sdone = False
        while not sdone:
            loc = spine_data.find("<spine>")
            if loc != -1:
                spine_data = spine_data[loc + len("<spine>") :]
                continue
            loc = spine_data.find("<itemref ")
            if loc != -1:
                spine_data = spine_data[loc + len("<itemref") :]
                loc = spine_data.find("idref")
                if loc != -1:
                    spine_data = spine_data[loc + len("idref") :]
                loc = spine_data.find('"')
                if loc != -1:
                    spine_data = spine_data[loc + 1 :]
                loc1 = spine_data.find('"')
                if loc1 != -1:
                    item = spine_data[:loc1]
                    splist.append(item)
                    spine_data = spine_data[loc1 + 1 :]
                    continue
            loc = spine_data.find("</spine>")
            if loc != -1:
                sdone = True
        if len(splist) == 0:
            self.wrlog(False, ("Fatal error - spine length is zero in navigation file"))
            self.rdict["pager_error"] = True
        return splist

    def parse_opf(self, opf_data):
        """

        Args:
            opf_data (): Data read from the opf file
        """

        self.rdict["manifest"] = self.get_manifest(opf_data)
        self.rdict["spine_lst"] = self.get_spine(opf_data)

    def dump_spine(self):
        self.wrlog(False, "spine dict:")
        for item in self.rdict["spine_lst"]:
            for key in item:
                self.wrlog(False, f"  {key}: {item[key]}")

    def dump_manifest(self):
        self.wrlog(False, f"Manifest dict:")
        for item in self.rdict["manifest"]:
            for key in item:
                self.wrlog(False, f"  {key}: {item[key]}")

    def dump_dict(self, name, ld):
        self.wrlog(False, f"{name}:")
        for key in ld.keys():
            self.wrlog(False, f"  {key}: {ld[key]}")

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

        # self.dump_manifest()
        if self.genplist:
            for item in self.rdict["manifest"]:
                if item.get("properties") == "nav":
                    navf = Path(f"{self.rdict['disk_path']}{item['href']}")
                    self.rdict["nav_item"] = item["href"]
                    self.rdict["nav_file"] = navf
            if self.rdict["nav_file"] == "None":
                self.wrlog(False, ("Fatal error - did not find navigation file"))
                self.rdict["pager_error"] = True
                return
            else:
                lstr = f"nav_file found: {self.rdict['nav_file']}"
                self.wrlog(False, lstr)
                # we have a nav file, verify there is no existing page_list
                # element
                if self.genplist:
                    with self.rdict["nav_file"].open("r") as nav_r:
                        nav_data = nav_r.read()
                        lstr = 'epub:type="page-list"'
                        if nav_data.find(lstr) != -1:
                            self.genplist = False
                            self.rdict["has_plist"] = True
                            self.wrlog(
                                True,
                                (
                                    "    ->INFO<- This epub file "
                                    "already has a page-list "
                                    "navigation element."
                                ),
                            )
                            self.wrlog(
                                True,
                                (
                                    "   ->INFO<- page-list navigation "
                                    "was selected but will not "
                                    "be created."
                                ),
                            )
                            if self.match:
                                self.rdict["match"] = True
                                # count the total number of pages in the
                                # nav pagelist
                                pgs = self.get_nav_pagecount()
                                self.rdict["pages"] = pgs
                            else:
                                self.rdict["match"] = False
                        else:
                            # there is no pagelist, unset match
                            self.match = False
                            self.rdict["has_plist"] = False
                            self.rdict["match"] = False
        # we're good to go
        spine_lst = []
        # for spine_item in opf_dict[opf_dictkey]["spine"]["itemref"]:  # type: ignore
        for spine_item in self.rdict["spine_lst"]:
            if self.DEBUG:
                lstr = f"spine_item idref: {spine_item['idref']}"
                self.wrlog(False, lstr)
            # sometimes the manifest is opf:manifest, check this
            # this only happens if we have an epub2 and didn't convert to epub3
            # THIS MUST BE FIXED IN parse_opf
            # if opf_dict[opf_dictkey].get("manifest", "fucked") != "fucked":  # type: ignore
            #     manifest_key = "manifest"
            # elif opf_dict[opf_dictkey].get("opf:manifest", "epub2") != "epub2":  # type: ignore
            #     manifest_key = "opf:manifest"
            # else:
            #     self.wrlog(False, f"Fatal Error: Cannot find manifest in opf file")
            #     self.rdict["pager_error"] = True
            #     return
            for m_item in self.rdict["manifest"]:
                if spine_item == m_item["id"]:
                    # we don't care about any properties keys except for 'nav'
                    # if "properties" in m_item.keys():
                    #     if m_item["properties"] == "svg":
                    #         self.wrlog(
                    #             True,
                    #             f"dropping m_item: {m_item}; spine_item: {spine_item}",
                    #         )
                    #         continue
                    # elif (
                    if (
                        "toc" in m_item["href"].casefold()
                        or "contents" in m_item["href"].casefold()
                    ):
                        self.wrlog(
                            True,
                            (f"Skipping file " f"{m_item['href']} " f"because TOC."),
                        )
                    else:
                        fdict = {}
                        uqdfile = urllib.parse.unquote(m_item["href"])
                        fdict["disk_file"] = f"{self.rdict['disk_path']}{uqdfile}"
                        # take care of books structured with opf file and
                        # nav file at different directory levels
                        if self.genplist:
                            fdict["href"] = self.bld_href(m_item)
                        else:
                            fdict["href"] = ""
                        spine_lst.append(fdict)
        self.rdict["spine_lst"] = spine_lst
        return ()  # scan_spine

    def process_html(self, ebdata):
        """
        ebdata[0] == '<'. Grab, identify, and handle the html element.


        Returns:

        d = {
            'done': Boolean -- we found </body>, we are done
            'idx':  Int     -- location to begin the next scan
            'el':   string  -- the html_element found
        }
        """

        stat = {}
        stat["done"] = False
        stat["idx"] = 0
        stat["el"] = ""
        endel = [" ", ">"]
        loc = ebdata.find(">")
        stat["idx"] = loc + 1
        stat["el"] = ebdata[: loc + 1]
        # self.wrlog(False, f"html element: {stat['el']}")
        eltype = ""
        idx = 1
        while stat["el"][idx] not in endel:
            eltype += stat["el"][idx]
            idx += 1
        if eltype[0] == "<":
            eltype = eltype[1:]
        # self.wrlog(False, f"eltype: {eltype}")
        if eltype == "/body":
            # self.wrlog(False, f"done: html element: {stat['el']}")
            stat["done"] = True
        elif eltype == "!--":  # skip comments
            self.wrlog(False, "skipping comments")
            loc = ebdata.find("-->")
            stat["el"] += ebdata[: loc + 3]
            stat["idx"] = loc + 3
        elif eltype == "nav":
            self.wrlog(False, "skipping nav")
            loc = ebdata.find("/nav")
            stat["el"] += ebdata[: loc + 5]
            # self.wrlog(False, f"html element: {stat['el']}")
            stat["idx"] = loc + 5
        return stat

    def count_words(self):
        """
        Scan book contents and count words

        This is an informational scan only, data is gathered, but no
        changes are made
        """

        wdcnt = 0
        for chapter in self.rdict["spine_lst"]:
            pstr = f"{chapter['disk_file']}"
            pstr = pstr.replace(r"amp;", "")
            efile = Path(pstr)
            ebook_data = efile.read_text(encoding="utf-8")
            body1 = ebook_data.find("<body")
            if body1 == -1:
                self.rdict["error_lst"].append(
                    f"Fatal error: No <body> found. " f"File: {chapter['disk_file']}"
                )
                self.rdict["pager_error"] = True
                return 0
            else:
                ebook_data = ebook_data[body1:]
                stat = self.process_html(ebook_data)
                ebook_data = ebook_data[stat["idx"] :]
            done = False
            while not done:
                lidx = 0
                while ebook_data[lidx] in ["\n", " ", "\t"]:
                    lidx += 1
                ebook_data = ebook_data[lidx:]
                if ebook_data[0] == "<":
                    stat = self.process_html(ebook_data)
                    if stat["done"]:
                        done = True
                    else:
                        ebook_data = ebook_data[stat["idx"] :]
                else:
                    loc = ebook_data.find("<")
                    wdcnt += len(ebook_data[:loc].split())
                    ebook_data = ebook_data[loc:]
        self.wrlog(False, f"count_words result: {wdcnt}")
        self.rdict["words"] = wdcnt
        if self.rdict["has_plist"] and self.rdict["match"]:
            wc = int(self.rdict["words"] / self.rdict["pages"])
            self.rdict["pgwords"] = wc
        else:
            self.rdict["pgwords"] = self.pgwords
        return

    def chk_xmlns(self, ebook_data):
        """
        Verify that ebook_data has proper xmlns:epub statement. If not,
        insert it.

        **Keyword arguments:**
        ebook_data - complete data from an xhtml file.
        """
        # find the html element and grab it
        l1 = ebook_data.find("<html")
        if l1 == -1:
            estr = f"Fatal Error: searching for xmlns, but did not find <html."
            self.wrlog(True,estr)
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            return
        else:
            l2 = ebook_data[l1:].find(">")
            if l2 == -1:
                estr = f"Fatal Error: searching for xmlns, but did not find <html end."
                self.wrlog(True,estr)
                self.rdict["error_lst"].append(estr)
                self.rdict["pager_error"] = True
                return
            else:
                html_el = ebook_data[l1:l1+l2]
                self.wrlog(False,f"<html element: {html_el}")
                # these are valid xmlns items, be sure we have one
                if html_el.find("xmlns:epub") != -1:
                    self.wrlog(False,"xmlns was found.")
                    return ebook_data
                elif html_el.find("http://www.idpf.org/2007/ops") != -1:
                    self.wrlog(False,"xmlns was found.")
                    return ebook_data
                # otherwise, add it
                else:
                    self.wrlog(False, f"Adding xmlns:epub namespace.")
                    loc = ebook_data.find("<html")
                    newbk = ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    loc2 = ebook_data.find(">")
                    newbk += ebook_data[:loc2]
                    newbk += " "
                    newbk += epubns
                    newbk += ebook_data[loc2:]
                    return newbk

    def scan_sections(self):
        """
        Scan book contents, book pages, and section pages.

        This is an informational scan only, data is gathered, but no
        changes are made

        **Keyword arguments:**

        """

        page_words = 0
        book_curpg = 1
        # scan until we find '<body' and just copy all the header stuff.
        for chapter in self.rdict["spine_lst"]:
            sct_pgcnt = 0
            pstr = f"{chapter['disk_file']}"
            pstr = pstr.replace(r"amp;", "")
            # print(f"pstr: {pstr}")
            efile = Path(pstr)
            # efile = Path((f"{chapter['disk_file']}"))
            ebook_data = efile.read_text(encoding="utf-8")
            # with efile.open("r") as ebook_rfile:
            #     ebook_data = ebook_rfile.read()
            if self.rdict["match"]:
                lstr = 'epub:type="pagebreak"'
                ep_typcnt = ebook_data.count(lstr)
                # in case this is an aria file
                lstr = 'role="doc-pagebreak"'
                aria_typcnt = ebook_data.count(lstr)
                if aria_typcnt:
                    # book_curpg += aria_typcnt
                    chapter["sct_pgcnt"] = aria_typcnt
                else:
                    # book_curpg += ep_typcnt
                    chapter["sct_pgcnt"] = ep_typcnt
            # we always do this loop to count words.  But if we are matching
            # pages, do not change chapter nor book_curpg
            body1 = ebook_data.find("<body")
            if body1 == -1:
                self.rdict["error_lst"].append(
                    f"Fatal error: No <body> found. " f"File: {chapter['disk_file']}"
                )
                self.rdict["pager_error"] = True
                return 0
            else:
                ebook_data = ebook_data[body1:]
                stat = self.process_html(ebook_data)
                ebook_data = ebook_data[stat["idx"] :]
            done = False
            while not done:
                # self.wrlog(False, f"1 process {ebook_data[:80]}")
                # copy returns and tabs and spaces
                lidx = 0
                while ebook_data[lidx] in ["\n", " ", "\t"]:
                    lidx += 1
                ebook_data = ebook_data[lidx:]
                # self.wrlog(False, f"1+ process {ebook_data[:80]}")
                stat = self.process_html(ebook_data)
                if stat["done"]:
                    # estr = f"writing last: {ebook_data[stat['idx']:]}"
                    # self.wrlog(False, estr)
                    done = True
                else:
                    ebook_data = ebook_data[stat["idx"] :]
                # if len(ebook_data) == 0:
                # self.wrlog(False, (f"File: {chapter['disk_file']} is"
                #                       f"finished, but no /body found?"))
                if ebook_data[0] == "<":
                    continue
                else:
                    loc = ebook_data.find("<")
                    page_words += len(ebook_data[:loc].split())
                    # self.wrlog(False, f"loc: {loc}; {ebook_data[:80]}")
                    ebook_data = ebook_data[loc:]
                    # self.wrlog(False, f"loc: {loc}; {ebook_data[:80]}")
                    if self.rdict["pgwords"] and not self.rdict["match"]:
                        if page_words > self.rdict["pgwords"]:
                            if not self.rdict["match"]:
                                sct_pgcnt += 1
                                book_curpg += 1
                            page_words = page_words - self.pgwords
            if not self.rdict["match"] and self.DEBUG:
                lstr = f"Section page count is: {sct_pgcnt}"
                self.wrlog(False, lstr)
            # store the section pagecount in the dictionary.
            if not self.rdict["match"]:
                chapter["sct_pgcnt"] = sct_pgcnt
        if self.rdict["pgwords"] and not self.rdict["match"]:
            self.rdict["pages"] = book_curpg
        return

    def scan_file(self, ebook_data, chapter):
        """
        Scan a section file and place page-links, page pagelines,
        superscripts as appropriate.

        This function is very similar to scan_section, but this one adds
        the pagelinks and page pagelines.

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
        pgbook = ""
        sct_pg = 1
        pl_lst = []
        # scan until we find '<body' and just copy all the header stuff.
        # we only scan for <body since calibre conversion makes the body
        # element '<body class=calibre>
        body1 = ebook_data.find("<body")
        if body1 == -1:
            pgbook += ebook_data
            estr = f"Fatal error: No <body> found in {chapter['disk_file']}"
            self.rdict["error_lst"].append(estr)
            self.rdict["pager_error"] = True
            return pgbook
        else:
            pgbook += ebook_data[:body1]
            ebook_data = ebook_data[body1:]
        done = False
        while not done:
            # If we find an html element, just copy it and don't count
            # words
            if ebook_data[0] == "<":
                stat = self.process_html(ebook_data[idx:])
                if stat["done"]:
                    # self.wrlog(False,(f"writing last: "
                    #                 f"{ebook_data[stat['idx']:]}"))
                    pgbook += ebook_data[: stat["idx"]]
                    pgbook += ebook_data[stat["idx"] :]
                    done = True
                else:
                    pgbook += ebook_data[: stat["idx"]]
                    ebook_data = ebook_data[stat["idx"] :]
                    insfoot = stat["el"] == "</p>" or stat["el"] == "</div>"
                    if insfoot and pl_lst:
                        for pl in pl_lst:
                            pgbook += pl
                            self.wrlog(
                                False, f"Inserting pageline: {pl} in {chapter['href']}"
                            )
                        pl_lst = []
            else:
                # we are at the beginning of a text string, just past
                # the <p>
                loc = ebook_data.find("<")
                wdcnt = len(ebook_data[:loc].split())
                # new need calculation
                need = self.pgwords - self.pg_wcnt
                self.pg_wcnt += wdcnt
                
                if self.pg_wcnt >= self.pgwords:
                    # self.wrlog(False, f"need {need} words and we crossed page {self.curpg} with {wdcnt} words added.")
                    # self.wrlog(
                    #     False,
                    #     (f"Pageline {self.curpg} covers {self.pg_wcnt} words."),
                    # )
                    # build and stage a pageline because we are at a page
                    # boundary
                    if self.pageline:
                        pl_lst.append(
                            self.bld_foot(self.curpg, sct_pg, chapter["sct_pgcnt"])
                        )
                    # need == -1 means page ends just before this
                    # paragraph, put the pagelist entry here. Also,
                    # place it here if need is less than 10--or about
                    # one line.
                    if need < 10:
                        # self.wrlog(False, f"Placing plist beginning")
                        if self.genplist:
                            pstr = (
                                f'<span epub:type="pagebreak" '
                                f'id="{pglnk}{self.curpg}" '
                                f' role="doc-pagebreak" '
                                f'title="{self.curpg}"/>'
                            )
                            pgbook += pstr
                            self.add_plist_target(self.curpg, chapter["href"])
                        # and insert the superscripted page number
                        if self.superscript:
                            pgbook += self.new_super(
                                self.curpg, sct_pg, chapter["sct_pgcnt"]
                            )
                        pgbook += ebook_data[:loc]
                        ebook_data = ebook_data[loc:]
                    else:
                        # now count words and put in pgbook until we get to
                        # our next page locaton--this is need words.
                        lidx = 0
                        words = 0
                        while lidx < loc:
                            # self.wrlog(False, f"lidx: {lidx}.")
                            if ebook_data[lidx] == " ":
                                words += 1
                            if words == need:
                                # estr = f"Insert page link at {self.pg_wcnt - wdcnt + words}"
                                # self.wrlog(False, estr)
                                if self.genplist:
                                    pstr = (
                                        f'<span epub:type="pagebreak" '
                                        f'id="{pglnk}{self.curpg}" '
                                        f' role="doc-pagebreak" '
                                        f'title="{self.curpg}"/>'
                                    )
                                    pgbook += pstr
                                    self.add_plist_target(self.curpg, chapter["href"])
                                # and insert the superscripted page number
                                if self.superscript:
                                    pgbook += self.new_super(
                                        self.curpg,
                                        sct_pg,
                                        chapter["sct_pgcnt"],
                                    )
                                pgbook += ebook_data[lidx:loc]
                                lidx = loc
                            else:
                                pgbook += ebook_data[lidx]
                                lidx += 1
                        ebook_data = ebook_data[loc:]
                    sct_pg += 1
                    self.curpg += 1
                    self.pg_wcnt = self.pg_wcnt - self.pgwords
                    # self.wrlog(False, f"Page {self.curpg} starts with {self.pg_wcnt} words.")
                else:
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
        return pgbook  

    def scan_match_file(self, ebook_data, chapter):
        """
        Called when the ebook already has page links and we are told to
        insert pagelines/superscripts matching existing paging.

        Scan a section file and place page pagelines, superscripts based
        on existing pagebreaks.

        **Keyword arguments:**

        **_ebook_data_**

        The data read from the section file.

        **_chapter_**

        Dict with href for pagelinks; section pages.

        """

        pgbook = ""
        sct_pg = 1
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
                spanst = ebook_data[:plink_loc].rfind("<span")
                pgbook += ebook_data[:spanst]
                ebook_data = ebook_data[spanst:]
                # Find the page number. Could be title or aria-label or id
                loctitle = ebook_data.find("title=")
                loclabel = ebook_data.find("aria-label=")
                locid = ebook_data.find("id=")
                if loctitle == -1 and loclabel == -1 and locid == -1:
                    estr = (
                        f"Error: {chapter['disk_file']}: "
                        f"Did not find title or aria-label or id "
                        f"for pagebreak"
                    )
                    self.wrlog(False, estr)
                    self.rdict["warn_lst"].append(estr)
                    self.rdict["pager_warn"] = True
                    pgbook += ebook_data
                    not_done = False
                else:
                    loc = 0  # only here to reassure linter
                    if loctitle != -1:
                        loc = loctitle
                        loc += len("title=")
                    elif loclabel != -1:
                        loc = loclabel
                        loc += len("aria-title")
                    elif locid != -1:
                        loc = locid
                        loc += len("id")
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    qlist = ebook_data.split('"')
                    thispage = qlist[1]
                    if locid != -1:
                        newpage = ""
                        for c in thispage:
                            if c.isdigit():
                                newpage += c
                        if newpage:
                            thispage = newpage
                    # now find the end of this element '/'
                    loc = ebook_data.find("/")
                    loc += 1
                    if ebook_data[loc] == ">":
                        # if next char is a >, found it
                        loc += 1
                    else:
                        # otherwise must find 'span>'
                        if ebook_data.find("span>") == -1:
                            estr = (
                                f"Error: {chapter['disk_file']}: "
                                f"In match mode did not find "
                                f"closing span for pagebreak"
                            )
                            self.wrlog(False, estr)
                            self.rdict["warn_lst"].append(estr)
                            self.rdict["pager_warn"] = True
                        else:
                            loc += len("span>")
                    pgbook += ebook_data[:loc]
                    ebook_data = ebook_data[loc:]
                    # insert superscript here
                    if self.superscript:
                        sstr = self.new_super(thispage, sct_pg, chapter["sct_pgcnt"])
                        pgbook += sstr
                    # scan for next paragraph start or end and insert pageline.
                    # Could miss a page if a paragraph contains two page links
                    loc = ebook_data.find("</p>")
                    if loc == -1:
                        lstr = (
                            f"Warning: {chapter['disk_file']}: Did not find </p> for"
                            f" matched pageline."
                        )
                        self.wrlog(False, lstr)
                        self.rdict["warn_lst"].append(lstr)
                        lstr = f"--> thispage: {thispage}; " f"sct_pg: {sct_pg}"
                        self.wrlog(False, lstr)
                        self.rdict["warn_lst"].append(lstr)
                        self.rdict["pager_warn"] = True
                    else:
                        loc += 4
                        pgbook += ebook_data[:loc]
                        ebook_data = ebook_data[loc:]
                        if self.pageline:
                            pgbook += self.bld_foot(
                                thispage, sct_pg, chapter["sct_pgcnt"]
                            )
                    sct_pg += 1
        return pgbook

    def run_chk_external(self, original):
        t1 = time.perf_counter()
        self.wrlog(False, "---------------------------")
        if original:
            self.wrlog(True, "Running external epubcheck on original epub file:")
            epubcheck_cmd = [self.epubcheck, self.epub_file]
        else:
            self.wrlog(True, "Running external epubcheck on paged epub file:")
            epubcheck_cmd = [self.epubcheck, self.rdict["bk_outfile"]]
        result = run(epubcheck_cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        # check and log the errors from epubcheck
        err = False
        for line in result.stdout.splitlines():
            # with -e ignoring warnings
            # Messages: 0 fatals / 0 errors
            # 0         1 2      3 4
            if line.find("Messages:") != -1:
                w = line.split(" ")
                if original:
                    self.rdict["orig_fatal"] = int(w[1])
                    self.rdict["orig_error"] = int(w[4])
                    # self.rdict['orig_warn'] = int(w[7])
                    if self.rdict["orig_fatal"]:
                        err = True
                        self.wrlog(
                            True,
                            (
                                f"--> {self.rdict['orig_fatal']} fatal "
                                f"errors reported in epubcheck."
                            ),
                        )
                    if self.rdict["orig_error"]:
                        err = True
                        self.wrlog(
                            True,
                            (
                                f"--> {self.rdict['orig_error']} "
                                f"errors reported in epubcheck."
                            ),
                        )
                else:
                    self.rdict["echk_fatal"] = int(w[1])
                    self.rdict["echk_error"] = int(w[4])
                    if self.rdict["echk_fatal"]:
                        err = True
                        self.wrlog(
                            True,
                            (
                                f"--> {self.rdict['echk_fatal']} fatal "
                                f"errors reported in epubcheck."
                            ),
                        )
                    if self.rdict["echk_error"]:
                        err = True
                        self.wrlog(
                            True,
                            (
                                f"--> {self.rdict['echk_error']} "
                                f"errors reported in epubcheck."
                            ),
                        )
        self.wrlog(False, result.stdout)
        if len(result.stderr) > 0:
            self.wrlog(False, result.stderr)
        t2 = time.perf_counter()
        et = t2 - t1
        self.wrlog(True, f"    epubcheck took {et:.2f} seconds.")
        if err:
            self.wrlog(True, f"    Errors were reported")
        else:
            self.wrlog(True, f"    No errors were reported")
        if original:
            self.rdict["epubchkorig_time"] = et
        else:
            self.rdict["epubchkpage_time"] = et
        return

    def run_chk_python(self, original):
        self.wrlog(
            True, f"Running python module epubcheck--this will take a while . . ."
        )
        t1 = time.perf_counter()
        self.wrlog(False, CR + "---------------------------")
        if original:
            echk_result = EpubCheck(self.epub_file)
            self.rdict["orig_fatal"] = echk_result.result_data["checker"]["nFatal"]  # type: ignore
            self.rdict["orig_error"] = echk_result.result_data["checker"]["nError"]  # type: ignore
            self.rdict["orig_warn"] = echk_result.result_data["checker"]["nWarning"]  # type: ignore
            self.rdict["epubchkorig_time"] = (
                echk_result.result_data["checker"]["elapsedTime"] / 1000.0  # type: ignore
            )
            if echk_result.valid:
                self.wrlog(
                    True,
                    f"For {echk_result.result_data['checker']['path']} epubcheck reports no errors.",  # type: ignore
                )
            else:
                self.wrlog(
                    True,
                    f"For {echk_result.result_data['checker']['path']} epubcheck reported errors.",  # type: ignore
                )
            for errdict in echk_result.result_data["messages"]:  # type: ignore
                if errdict["severity"] == "ERROR" or errdict["severity"] == "FATAL":
                    self.wrlog(False, f"{errdict['message']}")
                    for loc in errdict["locations"]:
                        self.wrlog(
                            True,
                            f"   File: {loc['path']}; line: {loc['line']}; column: {loc['column']}",
                        )
        else:
            echk_result = EpubCheck(self.rdict["bk_outfile"])
            self.rdict["echk_fatal"] = echk_result.result_data["checker"]["nFatal"]  # type: ignore
            self.rdict["echk_error"] = echk_result.result_data["checker"]["nError"]  # type: ignore
            self.rdict["epubchkpage_time"] = (
                echk_result.result_data["checker"]["elapsedTime"] / 1000.0  # type: ignore
            )
            if echk_result.valid:
                self.wrlog(
                    True,
                    f"For {echk_result.result_data['checker']['path']} epubcheck reports no errors.",  # type: ignore
                )
            else:
                self.wrlog(
                    True,
                    f"For {echk_result.result_data['checker']['path']} epubcheck reported errors.",  # type: ignore
                )
            for errdict in echk_result.result_data["messages"]:  # type: ignore
                if errdict["severity"] == "ERROR" or errdict["severity"] == "FATAL":
                    self.wrlog(False, f"{errdict['message']}")
                    for loc in errdict["locations"]:
                        self.wrlog(
                            False,
                            f"   File: {loc['path']}; line: {loc['line']}; column: {loc['column']}",
                        )
        t2 = time.perf_counter()
        et = t2 - t1
        self.wrlog(True, f"    epubcheck took {et:.2f} seconds.")
        if original:
            self.rdict["epubchkorig_time"] = et
        else:
            self.rdict["epubchkpage_time"] = et
        return

    def run_chk(self, original):
        """
        Run epubcheck on the epub source file. Copy results to log file.
        Save error counts to global rdict.

        There are two options, an external version of epubcheck, which usually
        runs in 2-5 seconds, and the epubcheck python module, which takes about
        5x longer to run. If the external epubcheck is available
        (self.epubcheck != "none", then run it, otherwise see if the module is
        available and run it.

        **Instance Variables**

        **_original_** -- Original file or paged output file to be
        checked
        """
        if Path(self.epubcheck).is_file():
            self.wrlog(False, f"Running external epubcheck.")
            self.run_chk_external(original)
        else:
            if has_echk:
                self.wrlog(False, f"Running python module epubcheck.")
                self.run_chk_python(original)
            else:
                self.wrlog(False, f" --> No epubcheck is available.")
                return

    def paginate_epub(self, source_epub) -> typing.Dict:

        """
        **paginate_epub**

        Unzip *source_epub*.

        Verify ePub version, navigation capable, navigation exists.

        Generate list of files to scan and their order.

        Scan each file and add page links and page pagelines as requested.

        Build a page-list element while scanning.

        Update the navigation file with the page-list element.

        Save the modified files a a paginated ePub.

        **Keyword arguments:**

        **_source_epub_** -- The original ePub file to modify.

        """

        t1pagination = time.perf_counter()
        # re-initialize on each call
        self.curpg = 1
        self.tot_wcnt = 0
        self.pg_wcnt = 0
        self.plist = ""
        self.bk_flist = []

        # rdict definition 
        self.rdict["logfile"] = ""  # logfile Path
        self.rdict["bk_outfile"] = ""  # outfile Path
        self.rdict["unzip_path"] = ""  # unzipped epub Path
        self.rdict["disk_path"] = ""  # disk path to unzips
        self.rdict["title"] = ""
        self.rdict["nav_file"] = "None"  # nav file Path
        self.rdict["nav_item"] = "None"
        self.rdict["opf_file"] = "None"  # opf Path
        self.rdict["has_plist"] = False
        self.rdict["spine_lst"] = []
        self.rdict["words"] = 0
        self.rdict["match"] = False
        self.rdict["pgwords"] = 0  # words/page
        self.rdict["pages"] = 0  # pages
        self.rdict["epub_version"] = "no_version"
        self.rdict["converted"] = False  # if True, converted from epub2
        self.rdict["error_lst"] = []  # list of errors that occurred
        self.rdict["warn_lst"] = []  # list of warnings that occurred
        self.rdict["pager_error"] = False  # Was there a fatal error?
        self.rdict["pager_warn"] = False  # epub_pager warning
        self.rdict["orig_fatal"] = 0  # epubcheck fatal error original file
        self.rdict["orig_error"] = 0  # epubcheck error original file
        self.rdict["orig_warn"] = 0  # epubcheck warning original file
        self.rdict["echk_fatal"] = 0  # epubcheck fatal error
        self.rdict["echk_error"] = 0  # epubcheck error
        self.rdict["convert_time"] = 0  # time to convert from epub2 to epub3
        self.rdict["paginate_time"] = 0  # time to paginate the epub
        self.rdict["epubchkpage_time"] = 0  # time to run epubcheck on paged epub
        self.rdict["epubchkorig_time"] = 0  # time to run epubcheck on original epub
        self.rdict["messages"] = ""  # list of messages generated.
        

        # initialize logfile
        # The epub name is the book file name with spaces removed and '.epub'
        # removed.
        if not Path(source_epub).is_file():
            self.wrlog(True, "Fatal error: Source epub not found.")
            self.rdict["error_lst"].append("Fatal error: Source epub not found.")
            self.rdict["pager_error"] = True
            return self.rdict

        if not Path(self.outdir).is_dir:
            self.wrlog(True,f"Fatal error: output directory does not exist: {self.outdir}")
            self.rdict["error_lst"].append("Fatal error: output directory not found.")
            self.rdict["pager_error"] = True
            return self.rdict

        dirsplit = source_epub.split("/")
        stem_name = dirsplit[len(dirsplit) - 1].replace(" ", "")
        self.rdict["title"] = stem_name.replace(".epub", "")
        self.logpath = Path(f"{self.outdir}/{self.rdict['title']}.log")
        self.rdict["logfile"] = self.logpath
        with self.logpath.open("w") as logfile:
            logfile.write("" + "\n")

        self.wrlog(False, echk_message)

        # copy the source epub file to stem_name
        self.epub_file = f"{self.outdir}/{self.rdict['title']}_orig.epub"
        shutil.copyfile(source_epub,self.epub_file)
        self.wrlog(True,f"Operating on epub file: {self.epub_file}")
        if self.epubcheck.casefold() != "none" and (self.chk_orig or self.chk_paged):
            self.wrlog(False, f"External epubcheck will be run.")
        elif has_echk and (self.chk_orig or self.chk_paged):
            self.wrlog(False, f"Python epubcheck module will be run.")
        else:
            self.wrlog(False, f"No epubcheck is available.")
        self.wrlog(False, "---------------------------")
        self.wrlog(False, f"epub_paginator version {self.get_version()}")
        self.wrlog(False, f"Paginating {dirsplit[len(dirsplit)-1]}")
        # dump configuration
        self.wrlog(False, f"Configuration:")
        self.wrlog(False, f"  outdir: {self.outdir}")
        self.wrlog(False, f"  match: {self.match}")
        self.wrlog(False, f"  genplist: {self.genplist}")
        self.wrlog(False, f"  pgwords: {self.pgwords}")
        self.wrlog(False, f"  pages: {self.pages}")
        self.wrlog(False, f"  pageline: {self.pageline}")
        self.wrlog(False, f"  pl_align: {self.pl_align}")
        self.wrlog(False, f"  pl_color: {self.pl_color}")
        self.wrlog(False, f"  pl_bkt: {self.pl_bkt}")
        self.wrlog(False, f"  pl_fntsz: {self.pl_fntsz}")
        self.wrlog(False, f"  pl_pgtot: {self.pl_pgtot}")
        self.wrlog(False, f"  superscript: {self.superscript}")
        self.wrlog(False, f"  super_color: {self.super_color}")
        self.wrlog(False, f"  super_fntsz: {self.super_fntsz}")
        self.wrlog(False, f"  super_total: {self.super_total}")
        self.wrlog(False, f"  chap_pgtot: {self.chap_pgtot}")
        self.wrlog(False, f"  chap_bkt: {self.chap_bkt}")
        self.wrlog(False, f"  ebookconvert: {self.ebookconvert}")
        self.wrlog(False, f"  epubcheck: {self.epubcheck}")
        self.wrlog(False, f"  chk_orig: {self.chk_orig}")
        self.wrlog(False, f"  chk_paged: {self.chk_paged}")
        self.wrlog(False, f"  DEBUG: {self.DEBUG}")
        self.wrlog(False, "\n")

        self.rdict["bk_outfile"] = Path(
            f"{self.outdir}/{self.rdict['title']}_paged.epub"
        )
        self.rdict["unzip_path"] = Path(f"{self.outdir}/{self.rdict['title']}")
        # this gets epub version without unzipping
        epub_ver = self.get_epub_version(self.epub_file)
        self.wrlog(True, f"Original file is epub version {epub_ver}")
        if epub_ver[0] != "3":
            if Path(self.ebookconvert).is_file():
                self.convert_epub()
                if self.rdict["pager_error"]:
                    return self.rdict
                # we have an epub 3
                self.plist = pg_xmlns
            else:
                lstr = (
                    "    --> WARNING <-- Epub version is not 3 or newer,"
                    "page-link navigation disabled."
                )
                self.wrlog(True, lstr)
                lstr = (
                    "    --> WARNING <-- To enable page-link "
                    "navigation, convert to Epub3 and try again."
                )
                self.wrlog(True, lstr)
                self.genplist = False
                self.match = False
                self.rdict["has_plist"] = False
        else:
            self.plist = pg_xmlns
        # at this point, we should have a converted file, or an epub2 because no conversion.
        self.ePubUnZip(self.epub_file, self.rdict["unzip_path"])
        self.rdict[
            "epub_version"
        ] = self.simple_epub_version()  # this epub_version uses disk files
        if self.rdict["pager_error"]:
            return self.rdict
        self.initialize()
        if self.rdict["pager_error"]:
            self.wrlog(False, "Fatal error from initialize().")
            return self.rdict
        # run epubcheck on the file to be paged if requested
        if self.chk_orig:
            self.run_chk(True)
        # figure out where everything is and the order they are in.
        self.scan_spine(self.rdict["unzip_path"])
        # if we have a plist and aren't generating pagelines or superscripts, there is nothing to do.
        if self.rdict['has_plist'] and not self.pageline and not self.superscript:
            estr = "This book has an existing pagelist and neither pagelines nor superscripts were requested."
            self.wrlog(True, f"{estr}")
            self.wrlog(True, f"There is nothing to do.")
            self.rdict["warn_lst"].append(estr)
            self.rdict["pager_warn"] = True
            return(self.rdict)
        if self.rdict["pager_error"]:
            self.wrlog(False, "Fatal error.")
            return self.rdict
        # scan the book to count words, section pages and total pages based on
        # words/page
        self.count_words()
        self.wrlog(False, f"Begin section scan.")
        self.scan_sections()
        # report what we are doing
        if self.rdict["has_plist"] and self.rdict["match"]:
            self.wrlog(False, f"Matching existing pagination.")
            self.wrlog(
                False,
                (f"Approximately {self.rdict['pgwords']}" f" words per page."),
            )
        elif self.genplist:
            if self.pgwords == 0 and self.pages == 0:
                self.wrlog(False, "Fatal error:")
                self.wrlog(False, f"match: {self.rdict['match']}")
                self.wrlog(False, f"pgwords: {self.pgwords}")
                self.wrlog(False, f"pages: {self.pages}")
                self.wrlog(False, f"cannot determine how to paginate.")
                self.rdict["pager_error"] = True
                return self.rdict
            elif self.pgwords:
                self.wrlog(
                    True,
                    (
                        f"Generating pagelist with "
                        f"{self.rdict['pgwords']} words per page."
                    ),
                )
            else:
                self.pgwords = int(self.rdict["words"] / self.pages)
                self.wrlog(
                    True,
                    (
                        f"Generating pagelist with calculated"
                        f" {self.rdict['pgwords']} words per page."
                    ),
                )
        else:
            if not self.pageline and not self.superscript:
                self.wrlog(True,f"No pagination was selected.")
                self.wrlog(True,f"Pages: {self.rdict['pages']}")
                self.wrlog(True,f"Words: {self.rdict['words']:,d}")
            else:
                if self.pageline:
                    self.wrlog(
                        True,
                        (
                            f"Generating page pageline with "
                            f"{self.rdict['pgwords']} words per page."
                        ),
                    )
                if self.superscript:
                    self.wrlog(
                        True,
                        (
                            f"Generating page superscripts with "
                            f"{self.rdict['pgwords']} words per page."
                        ),
                    )
        if self.genplist or self.pageline or self.superscript:
            # this is the working loop. Scan each file, locate pages and insert
            # page-links and/or pagelines or superscripts
            self.curpg = 1
            self.wrlog(False, "Begin pagination, scanning spine.")
            for chapter in self.rdict["spine_lst"]:
                if self.DEBUG:
                    lstr = f"file: {chapter['disk_file']}"
                    self.wrlog(False, lstr)
                # this stupid fix is required by Hunter's Moon which puts '&amp;' in file names.
                pstr = f"{chapter['disk_file']}"
                pstr = pstr.replace(r"amp;", "")
                erfile = Path(pstr)
                ebook_data = erfile.read_text(encoding="utf-8")
                # with erfile.open("r") as ebook_rfile:
                #     ebook_data = ebook_rfile.read()
                # ewfile = Path(f"{chapter['disk_file']}")
                ewfile = Path(pstr)
                # with ewfile.open("w") as ebook_wfile:
                start_total = self.tot_wcnt
                lstr = f"Scanning {chapter['disk_file']}"
                self.wrlog(False, lstr)
                if self.rdict["match"]:
                    if self.DEBUG:
                        lstr = f"file: " f"{chapter['disk_file']}"
                        self.wrlog(False, lstr)
                    new_ebook = self.scan_match_file(ebook_data, chapter)
                else:
                    new_ebook = self.scan_file(ebook_data, chapter)
                xebook_data = self.chk_xmlns(new_ebook)
                if self.rdict["pager_error"]:
                    return self.rdict
                # ebook_wfile.write(xebook_data)
                ewfile.write_text(xebook_data, "utf-8")
            if self.rdict["pager_error"]:
                return self.rdict
            if self.rdict["match"]:
                w_per_page = self.rdict["words"] / self.rdict["pages"]
                lstr = (
                    f"    {self.rdict['words']:,} words; "
                    f"    {self.rdict['pages']:,} pages; "
                    f"    {int(w_per_page)} words per page"
                )
                self.wrlog(False, lstr)
            else:
                self.wrlog(
                    True,
                    (
                        f"    {self.rdict['words']:,} words;"
                        f"    {self.rdict['pages']:,} pages"
                    ),
                )
            # modify the nav_file to add the pagelist
            if self.genplist:
                self.plist += "  </ol></nav>" + CR
                self.update_navfile()
            self.update_opffile()

            # build the epub file
            # self.wrlog(
            #     True,
            #     f"ready to zip: {self.rdict['bk_outfile']}, with {self.rdict['unzip_path']}",
            # )
            self.ePubZip(
                self.rdict["bk_outfile"],
                self.rdict["unzip_path"],
                self.bk_flist,
            )
            t2pagination = time.perf_counter()
            if self.chk_paged:
                self.run_chk(False)
            self.wrlog(True, f"The paged epub is at: {self.rdict['bk_outfile']}" + CR)
            self.rdict["paginate_time"] = (
                (t2pagination - t1pagination)
                - self.rdict["epubchkorig_time"]
                - self.rdict["convert_time"]
            )
            ttime = (
                self.rdict["paginate_time"]
                + self.rdict["epubchkorig_time"]
                + self.rdict["convert_time"]
                + self.rdict["epubchkpage_time"]
            )
            self.wrlog(True, f"Total processing time was {ttime:.2f} seconds")
            if self.rdict["converted"]:
                self.wrlog(
                    True,
                    f"    epub conversion took {self.rdict['convert_time']:.2f} seconds.",
                )
            if self.rdict["epubchkorig_time"] > 0:
                self.wrlog(
                    True,
                    f"    epubcheck original took {self.rdict['epubchkorig_time']:.2f} seconds.",
                )
            if self.rdict["epubchkpage_time"] > 0:
                self.wrlog(
                    True,
                    f"    epubcheck paged took {self.rdict['epubchkpage_time']:.2f} seconds.",
                )
            self.wrlog(
                True,
                f"    Pagination took {self.rdict['paginate_time']:.2f} seconds.",
            )  # end of pagination, only done if requested.
        else:
            self.wrlog(True, f"No pagination was selected.")
        # and if DEBUG is not set, we remove the unzipped epub directory
        if not self.DEBUG:
            shutil.rmtree(self.rdict["unzip_path"], ignore_errors=True)
            try:
                Path(self.epub_file).unlink(False)
            except FileNotFoundError:
                estr = f"FileNotFoundError in unlinking {Path(self.epub_file)}"
                self.rdict["error_lst"].append(estr)
                self.wrlog(True, estr)
        self.wrlog(False, "Dumping rdict")
        self.dump_dict("rdict", self.rdict)
        # for key in self.rdict.keys():
        #     if key != "manifest" and key != "spine_lst":
        #         self.wrlog(False, f"{key}: {self.rdict[key]}")

        return self.rdict
