from shutil import copyfile
from subprocess import PIPE, run
import os

ebook_file = '/Users/tbrown/Documents/Calibre Library/Michael Connelly/The Dark Hours (1041)/The Dark Hours - Michael Connelly.epub'

epub3_file = ebook_file.replace('.epub','epub3.epub')
print(epub3_file)

ebookconvert_cmd = ['/Applications/calibre.app/Contents/MacOS/ebook-convert',ebook_file,epub3_file, '--epub-version', '3']
result = run(ebookconvert_cmd, stdout=PIPE, stderr=PIPE,universal_newlines=True)
print(result.returncode)
# print (result.stdout)
print (result.stderr)
