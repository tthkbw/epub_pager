#!/usr/bin/env python3

import json
import argparse
from pathlib import Path
from epub_pager import epub_paginator

Version = "1.0"
# Version 1.0
# Added argparse for parsing command line options. There are options to set and
# default values for every option that epub_pager supports.
# changed name of footer to pageline

default_cfg = {
    "outdir": "/Users/tbrown/data_store/paged_epubs",
    "match": False,
    "genplist": True,
    "pgwords": 300,
    "pages": 0,
    "footer": False,
    "pl_align": "right",
    "pl_color": "red",
    "pl_bkt": "<",
    "pl_fntsz": "75%",
    "pl_pgtot": True,
    "superscript": True,
    "super_color": "red",
    "super_fntsz": "60%",
    "super_total": True,
    "chap_pgtot": True,
    "chap_bkt": "",
    "ebookconvert": "",
    "epubcheck": "/opt/homebrew/bin/epubcheck",
    "chk_orig": True,
    "DEBUG": False,
}

# setup and parse command line arguments
parser = argparse.ArgumentParser(description="Paginate ePub file.")
parser.add_argument("ePub_file", help="The ePub file to be paginated.")
parser.add_argument(
    "-c", "--cfg", default="", help="path to configuration file"
)
parser.add_argument(
    "--outdir", help="location for output ePub files", default="./"
)
parser.add_argument(
    "--match",
    help="If pagination exists, match it.",
    action=argparse.BooleanOptionalAction,
    default=True,
)
parser.add_argument(
    "--genplist",
    help=(
        "generate the navigation page list and page links " "for page numbers"
    ),
    action=argparse.BooleanOptionalAction,
    default=True,
)
parser.add_argument(
    "--pgwords",
    help="define words per page; if 0, use pages",
    type=int,
    default=300,
)
parser.add_argument(
    "--pages",
    help="if = 0 use pgwords; else pgwords=(wordcount/pages)",
    type=int,
    default=0,
)
parser.add_argument(
    "--pageline",
    help="generate and insert page pagelinesinto the ePub text",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "--pl_align",
    help="'right', 'left' or 'center'; "
    "specify alignment of the pageline",
    default="right",
)
parser.add_argument(
    "--pl_color",
    choices=["red", "blue", "green", "none"],
    help="html color for the inserted pageline",
    default="none",
)
parser.add_argument(
    "--pl_bkt",
    choices=["<", "(", "none"],
    help="character to use to bracket page number",
    default="<",
)
parser.add_argument(
    "--pl_fntsz",
    help="font size as percentage of book font for the pageline",
    default="75%",
)
parser.add_argument(
    "--pl_pgtot",
    help="include total pages in the pageline",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "--superscript",
    help="generate superscripted page numbers",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "--super_color",
    choices=["red", "blue", "green", "none"],
    help="html color for the inserted page pagelinee.g. 'red'",
)
parser.add_argument(
    "--super_fntsz",
    help="font size as percentage of book font for the pageline",
    default="60%",
)
parser.add_argument(
    "--super_total",
    help="include total pages in the pageline",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "--chap_pgtot",
    help="include chapter page and total in the pagelineand/or superscript",
    action=argparse.BooleanOptionalAction,
    default=True,
)
parser.add_argument(
    "--chap_bkt",
    help="'<', '(' or nothing; character to use to bracket page number",
    default="",
)
parser.add_argument(
    "--epubcheck", help="location of epubcheck executable", default="none"
)
parser.add_argument(
    "--chk_orig",
    help="Run epubcheck on original file",
    action=argparse.BooleanOptionalAction,
    default="True",
)
parser.add_argument(
    "--ebookconvert",
    help="location of ebook conversion executable",
    default="none",
)
parser.add_argument(
    "--DEBUG",
    help="print additional debug information to the log file",
    action=argparse.BooleanOptionalAction,
    default=False,
)
args = parser.parse_args()


