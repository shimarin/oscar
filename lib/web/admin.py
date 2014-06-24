'''
Created on 2014/06/24

@author: shimarin
'''

import flask
import oscar,samba

app = flask.Blueprint(__name__, "admin")

@app.before_request
def before_request():
    if not oscar.admin_user_exists(): return
    auth = flask.request.authorization
    if not auth or not oscar.check_user_password(auth.username, auth.password) or not oscar.get_user(auth.username).admin:
        return flask.Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route("/")
def index():
    return flask.render_template("admin.html")

@app.route("/info")
def info():
    return flask.jsonify({"foo":"bar"})

@app.route("/share")
def share():
    return flask.Response(oscar.to_json(map(lambda x:{"name":x}, oscar.share_names())),  mimetype='application/json')

@app.route("/share/<share_name>", methods=['GET'])
def share_get(share_name):
    share = oscar.get_share(share_name)
    if not share: return "Share not found", 404
    return flask.jsonify({"name":share.name,"comment":share.comment,"options":share.options})

@app.route("/share/<share_name>/create", methods=['POST'])
def share_create(share_name):
    # TODO: disable some characters to use http://internet.designcross.jp/2010/02/blog-post.html
    params = flask.request.json
    print params
    success, info = samba.create_share_folder(share_name, 
        params[u"comment"] if u"comment" in params else None,
        params[u"options"] if u"options" in params else {})
    return flask.jsonify({"success":success, "info":info})

@app.route("/share/<share_name>/update", methods=['POST'])
def share_update(share_name):
    params = flask.request.json
    success, info = samba.update_share_folder(share_name,
        params[u"comment"] if u"comment" in params else None,
        params[u"options"] if u"options" in params else {})
    return flask.jsonify({"success":success, "info":info})

@app.route("/share/<share_name>", methods=['DELETE'])
def share_delete(share_name):
    success, info = samba.delete_share_folder(share_name)
    return flask.jsonify({"success":success, "info":info})

@app.route("/user")
def user():
    return flask.Response(oscar.to_json(map(lambda x:{"name":x}, oscar.user_names())),  mimetype='application/json')

@app.route("/user/<user_name>", methods=['GET'])
def user_get(user_name):
    return flask.jsonify(oscar.get_user(user_name).__dict__)

@app.route("/user/<user_name>/create", methods=['POST'])
def user_create(user_name):
    options = flask.request.json
    rst = oscar.register_user(oscar.User(user_name, options["admin"]), options["password"])
    return flask.jsonify({"success":rst, "info":None})

@app.route("/user/<user_name>/update", methods=['POST'])
def user_update(user_name):
    user = oscar.get_user(user_name)
    if not user: return "User not found", 404
    options = flask.request.json
    password = options["password"] if "password" in options else None
    if password == "": password = None
    admin = options["admin"] if "admin" in options else False
    if not admin: admin = False
    user.admin = admin
    rst = oscar.update_user(user, password)
    return flask.jsonify({"success":rst, "info":None})

@app.route("/user/<user_name>", methods=['DELETE'])
def user_delete(user_name):
    rst = oscar.remove_user(user_name)
    return flask.jsonify({"success":rst, "info":None})
