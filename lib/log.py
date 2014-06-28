'''
Created on 2014/06/28

@author: shimarin
'''

import time,json
import oscar

def get_log(base_dir, category = None, offset = None, limit = None):
    with oscar.context(base_dir) as context:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "Log")
            command.add_argument("output_columns", "time,category,content")
            if category: command.add_argument("filter", "category == \"%s\"" % oscar.escape_for_groonga(category))
            if offset: command.add_argument("offset", str(offset))
            if limit: command.add_argument("limit", str(limit))
            command.add_argument("sortby", "-time")
            result = json.loads(command.execute())
    return {
        "count":result[0][0][0],
        "rows":map(lambda row:{"time":row[0],"category":row[1],"content":row[2]}, result[0][2:])
    }

def create_log(base_dir, category, content):
    row = {
        "time":time.time(),
        "category":category,
        "content":content
    }
    with oscar.context(base_dir) as context:
        with oscar.command(context, "load") as command:
            command.add_argument("table", "Log")
            command.add_argument("values", oscar.to_json([row]))
            command.execute()
