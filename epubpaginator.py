#!/usr/bin/env python3

import json
import argparse
from pathlib import Path
from epubpager import epub_paginator
from typing import Dict

# Version 1.0
# Added argparse for parsing command line options. There are options to set and
# default values for every option that epub_pager supports.
# changed name of footer to pageline

# default_cfg = {
#     "outdir": "/Users/tbrown/data_store/paged_epubs",
#     "match": False,
#     "genplist": True,
#     "pgwords": 300,
#     "pages": 0,
#     "pageline": False,
#     "pl_align": "right",
#     "pl_color": "red",
#     "pl_bkt": "<",
#     "pl_fntsz": "75%",
#     "pl_pgtot": True,
#     "superscript": True,
#     "super_color": "red",
#     "super_fntsz": "60%",
#     "super_total": True,
#     "chap_pgtot": True,
#     "chap_bkt": "",
#     "ebookconvert": "/Applications/calibre.app/Contents/MacOS/ebook-convert",
#     "chk_orig": True,
#     "chk_paged": True,
#     "DEBUG": False,
# }

# setup and parse command line arguments
def main():
    Version = "1.0"
    parser = argparse.ArgumentParser(description="Paginate ePub file.")
    parser.add_argument("ePub_file", help="The ePub file to be paginated.")
    parser.add_argument("-c", "--cfg", default="", help="configuration file")
    parser.add_argument("--outdir", help="location for output ePub files", default="./")
    parser.add_argument(
        "--match",
        help="If pagination exists, match it.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--genplist",
        help=("If no pagination generate the navigation page list and page links"),
        # action=argparse.BooleanOptionalAction,
        action="store_true",
        default=False,
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
        # action=argparse.BooleanOptionalAction,
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--pl_align",
        choices=["right", "left", "center"],
        help="'right', 'left' or 'center'; " "specify alignment of the pageline",
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
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--superscript",
        help="generate superscripted page numbers",
        action="store_true",
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
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--chap_pgtot",
        help="include chapter page and total in the pagelineand/or superscript",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--chap_bkt",
        choices=["<", "(", "none"],
        help="'<', '(' or nothing; character to use to bracket page number",
        default="none",
    )
    parser.add_argument(
        "--epubcheck",
        help="location of epubcheck external executable",
        default="none",
    )
    parser.add_argument(
        "--chk_paged", 
        help="Run epubcheck on paged epub file", 
        action = "store_true",
        default = False,
    )
    parser.add_argument(
        "--chk_orig",
        help="Run epubcheck on file being paginated",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--ebookconvert",
        help="location of ebook conversion executable",
        default="none",
    )
    parser.add_argument(
        "--DEBUG",
        help="print additional debug information to the log file",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    # def get_config(args) -> Dict:
    def get_config(args):
        if args.cfg:
            cfile = Path(args.cfg)
            if cfile.exists():
                # print(f" --> Using config file {args.cfg}")
                with cfile.open("r") as config_file:
                    return dict(json.loads(config_file.read()))
            else:
                print(f" --> Aborted: Specified configuration file {args.cfg} not found.")
                return dict({})
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
            config["chk_paged"] = args.chk_paged
            config["DEBUG"] = args.DEBUG
            return dict(config)


    # get the config file to set things up
    config = get_config(args)
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
    paginator.epubcheck= config["epubcheck"]
    paginator.chk_orig = config["chk_orig"]
    paginator.chk_paged= config["chk_paged"]
    paginator.DEBUG = config["DEBUG"]


    lpad = 10
    rpad = 50
    print()
    print("-" * (lpad + rpad))
    print(f"Epub Paginator version {Version}")
    print()
    print(f"Paginating {args.ePub_file}")

    return_dict = {}
    return_dict = paginator.paginate_epub(args.ePub_file)

    # for key in return_dict.keys():
    #     if key == 'spine_lst':
    #         continue
    #     elif key == 'manifest':
    #         continue
    #     else:
    #         print(f"{key}: {return_dict[key]}")

    # if return_dict['epub_version'][0] == '3':
    #     print(f" --> This is an ePub 3 book.")
    # else:
    #     print(f" --> This is an ePub 2 book.")
    # if return_dict["converted"]:
    #     print(f" --> This epub book was converted to epub3.")
    if return_dict["pager_error"]:
        pager_err= True
        # print()
        print(" --> Fatal errors occurred in epub_pager. Book may not be properly paginated.")
        if return_dict['epub_version'][0] == '2':
            print(" --> This is an ePub2 book. Often if books are first converted to ePub3 epubpaginator can successfully paginate them.")
            for e in return_dict['error_lst']:
                print(f"   --> {e}")
            print(f"See details in log: {return_dict['logfile']}")

    echk_err = False
    pager_err = False
    pager_warn = False
    if return_dict["pager_warn"]:
        pager_warn= True
        print("  --> There were warnings in epub_pager.")
        for w in return_dict['warn_lst']:
            print(f"   --> {w}")
        print(f"See details in log: {return_dict['logfile']}")
    if return_dict["echk_fatal"] or return_dict["orig_fatal"]:
        echk_err = True
        s = "Fatal Errors"
        print()
        print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")
        print(f"  --> {return_dict['echk_fatal']:3} fatal " f"error(s) in paged book epubcheck.")
        print(
            f"  --> {return_dict['orig_fatal']:3} fatal " f"error(s) in original book epubcheck."
        )
    if return_dict["echk_error"] or return_dict["orig_error"]:
        echk_err = True
        s = "Errors"
        print()
        print(f"{'-' * lpad}{s}{'-' * (rpad - len(s))}")
        print(f"  --> {return_dict['echk_error']:3} error(s) in paged book epubcheck.")
        print(f"  --> {return_dict['orig_error']:3} error(s) in original book epubcheck.")
    if not pager_err and not pager_warn and not echk_err:
        print()
        print(f"Processing completed without error.")
        if not pager_err:
            print(f"Paginated ebook created: {return_dict['bk_outfile']}")
    print("-" * (lpad + rpad))
    print()

if __name__ == "__main__":
    main()
