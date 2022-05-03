#!/usr/bin/env python
# from ctypes import string_at
# import sys
import os

# import datetime
import time
from pathlib import Path
import shutil
import zipfile
import io
import copy

import PySimpleGUI as sg
import threading
import json
import base64
import textwrap
from html2text import html2text

from PIL import Image

# from subprocess import PIPE, run
# from dateutil import parser

# these are my modules
# from packages.pst import PrettySimpleTable
from epubpager import epub_paginator

Version = "0.3"

"""
GUIepubpager.py based on CalibrePaginator.py
Version = "0.3"

Version = "0.2"
1. Add epub version to metadata from the epub and display.
2. Determine if file is already paginated by epubpager (requires enhancement to
   epubpager).
3. Add ability to paginate all books in the list. Select Find files becomes the
   means to paginate selected books. 
4. Hide the epubpage metadata if there is none in the epub file.
5. Implemented a method to perform_long_operation method of running pagination
in a thread and allowing canceling of a long list at any point.

TODO

Version = '0.1'
Basics work:
    1. Open a directory, read all epubs. 
    2. Open files with multifile capability.
    3. Opened files are scannned to get metadata and covers. 
    4. Epub information displayed.
    5. Pagination of single selected epub works.
    6. Find works to filter books in the list. 
       When Find is active (list is filtered), Find button becomes "ShowAll"
       and clicking it returns to unfiltered list.
    7. 

"""

# the minimal database for generic epubs to paginate.
"""
"title": string
"author": string
"blurb": 
"cover":
"formats": 
"identifiers":
"pubdate":
"publisher":
"


"""
# string constants for formatting stuff
CR = "\n"
INDENT = "  "
BREAK = "-------------------" + CR
MainWindowSize = (1024, 920)
termcolumns = 148
termrows = 20
help_length = termrows + 5
output_width = 80
output_height = 32
debug_width = 56
bookdata_textwidth = 24
booklist_width = 68
indent = 3
wrap_width = output_width - 8
recent_table_length = 28  # how many lines in each section of recent books table

# Render Markdown Styles and PrettyTable rendering styles for Multiline
defaultfont = "Menlo"
defaultfontsize = "12"
nocolor = "black"
codefont = "Hack"
codefontsize = "10"
head1size = "20"
head2size = "16"
head3size = "14"
none = defaultfont + " " + defaultfontsize
noformat = none
bold = defaultfont + " " + defaultfontsize + " bold"
italic = defaultfont + " " + defaultfontsize + " italic"
bolditalic = defaultfont + " " + defaultfontsize + " bold italic"
head1none = defaultfont + " " + head1size + " bold"
head1italic = defaultfont + " " + head1size + " bold italic"
head2none = defaultfont + " " + head2size + " bold"
head2italic = defaultfont + " " + head2size + " bold italic"
head3none = defaultfont + " " + head3size + " bold"
head3italic = defaultfont + " " + head3size + " bold italic"
code = codefont + " " + codefontsize

# unicode box drawing characters
hline = "\u2501"
vbar = "\u2503"
cross = "\u254b"
top_left_corner = "\u250f"
top_right_corner = "\u2513"
bottom_left_corner = "\u2517"
bottom_right_corner = "\u251b"
top_tee = "\u2533"
bottom_tee = "\u253b"
left_tee = "\u2523"
right_tee = "\u252b"
cross = "\u254b"
bullet = "\u2022"
# hline = '\u23af'
# vbar = '\u2758'

current_book = {}  # The current book, this is the json dictionary for the book
format_list = []
booklist = []  # List of books in Booklist item. Current books, or result of search
findlist = []  # books found from the 'find' button
cb_cover = ""
nocover = "./NoBookCover.png"
findlist_active = False
cancel_pagination = False
paginate_list = []
paginate_count = 0

config = {
    "srcdir": "/Users/tbrown/data_store/epubs",
    "outdir": "./paged_epubs",
    "match": True,
    "genplist": True,
    "pgwords": 275,
    "pages": 0,
    "pageline": True,
    "pl_align": "center",
    "pl_color": "red",
    "pl_bkt": "<",
    "pl_fntsz": "75%",
    "pl_pgtot": True,
    "superscript": False,
    "super_color": "red",
    "super_fntsz": "60%",
    "super_total": True,
    "chap_pgtot": True,
    "chap_bkt": "",
    "ebookconvert": "/Applications/calibre.app/Contents/MacOS/ebook-convert",
    "epubcheck": "/Users/tbrown/bin/epubcheck.sh",
    "chk_orig": True,
    "chk_paged": True,
    "quiet": True,
    "DEBUG": False,
}
# chars to remove from titles
badchars = [",", "(", ")", "&", "*", "/", "."]

CalibredbCmd = "/Applications/calibre.app/Contents/MacOS/calibredb"

month_str = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# import tkinter
# root = tkinter.Tk()
# width = root.winfo_screenwidth()
# height = root.winfo_screenheight()
# print(f"The screen resolution is {width} x {height}")

# the print for the help MLINE element
def cprint(*args, **kwargs):
    window["-config_help-" + sg.WRITE_ONLY_KEY].print(*args, **kwargs)


def hprint(*args, **kwargs):
    window["-DEBUG-" + sg.WRITE_ONLY_KEY].print(*args, **kwargs)


# this function and assignment redefines print so it prints to the multiline field
def mprint(*args, **kwargs):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(*args, **kwargs)


lprint = mprint
# functions


def LogWarning(message):
    window["-DEBUG-" + sg.WRITE_ONLY_KEY].print(message, font="Menlo 12 bold", t="red")


def LogEvent(message):
    window["-DEBUG-" + sg.WRITE_ONLY_KEY].print(message)


