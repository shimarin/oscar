# -*- coding:utf-8 mode:python -*-
import sys,os,logging

oscar_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.append(os.path.join(oscar_dir, "lib"))

import oscar
import samba
import web

log_dir = "/var/log/oscar"

oscar.init()
if os.path.isdir(log_dir) and os.access(log_dir, os.W_OK):
    handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "wsgi.log"), 'a', 1024*1024*100,9)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s %(name)s %(levelname)s] %(message)s"))
    web.app.logger.addHandler(handler)
    oscar.set_logger(web.app.logger)

oscar.set_share_registry(samba.ShareRegistry(os.path.join(oscar_dir, "etc/smb.conf")))

application = web.app
