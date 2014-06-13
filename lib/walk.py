# -*- coding: utf-8 -*-
import os,re,json

import oscar

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="walk")


class QueueWriter:
    def __init__(self, context, base_dir):
        self.buffer = []
        self.context = context
        self.base_dir = base_dir

    def enqueue(self, filename, size):
        exact_filename = os.path.join(self.base_dir, filename)
        if not os.path.isfile(exact_filename):
            oscar.log.error("File not found: %s" % exact_filename)
            return False
        #else
        self.buffer.append({"_key":oscar.sha1(filename),"name":filename,"size":size})
        if len(self.buffer) > 100:
            self.flush()
        return True

    def flush(self):
        with oscar.command(self.context, "load") as command:
            command.add_argument("table", "FileQueue")
            command.add_argument("values", oscar.to_json(self.buffer))
            command.execute()
        self.buffer = []

def check_if_uptodate(context, filename,mtime):
    with oscar.command(context, "select") as command:
        command.add_argument("table", "Files")
        command.add_argument("output_columns", "_id,mtime")
        command.add_argument("filter","_key == '%s'" % oscar.sha1(filename))
        result = json.loads(command.execute())
    rows = result[0][2:]
    if len(rows) == 0: return False
    return (rows[0][1] >= mtime * 1000)

def walk(context, base_dir):
    qw = QueueWriter(context, base_dir)
    for root, dirs, files in os.walk(base_dir):
        r = re.sub(r'^\/+', "", root[len(base_dir):])
        if r.startswith('.'): continue
        for file in files:
            filename = os.path.join(r, file)
            exact_filename = os.path.join(base_dir, filename)
            stat = os.stat(exact_filename)
            if (not check_if_uptodate(context, filename, stat.st_mtime)):
                if qw.enqueue(filename,stat.st_size):
                    oscar.log.debug("%s enqueued" % filename)
                else:
                    oscar.log.debug("%s is not enqueued" % filename)
                
            else:
                oscar.log.debug("%s skipped because file already exists on database" % filename)
    qw.flush()

def run(args):
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context:
            walk(context, base_dir)