def IsNumber(s):
    """Returns True if string is a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False


config_file = ""

# the config file may be local, which has precedence, or in the ~/.config/BookTally directory
def read_config():

    if os.path.exists("./GUIepubpager.cfg"):
        config_file = "./GUIepubpager.cfg"
    elif os.path.exists("/Users/tbrown/.config/GUIepubpager/GUIepubpager.cfg"):
        config_file = "/Users/tbrown/.config/GUIepubpager/GUIepubpager.cfg"
    else:
        # print("No config file found!")
        return config
    with open(config_file, "r") as cfg:
        return json.loads(cfg.read())


def update_config(values):
    """
    Called from main event loop, updates config dictionary with values set in Configuration Frame.
    """
    global window

    config["srcdir"] = window["-cfgsrcdir-"].get()
    config["outdir"] = values["-outdir-"]
    config["match"] = values["-match-"]
    config["genplist"] = values["-genplist-"]
    config["pgwords"] = int(values["-pgwords-"])
    config["pages"] = int(values["-pages-"])
    config["pageline"] = values["-pageline-"]
    if values["-align_left-"]:
        config["pl_align"] = "left"
    elif values["-align_center-"]:
        config["pl_align"] = "center"
    else:
        config["pl_align"] = "right"
    if values["-pl_color_red-"]:
        config["pl_color"] = "red"
    elif values["-pl_color_green-"]:
        config["pl_color"] = "green"
    else:
        config["pl_color"] = "none"
    if values["-pl_bkt_angle-"]:
        config["pl_bkt"] = "<"
    elif values["-pl_bkt_paren-"]:
        config["pl_bkt"] = "("
    else:
        config["pl_bkt"] = ""
    config["pl_fntsz"] = values["-pl_fntsz-"]
    config["pl_pgtot"] = values["-pl_pgtot-"]
    config["superscript"] = values["-superscript-"]
    if values["-super_color_red-"]:
        config["super_color"] = "red"
    elif values["-super_color_green-"]:
        config["super_color"] = "green"
    else:
        config["super_color"] = "none"
    config["super_fntsz"] = values["-super_fntsz-"]
    config["super_total"] = values["-super_total-"]
    config["chap_pgtot"] = values["-chap_pgtot-"]
    # config['chap_bkt'] = values['-chap_bkt-']
    if values["-chap_bkt_angle-"]:
        config["chap_bkt"] = "<"
    elif values["-chap_bkt_paren-"]:
        config["chap_bkt"] = "("
    else:
        config["chap_bkt"] = ""
    config["ebookconvert"] = values["-ebookconvert-"]
    config["epubcheck"] = values["-epubcheck-"]
    config["chk_orig"] = values["-chk_orig-"]
    config["chk_paged"] = values["-chk_paged-"]
    config["quiet"] = values["-quiet-"]
    config["DEBUG"] = values["-DEBUG-"]


# this is a wait function to read debug output.
def waitinput(message):  # {{{
    dummy = sg.popup_get_text(message, "Check debug statement.")  # }}}


# field definitions for the table
# item:       4 - allows for digits up to 9999
# title:      2+ variable 35/20 ratio with author
# author:     2+ variable 35/20 ratio with title
# pages:      6 for comma formatted number, 2 in front, rjust6 number up to 9,999
# words:      8 for comma formatted number, 2 in front, rjust8 number up to 999,999
# rating:     4 rjust2 number 1-10
# def browse_booklist(browselist):# {{{
#     titlelength = int(35/80 * termcolumns) - 5
#     authorlength = int(20/80 * termcolumns) - 2
#     titleheadlen = titlelength - 5
#     authorheadlen = authorlength - 6
#     pagelength = 6
#     wordlength = 8
#     ratinglength = 4
#     outputlist = []
#     outputlist.append('  ID  | Title' + ' '*titleheadlen + '| Author' + ' '*authorheadlen + '| Pages | Words   | Rating ')
#     outputlist.append('      |-' + '-'*titlelength + '+-' + '-'*authorlength + '|-------|---------|-------|')
#     for book in browselist:
#         tstring = book['title']
#         bookid = book['id']
#         if len(tstring) >= titlelength:
#             tstring = tstring[0:titlelength-1]
#         else:
#             tstring = tstring.ljust(titlelength-1,' ')
#         astring = book['author']
#         if len(astring) >= authorlength:
#             astring = astring[0:authorlength-1]
#         else:
#             astring = astring.ljust(authorlength-1,' ')
#         pages = "{:,}".format(book['Pages'])
#         words = "{:,}".format(book['Words'])
#         rating = "{:,}".format(book['Rating'])
#         outputlist.append(str(bookid).rjust(3,' ') + '| ' +  tstring + ' | ' + astring + ' | ' + pages.rjust(pagelength-1,' ') + ' | ' + words.rjust(wordlength-1,' ') + ' |' + rating.rjust(ratinglength-1,' ') + ' |')
#     return outputlist# }}}

# Format a string with a color, size, and font. Add CR or not
# Format types:
#     header1 - Menlo 18 bold
#     header2 - Menlo 16 bold
#     titlestr = Menlo 16 bold italic, t='red', end=''
#     authorstr = Menlo 16 bold, t='green', end=''


def print_title(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(
        fstr, font="Menlo 16 italic", t="red", end=""
    )


def print_author(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(
        fstr, font="Menlo 16 bold", t="green", end=""
    )


def print_header1(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 20 bold")


def print_header2(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 18 bold")


def print_nocr(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 12", end="")


def print_color_nocr(fstr, thecolor):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(
        fstr, font="Menlo 12", t=thecolor, end=""
    )


def print_bold(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 12 bold")


def print_color(fstr, thecolor):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 12", t=thecolor)


def print_line(fstr):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(fstr, font="Menlo 12")


def print_hline():
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(
        "".join([char * 80 for char in hline]), font="Menlo 12", t="blue"
    )


def print_bluechar(char):
    window["-MLINE-" + sg.WRITE_ONLY_KEY].print(char, font="Menlo 12", t="blue", end="")


# render markdown in the -MLINE- multiline window
# currently only support for three levels of header and bold and italic
def next_style(current_style, new_style):  # {{{
    styleitalic = {
        none: italic,
        bold: bolditalic,
        italic: none,
        bolditalic: bold,
        head1none: head1italic,
        head1italic: head1none,
        head2none: head2italic,
        head2italic: head2none,
        head3none: head3italic,
        head3italic: head3none,
    }
    stylebold = {
        none: bold,
        bold: none,
        italic: bolditalic,
        bolditalic: italic,
        head1none: head1none,
        head1italic: head1italic,
        head2none: head2none,
        head2italic: head2italic,
        head3none: head3none,
        head3italic: head3italic,
    }
    if new_style == italic:
        return styleitalic.get(current_style, none)
    if new_style == bold:
        return stylebold.get(current_style, none)  # }}}

def wraplines(source):  # {{{
    prelines = source.splitlines()
    # pre-process the source with TextWrapper to properly wrap blockquotes
    wrapper = textwrap.TextWrapper()
    wrapper.width = wrap_width
    wrapper.initial_indent = "> "
    wrapper.subsequent_indent = "> "
    lines = ""
    for preline in prelines:
        if len(preline) > 0:
            if preline[0] == ">":
                lines = lines + wrapper.fill(preline[2 : len(preline)]) + CR
            else:
                lines = lines + preline + CR
        else:
            lines = lines + preline + CR
    return lines  # }}}

def render_markdown(lprint, source):  # {{{
    # preprocess in case there are block quotes
    lines = wraplines(source).splitlines()
    # the stylelist is a list of tuples (style, location)
    # The style is applied beginning at the location until the next location.
    listnum = 1
    codeblock = False
    for line in lines:
        stylelist = []
        words = line.split()
        if len(words) > 0:
            # set up the initial style as a header or none
            if words[0] == "#":
                listnum = 1
                stylelist.append((head1none, 0))
                if line[1] == " ":
                    line = line[2 : len(line)]
                else:
                    line = line[1 : len(line)]
            elif words[0] == "##":
                listnum = 1
                stylelist.append((head2none, 0))
                if line[2] == " ":
                    line = line[3 : len(line)]
                else:
                    line = line[2 : len(line)]
            elif words[0] == "###":
                listnum = 1
                stylelist.append((head3none, 0))
                if line[3] == " ":
                    line = line[4 : len(line)]
                else:
                    line = line[3 : len(line)]
            # this is an unordered list
            elif words[0] == "+":
                listnum = 1
                line = "  " + bullet + " " + line[2 : len(line)]
                stylelist.append((none, 0))
            # this is an ordered list
            elif words[0][0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                line = (
                    "  "
                    + "{:3d}".format(listnum)
                    + ". "
                    + line[len(words[0]) + 1 : len(line)]
                )
                listnum += 1
                stylelist.append((none, 0))
            # This is a horizontal line
            elif words[0] == "***" or words[0] == "---":
                line = hline * (wrap_width - 1)
                stylelist.append((none, 0))
            # this is a blockquote--just indent
            elif words[0] == ">":
                line = " " * (indent) + vbar + " " + line[2 : len(line)]
                stylelist.append((none, 0))
            # this is a code block, either start or end
            elif words[0] == "```":
                if codeblock:
                    codeblock = False
                else:
                    codeblock = True
                lprint(hline * (wrap_width - 1))
                continue
            else:
                listnum = 1
                stylelist.append((none, 0))
        else:
            # this is a blank line
            lprint("")
            continue
        # if we have a code block, just print with code style
        if codeblock:
            lprint(line, font=code)
            continue
        # now scan the line by character and add character styles as appropriate
        renderline = ""
        current_style = stylelist[0][0]
        j = 0
        skip = False
        nocharstyle = False
        for i in range(0, len(line)):
            if skip:
                skip = False
                continue
            char = line[i]
            # handle escaping character styles
            # skip the escape char and mark to ignore style
            if char == '\\':
                nocharstyle = True
                continue
            if i < len(line) - 2:
                nextchar = line[i + 1]
            else:
                # this is a dummy, just to not be '*'
                nextchar = "a"
            # this is italic
            if (char == "*" and nextchar != "*") or char == "_" and not nocharstyle:
                thenextstyle = next_style(current_style, italic)
                stylelist.append((thenextstyle, j))
                current_style = thenextstyle
            # and this is bold
            elif char == "*" and nextchar == "*" and not nocharstyle:
                thenextstyle = next_style(current_style, bold)
                stylelist.append((thenextstyle, j))
                current_style = thenextstyle
                skip = True
            else:
                nocharstyle = False
                renderline += char
                j += 1
        start = 0
        # print(f"Before printing: {stylelist}")
        # print(f"renderline: {renderline}")
        if len(stylelist) == 1:
            style = stylelist[0][0]
            lprint(renderline, font=style, t="black")
            # In this case, we reset the stylelist for the next line, it's all used up.
            stylelist = []
        else:
            bound = len(stylelist)
            for i in range(1, len(stylelist)):
                # style and start location are previous entry in stylelist
                style = stylelist[i - 1][0]
                start = stylelist[i - 1][1]
                # end location is where the next style starts, current entry in stylelist
                end = stylelist[i][1]
                lprint(renderline[start:end], font=style, end="")
            # this is the last of the line
            lprint(renderline[end : len(line)], font=stylelist[len(stylelist) - 1][0])
# }}}

def present_book():  # {{{
    global lprint

    # clear the window
    window["-MLINE-" + sg.WRITE_ONLY_KEY].update("")
    print_hline()

    # present formatted information about the book, partly based on its status
    # first the title, author and publication date
    # clear the window
    window["-MLINE-" + sg.WRITE_ONLY_KEY].update("")
    print_title(current_book["title"])
    print_nocr(" by ")
    print_author(current_book["author"])
    mprint()
    print_bold("Published " + current_book["pubdate"])
    print_hline()
    s = fix_amp(current_book["blurb"])
    s = html2text(s)
    render_markdown(mprint, s)
    print_hline()
    return  # }}}


def place_value(number):  # {{{
    return "{:,}".format(number)  # }}}


def update_view(current_book):  # {{{
    present_book()
    load_cover(current_book)
    update_BookDataFrame()


# }}}


def create_bookname(title, author):# {{{
    """
    Create a book name of the form title-author. Remove odd characters for
    file system simplicity.
    """
    for c in badchars:
        title = title.replace(c, "-")
        author = author.replace(c, "-")
    title = title.replace(" ", "_")
    author = author.replace(" ", "_")
    return f"{title}-{author}"# }}}


def print_dict(idict):# {{{
    print("{")
    for key in idict.keys():
        print(f'''  "{key}": {idict[key]}"''')
    print("}")# }}}


def show_dict(idict):# {{{
    LogEvent("{")
    for key in idict.keys():
        LogEvent(f'''  "{key}": {idict[key]}"''')
    LogEvent("}")# }}}


def read_opf(epub_file):# {{{
    "Read the opf file data from the epub zipfile and return the opf_path and opf_data."

    opf_data = "No opf data"
    opf_path = "No opf path"
    # find the opf file

    with zipfile.ZipFile(epub_file) as zfile:
        with zfile.open(f"META-INF/container.xml") as c:
            c_data = c.read()

            cs = str(c_data)
            rloc = cs.find("<rootfiles>")
            if rloc == -1:
                print("Error: did not find <rootfiles> in container")
                return (opf_path, opf_data)
            cs = cs[rloc + 3 :]
            rloc = cs.find("<rootfile")
            if rloc == -1:
                print("Error: did not find <rootfile in container")
                return (opf_path, opf_data)
            cs = cs[rloc + 3 :]
            rloc = cs.find("full-path=")
            if rloc == -1:
                print("Error: did not find full-path in container")
                return (opf_path, opf_data)
            cs = cs[rloc + 3 :]
            opflist = cs.split('"')
            opf_path = f"{opflist[1]}"  # d/d/d/fname
            # print(f"opf_path: {opf_path}")
            if opf_path == "":
                print(
                    "Error: apparently opf file was not found. Return value was blank."
                )
                return (opf_path, opf_data)
            # print(opf_path)
            opf = opf_path.split("/")
            # print(f"opf.split: {opf}; opf len: {len(opf)}")
            opf_file = opf[len(opf) - 1]
            opf = opf[: len(opf) - 1]
            opf_path = ""
            for d in opf:
                opf_path += f"{d}/"
            # print(f"{opf_path} - {opf_file}; cat: {opf_path}/{opf_file}")
            # with zfile.open(f"{opf_path}{opf_file}") as o:
            with io.TextIOWrapper(
                zfile.open(f"{opf_path}{opf_file}"), encoding="utf-8"
            ) as o:
                opf_data = o.read()
                # opf_data = str(opf_b)
            return (opf_path, opf_data)# }}}


def get_cover(epubfile, coverpath, bname, opf_path, opf_data):# {{{
    "Get the cover file from epubfile and return it as coverpath/ename.jpg in path coverpath."
    """ 
    TODO
        in epub 2 files, we might find the cover in this type of xml
        <reference href="Text/Octavia E Butler - Parable of the Sower.html" title="Cover" type="cover" />
    """
    # print(f"get_cover {bname}")
    with zipfile.ZipFile(epubfile) as z:
        # opf_tuple = read_opf(z) # d/d/d/fname
        # opf_path = opf_tuple[0]
        # opf_data = opf_tuple[1]
        v1 = 'properties="cover-image"'
        v2 = 'id="cover-image"'
        v3 = 'id="coverimage"'
        v4 = 'id="cover"'
        if opf_data.find(v1) != -1:
            ss = v1
        elif opf_data.find(v2) != -1:
            ss = v2
        elif opf_data.find(v3) != -1:
            ss = v3
        elif opf_data.find(v4) != -1:
            ss = v4
        else:
            LogWarning("Warning: No property or id for cover-image found")
            return "nocover"
        # print(f"ss found is: {ss}")
        cloc = opf_data.find(ss)
        # since the item may be ordered randomly, we need to find the bounding
        # element < all the stuff >, then search for href.
        lftang = opf_data[:cloc].rfind("<")
        if lftang != -1:
            # print(f"found lftang: {opf_data[lftang:lftang+50]}")
            opf_data = opf_data[lftang:]
            # print(f"new opf1: {opf_data[:20]}")
            hloc = opf_data.find("href=")
            if hloc != -1:
                # print(f"found href: {opf_data[hloc:hloc+20]}")
                # end location of the href
                # we add 6 for 'href="'
                opf_data = opf_data[hloc+6:]
                # print(f"new opf2: {opf_data[:20]}")
                eloc = opf_data.find('"')
                if eloc != -1:
                    cpath = opf_data[:eloc]
                    # print(f"cpath is: {opf_path}{cpath}")
                    ftype = Path(cpath).suffix
                    # print(f"ftype: {ftype}")
                    z.extract(f"{opf_path}{cpath}", "./")
                    shutil.copyfile(f"{opf_path}{cpath}", f"{coverpath}/{bname}{ftype}")
                    rmlink = f"{opf_path}{cpath}"
                    if Path(rmlink).is_file():
                        Path(rmlink).unlink
                    if Path(rmlink).is_dir():
                        shutil.rmtree(Path(rmlink).parts[0])
                    return f"{coverpath}/{bname}.jpg"
                else:
                    LogWarning("get_cover Error: Did not find href")
                    return "nocover"
            else:
                LogWarning("get_cover Error: Did not find href")
                return "nocover"
        else:
            LogWarning("get_cover Error: Did not find href")
            return "nocover"# }}}

def get_metaprop(opf_data, loc):
    '''
    given opf_data and location of a dc:item, find the value of the iterm
    form of xml lines:
    <meta property="dcterms:modified">2021-11-12T15:12:06Z</meta>
    Location is pinting to the property location, so we find '>' and then '<'
    then return the information between the two.
    '''
    loc1 = opf_data[loc:].find(">")
    loce= opf_data[loc + loc1 :].find("<")
    return (opf_data[loc + loc1 + 1 : loc + loc1 + loce])

def fetch_tlb(opf_data):# {{{
    """
    parse opf file and grab data from:
        dc:title
        dc:creator
        dc:date
        cd:description
    """

    rdict = {}
    rdict["title"] = "none"
    rdict["author"] = "none"
    rdict["epub_version"] = 0
    rdict["pubdate"] = "none"
    rdict["publisher"] = "none"
    rdict["blurb"] = "none"
    rdict["cover"] = "none"
    rdict["identifiers"] = []
    rdict["pages"] = 0
    rdict["words"] = 0
    rdict["modified"] = False

    # get the epub version 
    # find the <package element
    ploc = opf_data.find("<package")
    if ploc == -1:
        LogEvent(
            "get_epub_version: Did not find package string in opf file"
        )
    else:
        # find the version= string
        # print(f"package: {opf_data[ploc:ploc+50]}")
        opf_str = opf_data[ploc:]
        vloc = opf_str.find("version=")
        if vloc == -1:
            LogEvent(
                "get_epub_version: Did not find version string in opf file"
            )
        else:
            # print(f"epub_version: {opf_data[vloc : vloc + 15]}")
            vlist = opf_str[vloc : vloc + 15].split('"')
            rdict['epub_version'] = vlist[1]

    # title
    lt = opf_data.find("dcterms:title")
    if lt == -1:
        # print("Looking for dc:title")
        # look for <dc:title
        lt = opf_data.find("<dc:title")
        if lt == -1:
            print("Error: Title meta data not found in opf file.")
            return rdict
    if lt != -1:
        rdict['title'] = get_metaprop(opf_data, lt)

    # author
    lc = opf_data.find("<dcterms:creator")
    if lc == -1:
        # print("Looking for dc:creator")
        # look for <dc:creator
        lc = opf_data.find("<dc:creator")
        if lc == -1:
            LogWarning("Error: Author meta data not found in opf file.")
            return rdict
    if lc != -1:
        rdict['author'] = get_metaprop(opf_data, lc)
        # check to see if the creator name is of the form "last, first", and if so fix it.
        if "," in rdict["author"]:
            rdict["author"] = rdict["author"].replace(",", "")
            asplit = rdict["author"].split()
            au = ""
            for item in asplit[1:]:
                au += item + " "
            au += asplit[0]
            rdict["author"] = au

    hprint("-----")
    hprint(f"Fetch metadata from {rdict['title']} by {rdict['author']}")

    # pubdate
    ld = opf_data.find("dcterms:modified")
    if ld == -1:
        ld = opf_data.find("<dc:date")
        if ld == -1:
            LogWarning("Publication date not found in opf file.")
    if ld != -1:
        rdict['pubdate'] = get_metaprop(opf_data, ld)
        if rdict["pubdate"] != "none":
            pd = rdict["pubdate"]
            pds = pd.split("-")
            year = pds[0]
            if len(pds) > 1:
                if int(pds[1]) > 0 and int(pds[1]) < 13:
                    month = month_str[int(pds[1]) - 1]
                else:
                    print("month was not found.")
                    month = "Jan"
            else:
                month = "Jan"
            rdict["pubdate"] = f"{month} {year}"

    # publisher
    lp = opf_data.find("dcterms:publisher")
    if lp == -1:
        lp = opf_data.find("<dc:publisher")
        if lp == -1:
            LogWarning("Warning: publisher meta data not found in opf file.")
    if lp != -1:
        rdict['publisher'] = get_metaprop(opf_data, lp)

    # Blurb
    lb = opf_data.find("dcterms:description")
    if lb == -1:
        lb = opf_data.find("<dc:description")
        if lb == -1:
            lb = opf_data.find("<description")
            if lb == -1:
                LogWarning("Warning: Blurb meta data not found in opf file.")
    if lb != -1:
        rdict['blurb'] = get_metaprop(opf_data, lb)

    # identifiers 
    li = opf_data.find("dcterms:identifier")
    if li == -1:
        li = opf_data.find("<dc:identifier")
    if li != -1:
        lid = get_metaprop(opf_data, li)
        if len(lid) == 13 and (lid[0:3] == "978" or lid[0:3] == "979"):
            lid = "ISBN-13: " + lid
        rdict['identifiers'].append(lid)

    # epubpager meta data
    lew = opf_data.find('<meta name="tlbepubpager:words"')
    if lew != -1:
        rdict['words'] = get_metaprop(opf_data, lew)

    lep = opf_data.find('<meta name="tlbepubpager:words"')
    if lep != -1:
        rdict['pages'] = get_metaprop(opf_data, lep)

    lem = opf_data.find('<meta name="tlbepubpager:modified"')
    if lem != -1:
        if lem != -1:
            rdict['modified'] = get_metaprop(opf_data, lem)
    return rdict# }}}


def load_files(directory, flist):# {{{
    global epub_database
    global bnamelist

    t1 = time.perf_counter()
    count = 0
    idx = 1
    epub_database = []
    bnamelist = []
    for f in flist:
        count += 1
        fp = f"{directory}/{f}"
        ot = read_opf(fp)
        opf_path = ot[0]
        opf_data = ot[1]
        nbook = fetch_tlb(opf_data)
        nbook["formats"] = []
        # this loads the actual path of the format to formats
        nbook["formats"].append(fp)
        # show_dict(nbook)
        if nbook["title"] == "none" or nbook["author"] == "none":
            LogWarning(
                f"Fatal Error: Either title or author not found in epub metadata."
            )
        else:
            bname = create_bookname(nbook["title"], nbook["author"])
            # print(f"bname: {bname}")
            # this gets the cover from the original book
            nbook["cover"] = get_cover(fp, config["outdir"], bname, opf_path, opf_data)
            # print(f"cover: {cover}")
        epub_database.append(nbook)
        if idx < 10:
            bnamelist.append(f" {idx}. {nbook['title']} by {nbook['author']}")
        else:
            bnamelist.append(f"{idx}. {nbook['title']} by {nbook['author']}")
        idx += 1
        # if count == 10:
        #     break
    t2 = time.perf_counter()
    tt = t2 - t1
    tbook = tt / idx
    LogEvent('')
    LogEvent(
        f"Load and scan epubs took {t2-t1:.3f} seconds; {tbook:.3f} seconds per book."
    )# }}}


def get_dirpath(book):# {{{
    """
    return the path of the directory containing the formats and cover for the book
    """
    epub_path = ""
    coverpath = ""
    for fmt in book["formats"]:
        # LogEvent(f"fmt: {fmt}")
        if Path(fmt).suffix == ".epub":
            epub_path = fmt
            # LogEvent(f"epub_path: {epub_path}")
            pparts = Path(fmt).parts
            tp = ""
            for item in pparts[0 : len(pparts) - 1]:
                # print(item)
                tp += item
                if item != "/":
                    tp += "/"
                coverpath = f"{tp}cover.jpg"
                # LogEvent(f"coverpath: {coverpath}")
            break
    return coverpath, epub_path# }}}


def load_cover(book):  # {{{
    if book.get("cover", False):
        if book["cover"] == "nocover":
            LogWarning(f"There is no book cover in the epub file.")
            window["-Cover-"].update(filename=nocover)
            return
        if os.path.exists(book["cover"]):
            # LogEvent(f"load_cover: found cover file {book['cover']}")
            if Path(book["cover"]).is_file():
                size = 256, 256
                try:
                    im = Image.open(book["cover"])
                except IOError as e:
                    myerror = e
                    LogWarning(f"{myerror} attempting to open cover file.")
                    return
                else:
                    im.thumbnail(size, Image.Resampling.LANCZOS)
                    pngpath = "cover.png"
                    im.save(pngpath, "PNG")
            window["-Cover-"].update(filename=pngpath)
        else:
            LogWarning("load_cover: cover file not a file.")
            window["-Cover-"].update(filename=nocover)
    else:
        LogWarning("load_cover: No cover is available.")
        window["-Cover-"].update(filename=nocover)  # }}}


def fix_amp(s):# {{{
    amp_escape = [
        "&lt;",
        "&gt;",
        "&mdash;",
        "&amp",
        "&quot",
        "&ldquo;",
        "&rdquo;",
        "&rsquo;" "&nbsp",
    ]
    amp_replace = ["<", ">", "--", "&", '"', '"', '"', "'", " "]
    idx = 0
    for r in amp_escape:
        s = s.replace(r, amp_replace[idx])
        idx += 1
    return s# }}}


def FindTitleAuthor(searchstr):# {{{

    #     searchstr = str(searchstr)
    newbooklist = []
    for book in epub_database:
        # casefold gives a case insensitive search
        if (
            searchstr.casefold() in book["title"].casefold()
            or searchstr.casefold() in book["author"].casefold()
        ):
            newbooklist.append(book)
    return newbooklist# }}}

def paginate_book(book_location): # {{{
    '''
    Paginate the book at book_location using the active configuration.

    book_location: text path to an epub file.
    '''


    thread_str = ''
    if Path(book_location).is_file():
        paginator = epub_paginator()
        paginator.outdir = config["outdir"]
        paginator.match = config["match"]
        paginator.genplist = config["genplist"]
        paginator.pgwords = config["pgwords"]
        paginator.pages = config["pages"]
        paginator.pageline = config["pageline"]
        paginator.pl_align = config["pl_align"]
        paginator.pl_color = config["pl_color"]
        paginator.pl_bkt = config["pl_bkt"]
        paginator.pl_fntsz = config["pl_fntsz"]
        paginator.pl_pgtot = config["pl_pgtot"]
        paginator.superscript = config["superscript"]
        paginator.super_color = config["super_color"]
        paginator.super_fntsz = config["super_fntsz"]
        paginator.super_total = config["super_total"]
        paginator.chap_pgtot = config["chap_pgtot"]
        paginator.chap_bkt = config["chap_bkt"]
        paginator.ebookconvert = config["ebookconvert"]
        paginator.epubcheck = config["epubcheck"]
        paginator.chk_orig = config["chk_orig"]
        paginator.chk_paged = config["chk_paged"]
        paginator.quiet = config["quiet"]
        paginator.DEBUG = config["DEBUG"]
        return_dict = paginator.paginate_epub(book_location)
        thread_str += ""
        thread_str += CR
        # thread_str += f"Paginated ebook created: {return_dict['bk_outfile']}"
        thread_str += f"Paginated ebook log is at: "
        thread_str += CR
        thread_str += f"  {return_dict['logfile']}"
        thread_str += CR
        lpad = 10
        rpad = 50
        echk_err = False
        pager_err = False
        pager_warn = False
        if return_dict["pager_error"]:
            pager_err = True
            thread_str += " --> Fatal errors occurred in epub_pager. Book may not be properly paginated."
            thread_str += CR
            if return_dict["epub_version"][0] == "2":
                
                thread_str += " --> This is an ePub2 book. Often if books are first converted to ePub3 "
                thread_str += CR
                thread_str += "epubpaginator can successfully paginate them."
                thread_str += CR
                for e in return_dict["error_lst"]:
                    thread_str += f"   --> {e}"
                    thread_str += CR
                thread_str += f"See details in log: {return_dict['logfile']}"
                thread_str += CR
        if return_dict["pager_warn"]:
            pager_warn = True
            thread_str += "  --> There were warnings in epub_pager."
            thread_str += CR
            for w in return_dict["warn_lst"]:
                thread_str += f"   --> {w}"
                thread_str += CR
            thread_str += f"See details in log: {return_dict['logfile']}"
            thread_str += CR
        if return_dict["echk_fatal"] or return_dict["orig_fatal"]:
            echk_err = True
            s = "Fatal Errors"
            thread_str += ""
            thread_str += CR
            thread_str += f"{'-' * lpad}{s}{'-' * (rpad - len(s))}"
            thread_str += CR
            thread_str += f"  --> {return_dict['echk_fatal']:3} fatal "
            thread_str += CR
            thread_str += f"error(s) in paged book epubcheck."
            thread_str += CR
            thread_str += f"  --> {return_dict['orig_fatal']:3} fatal "
            thread_str += CR
            thread_str += f"error(s) in original book epubcheck."
            thread_str += CR
        if return_dict["echk_error"] or return_dict["orig_error"]:
            echk_err = True
            s = "Errors"
            thread_str += ""
            thread_str += CR
            thread_str += f"{'-' * lpad}{s}{'-' * (rpad - len(s))}"
            thread_str += CR
            thread_str += f"  --> {return_dict['echk_error']:3} error(s) in paged book epubcheck."
            thread_str += CR
            thread_str += f"  --> {return_dict['orig_error']:3} error(s) in original book epubcheck."
            thread_str += CR
        if not pager_err and not pager_warn and not echk_err:
            thread_str += ""
            thread_str += CR
            thread_str += f"Processing completed without error."
            thread_str += CR
            if not pager_err:
                thread_str += f"Paginated ebook created: {return_dict['bk_outfile']}"
                thread_str += CR
                thread_str += f"See details in log: {return_dict['logfile']}"
                thread_str += CR
            thread_str += "-" * (lpad + rpad)
            thread_str += CR
            thread_str += ""
            thread_str += CR
    else:
        thread_str += "Pagination not done. No epub file found."
        thread_str += CR
    return thread_str
# }}}

configuration_help = """
## Source Folder{{{

