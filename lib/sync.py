'''
Created on 2014/06/25

@author: shimarin
'''

import os,getpass,json,tempfile
import oscar

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run,name="sync")

def mount_command(path, username, password, mountpoint):
    mount_options = "ro,iocharset=utf8,uid=%s" % getpass.getuser()
    if password and password != "":
        mount_options += ",password=%s" % password
    else:
        mount_options += ",guest"
    if username and username != "":
        mount_options += ",username=%s" % username
    return "sudo mount -t cifs -o %s %s %s" % (mount_options, path, mountpoint)

def sync(base_dir):
    with oscar.context(base_dir) as context:
        with oscar.Command(context, "select") as command:
            command.add_argument("table", "Config")
            command.add_argument("filter", "_key == 'syncorigin'")
            rst = json.loads(command.execute())[0][2:]

    if len(rst) == 0: return False
    syncorigin = json.loads(rst[0][2])
    if u"path" not in syncorigin: return False
    path = syncorigin[u"path"]
    username = syncorigin[u"username"] if u"username" in syncorigin else None
    password = syncorigin[u"password"] if u"password" in syncorigin else None
    if username == u"": username = None
    if password == u"": password = None
    
    tempdir = tempfile.mkdtemp()
    try:
        rst = os.system(mount_command(path, username, password, tempdir))
        if rst != 0:
            oscar.log.error("Unable to mount sync source %s (%d)" % (path, rst))
            return False
        try:
            rst = os.system("rsync -ax %s/ %s" % (tempdir, base_dir))
            if rst != 0:
                oscar.log.error("rsync (%s -> %s) returned error code: %d" % (path, base_dir, rst))
                return False
        finally:
            os.system("sudo umount %s" % tempdir)
    finally:
        os.rmdir(tempdir)

    return True

def run(args):
    for base_dir in args.base_dir:
        sync(base_dir)
