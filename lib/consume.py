import json
import oscar

import add

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.add_argument("--utf8-check", action="store_true")
    parser.add_argument("--id-prefix")
    parser.set_defaults(func=run,name="consume")

def consume(context, base_dir, id_prefix, utf8_check, limit=1):
    with oscar.command(context, "select") as command:
        command.add_argument("table", "FileQueue")
        command.add_argument("output_columns", "_id,_key,name")
        if id_prefix: command.add_argument("filter", "_key @^ \"%s\"" % oscar.escape_for_groonga(id_prefix))
        command.add_argument("sortby","size")
        command.add_argument("limit",str(limit))
        rows = json.loads(command.execute())[0][2:]

    cnt = 0
    for row in rows:
        _id, _key, filename = row[0], row[1].encode("utf-8"), row[2].encode("utf-8")
        oscar.log.debug("%s: %s" % (_key, filename))
        add.add_file(context, base_dir, filename, utf8_check)
        with oscar.command(context, "delete") as command:
            command.add_argument("table", "FileQueue")
            command.add_argument("id", str(_id))
            command.execute()
        cnt += 1

    return cnt

def run(args):
    for base_dir in args.base_dir:
        while True:
            with oscar.context(base_dir) as context:
                if consume(context, base_dir, args.id_prefix, args.utf8_check,100) == 0: break