def get_config(args) -> dict:
    if args.cfg:
        cfile = Path(args.cfg)
        if cfile.exists():
            print(f"Using config file {args.cfg}")
            with cfile.open("r") as config_file:
                return dict(json.loads(config_file.read()))
        else:
            return(dict({}))
    else:
        # no config file, build the config from the parameters
        config = dict({})
        config["outdir"] = args.outdir
        config["match"] = args.match
        config["genplist"] = args.genplist
        config["pgwords"] = args.pgwords
        config["pages"] = args.pages
        config["pageline"] = args.pageline
        config["pl_align"] = args.pl_align
        config["pl_color"] = args.pl_color
        config["pl_bkt"] = args.pl_bkt
        config["pl_fntsz"] = args.pl_fntsz
        config["pl_pgtot"] = args.pl_pgtot
        config["superscript"] = args.superscript
        config["super_color"] = args.super_color
        config["super_fntsz"] = args.super_fntsz
        config["super_total"] = args.super_total
        config["chap_pgtot"] = args.chap_pgtot
        config["chap_bkt"] = args.chap_bkt
        config["ebookconvert"] = args.ebookconvert
        config["epubcheck"] = args.epubcheck
        config["chk_orig"] = args.chk_orig
        config["DEBUG"] = args.DEBUG
        return (dict(config))


# get the config file to set things up
config = get_config(args)
if len(config):
    for dkey in config.keys():
        print(f"{dkey}: {config[dkey]}")
else:
    print(f"Configuration failed.")
paginator = epub_paginator()
paginator.outdir = config["outdir"]
paginator.match = config["match"]
paginator.genplist = config["genplist"]
paginator.pgwords = config["pgwords"]
paginator.pages = config["pages"]
paginator.pageline= config["pageline"]
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
paginator.DEBUG = config["DEBUG"]

return_dict = paginator.paginate_epub(args.ePub_file)
print()
print(f"Paginated ebook created: {return_dict['bk_outfile']}")
print(f"Paginated ebook log: {return_dict['logfile']}")
print()

b_edb = {}
b_edb["pager_fatal"] = return_dict["fatal"]
b_edb["pager_error"] = return_dict["fatal"]
b_edb["pager_warn"] = return_dict["fatal"]
b_edb["orig_fatal"] = return_dict["orig_fatal"]
b_edb["orig_error"] = return_dict["orig_error"]
b_edb["orig_warn"] = return_dict["orig_warn"]
b_edb["echk_fatal"] = return_dict["echk_fatal"]
b_edb["echk_error"] = return_dict["echk_error"]
b_edb["echk_warn"] = return_dict["echk_warn"]
if b_edb["pager_fatal"]:
    print("  --> Fatal error in epub_pager.")
if b_edb["pager_error"]:
    print("  --> Error in epub_pager.")
if b_edb["pager_warn"]:
    print("  --> Warning in epub_pager.")
print()
lpad = 10
rpad = 50
if b_edb["echk_fatal"] or b_edb["orig_fatal"]:
    s = "Fatal Errors"
    print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")
    print(
        f"  --> {b_edb['echk_fatal']:3} fatal "
        f"error(s) in paged book epubcheck."
    )
    print(
        f"  --> {b_edb['orig_fatal']:3} fatal "
        f"error(s) in original book epubcheck."
    )
if b_edb["echk_error"] or b_edb["orig_error"]:
    s = "Warnings"
    print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")
    print(f"  --> {b_edb['echk_error']:3} error(s) in paged book epubcheck.")
    print(
        f"  --> {b_edb['orig_error']:3} error(s) in original book epubcheck."
    )
if b_edb["echk_warn"] or b_edb["orig_warn"]:
    s = "Warnings"
    print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")
    print(f"  --> {b_edb['echk_warn']:3} warning(s) in paged book epubcheck.")
    print(
        f"  --> {b_edb['orig_warn']:3} warning(s) in original book epubcheck."
    )
print("-" * (lpad + rpad))
