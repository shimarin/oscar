# -*- coding:utf-8 mode:python -*-
import sys,os,logging

oscar_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.append(os.path.join(oscar_dir, "lib"))

import oscar,samba,web

oscar.init()
oscar.set_logger(web.app.logger)
oscar_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
oscar.set_share_registry(samba.ShareRegistry(os.path.join(oscar_dir, "etc/smb.conf")))
# chgrp oscar /var/lib/samba/private /var/lib/samba/private/passdb.tdb
# chmod g+rx /var/lib/samba/private
# chmod g+rw /var/lib/samba/private/passdb.tdb
oscar.set_user_registry(samba.UserRegistry("/var/lib/samba/private/passdb.tdb", os.path.join(oscar_dir, "etc/smbusers")))
web.app.run(host='0.0.0.0',debug=True)