Directory to read epub files from.

## Output Folder

Location for output ePub files. Cover files are also stashed here.

## Generate Pagelist

If no pagination generate the navigation page list and page links

## Defining How Pagination is Done

If **Match Existing Pagination** is true and a pagelist is found in the epub file, pagelines and superscript pagination are matched to the existing pagelist.

If **Match Existing Pagination** is false, page length is determined by the values of Words per Page and Total Pages.

If **Words Per Page** and **Total Pages** are both zero, this is a fatal error. epubpager does not know how to define the page length.

If **Words per Page** is non-zero, this becomes the page length for all pagination generated by epubpager.

If **Words per Page** is zero and **Total Pages** is non-zero, then the page length is defined by dividing epubpager's word count for the epub by Total Pages and using that value as Words per Page.

## Generate Pagelines

Generate and insert page pagelines into the ePub text.

## Pageline Font Size

Pageline font size as percentage of book font.

## Pageline Alignment

'right', 'left' or 'center'; specify alignment of the pageline.

## Pageline Color

html color for the inserted pageline - {red, green, none}.

## Include Pageline Page Total

Include total pages in the pageline.

## Pageline Bracket

Character to use to bracket page number - {'<', '(' , none}.

## Generate Superscripts

Generate superscripted page numbers.

## Superscript Font Size

