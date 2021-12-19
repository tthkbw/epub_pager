#!/opt/homebrew/bin/python3

import rpyc
import json
import sys
import argparse
from pathlib import Path
from epub_pager import epub_paginator

Version = '1.0'
# Version 1.0
# Added argparse for parsing command line options. There are options to set and
# default values for every option that epub_pager supports.

default_cfg = {
    "outdir": "/Users/tbrown/data_store/paged_epubs",
    "match": False,
    "genplist": True,
    "pgwords": 300,
    "pages": 0,
    "footer": False,
    "ft_align": "right",
    "ft_color": "red",
    "ft_bkt": "<",
    "ft_fntsz": "75%",
    "ft_pgtot": True,
    "superscript": True,
    "super_color": "red",
    "super_fntsz": "60%",
    "super_total": True,
    "chap_pgtot": True,
    "chap_bkt": "",
    "ebookconvert": "",
    "epubcheck": "/opt/homebrew/bin/epubcheck",
    "DEBUG": False
}

# setup and parse command line arguments
parser = argparse.ArgumentParser(description='Paginate ePub file.')
parser.add_argument(
        '-c',
        '--cfg',
        default='',
        help='path to configuration file')
parser.add_argument(
        'ePub_file',
        help='The ePub file to be paginated.')
parser.add_argument(
        '--outdir',
        help='location for output ePub files',
        default='./')
parser.add_argument(
        '--match',
        help='If pagination exists, match it.',
        action=argparse.BooleanOptionalAction,
        default=True)
parser.add_argument(
        '--genplist',
        help=('generate the navigation page list and page links '
              'for page numbers'),
        action=argparse.BooleanOptionalAction,
        default=True)
parser.add_argument(
        '--pgwords',
        help='define words per page; if 0, use pages',
        type=int,
        default=300)
parser.add_argument(
        '--pages',
        help='if = 0 use pgwords; else pgwords=(wordcount/pages)',
        type=int, default=0)
parser.add_argument(
        '--footer',
        help='generate and insert page footers into the ePub text',
        action=argparse.BooleanOptionalAction,
        default=False)
parser.add_argument(
        '--ft_align',
        help="'right', 'left' or 'center'; "
             "specify alignment of the page footer",
        default='right')
parser.add_argument(
        '--ft_color',
        choices=['red', 'blue', 'green', 'none'],
        help="html color for the inserted page footer",
        default='none')
parser.add_argument(
        '--ft_bkt',
        choices=['<', '(', 'none'],
        help="character to use to bracket page number",
        default='<')
parser.add_argument(
        '--ft_fntsz',
        help='font size as percentage of book font for the footer',
        default='75%')
parser.add_argument(
        '--ft_pgtot',
        help='include total pages in the footer',
        action=argparse.BooleanOptionalAction,
        default=False)
parser.add_argument(
        '--superscript',
        help='generate superscripted page numbers',
        action=argparse.BooleanOptionalAction,
        default=False)
parser.add_argument(
        '--super_color',
        choices=['red', 'blue', 'green', 'none'],
        help="html color for the inserted page footer e.g. 'red'")
parser.add_argument(
        '--super_fntsz',
        help='font size as percentage of book font for the footer',
        default='60%')
parser.add_argument(
        '--super_total',
        help='include total pages in the footer',
        action=argparse.BooleanOptionalAction,
        default=False)
parser.add_argument(
        '--chap_pgtot',
        help='include chapter page and total in the footer and/or superscript',
        action=argparse.BooleanOptionalAction,
        default=True)
parser.add_argument(
        '--chap_bkt',
        help="'<', '(' or nothing; character to use to bracket page number",
        default='')
parser.add_argument(
        '--epubcheck',
        help='location of epubcheck executable',
        default='none')
parser.add_argument(
        '--ebookconvert',
        help='location of ebook conversion executable',
        default='none')
parser.add_argument(
        '--DEBUG',
        help='print additional debug information to the log file',
        action=argparse.BooleanOptionalAction,
        default=False)
args = parser.parse_args()

# the config file may be local, which has precedence, or in the
# ~/.config/BookTally directory


def get_config(args):
    cfile = Path(args.cfg)
    if cfile.exists():
        print(f'Using config file {args.cfg}')
        with cfile.open('r') as config_file:
            return(json.loads(config_file.read()))
    else:
        if DEBUG:
            print('Configuration file {cfg_file} not found!')
        else:
            # no config file, build the config from the parameters
            config = {}
            config["outdir"] = args.outdir
            config["match"] = args.match
            config["genplist"] = args.genplist
            config["pgwords"] = args.pgwords
            config["pages"] = args.pages
            config["footer"] = args.footer
            config["ft_align"] = args.ft_align
            config["ft_color"] = args.ft_color
            config["ft_bkt"] = args.ft_bkt
            config["ft_fntsz"] = args.ft_fntsz
            config["ft_pgtot"] = args.ft_pgtot
            config["superscript"] = args.superscript
            config["super_color"] = args.super_color
            config["super_fntsz"] = args.super_fntsz
            config["super_total"] = args.super_total
            config["chap_pgtot"] = args.chap_pgtot
            config["chap_bkt"] = args.chap_bkt
            config["ebookconvert"] = args.ebookconvert
            config["epubcheck"] = args.epubcheck
            config["DEBUG"] = args.DEBUG
            return(config)

# get the config file to set things up
config = get_config(args)
for dkey in config.keys():
    print(f'{dkey}: {config[dkey]}')
paginator = epub_paginator()
paginator.outdir = config['outdir']
paginator.match = config['match']
paginator.genplist = config['genplist']
paginator.pgwords = config['pgwords']
paginator.pages = config['pages']
paginator.footer = config['footer']
paginator.ft_align = config['ft_align']
paginator.ft_color = config['ft_color']
paginator.ft_bkt = config['ft_bkt']
paginator.ft_fntsz = config['ft_fntsz']
paginator.ft_pgtot = config['ft_pgtot']
paginator.superscript = config['superscript']
paginator.super_color = config['super_color']
paginator.super_fntsz = config['super_fntsz']
paginator.super_total = config['super_total']
paginator.chap_pgtot = config['chap_pgtot']
paginator.chap_bkt = config['chap_bkt']
paginator.ebookconvert = config['ebookconvert']
paginator.epubcheck = config['epubcheck']
paginator.DEBUG = config['DEBUG']

return_dict = paginator.paginate_epub(args.ePub_file)

print()
print(f"Paginated ebook created: {return_dict['bk_outfile']}")
print(f"Paginated ebook log: {return_dict['logfile']}")
error = False
print()
if return_dict['fatal']:
    error = True
    print(f"--> Fatal Error reported.")
    for error in return_dict['errors']:
        print(f' ----> {error}')
if return_dict['echk_fatal']:
    error = True
    print(f"--> Fatal error reported in epubcheck.")
if return_dict['echk_error']:
    error = True
    print(f"--> Error reported in epubcheck.")
if return_dict['echk_warn']:
    error = True
    print(f"--> Warning reported in epubcheck.")
if not error:
    print('No errors detected.')
# print out the epub info structure
# print(return_dict['epub_info'].items())
print(return_dict['messages'])
