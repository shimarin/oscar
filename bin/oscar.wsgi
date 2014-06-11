# -*- coding:utf-8 mode:python -*-
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../lib')

import oscar
import web

oscar.init()
oscar.logger_init("web", False, "/var/log/oscar/web.log")

application = web.app
