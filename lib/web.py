# -*- coding: utf-8 -*-
import os

import flask

import oscar

app = flask.Flask(__name__)

def parser_setup(parser):
    parser.set_defaults(func=run,name="web")

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/_info")
def info():
    st = os.statvfs("/")

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

    return flask.jsonify({"foo":"bar","loadavg":os.getloadavg(),"capacity":capacity})

@app.route("/<share>/")
def share(share):
    return flask.render_template("share.html",share_id=share)

@app.route("/<share>/_info")
def share_info(share):
    return flask.jsonify({"foo":"bar"})

@app.route("/<share>/_search")
def search(share):
    pass

def run(args):
    oscar.log.debug("Starting web...")
    app.run(host='0.0.0.0',debug=True)
