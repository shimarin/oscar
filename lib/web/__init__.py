#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import os,json,time,re

import flask

import oscar,samba,search,license
import admin

app = flask.Flask(__name__)
app.register_blueprint(admin.app, url_prefix="/_admin")
app.config.update(JSON_AS_ASCII=False)

private_address_regex = re.compile(r"(^127\.0\.0\.1)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)|(^fe80:)|(^FE80:)")

class AuthRequired(Exception):
    pass

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="web")

def is_private_network():
    return private_address_regex.match(flask.request.remote_addr)

def is_eden(request):
    # eden == MSIE in private network
    return "MSIE " in request.headers.get('User-Agent') and is_private_network()

def check_access_credential(share):
    if share.guest_ok: return is_private_network()
    if not flask.g.username or not oscar.check_user_credential(share.name, flask.g.username):
        raise AuthRequired()

@app.route("/static/js/<path:filename>")
def js(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "js"), filename)

@app.route("/static/css/<path:filename>")
def css(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "css"), filename)

@app.route("/static/img/<path:filename>")
def img(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "img"), filename)

@app.route("/static/fonts/<path:filename>")
def fonts(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "fonts"), filename)

@app.route("/favicon.ico")
def favicon():
    return flask.send_from_directory(os.path.join(app.root_path, "static", "img"), "favicon.ico")

@app.route("/robots.txt")
def robots():
    return "File not found", 404
    
@app.before_request
def before_request():
    auth = flask.request.authorization
    flask.g.username = auth.username if auth and oscar.check_user_password(auth.username, auth.password) else None

@app.errorhandler(AuthRequired)
def auth_required(error):
    return flask.Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route("/")
def index():
    # プライベートネットワーク以外からのアクセスは認証必要
    if not is_private_network() and not flask.g.username:
        raise AuthRequired()
    return flask.render_template("index.html")

@app.route("/login")
def login():
    if not flask.g.username:
        return flask.Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    #else
    return flask.redirect("./")

@app.route("/_info")
def info():
    shares = []
    share_names = oscar.share_names()
    for share_name in share_names:
        share = oscar.get_share(share_name)
        comment = share.comment if share.comment else (u"共有フォルダ" if share.guest_ok else u"アクセス制限された共有フォルダ")
        if share.guest_ok or (flask.g.username and oscar.check_user_credential(share_name, flask.g.username)):
            share_info = {"name":share.name,"comment":comment,"guest_ok":share.guest_ok}
            shares.append(share_info)

    # 共有フォルダが存在するがいずれもアクセス可能な権限を持たない場合 or
    # プライベートでないIPアドレスからアクセスされている場合 認証必要
    if ((len(share_names) > 0 and len(shares) == 0) or not is_private_network()) and not flask.g.username:
        raise AuthRequired()

    st = os.statvfs(samba.get_share_folder_base())

    def capacity_string(nbytes):
        if nbytes >= 1024 * 1024 * 1024 * 1024:
            return "%.1fTB" % (nbytes / (1024 * 1024 * 1024 * 1024.0))
        if nbytes >= 1024 * 1024 * 1024:
            return "%.1fGB" % (nbytes / (1024 * 1024 * 1024.0))
        if nbytes >= 1024 * 1024:
            return "%.1fMB" % (nbytes / (1024 * 1024.0))

    free_bytes = st.f_bavail * st.f_frsize
    total_bytes = st.f_blocks * st.f_frsize
    used_bytes = (st.f_blocks - st.f_bfree) * st.f_frsize
    capacity = {
        "used" :( capacity_string(used_bytes), used_bytes * 100 / total_bytes ),
        "total" : ( capacity_string(total_bytes), 100 )
    }
    capacity["free"] = ( capacity_string(free_bytes), 100 - capacity["used"][1] )

    return flask.jsonify({"loadavg":os.getloadavg(),"capacity":capacity,"shares":shares,"eden":is_eden(flask.request)})

@app.route("/<share_name>/")
def share_index(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404
    if not os.path.isdir(share.real_path("/")):
        return "Dir not found", 404
    check_access_credential(share)

    return flask.render_template("share.html",share_id=share.name,license=license.get_license_string())

@app.route("/<share_name>/_info")
def share_info(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    path = oscar.remove_preceding_slash(flask.request.args.get("path") or "")
    if not os.path.isdir(share.real_path(path)):
        return "Dir not found", 404
    
    check_access_credential(share)

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
    
    return flask.jsonify({"share_name":share_name,"count":count,"queued":queued,"eden":is_eden(flask.request)})

@app.route("/<share_name>/_dir")
def share_dir(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    path = oscar.remove_preceding_slash(flask.request.args.get("path") or "")
    if not os.path.isdir(share.real_path(path)):
        return "Dir not found", 404

    check_access_credential(share)

    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    root, dirs, files = next(os.walk(share.real_path(path)))
    dirs = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":True}, dirs))
    files = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":False}, files))

    rst = {
        "count":len(dirs) + len(files),
        "limit":limit,
        "rows":(dirs + files)[offset:offset + limit]
    }
    return flask.jsonify(rst)

@app.route("/<share_name>/_search")
def exec_search(share_name):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    check_access_credential(share)

    path = flask.request.args.get("path") or ""
    q = flask.request.args.get("q")

    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    if q == "" or q == None:
        return flask.jsonify({"count":0, "rows":[]})

    start_time = time.clock()
    with oscar.context(share.real_path("/")) as context:
        result = search.search(context,path,q, offset, limit)
    for row in result["rows"]:
        path = oscar.remove_preceding_slash(row["path"].encode("utf-8"))
        row["exists"] = os.path.exists(os.path.join(share.path, path,row["name"].encode("utf-8")))
    search_time = time.clock() - start_time
    result["q"] = q
    result["time"] = search_time
    #time.sleep(3)
    return flask.jsonify(result)

@app.route("/<share_name>/_dup")
def detect_dups(share_name):
    # select --table Files --drilldown fulltext --drilldown_sortby -_nsubrecs
    pass

@app.route('/<share_name>/<filename>', defaults={'path': ''})
@app.route("/<share_name>/<path:path>/<filename>")
def get_file(share_name, path,filename):
    share = oscar.get_share(share_name)
    if share == None: return "Share not found", 404

    check_access_credential(share)

    return flask.send_from_directory(share.real_path(path), filename.encode("utf-8"))


def run(args):
    share_registry = oscar.ShareRegistry()
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context: pass # just check if exists
        share_registry.register_share(oscar.Share(os.path.basename(oscar.remove_trailing_slash(base_dir)),base_dir))
    oscar.set_share_registry(share_registry)

    oscar.log.debug("Starting web...")
    app.run(host='0.0.0.0',debug=True)
