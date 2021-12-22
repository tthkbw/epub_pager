#!/opt/homebrew/bin/python3

import rpyc
import json
import sys
import argparse
from pathlib import Path
from subprocess import PIPE, run
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
    "chk_orig": True,
    "DEBUG": False
}

# setup and parse command line arguments
parser = argparse.ArgumentParser(description='Paginate ePub file.')
parser.add_argument(
        'ePub_file',
        help='The ePub file to be paginated.')
parser.add_argument(
        '-c',
        '--cfg',
        default='',
        help='path to configuration file')
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
        '--chk_orig',
        help='Run epubcheck on original file',
        action=argparse.BooleanOptionalAction,
        default='True')
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

def get_config(args):
    if args.cfg:
        cfile = Path(args.cfg)
        if cfile.exists():
            print(f'Using config file {args.cfg}')
            with cfile.open('r') as config_file:
                return(json.loads(config_file.read()))
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
        config["chk_orig"] = args.chk_orig
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
print()

b_edb = {}
b_edb['pager_fatal'] = False
b_edb['pager_error'] = False
b_edb['pager_warn'] = False
b_edb['orig_fatal'] = False
b_edb['orig_error'] = False
b_edb['orig_warn'] = False
b_edb['echk_fatal'] = False
b_edb['echk_error'] = False
b_edb['echk_warn'] = False
epubchk_error = False
orig_epubchk_error = False
# run epubcheck on original for comparisons
print('--------------------')
if config['chk_orig']:
    epubcheck_cmd = [config['epubcheck'],args.ePub_file]
    result = run(epubcheck_cmd,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True)
    with Path(return_dict['logfile']).open('a') as logfile:
        logfile.write('Appending original epubcheck output:')
        logfile.write(result.stdout)
        logfile.write(result.stderr)
    # check and log the errors from epubcheck
    for line in result.stdout.splitlines():
        # Messages: 0 fatals / 0 errors / 0 warnings
        # 0         1 2      3 4  5     6    7
        if line.find('Messages:') != -1:
            w = line.split(' ')
            if w[1] != '0':
                print(f'  --> Fatal in original epubcheck')
                b_edb['orig_fatal'] = True
                orig_epubchk_error = True
            if w[4] != '0':
                print('  --> Error in original epubcheck')
                b_edb['orig_error'] = True
                orig_epubchk_error = True
            if w[7] != '0':
                print('  --> Warning in original epubcheck')
                b_edb['orig_warn'] = True
b_edb['pager_fatal'] = return_dict['fatal']
b_edb['pager_error'] = return_dict['error']
b_edb['pager_warn'] = return_dict['warn']
b_edb['echk_fatal'] = return_dict['echk_fatal']
b_edb['echk_error'] = return_dict['echk_error']
b_edb['echk_warn'] = return_dict['echk_warn']
if b_edb['echk_fatal']:
    print('  --> Fatal error in paged book epubcheck.')
    epubchk_error = True
if b_edb['echk_error']:
    print('  --> Error in paged book epubcheck.')
    epubchk_error = True
if b_edb['echk_warn']:
    print('  --> Warning in paged book epubcheck.')
print('--------------------')
if b_edb['orig_fatal'] != b_edb['echk_fatal']:
    if edb['orig_fatal']:
        print(f' - Original has fatal; paged does not.')
    else:
        print(f' - Paged has fatal; original does not.')
if b_edb['orig_error'] != b_edb['echk_error']:
    if edb['orig_error']:
        print(f' - Original has error; paged does not.')
    else:
        print(f' - Paged has error; original does not.')
if b_edb['orig_warn'] != b_edb['echk_warn']:
    if b_edb['orig_warn']:
        print(f' - Original has warning; paged does not.')
    else:
        print(f' - Paged has warning; original does not.')
print('--------------------')
if b_edb['pager_fatal']:
    print('  --> Fatal error in epub_pager.')
if b_edb['pager_error']:
    print('  --> Error in epub_pager.')
if b_edb['pager_warn']:
    print('  --> Warning in epub_pager.')

