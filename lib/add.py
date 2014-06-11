import os

import oscar

name = "add"

def add_file(context, base_dir, filename):
    exact_filename = os.path.join(base_dir, filename)
    oscar.log.info("Adding: %s" % exact_filename)

def run(args):
    with oscar.context(args.base_dir) as context:
        for filename in args.args:
            add_file(context, args.base_dir, filename)

    oscar.log.info("Files added.")