Superscript font size as percentage of book font.

## Superscript Color

html color for the inserted page superscript - {red, green, none}.

## Include Superscript Page Total

Include total pages in the superscript.

## Include Chapter Page Total

Include chapter page and total in the pageline and/or superscript.

## Chapter Bracket {<,(,none}

Character to use to bracket page number - '<', '(' or none.

## Ebook Conversion

Location of ebook conversion executable (Calibre's ebook-convert). If this value is blank or incorrect, no conversion will be done. If this value is valid, any version 2 epub will be converted to epub version 3. Generally speaking, epubpage handles converted epub 3 books more effectively than epub version 2 books.

## Use of Epubcheck

If Epubcheck points to an epubcheck executable or script, it will be used when epubcheck is run. 

If Epubcheck is blank, epubpager will check to see if the epubcheck Python module is available, and use it if so. The Python epubceck module can be installed using pip.

Please note the external epubcheck program is about five times faster than the Python module epubcheck.

## Epubcheck

Location of epubcheck external executable.

## Epubcheck Original

Run epubcheck on the original epub file.

## Epubcheck Paged

Run epubcheck on file after pagination.

## Quiet

If Quiet is true, no output will be printed to the console. 

## DEBUG

Print additional debug information to the log file.

```
"""# }}}
gui_help = """
# Basic Operation{{{

**Book List** shows a list of all books in the selected directory. Select any book by clicking on the entry. All fields are updated when the book is changed.

The **Book Data** section gives additional information taken from the metadata contained in the epub's .opf file. Epubpager inserts its own custom metadata (the word count for the book, and the page count for the book) when paginating an epub. If these are present, they will be displayed. In addition, currently epubpage will not paginate an epub it has already operated on.

The **Output** section contains two text view. 

The leftmost section displays the book title, author and publication date and a description of the book. The publication data and description are taken from the epub metadata.

The rightmost section serves two functions. Initially it is a log of operations. If the "Help" button is clicked, this field shows help information. Log infomration can again be shown by clicking the "Log" button when help is active.

If the configure button is clicked, this field will show configuration help.

## Commands

1. **Find** - Search the book list for a string. The list will be populated with all books where the search string is found either in the book title, or the book author.
2. **Paginate** - The book will be paginated according using the selected configuration. 
3. **Paginate All** - All books in the list will be paginated using the selected configuration.
4. **Configure** - Show a page of selectable options for configuring the operation of GUIepubPaginator. When configuration is shown it is accompanied by configuration help information in the right text window.
5. **About** - Show version information for GUIepubPaginator.
6. **Help/Log** - Toggle the display of Help information or Log information in the text field at the lower right of the display.
7. **Exit** - Quit the program.
"""# }}}


def update_BookDataFrame():  # {{{
    global current_book
    global format_list

    window["-BookDataTitle-"].update(current_book["title"])
    window["-BookDataAuthor-"].update(current_book["author"])
    window["-epub_version-"].update(f"{current_book['epub_version']:>7}")
    if current_book['modified']:
        window["-epMetaData-"].update(visible=True)
        window["-epPages-"].update(visible=True)
        window["-epWords-"].update(visible=True)
        window["-Pages-"].update(visible=True)
        window["-Pages-"].update(f"{current_book['pages']:>7,d}")
        window["-Words-"].update(visible=True)
        window["-Words-"].update(f"{current_book['words']:>7,d}")
    else:
        window["-epMetaData-"].update(visible=False)
        window["-epPages-"].update(visible=False)
        window["-epWords-"].update(visible=False)
        window["-Pages-"].update(visible=False)
        window["-Words-"].update(visible=False)
    window["-pubdate-"].update(current_book["pubdate"])
    if "identifiers" in current_book.keys():
        window["-identifiers-"].update(current_book["identifiers"])
    # if 'series' in current_book.keys():
    #     window['-series-'].update(current_book['series'])
    # else:
    #     current_book['series'] = 'Standalone Book'
    #     window['-series-'].update(current_book['series'])
    # if 'series_index' in current_book.keys():
    #     window['-series_index-'].update(current_book['series_index'])
    # else:
    #     current_book['series_index'] = 1.0
    #     window['-series_index-'].update(current_book['series_index'])
    # }}}


def toggle_configure(window):# {{{
    global show_configure

    if show_configure:
        window["-Cover-"].update(visible=False)
        window["-BookList-"].update(visible=False)
        window["-col_bookdata-"].update(visible=False)
        window["-col_output-"].update(visible=False)
        window["-Find-"].update(visible=False)
        window["-Paginate-"].update(visible=False)
        window["-PaginateAll-"].update(visible=False)
        window["-Configure-"].update(visible=False)
        window["-About-"].update(visible=False)
        window["-Help-"].update(visible=False)
        window["-Exit-"].update(visible=False)
        window["-col_config-"].update(visible=True)
        window["-col_confighelp-"].update(visible=True)
        window["-UpdateConfig-"].update(visible=True)
        window["-CancelConfig-"].update(visible=True)
        window["-SaveConfig-"].update(visible=True)
        window["-LoadConfig-"].update(visible=True)
        show_configure = False
    else:
        window["-Cover-"].update(visible=True)
        window["-BookList-"].update(visible=True)
        window["-col_bookdata-"].update(visible=True)
        window["-col_output-"].update(visible=True)
        window["-Find-"].update(visible=True)
        window["-Paginate-"].update(visible=True)
        window["-PaginateAll-"].update(visible=True)
        window["-Configure-"].update(visible=True)
        window["-About-"].update(visible=True)
        window["-Help-"].update(visible=True)
        window["-Exit-"].update(visible=True)
        window["-col_config-"].update(visible=False)
        window["-col_confighelp-"].update(visible=False)
        window["-UpdateConfig-"].update(visible=False)
        window["-CancelConfig-"].update(visible=False)
        window["-SaveConfig-"].update(visible=False)
        window["-LoadConfig-"].update(visible=False)
        show_configure = True# }}}

# def paginate_thread():# {{{

#     tbooks = len(epub_database)
#     cbook = 1
#     for book in epub_database:
#         if book['modified']:
#             LogWarning(f"{book['title']} has already been paginated by epubpager.")
#             continue
#         book_location = book['formats'][0]
#         LogEvent("")
#         LogEvent(f"Paginating {book['title']}")
#         paginate_book(book_location)
#         cbook += 1
#         window.write_event_value("-threadupdate-",(cbook, tbooks))

# ---------Layout-------------------------
# Build the PySimpleGui window with buttons and multiline output

sg.theme("Dark Blue 3")
config = read_config()

# Tuesday, August 3, 2021 9:25:56 AM try a new layout:
# +======================================================+
# | Cover Image | Current List | Book Data               |
# |------------------------------------------------------|
# | Command Bar of Buttons                              |
# |------------------------------------------------------|
# | Output      | Debug/Help                             |  /swaps with configuration row
# |------------------------------------------------------|
# | Configuration                                        | /configuration replaces previous row
# +======================================================+
ColCurrentList = sg.Column( # {{{
    [
        [
            sg.Frame(
                "Book List",
                [
                    [
                        sg.Listbox(
                            booklist,
                            key="-BookList-",
                            # select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                            select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
                            enable_events=True,
                            size=(booklist_width, termrows),
                            font="Menlo 12",
                        )
                    ]
                ],
            ),
        ]
    ],
    pad=(0, 0),
) # }}}

ColBookData = sg.Column(# {{{
    [
        [
            sg.Frame(
                "Book Data:",
                [
                    [
                        sg.Text(
                            "title",
                            key="-BookDataTitle-",
                            size=(60, 1),
                            font="Menlo 14 bold italic",
                        )
                    ],
                    [
                        sg.Text(
                            "author",
                            key="-BookDataAuthor-",
                            size=(60, 1),
                            font="Menlo 14 bold",
                        )
                    ],
                    [
                        sg.Text("Epub Version".rjust(13), font="Menlo 12"),
                        sg.Input(
                            default_text="", key="-epub_version-", font="Menlo 12", size=(7, 1)
                        ),
                    ],
                    [
                        sg.Text("pubdate".rjust(13), font="Menlo 12"),
                        sg.Input(
                            default_text="",
                            key="-pubdate-",
                            size=(bookdata_textwidth, 1),
                        ),
                    ],
                    [
                        sg.Text("Identifiers".rjust(13), font="Menlo 12"),
                        sg.LBox(
                            [], key="-identifiers-", size=(bookdata_textwidth, 1)
                        ),
                    ],
                    [sg.HorizontalSeparator()],
                    [
                        sg.Text(
                            "epubpager Metadata",
                            size=(60, 1),
                            font="Menlo 14 bold",
                            key = "-epMetaData-",
                        )
                    ],
                    [
                        sg.Text("Pages".rjust(13), font="Menlo 12", key = "-epPages-",),
                        sg.Input(
                            default_text="", key="-Pages-", font="Menlo 12", size=(7, 1)
                        ),
                    ],
                    [
                        sg.Text("Words".rjust(13), font="Menlo 12", key = "-epWords-"),
                        sg.Input(
                            default_text="", key="-Words-", font="Menlo 12", size=(7, 1)
                        ),
                    ],
                ],
            )
        ]
    ],
    pad=(0, 0),
    key="-col_bookdata-",
    visible=True,
) # }}}

ColImage = sg.Column(# {{{
    [  
        [
            sg.Frame(
                "Cover",
                [
                    [sg.Image(filename=cb_cover, key="-Cover-")],
                ],
            ),
        ]
    ],
    pad=(0, 0),
)  # }}}

ColFolder = sg.Column(# {{{
    [
        [
            # sg.Text(config['srcdir'].rjust(60), enable_events = True, font='Menlo 12', size=(60,1), key='-srcdir-'),
            # sg.FolderBrowse(button_text='Open Folder',  font='Menlo 12 bold', enable_events = True, initial_folder = "./", target = '-srcdir-',),
            sg.Input(
                default_text=config["srcdir"],
                enable_events=True,
                visible = False, 
                font="Menlo 12",
                size=(10, 1),
                key="-srcdir-",
            ),
            sg.FolderBrowse(
                button_text="Open Folder",
                font="Menlo 12 bold",
                enable_events=True,
                initial_folder=config["srcdir"],
                key="-fbsrcdir-",
                target="-srcdir-",
            ),
            sg.Input(
                default_text=config["srcdir"],
                enable_events=True,
                visible = False, 
                font="Menlo 12",
                size=(10, 1),
                key="-files-",
            ),
            sg.FilesBrowse(
                button_text="Open Files",
                font="Menlo 12 bold",
                enable_events=True,
                initial_folder="./",
                key="-fbfiles-",
                target="-files-",
            ),
        ],
    ]
)# }}}

ColButtons = sg.Column(# {{{
    [
        [
            sg.Frame(
                "Commands",
                [
                    [
                        sg.Button(
                            key="-Find-",
                            button_text="Find",
                        ),
                        sg.Button(
                            key="-Paginate-",
                            button_text="Paginate",
                        ),
                        sg.Button(
                            key="-PaginateAll-",
                            button_text="Paginate All",
                        ),
                        sg.Button(
                            key="-Configure-",
                            button_text="Configure",
                        ),
                        sg.Button(
                            key="-About-",
                            button_text="About",
                        ),
                        sg.Button(
                            key="-Help-",
                            button_text="Help",
                        ),
                        sg.Button(
                            key="-Exit-",
                            button_text="Exit",
                        ),
                        # the configuration buttons
                        sg.Input(
                            visible=False, enable_events=True, key="-config_file-"
                        ),
                        sg.FileBrowse(
                            button_text="Load Config File",
                            visible=False,
                            k="-LoadConfig-",
                        ),
                        sg.Input(
                            visible=False, enable_events=True, key="-save_config-"
                        ),
                        sg.FileSaveAs(
                            button_text="Save Config File",
                            visible=False,
                            k="-SaveConfig-",
                        ),
                        sg.Button(
                            key="-UpdateConfig-",
                            button_text="Update Config",
                            visible=False,
                        ),
                        sg.Button(
                            key="-CancelConfig-",
                            button_text="Cancel",
                            visible=False,
                        ),
                    ]
                ],
            )
        ]
    ],
    pad=(0, 0),
)# }}}

ColOutput = sg.Column(# {{{
    [
        [
            sg.Frame(
                "Output",
                [
                    [
                        sg.Multiline(
                            key="-MLINE-" + sg.WRITE_ONLY_KEY,
                            enable_events=True,
                            autoscroll=True,
                            size=(output_width, output_height),
                            font="Menlo 12",
                        ),
                        sg.Multiline(
                            key="-DEBUG-" + sg.WRITE_ONLY_KEY,
                            autoscroll=True,
                            size=(debug_width, output_height),
                            font="Menlo 12",
                            visible=True,
                        ),
                    ]
                ],
            ),
        ]
    ],
    key="-col_output-",
    pad=(0, 0),
)# }}}

ColConfig = sg.Column(# {{{
    [
        [
            sg.Frame(
                "Configuration",
                [
                    [
                        sg.FolderBrowse(
                            button_text="Source Folder",
                            font="Menlo 12 bold",
                            initial_folder="./",
                            target="-cfgsrcdir-",
                        ),
                        sg.Text(
                            config["srcdir"],
                            font="Menlo 12",
                            size=(60, 1),
                            enable_events=True,
                            key="-cfgsrcdir-",
                        ),
                    ],
                    [
                        sg.FolderBrowse(
                            button_text="Output Folder",
                            font="Menlo 12 bold",
                            initial_folder="./",
                            target="-outdir-",
                        ),
                        sg.Input(
                            default_text=config["outdir"],
                            font="Menlo 12",
                            size=(60, 1),
                            key="-outdir-",
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Generate Pagelist",
                            font="Menlo 12 bold",
                            default=config["genplist"],
                            key="-genplist-",
                        ),
                        sg.Checkbox(
                            "Match Existing Pagination",
                            font="Menlo 12 bold",
                            default=config["match"],
                            key="-match-",
                        ),
                    ],
                    [
                        sg.Text("Words per Page", font="Menlo 12 bold"),
                        sg.Input(
                            default_text=config["pgwords"], key="-pgwords-", size=(5, 1)
                        ),
                        sg.Text("Total Pages", font="Menlo 12 bold"),
                        sg.Input(
                            default_text=config["pages"], key="-pages-", size=(5, 1)
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Generate Pagelines",
                            font="Menlo 12 bold",
                            default=config["pageline"],
                            key="-pageline-",
                        ),
                        sg.Text("Pageline Font Size", font="Menlo 12 bold"),
                        sg.Input(
                            default_text=config["pl_fntsz"],
                            key="-pl_fntsz-",
                            size=(5, 1),
                        ),
                    ],
                    [
                        sg.Text("Pageline Alignment:", font="Menlo 12 bold"),
                        sg.Radio(
                            "Left",
                            group_id="pl_align",
                            default=config["pl_align"] == "left",
                            key="-align_left-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Center",
                            group_id="pl_align",
                            default=config["pl_align"] == "center",
                            key="-align_center-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Right",
                            group_id="pl_align",
                            default=config["pl_align"] == "right",
                            key="-align_right-",
                            font="Menlo 12",
                        ),
                    ],
                    [
                        sg.Text("Pageline Color:", font="Menlo 12 bold"),
                        sg.Radio(
                            "Red",
                            group_id="pl_color",
                            default=config["pl_color"] == "red",
                            key="-pl_color_red-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Green",
                            group_id="pl_color",
                            default=config["pl_color"] == "green",
                            key="-pl_color_green-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "None",
                            group_id="pl_color",
                            default=config["pl_color"] == "none",
                            key="-pl_color_none-",
                            font="Menlo 12",
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Include Pageline Page Total",
                            font="Menlo 12 bold",
                            default=config["pl_pgtot"],
                            key="-pl_pgtot-",
                        ),
                    ],
                    [
                        sg.Text("Pageline Bracket", font="Menlo 12 bold"),
                        sg.Radio(
                            "Angle - <>",
                            group_id="pl_bkt",
                            default=config["pl_bkt"] == "<",
                            key="-pl_bkt_angle-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Parenthesis - ()",
                            group_id="pl_bkt",
                            default=config["pl_bkt"] == "(",
                            key="-pl_bkt_paren-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "None",
                            group_id="pl_bkt",
                            default=config["pl_bkt"] == "",
                            key="-pl_bkt_none-",
                            font="Menlo 12",
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Generate Superscripts",
                            font="Menlo 12 bold",
                            default=config["superscript"],
                            key="-superscript-",
                        ),
                        sg.Text("Superscript Font Size", font="Menlo 12 bold"),
                        sg.Input(
                            default_text=config["super_fntsz"],
                            key="-super_fntsz-",
                            size=(5, 1),
                        ),
                    ],
                    [
                        sg.Text("Superscript Color", font="Menlo 12 bold"),
                        sg.Radio(
                            "Red",
                            group_id="super_color",
                            default=config["pl_color"] == "red",
                            key="-super_color_red-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Green",
                            group_id="super_color",
                            default=config["pl_color"] == "green",
                            key="-super_color_green-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "None",
                            group_id="super_color",
                            default=config["pl_color"] == "none",
                            key="-super_color_none-",
                            font="Menlo 12",
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Include Superscript Page Total",
                            font="Menlo 12 bold",
                            default=config["super_total"],
                            key="-super_total-",
                        ),
                        sg.Checkbox(
                            "Include Chapter Page Total",
                            font="Menlo 12 bold",
                            default=config["chap_pgtot"],
                            key="-chap_pgtot-",
                        ),
                    ],
                    [
                        sg.Text("Chapter Bracket", font="Menlo 12 bold"),
                        sg.Radio(
                            "Angle - <>",
                            group_id="chap_bkt",
                            default=config["chap_bkt"] == "<",
                            key="-chap_bkt_angle-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "Parenthesis - ()",
                            group_id="chap_bkt",
                            default=config["chap_bkt"] == "(",
                            key="-chap_bkt_paren-",
                            font="Menlo 12",
                        ),
                        sg.Radio(
                            "None",
                            group_id="chap_bkt",
                            default=config["chap_bkt"] == "",
                            key="-chap_bkt_none-",
                            font="Menlo 12",
                        ),
                    ],
                    [
                        sg.FileBrowse(
                            button_text="Ebook Conversion",
                            font="Menlo 12 bold",
                            initial_folder="./",
                            target="-ebookconvert-",
                        ),
                        sg.Input(
                            default_text=config["ebookconvert"],
                            font="Menlo 12",
                            size=(60, 1),
                            key="-ebookconvert-",
                        ),
                    ],
                    [
                        sg.FileBrowse(
                            button_text="Epubcheck",
                            font="Menlo 12 bold",
                            initial_folder="./",
                            target="-epubcheck-",
                        ),
                        sg.Input(
                            default_text=config["epubcheck"],
                            font="Menlo 12",
                            size=(60, 1),
                            key="-epubcheck-",
                        ),
                    ],
                    [
                        sg.Checkbox(
                            "Epubcheck Original",
                            font="Menlo 12 bold",
                            default=config["chk_orig"],
                            key="-chk_orig-",
                        ),
                        sg.Checkbox(
                            "Epubcheck Paged",
                            font="Menlo 12 bold",
                            default=config["chk_paged"],
                            key="-chk_paged-",
                        ),
                        sg.Checkbox(
                            "Quiet",
                            font="Menlo 12 bold",
                            default=config["quiet"],
                            key="-quiet-",
                        ),
                        sg.Checkbox(
                            "DEBUG",
                            font="Menlo 12 bold",
                            default=config["DEBUG"],
                            key="-DEBUG-",
                        ),
                    ],
                ],
            ),
        ]
    ],
    key="-col_config-",
    pad=(0, 0),
)# }}}

ColConfigHelp = sg.Column(# {{{
    [
        [
            sg.Frame(
                "Help",
                [
                    [
                        sg.Multiline(
                            key="-config_help-" + sg.WRITE_ONLY_KEY,
                            enable_events=True,
                            autoscroll=True,
                            size=(debug_width, output_height),
                            font="Menlo 12",
                        ),
                    ]
                ],
            ),
        ]
    ],
    key="-col_confighelp-",
    pad=(0, 0),
)# }}}

# Tuesday, August 3, 2021 9:25:56 AM try a new layout:
# +=============================+
# | Cover Image | Current List  |
# |-----------------------------|
# | Command Bar of Buttons      |
# |-----------------------------|
# | Output      | Debug         |
# |-----------------------------|
# | Configuration               |
# +=============================+
layout = [
    [ColImage, ColCurrentList, ColBookData],
    [ColFolder],
    [ColButtons],
    # [ ColOutput(visible=True), ColConfig(visible=False)],
    [ColOutput, ColConfig, ColConfigHelp],
]
# layout = [
#             [ ColImage, ColCurrentList,ColBookData],
#             [ ColButtons],
#             [ ColOutput],
#             [ ColConfig],
#          ]

# sg.set_options(tooltip_offset=(0,-20))
# sg.PySimpleGUI.DEFAULT_TOOLTIP_OFFSET = (0, -20)
sg.set_options(
    icon=base64.b64encode(
        open(
            r"/Users/tbrown/Documents/projects/CalibrePaginator/icon_CalibrePaginator.png",
            "rb",
        ).read()
    )
)
window = sg.Window(
    "Epub Paginator", layout, finalize=True, font="Menlo 12", size=(MainWindowSize)
)

# ------------------ initialize and build window--------------------
window["-srcdir-"].update(value=config["srcdir"])
# LogEvent(f"Config file is: {config_file}")
show_configure = False
show_help = True
debug_str = ""
toggle_configure(window)

# signon message
LogEvent('')
LogEvent(f"Epub Paginator Version {Version}")
LogEvent('')


# show_dict(config)
# window initialization code

# update the booklist, by default the current list
# GetCurrentList returns an array of books
# create a booklist for intial viewing
epub_database = []
save_database = []
bnamelist = []
flist = [f for f in os.listdir(config['srcdir']) if f.endswith(".epub")]
load_files(config['srcdir'], flist)
window["-BookList-"].update(values=bnamelist)
window["-BookList-"].SetValue(bnamelist[0])  # }}}
current_book = epub_database[0]
update_view(current_book)

# update the main display text field
window["-MLINE-" + sg.WRITE_ONLY_KEY].expand(
    expand_row=True, expand_x=True, expand_y=True
)
# update_view(current_book)

# and drop into the event loop
while True:
    event, values = window.read(timeout=100)
    # print(f"event: {event}")
    if event == "sg.TIMEOUT_KEY":
        continue
    if event in (None, "Quit", "-Exit-"):
        break
    # }}}
    # --About-------------------------------{{{
    elif event == "-About-":
        sg.main_get_debug_data()
        # sg.tclversion_detailed
    # }}}
    # --Help-------------------------------{{{
    elif event == "-Help-":
        if show_help:
            debug_str = window["-DEBUG-" + sg.WRITE_ONLY_KEY].get()
            window["-DEBUG-" + sg.WRITE_ONLY_KEY].update("")
            render_markdown(hprint, gui_help)
            window['-Help-'].update("Log")
            window['-DEBUG-' + sg.WRITE_ONLY_KEY].set_vscroll_position(0)
            show_help = False
        else:
            window["-DEBUG-" + sg.WRITE_ONLY_KEY].update("")
            window["-DEBUG-" + sg.WRITE_ONLY_KEY].update(debug_str)
            window['-Help-'].update("Help")
            show_help = True
    # }}}
    elif event == "-MLINE-":
        print("MLINE event: ")
        print(str(values["-MLINE-"]))

    # ---files-------------------------------------{{{
    elif event == "-files-":
        LogEvent("Event -files-")
        LogEvent(f'''Files selected: {values["-fbfiles-"]}''')
        flist = values['-fbfiles-'].split(';')
        load_files('', flist)
        if len(bnamelist):
            window["-BookList-"].update(values=bnamelist)
            window["-BookList-"].SetValue(bnamelist[0])  
            current_book = epub_database[0]
            update_view(current_book)
        else:
            LogWarning("No epubs selected.")
    # }}}

    # ---srcdir-------------------------------------{{{
    elif event == "-srcdir-":
        LogEvent("Event -srcdir-")
        directory = values["-srcdir-"]
        LogEvent(f"directory: {directory}")
        flist = [f for f in os.listdir(directory) if f.endswith(".epub")]
        load_files(directory, flist)
        if len(bnamelist):
            window["-BookList-"].update(values=bnamelist)
            window["-BookList-"].SetValue(bnamelist[0])  
            current_book = epub_database[0]
            update_view(current_book)
            # change the folder browser to start at this directory next time
            window["-fbsrcdir-"].InitialFolder = directory
            window["-fbsrcdir-"].update()
        else:
            LogWarning("No epubs found in {directory}")

    # }}}
    # --BookList-------------------------------------{{{
    elif event == "-BookList-":
        # the booklist of the form: "1. book by author"
        selection = values["-BookList-"][0]
        listentry = int(selection.split(".")[0])
        current_book = epub_database[listentry - 1]

        # if we split with no parameters, we get split on whitespace! this eats all leading spaces
        LogEvent("BookList: " + current_book["title"])
        update_view(current_book)
# }}}
    # --Find-----------------------------------------{{{
    elif event == "-Find-":
        if paginate_count:
            paginate_count = 0
            LogWarning("Pagination canceled.")
            LogWarning("Wait for completion message of in progress book.")
        else:
            if findlist_active:
                epub_database = copy.deepcopy(save_database)
                window['-Find-'].update("Find")
                findlist_active = False
                #update the booklist view.
                bnamelist = []
                idx = 1
                for book in epub_database:
                    bname = create_bookname(book["title"], book["author"])
                    if idx < 10:
                        bnamelist.append(f" {idx}. {book['title']} by {book['author']}")
                    else:
                        bnamelist.append(f"{idx}. {book['title']} by {book['author']}")
                    idx += 1
                window['-BookList-'].update(values=bnamelist)
                current_book = epub_database[0]
                update_view(current_book)
            else:
                searchstr = sg.popup_get_text(
                    "Search String:",
                    title="Find Book or Author",
                    font="Menlo 12",
                    location=window.mouse_location(),
                )
                if searchstr is not None:
                    findlist_active = True
                    window['-Find-'].update("ShowAll")
                    findlist = FindTitleAuthor(searchstr)
                    if len(findlist) == 0:
                        LogWarning("Nothing found")
                    else:
                        save_database = copy.deepcopy(epub_database)
                        epub_database = copy.deepcopy(findlist)
                        #update the booklist view.
                        bnamelist = []
                        idx = 1
                        for book in epub_database:
                            bname = create_bookname(book["title"], book["author"])
                            if idx < 10:
                                bnamelist.append(f" {idx}. {book['title']} by {book['author']}")
                            else:
                                bnamelist.append(f"{idx}. {book['title']} by {book['author']}")
                            idx += 1
                        window['-BookList-'].update(values=bnamelist)
                        current_book = epub_database[0]
                        update_view(current_book)
# }}}
    # --Configure -----------------------------------{{{
    elif event == "-Configure-":
        # LogEvent("Open Configure Page")
        toggle_configure(window)
        render_markdown(cprint, configuration_help)
        window['-config_help-' + sg.WRITE_ONLY_KEY].set_vscroll_position(0)
# }}}
    # --Cancel-----------------------------------{{{
    elif event == "-CancelConfig-":
        # LogEvent("Close config page without saving.")
        toggle_configure(window)
# }}}
    # --UpdateConfig-----------------------------------{{{
    elif event == "-UpdateConfig-":
        # LogEvent("Update config dictionary and close config page.")
        # LogEvent(f"cfgsrcdir: {window['-cfgsrcdir-'].get()}")
        update_config(values)
        window["-srcdir-"].update(value=config["srcdir"])
        window["-outdir-"].update(value=config["outdir"])
        toggle_configure(window)
        flist = [f for f in os.listdir(config['srcdir']) if f.endswith(".epub")]
        load_files(config['srcdir'], flist)
        window["-BookList-"].update(values=bnamelist)
        window["-BookList-"].SetValue(bnamelist[0])  
        current_book = epub_database[0]
        update_view(current_book)
        # change the folder browser to start at the directory next time
        window["-fbsrcdir-"].InitialFolder = config["srcdir"]
        window["-fbsrcdir-"].update()
    # }}}
    # --config_file-----------------------------------{{{
    elif event == "-config_file-":
        config_file = values["-config_file-"]
        if Path(config_file).is_file():
            # window["-config_label-"].update(f"Config File: {config_file}")
            LogEvent(f"-config_file- event; config_file input element: {config_file}")
            with open(config_file, "r") as cfg_file:
                config = json.loads(cfg_file.read())
                # now update the displayed window
                window["-outdir-"].update(config["outdir"])
                window["-genplist-"].update(config["genplist"])
                window["-match-"].update(config["match"])
                window["-pgwords-"].update(config["pgwords"])
                window["-pages-"].update(config["pages"])
                window["-pageline-"].update(config["pageline"])
                window["-pl_fntsz-"].update(config["pl_fntsz"])
                window["-align_left-"].update(config["pl_align"] == "left")
                window["-align_center-"].update(config["pl_align"] == "center")
                window["-align_right-"].update(config["pl_align"] == "right")
                window["-pl_color_red-"].update(config["pl_color"] == "red")
                window["-pl_color_green-"].update(config["pl_color"] == "green")
                window["-pl_color_none-"].update(config["pl_color"] == "none")
                window["-pl_pgtot-"].update(config["pl_pgtot"])
                window["-pl_bkt_angle-"].update(config["pl_bkt"])
                window["-pl_bkt_paren-"].update(config["pl_bkt"])
                window["-pl_bkt_none-"].update(config["pl_bkt"])
                window["-superscript-"].update(config["superscript"])
                window["-super_fntsz-"].update(config["super_fntsz"])
                window["-super_color_red-"].update(config["pl_color"])
                window["-super_color_green-"].update(config["pl_color"])
                window["-super_color_none-"].update(config["pl_color"])
                window["-ebookconvert-"].update(config["ebookconvert"])
                window["-epubcheck-"].update(config["epubcheck"])
                window["-chk_orig-"].update(config["chk_orig"])
                window["-chk_paged-"].update(config["chk_paged"])
                window["-quiet-"].update(config["quiet"])
                window["-DEBUG-"].update(config["DEBUG"])
    # }}}
    # --save_config-----------------------------------{{{
    elif event == "-save_config-":
        LogEvent(f"--> Save configuration file: {values['-save_config-']}.")
        # update the config dictionary first
        update_config(values)
        window["-srcdir-"].update(value=config["srcdir"])
        window["-outdir-"].update(value=config["outdir"])
        # then save the file
        with open(values["-save_config-"], "w") as cfg_file:
            cfg_file.write(json.dumps(config, indent=4))
    # }}}
    # --Paginate-----------------------------------{{{
    elif event == "-Paginate-":
        if current_book['modified']:
            LogWarning(f"{current_book['title']} has already been paginated by epubpager.")
            continue
        book_location = current_book['formats'][0]
        LogEvent("")
        LogEvent(f"Paginating {current_book['title']}")
        # set this globals so that -threadupdate- event stops properly.
        paginate_count = 0
        window.perform_long_operation(lambda : paginate_book(book_location), "-threadupdate-")
    # }}}
    # --Paginate All-----------------------------------{{{
    elif event == "-PaginateAll-":
        """
        Possibility:
        A. Must modify paginate_book to not call LogEvent, but rather store the output in a string.
        1. PaginateAll set up:
            1. Generate a list of books to paginate as paginate_list
            2. Toggle visibility of buttons to avoid interruption that is inconsistent.
               Set up Find button to enable stopping.
            3. pbook is set to 0, the first book in the list
            4. ptot is set to len(paginate_list)
            5. Generate an event called -NextBook-.
        2. Next Book event tasks:
            1. If stop_pagination is True, we have been terminated. 
               1. Reverse toggle of button visibility.
               2. exit the NextBook event without launching another pagination.
            2. if stop_pagination is False, paginate the next book using perform_long_operation which will generate another Next_Book event.
               1. When pagination is done, 
        """
        LogEvent("--> Paginate books in list.")
        window['-fbsrcdir-'].update(visible=False)
        window['-fbfiles-'].update(visible=False)
        window['-Paginate-'].update(visible=False)
        window['-PaginateAll-'].update(visible=False)
        window['-Configure-'].update(visible=False)
        window['-About-'].update(visible=False)
        window['-Help-'].update(visible=False)
        window['-Exit-'].update(visible=False)
        window['-Find-'].update("Cancel Paginate All")
        # build the paginate_list from the epub_database
        # paginating = True
        # cancel_pagination = False
        paginate_list = []
        for book in epub_database:
            if book['modified']:
                LogWarning(f"{book['title']} has already been paginated by epubpager.")
            else:
                paginate_list.append(book['formats'][0])
        paginate_count = len(paginate_list)
        book_location = paginate_list[paginate_count - 1]
        window.perform_long_operation(lambda : paginate_book(book_location), "-threadupdate-")

    # }}}
    elif event == "-threadupdate-":
        # update the text field with the return data from paginate_book
        LogEvent(values[event])
        paginate_count -= 1
        if paginate_count >= 0:
            book_location = paginate_list[paginate_count - 1]
            window.perform_long_operation(lambda : paginate_book(book_location), "-threadupdate-")
        else:
            LogWarning("All books paginated.")
            window['-fbsrcdir-'].update(visible=True)
            window['-fbfiles-'].update(visible=True)
            window['-Paginate-'].update(visible=True)
            window['-PaginateAll-'].update(visible=True)
            window['-Configure-'].update(visible=True)
            window['-About-'].update(visible=True)
            window['-Help-'].update(visible=True)
            window['-Exit-'].update(visible=True)
            window['-Find-'].update("Find")

window.close()
