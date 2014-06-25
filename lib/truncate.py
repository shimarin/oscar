import json
import oscar

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="truncate")

def truncate_table(context, table_name):
    with oscar.command(context, "truncate") as command:
        command.add_argument("table", table_name)
        return json.loads(command.execute())

def _truncate(context):
    truncate_table(context, "Files")
    truncate_table(context, "Fulltext")
    truncate_table(context, "FileQueue")
    return True

def truncate(base_dir_or_context):
    if isinstance(base_dir_or_context, oscar.Context):
        return _truncate(base_dir_or_context)
    #else
    with oscar.context(base_dir_or_context) as context: # assume base_dir
        return _truncate(context)

def run(args):
    for base_dir in args.base_dir:
        if raw_input("Are you sure to truncate database at %s? ('yes' if sure): " % base_dir) == "yes":
            with oscar.context(base_dir) as context:
                truncate(context)
        else:
            print("Looks like you're sane.")
