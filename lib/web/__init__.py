#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import os,json,time,re

import flask

import oscar,samba,search
import admin,share

app = flask.Flask(__name__)
app.register_blueprint(admin.app, url_prefix="/_admin")

app.register_blueprint(share.app, url_prefix="/<share_name>")
app.config.update(JSON_AS_ASCII=False)

private_address_regex = re.compile(r"(^127\.0\.0\.1)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)")

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="web")

def is_eden(request):
    local_access = private_address_regex.match(flask.request.remote_addr)
    # eden == MSIE in private network
    return "MSIE " in request.headers.get('User-Agent') and local_access

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/_info")
def info():
    shares = []
    for share_name in oscar.share_names():
        share = oscar.get_share(share_name)
        comment = share.comment if share.comment else (u"共有フォルダ" if share.guest_ok else u"アクセス制限された共有フォルダ")
        share_info = {"name":share.name,"comment":comment,"guest_ok":share.guest_ok}
        shares.append(share_info)

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

def run(args):
    share_registry = oscar.ShareRegistry()
    for base_dir in args.base_dir:
        with oscar.context(base_dir) as context: pass # just check if exists
        share_registry.register_share(oscar.Share(os.path.basename(oscar.remove_trailing_slash(base_dir)),base_dir))
    oscar.set_share_registry(share_registry)

    oscar.log.debug("Starting web...")
    app.run(host='0.0.0.0',debug=True)

