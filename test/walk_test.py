#!/usr/bin/python2.7
# -*- coding:utf-8 mode:python -*-

import os,sys,shutil,re

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../lib')

import oscar,init,walk,consume,search

base_dir = "tmp"

def perform_walk(base_dir):
    for root, dirs, files in os.walk(base_dir):
        dir = re.sub(r'^\/+', "", root[len(base_dir):])
        if dir.startswith('.'): continue

        print dir, files
    
    #with oscar.context(base_dir) as context:
    #    walk.walk(context, base_dir)
    #consume.consume(base_dir)

def perform_search():
    with oscar.context(base_dir) as context:
        return search.search(context, "", "公募", 0, 10)

if __name__ == '__main__':
    oscar.init()
    oscar.logger_init("walk-test", True)
    
    init.init(base_dir)
    
    os.system("unzip -q -d %s testdata.zip" % base_dir)
    
    try:
        perform_walk(base_dir)
        #print perform_search()
    finally:
        oscar.fin()
        shutil.rmtree(base_dir)
