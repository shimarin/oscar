import os
import logging
import logging.handlers

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
            self.context.open_database(self.database)
        else:
            os.makedirs(os.path.dirname(self.database))
            self.context.create_database(self.database)
        return self.context

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            del self.context
            return False
        #else
        del self.context
        return True

def context(base_dir, create = False):
    db_name = "%s/.oscar/groonga" % base_dir
    if not create:
        with open(db_name) as db:
            pass # exception if db doesnot exist
    return Context("%s/.oscar/groonga" % base_dir)

def init():
    gi.repository.Groonga.init()

def fin():
    gi.repository.Groonga.fin()
