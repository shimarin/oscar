# -*- coding: utf-8 -*-

import json

import oscar

def parser_setup(parser):
    parser.add_argument("-p", "--path", default="")
    parser.add_argument("base_dir")
    parser.add_argument("keyword")
    parser.set_defaults(func=run,name="search")

def search(context, path, keyword, offset=None, limit=None):
    path = oscar.remove_preceding_slash(path)
    if path != "" and not path.endswith("/"): path = path + "/"

    with oscar.command(context, "select") as command:
        command.add_argument("table", "Files")
        command.add_argument("output_columns", "_key,path,name,mtime,snippet_html(path),snippet_html(name),snippet_html(fulltext.content)")
        command.add_argument("match_columns", "name*10||fulltext.content*5||path_ft")
        if path != "": command.add_argument("filter", "path @^ \"%s\"" % oscar.escape_for_groonga(path))
        command.add_argument("query", keyword)
        command.add_argument("sortby", "-_score")
        command.add_argument("command_version", "2")
        if offset: command.add_argument("offset", str(offset))
        if limit: command.add_argument("limit", str(limit))
        result = json.loads(command.execute())

    return {
        "count":result[0][0][0],
        "rows":map(lambda row:{"key":row[0],"path":row[1],"name":row[2],"mtime":row[3],"snippets":{"path":row[4],"name":row[5],"content":row[6]}}, result[0][2:])
    }
    

def run(args):
    with oscar.context(args.base_dir) as context:
        result = search(context, args.path, args.keyword)

    print "count=%d" % result["count"]
    for row in result["rows"]:
        print "%s %s%s %s%s%s" % (row["key"],row["path"],row["name"],row["snippets"]["path"],row["snippets"]["name"],row["snippets"]["content"])

'''
select Fulltext --command_version 2 --output_columns 'snippet_html(content)' --match_columns 'content' --query '総務' --sortby -_score
'''
