import os,json
import oscar

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="cleanup")

def cleanup(context, base_dir):
    offset = 0
    total = 1
    while offset < total:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "Files")
            command.add_argument("output_columns", "_id,path,name")
            command.add_argument("offset", str(offset))
            result = json.loads(command.execute())
        total = result[0][0][0]
        rows=result[0][2:]
        #oscar.log.debug("total:%d offset:%d" % (total, offset))
        for row in rows:
            _id,path,name = row[0],row[1].encode("utf-8"),row[2].encode("utf-8")
            exact_filename = os.path.join(base_dir,path if path != "/" else "",name)
            if not os.path.isfile(exact_filename):
                oscar.log.info("Missing file: %s. remove from database" % exact_filename)
                with oscar.command(context, "delete") as command:
                    command.add_argument("table", "Files")
                    command.add_argument("id", str(_id))
                    command.execute()
        offset += len(rows)

def run(args):
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context:
            return cleanup(context, base_dir)
