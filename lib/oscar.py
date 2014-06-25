# -*- coding: utf-8 -*-

import os,re,hashlib,json
import logging.handlers

# USE="-cairo" emerge pygobject
# http://packages.groonga.org/source/groonga-gobject/
os.environ['GI_TYPELIB_PATH'] = '/usr/local/lib/girepository-1.0'
import gi.repository.Groonga    #@UnresolvedImport

log = None
_share_registry = None
_user_registry = None

def logger_init(name, verbose=False, filename=None):
    """Initialize logger instance."""
    global log
    log = logging.getLogger(name)
    handler = logging.handlers.RotatingFileHandler(filename, 'a', 1024*1024*100,9) if filename else logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s %(name)s %(levelname)s] %(message)s"))
    log.addHandler(handler)
    log.setLevel(10 if verbose else 20)

def set_logger(logger):
    global log
    log = logger

class Context:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        self.context = gi.repository.Groonga.Context.new()
        if os.path.exists(self.database):
            #log.debug("open_database(%s)" % self.database)
            self.context.open_database(self.database)
        else:
            os.makedirs(os.path.dirname(self.database))
            self.context.create_database(self.database)
        return self.context

    def __exit__(self, exc_type, exc_value, traceback):
        #log.debug("close_database(%s)" % self.database)
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

def set_share_registry(share_registry):
    global _share_registry
    _share_registry = share_registry

def set_user_registry(user_registry):
    global _user_registry
    _user_registry = user_registry

def fin():
    gi.repository.Groonga.fin()

def sha1(val):
    val = val.encode("utf-8") if isinstance(val, unicode) else val
    return hashlib.sha1(val).hexdigest()

def remove_preceding_slash(filename):
    return re.sub(r'^\/+', "", filename)

def remove_trailing_slash(dirname):
    return re.sub(r'\/+$', "", dirname)

class Share:
    def __init__(self, name, path, guest_ok=False, writable=False, comment=None,locking=True,valid_users=None,options=None):
        self.name = name if isinstance(name, unicode) else name.decode("utf-8")
        self.path = remove_trailing_slash(path) # must be str
        self.guest_ok = guest_ok
        self.writable = writable
        self.comment = comment if isinstance(comment, unicode) else comment.decode("utf-8") if comment else None
        self.locking = locking
        self.valid_users = valid_users
        self.options = options

    def real_path(self, path):
        if isinstance(path, unicode): path = path.encode("utf-8")
        if path.startswith('/'): path = re.sub(r'^/+', "", path)
        return os.path.join(self.path, path)

#    def urlencoded_name(self):
#        return urllib2.quote(self.name.encode("utf-8"))

    def is_user_valid(self, user, groups):
        if self.valid_users == None: return True
        valid_users = map(lambda x:x.lower(), re.split(r' *,? *', self.valid_users))
        if user.lower() in valid_users: return True
        for group in groups:
            for group_prefix in ('@','+','@+','+@'):
                if group_prefix + group.lower() in valid_users: return True
        return False

class ShareRegistry:
    def __init__(self):
        self.shares = []
    def share_exists(self, name):
        for share in self.shares: 
            if share.name == name: return True
        return False
    def get_share(self, name):
        for share in self.shares: 
            if share.name == name: return share
        return None
    def share_names(self):
        return map(lambda x:x.name, self.shares)
    def register_share(self, share):
        if self.share_exists(share.name):
            raise Exception("Share %s already exists" % share.name)
        self.shares.append(share)
    def check_user_credential(self, share_name, user_name):
        return user_name is not None

def share_exists(name):
    return _share_registry.share_exists(name)

def get_share(name):
    return _share_registry.get_share(name)

def share_names():
    return _share_registry.share_names()

def register_share(share):
    return _share_registry.register_share(share)

def remove_share(share_name):
    return _share_registry.remove_share(share_name)

def update_share(share):
    return _share_registry.update_share(share)

def check_user_credential(share_name, user_name):
    return _share_registry.check_user_credential(share_name, user_name)

class User:
    def __init__(self, name, admin):
        self.name = name if isinstance(name,str) else name.encode("utf-8")
        self.admin = admin

class UserRegistry:
    def __init__(self):
        self.users = []
    def auth(self, name, password):
        user = self.get_user(name)
        if not user: return False
        return user.password == password
    def user_exists(self, name):
        return any(lambda x:x.name == name, self.users)
    def get_user(self, name):
        return (filter(lambda x:x.name == name, self.users) + [None])[0]
    def user_names(self):
        return map(lambda x:x.name,self.users)
    def register_user(self, user, password):
        if self.user_exists(user.name):
            raise Exception("User %s already exists" % user.name)
        self.users.append(user)
    def remove_user(self, user_name):
        raise Exception("TBD")
    def set_password(self, user_name, password):
        raise Exception("TBD")

def user_names():
    return _user_registry.user_names()

def get_user(name):
    return _user_registry.get_user(name)

def register_user(user, password):
    return _user_registry.register_user(user, password)

def update_user(user, password=None):
    return _user_registry.update_user(user, password)

def remove_user(user_name):
    return _user_registry.remove_user(user_name)

def set_user_password(user_name, password):
    return _user_registry.set_password(user_name, password)

def check_user_password(user_name, password):
    return _user_registry.check_user_password(user_name, password)

def admin_user_exists():
    return _user_registry.admin_user_exists()

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False) # 𡵅 に対応するため
