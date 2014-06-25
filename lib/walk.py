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

def check_if_ignoreable(base_dir, filename):
    ignore_prefixes = [".", "#", "~$"]
    ignore_suffixes = [".tmp", ".bak", "~"]
    basename = os.path.basename(filename).lower()
    if any(map(lambda x:basename.startswith(x), ignore_prefixes)) or any(map(lambda x:basename.endswith(x), ignore_suffixes)):
        return True
    #else
    return False

def enqueue(context, base_dir, filename, qw = None):
    exact_filename = os.path.join(base_dir, filename)
    stat = os.stat(exact_filename)

    if check_if_ignoreable(base_dir, filename):
        oscar.log.debug("%s ignored" % filename)
        return False

    if not check_if_uptodate(context, filename, stat.st_mtime):
        queue_should_be_flushed = False
        if qw == None: 
            qw = QueueWriter(context, base_dir)
            queue_should_be_flushed = True
        if qw.enqueue(filename,stat.st_size):
            oscar.log.debug("%s enqueued" % filename)
        else:
            oscar.log.debug("%s is not enqueued" % filename)
            return False
        if queue_should_be_flushed: qw.flush()
        return True
    else:
        oscar.log.debug("%s skipped because file already exists on database" % filename)
    return False

def walk(context, base_dir):
    qw = QueueWriter(context, base_dir)
    for root, dirs, files in os.walk(base_dir):
        r = re.sub(r'^\/+', "", root[len(base_dir):])
        if r.startswith('.'): continue
        for file in files:
            filename = os.path.join(r, file)
            enqueue(context, base_dir, filename, qw)
    qw.flush()

def run(args):
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context:
            walk(context, base_dir)

'''
14704件のwalkに9秒、再walkには3秒 consumeに11分
'''
