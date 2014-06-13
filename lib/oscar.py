# -*- coding: utf-8 -*-

import os,re,hashlib,json
import logging,logging.handlers

# http://packages.groonga.org/source/groonga-gobject/
os.environ['GI_TYPELIB_PATH'] = '/usr/local/lib/girepository-1.0'
import gi.repository.Groonga

log = None

def logger_init(name, verbose=False, filename=None):
    """Initialize logger instance."""
    global log
    log = logging.getLogger(name)
    handler = logging.handlers.RotatingFileHandler(filename, 'a', 1024*1024*100,9) if filename else logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s %(name)s %(levelname)s] %(message)s"))
    log.addHandler(handler)
    log.setLevel(10 if verbose else 20)

class Context:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        self.context = gi.repository.Groonga.Context.new()
        if os.path.exists(self.database):
            log.debug("open_database(%s)" % self.database)
            self.context.open_database(self.database)
        else:
            os.makedirs(os.path.dirname(self.database))
            self.context.create_database(self.database)
        return self.context

    def __exit__(self, exc_type, exc_value, traceback):
        log.debug("close_database(%s)" % self.database)
        if exc_type:
            del self.context
            return False
        #else
        del self.context
        return True

def context(base_dir, create = False):
    db_name = os.path.join(base_dir, ".oscar/groonga")
    if not create:
        with open(db_name) as db:
            pass # exception if db doesnot exist
    return Context(db_name)

class Command:
    def __init__(self, context, name):
        self.context = context
        self.name = name
    def __enter__(self):
        self.command = gi.repository.Groonga.Command.new(self.context, self.name)
        return self.command
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            del self.command
            return False
        #else
        del self.command
        return True

def command(context, name):
    return Command(context, name)

def escape_for_groonga(val):
    return val # TODO: implement it

def init():
    gi.repository.Groonga.init()

def fin():
    gi.repository.Groonga.fin()

def sha1(val):
    val = val.encode("utf-8") if isinstance(val, unicode) else val
    return hashlib.sha1(val).hexdigest()

def remove_preceding_slash(filename):
    return re.sub(r'^\/+', "", filename)

class Share:
    def __init__(self, name, path, guest_ok=False, writable=False, comment=None,locking=True,valid_users=None):
        self.name = name if isinstance(name, unicode) else name.decode("utf-8")
        self.path = path
        self.guest_ok = guest_ok
        self.writable = writable
        self.comment = comment if isinstance(comment, unicode) else comment.decode("utf-8") if comment else None
        self.locking = locking
        self.valid_users = valid_users

    def real_path(self, path):
        if isinstance(path, unicode): path = path.encode("utf-8")
        if path.startswith('/'): path = re.sub(r'^/+', "", path)
        return os.path.join(self.path, path)

    def urlencoded_name(self):
        return urllib2.quote(self.name.encode("utf-8"))

    def is_user_valid(self, user, groups):
        if self.valid_users == None: return True
        valid_users = map(lambda x:x.lower(), re.split(r' *,? *', self.valid_users))
        if user.lower() in valid_users: return True
        for group in groups:
            for group_prefix in ('@','+','@+','+@'):
                if group_prefix + group.lower() in valid_users: return True
        return False

shares = []

def share_exists(name):
    for share in shares: 
        if share.name == name: return True
    return False

def get_share(name):
    for share in shares: 
        if share.name == name: return share
    return None

def share_names():
    return map(lambda x:x.name, shares)

def register_share(share):
    if share_exists(share.name): raise Exception("Share %s already exists" % share.name)
    shares.append(share)

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False) # 𡵅 に対応するため
