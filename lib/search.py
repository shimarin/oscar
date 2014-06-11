# -*- coding: utf-8 -*-

import json

import oscar

def parser_setup(parser):
    parser.add_argument("-d", "--base-dir", default=".")
    parser.add_argument("args", nargs=1)
    parser.set_defaults(func=run,name="search")

def run(args):
    query = args.args[0]
    with oscar.context(args.base_dir) as context:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "Files")
            command.add_argument("output_columns", "_key,path,name,snippet_html(path),snippet_html(name),snippet_html(fulltext.content)")
            command.add_argument("match_columns", "name||fulltext.content||path_ft")
            command.add_argument("query", query)
            command.add_argument("command_version", "2")
            result = json.loads(command.execute())

    for row in result[0][2:]:
        print "%s%s %s%s%s" % (row[1],row[2],row[3],row[4],row[5])



