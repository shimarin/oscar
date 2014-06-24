'''
Created on 2014/06/24

@author: shimarin
'''

import os,json,time
import flask
import web,oscar,search

app = flask.Blueprint(__name__, "share")

@app.route("/")
def index(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404
    if not os.path.isdir(share.real_path("/")):
        return "Dir not found", 404
    return flask.render_template("share.html",share_id=share.name)

@app.route("/_info")
def info(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    path = oscar.remove_preceding_slash(flask.request.args.get("path") or "")
    if not os.path.isdir(share.real_path(path)):
        return "Dir not found", 404
    
    if path != "" and not path.endswith("/"): path = path + "/"
    with oscar.context(share.real_path("/")) as context:
        with oscar.command(context, "select") as command:
            command.add_argument("table", "Files")
            if path != "": command.add_argument("filter", "path @^ \"%s\"" % oscar.escape_for_groonga(path))
            command.add_argument("limit", "0")
            count = json.loads(command.execute())[0][0][0]
        with oscar.command(context, "select") as command:
            command.add_argument("table", "FileQueue")
            command.add_argument("limit", "0")
            queued = json.loads(command.execute())[0][0][0]
    
    return flask.jsonify({"share_name":share_name,"count":count,"queued":queued,"eden":web.is_eden(flask.request)})

@app.route("/_dir")
def dir(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    path = oscar.remove_preceding_slash(flask.request.args.get("path") or "")
    if not os.path.isdir(share.real_path(path)):
        return "Dir not found", 404

    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    root, dirs, files = next(os.walk(share.real_path(path)))
    dirs = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":True}, dirs))
    files = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":False}, files))

    return flask.Response(oscar.to_json((dirs + files)[offset:offset + limit]),  mimetype='application/json')

@app.route("/_search")
def exec_search(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    path = flask.request.args.get("path") or ""
    q = flask.request.args.get("q")

    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    if q == "" or q == None:
        return flask.jsonify({"count":0, "rows":[]})

    start_time = time.clock()
    with oscar.context(share.real_path("/")) as context:
        result = search.search(context,path,q, offset, limit)
    search_time = time.clock() - start_time
    result["q"] = q
    result["time"] = search_time
    #time.sleep(3)
    return flask.jsonify(result)

@app.route('/<filename>', defaults={'path': ''})
@app.route("/<path:path>/<filename>")
def get_file(share_name, path,filename):
    if share_name == "static":
        return flask.send_from_directory(os.path.join(web.app.root_path, "static", path), filename)

    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    return flask.send_from_directory(share.real_path(path), filename.encode("utf-8"))

