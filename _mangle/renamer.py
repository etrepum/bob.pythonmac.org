#!/usr/bin/env python
import os
import sys
import glob
import yaml
import re
INGLOB = '../_posts/*'
OUTDIR = '../_jekyll'
URL_RE = re.compile(r'''^http://bob\.pythonmac\.org/(?P<category>[^/]+)/(?P<year>[^/]+)/(?P<month>[^/]+)/(?P<day>[^/]+)/(?P<slug>[^/]+)/?$''')

def renamer(fn, outdir):
    FM_PREFIX = '---\n'
    FM_BREAK = '\n' + FM_PREFIX
    with open(fn, 'rb') as f:
        s = f.read()
    assert s.startswith(FM_PREFIX)
    fm_index = s.index(FM_BREAK)
    fm = yaml.load(s[len(FM_PREFIX):fm_index])
    body = s[fm_index + len(FM_BREAK):]
    link_info = URL_RE.match(fm['permalink']).groupdict()
    out_fm = {
        'layout': 'post',
        'title': fm['title'],
        'category': link_info['category'],
        'categories': filter(None, fm['categories'].split(', ')),
        'tags': filter(None, fm.get('tags', '').split(', ')),
        }
    ext = os.path.splitext(fn)[1]
    out_fn = os.path.join(
        outdir,
        ('%(year)s-%(month)s-%(day)s-%(slug)s' % link_info) + ext)
    with open(out_fn, 'wb') as f:
        f.writelines([FM_PREFIX,
                      yaml.dump(out_fm).rstrip(),
                      FM_BREAK,
                      '{% include JB/setup %}\n\n{% raw %}\n',
                      body.strip(),
                      '\n{% endraw %}\n'])
    print fn, out_fn


def main():
    for fn in glob.glob(INGLOB):
        renamer(fn, OUTDIR)


if __name__ == '__main__':
    main()
