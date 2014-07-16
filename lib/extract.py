#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

'''
USE="python tools" emerge nkf xlrd poppler wv xlhtml elinks lxml
caution: nkf-2.0.7 is buggy
'''

'''
[ebuild  N     ] dev-libs/kpathsea-6.1.0_p20120701  USE="-doc -source -static-libs" 
[ebuild  N     ] app-text/dvipsk-5.992_p20120701  USE="-doc -source" 
[ebuild  N     ] app-text/ps2pkm-1.5_p20120701 
[ebuild  N     ] sys-apps/ed-1.6 
[ebuild  N     ] dev-tex/bibtexu-3.71_p20120701 
[ebuild  N     ] dev-tex/luatex-0.70.1-r2  USE="-doc" 
[ebuild  N     ] app-text/texlive-core-2012-r1  USE="-X -cjk -doc -source -tk -xetex" 
[ebuild  N     ] dev-texlive/texlive-documentation-base-2012  USE="-source" 
[ebuild  N     ] dev-texlive/texlive-basic-2012  USE="-doc -source" 
[ebuild  N     ] dev-texlive/texlive-latex-2012  USE="-doc -source" 
[ebuild  N     ] app-text/wv-1.2.9-r1  USE="tools -wmf" 
'''

import sys,os,re,subprocess,StringIO,codecs
import nkf,xlrd
import officex

class IndexingFailureException(Exception):
    def __init__(self, msg):
        self.str = msg
    def __str__(self):
        return u"Indexing failure '%s'" % (self.str)

def process_output(cmdline, timeout=30):
    proc = subprocess.Popen(["/usr/bin/timeout",str(timeout)] + cmdline, shell=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdoutdata, stderrdata = proc.communicate()
    rst = proc.wait()
    if rst == 124:
        raise IndexingFailureException("Process Timeout (%dsec)" % timeout)
    elif rst != 0:
        raise IndexingFailureException(stderrdata)
    return stdoutdata

def utf8_cleanup(text):
    if isinstance(text, str):
        #return nkf.nkf("-w", text)   # causes MemoryError
        return text
    #else
    return text.encode("utf-8")

def elinks(html):
    my_env = os.environ.copy()
    my_env["LANG"] = "ja_JP.utf8"
    elinks = subprocess.Popen(["/usr/bin/timeout","10","/usr/bin/elinks","-dump","-dump-width","1000","-dump-charset","utf-8"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=my_env)
    text, stderrdata = elinks.communicate(html)
    rst = elinks.wait()
    if rst == 124: IndexingFailureException("Elinks Process Timeout (10sec)")
    elif rst != 0: raise IndexingFailureException(stderrdata)
    return ("", utf8_cleanup(text))

def unoconv(os_pathname):
    html = process_output(["/usr/bin/unoconv","-f","html","--stdout",os_pathname], 30)
    lynx = subprocess.Popen(["/usr/bin/lynx","-stdin","-dump","-width","1000"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    text, stderrdata = lynx.communicate(html)
    if lynx.wait() != 0: raise IndexingFailureException(stderrdata)
    return ("", utf8_cleanup(text))

def ppthtml(os_pathname):
    html = process_output(["/usr/bin/ppthtml",os_pathname])
    title, text = elinks(html)
    text = re.sub(ur'[ 　]+', ' ', text.decode("utf-8"))
    text = re.sub(ur'_+', '_', text)
    text = re.sub(ur'-+', '-', text)
    return (title, utf8_cleanup(text))

def xl(os_pathname):
    def cell2str(cell):
        if (cell.ctype == xlrd.XL_CELL_TEXT): return cell.value
        if (cell.ctype == xlrd.XL_CELL_NUMBER): return unicode(cell.value)
        return ""

    out = StringIO.StringIO()
    book = xlrd.open_workbook(os_pathname)
    for i in range(0, book.nsheets):
        sheet = book.sheet_by_index(i)
        out.write(sheet.name + '\n')
        for row in range(0, sheet.nrows):
            out.write('\t'.join(map(lambda col:cell2str(sheet.cell(row,col)), range(0, sheet.ncols))) + '\n')
    text = re.sub(ur'[ 　]+', ' ', out.getvalue())
    return ("", utf8_cleanup(text))

def wvhtml(os_pathname):
    html = process_output(["/usr/bin/wvWare", "--nographics", os_pathname])
    title, text = elinks(html)
    text = re.sub(ur'[ 　]+', ' ', text.decode("utf-8"))
    text = re.sub(ur'-+', '-', text)
    return (title, utf8_cleanup(text))

def pdftotext(os_pathname):
    text = process_output(["/usr/bin/pdftotext",os_pathname, "-"])
    return ("", utf8_cleanup(text))

def text(os_pathname):
    if os.stat(os_pathname).st_size > 1024 * 1024 * 10:
        return "***TOO LARGE TEXT FILE***" 
    # else
    text = open(os_pathname).read()
    return ("", utf8_cleanup(text))

def htmltotext(os_pathname):
    html = open(os_pathname).read()
    html = nkf.nkf("-w", html)
    return elinks(html)

def officexml(os_pathname):
    text = officex.extract(os_pathname)
    if not text: raise IndexingFailureException("Empty document")
    return ("", utf8_cleanup(text))

extractor_funcs = {
    ".xls":xl,
    ".xlsx":xl,
    ".doc":wvhtml,
    ".docx":officexml,
    ".ppt":ppthtml,
    ".pptx":officexml,
    ".pdf":pdftotext,
    ".txt":text,
    ".csv":text,
    ".tsv":text,
    ".htm":htmltotext,
    ".html":htmltotext
}

def get_extractor(fullpath):
    extractor_func = None
    for suffix, func in extractor_funcs.iteritems():
        if fullpath.lower().endswith(suffix):
            extractor_func = func
            break
    return extractor_func

def parser_setup(parser):
    parser.add_argument("file", nargs='+')
    parser.set_defaults(func=run,name="extract")


def run(args):
    for filename in args.file:
        print "Extracting %s..." % filename
        extractor = get_extractor(filename)
        if extractor:
            sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
            title, content = extractor(filename)
            sys.stdout.write(title)
            sys.stdout.write(content)
        else:
            print "%s skipped(no extractor)" % filename

