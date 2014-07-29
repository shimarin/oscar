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

def check_if_uptodate(context, filename,mtime,file_id):
    with oscar.command(context, "select") as command:
        command.add_argument("table", "Files")
        command.add_argument("output_columns", "_id,mtime")
        command.add_argument("filter","_key == '%s'" % file_id)
        result = json.loads(command.execute())
    rows = result[0][2:]
    if len(rows) == 0: return False
    return (rows[0][1] >= mtime)

def check_if_ignoreable(base_dir, filename):
    ignore_prefixes = [".", "#", "~$"]
    ignore_suffixes = [".tmp", ".bak", "~"]
    basename = os.path.basename(filename).lower()
    if any(map(lambda x:basename.startswith(x), ignore_prefixes)) or any(map(lambda x:basename.endswith(x), ignore_suffixes)):
        return True
    #else
    return False

def enqueue(context, base_dir, filename, file_id=None, qw = None):
    if file_id is None: file_id = oscar.sha1(filename)
    exact_filename = os.path.join(base_dir, filename)
    if not os.path.isfile(exact_filename):
        oscar.log.debug(u"%s does not exist" % exact_filename.decode("utf-8"))
        return False
    stat = os.stat(exact_filename)

    if check_if_ignoreable(base_dir, filename):
        oscar.log.debug("%s ignored" % filename)
        return False

    if not check_if_uptodate(context, filename, stat.st_mtime, file_id):
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
    oscar.log.info(u"Performing walk on %s ..." % base_dir.decode("utf-8"))
    file_id_set = set()
    qw = QueueWriter(context, base_dir)
    for root, dirs, files in os.walk(base_dir):
        r = re.sub(r'^\/+', "", root[len(base_dir):])
        if r.startswith('.'): continue
        for file in files:
            filename = os.path.join(r, file)
            file_id = oscar.sha1(filename)
            enqueue(context, base_dir, filename, file_id, qw)
            file_id_set.add(file_id)
            #oscar.log.debug("file_id:%s, count=%d" % (file_id, len(file_id_set)))
    qw.flush()

    oscar.log.info(u"Performing cleanup on %s ..." % base_dir.decode("utf-8"))
    offset = 0
    total = 1
    while offset < total:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "Files")
            command.add_argument("output_columns", "_id,_key,path,name")
            command.add_argument("offset", str(offset))
            result = json.loads(command.execute())
        total = result[0][0][0]
        rows=result[0][2:]
        for row in rows:
            _id,key,path,name = row[0],row[1],row[2],row[3]
            if key not in file_id_set:
                oscar.log.info(u"Missing file: %s(%s). remove from database" % (os.path.join(base_dir, path if path != "/" else "",name).decode("utf-8"), key))
                with oscar.command(context, "delete") as command:
                    command.add_argument("table", "Files")
                    command.add_argument("id", str(_id))
                    command.execute()
        offset += len(rows)
    oscar.log.info(u"%s Done." % base_dir.decode("utf-8"))

def run(args):
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context:
            walk(context, base_dir)

'''
14704件のwalkに9秒、再walkには3秒 consumeに11分
'''
