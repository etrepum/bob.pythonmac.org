#!/usr/bin/env python
import os
import sys
import glob
from cStringIO import StringIO
from subprocess import Popen, PIPE
CMD = 'rst2html.py --no-toc-backlinks --no-doc-title --no-generator --no-source-link --no-footnote-backlinks --initial-header-level=2'.split()
INGLOB = '../_rstposts/*.rst'
OUTDIR = '../_posts'


def rst2html(fn, outfn):
    s = open(fn, 'rb').read()
    end_prefix = s.index('\n\n')
    pre, post = s[:end_prefix], s[end_prefix:]
    p = Popen(CMD, stdin=PIPE, stdout=PIPE)
    code_post = post.replace(
        '\n.. pycode', '\n').replace('\n  .. pycode', '\n  ')
    out_html = p.communicate(code_post)[0]
    outf = open(outfn, 'wb')
    outf.write(pre)
    # no fragment support in rst2html.py
    if '<div class="document">' in out_html:
        out_html = out_html.partition('<div class="document">')[2].rpartition('</div>')[0]
    outf.write(out_html)
    outf.close()


def main():
    for fn in glob.glob(INGLOB):
        outfn = os.path.join(OUTDIR, os.path.basename(fn)).replace('.rst', '.html')
        rst2html(fn, outfn)


if __name__ == '__main__':
    main()
