# -*- coding: utf-8 -*-

import os,re
import hashlib
import json

import oscar
import extract

def parser_setup(parser):
    parser.add_argument("-d", "--base-dir", default=".")
    parser.add_argument("args", nargs='*')
    parser.set_defaults(func=run,name="add")

def calc_file_hash(filename, blocksize=65536):
    hasher = hashlib.sha1()
    with open(filename, "rb") as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()

def add_file(context, base_dir, filename):
    filename = re.sub(r'^\/+', "", filename)
    exact_filename = os.path.join(base_dir, filename)
    if not os.path.isfile(exact_filename):
        oscar.log.error("File %s does not exist" % exact_filename)
        return False

    file_hash = calc_file_hash(exact_filename)
    oscar.log.debug("File hash: %s" % file_hash)

    with oscar.command(context, "select") as command:
        command.add_argument("table", "Fulltext")
        command.add_argument("output_columns", "_id")
        command.add_argument("filter","_key == '%s'" % file_hash)
        num_hits = json.loads(command.execute())[0][0][0]

    if num_hits == 0:  # まだ登録されてない場合
        extractor = extract.get_extractor(exact_filename)
        if extractor:
            text = extractor(exact_filename)
            row = {"_key":file_hash, "content": text }
            with oscar.command(context, "load") as command:
                command.add_argument("table", "Fulltext")
                command.add_argument("values", json.dumps([row]))
                command.execute()

    path = os.path.dirname(filename)
    if not path.endswith('/'): path += '/'
    row = {"_key":oscar.sha1(filename), "path":path, "path_ft":path, "name":os.path.basename(filename), "fulltext":file_hash }
    oscar.log.info("Adding: %s" % exact_filename)

    with oscar.command(context, "load") as command:
        command.add_argument("table", "Files")
        command.add_argument("values", json.dumps([row]))
        command.execute()

    return True

def run(args):
    with oscar.context(args.base_dir) as context:
        for filename in args.args:
            add_file(context, args.base_dir, filename)

    oscar.log.info("Files added.")
