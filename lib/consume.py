import json,multiprocessing
import oscar

import add

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.add_argument("--utf8-check", action="store_true")
    parser.add_argument("--id-prefix")
    parser.add_argument("-c", "--concurrency", type=int, default=None)
    parser.set_defaults(func=run,name="consume")

def add_file(args):
    base_dir, _id, filename, utf8_check = args
    with oscar.context(base_dir) as context:
        add.add_file(context, base_dir, filename, utf8_check)
        with oscar.command(context, "delete") as command:
            command.add_argument("table", "FileQueue")
            command.add_argument("id", str(_id))
            command.execute()
    return 1

def consume(base_dir, limit=100, concurrency = 1, id_prefix=None, utf8_check=False):
    with oscar.context(base_dir) as context:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "FileQueue")
            command.add_argument("output_columns", "_id,_key,name")
            if id_prefix: command.add_argument("filter", "_key @^ \"%s\"" % oscar.escape_for_groonga(id_prefix))
            command.add_argument("sortby","size")
            command.add_argument("limit",str(limit))
            rows = json.loads(command.execute())[0][2:]

    jobs = map(lambda x:(base_dir, x[0], x[2].encode("utf-8"), utf8_check), rows)
    if concurrency > 1:
        pool = multiprocessing.Pool(processes=concurrency)
        return sum(pool.map(add_file, jobs))
    #else
    return sum(map(add_file, jobs))

def run(args):
    concurrency = args.concurrency if args.concurrency else multiprocessing.cpu_count() + 1
    for base_dir in args.base_dir:
        while True:
            if consume(base_dir, 100, concurrency, args.id_prefix, args.utf8_check) == 0: break
