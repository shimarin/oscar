'''
Created on 2014/06/25

@author: shimarin
'''

import os,getpass,tempfile,re,time
import apscheduler.scheduler
import oscar,samba,config

oscar_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_smb_conf = os.path.join(oscar_dir, "etc/smb.conf")

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="*")
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
    syncorigin = config.get(base_dir, "syncorigin")
    if u"path" not in syncorigin or syncorigin[u"path"] == "": return False
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
            rsync_cmd = "rsync -ax %s/ %s" % (tempdir, base_dir)
            oscar.log.debug(rsync_cmd)
            rst = os.system(rsync_cmd)
            if rst != 0:
                oscar.log.error("rsync (%s -> %s) returned error code: %d" % (path, base_dir, rst))
                return False
        finally:
            umount_cmd = "sudo umount %s" % tempdir
            os.system(umount_cmd)
            oscar.log.debug(umount_cmd)
    finally:
        oscar.log.debug("Deleting tempdir %s" % tempdir)
        os.rmdir(tempdir)

    return True

def setup_new_scheduler():
    sched = apscheduler.scheduler.Scheduler()
    for path in map(lambda x:oscar.get_share(x).path, oscar.share_names()):
        syncday = config.get(path, "syncday")
        if not syncday or not isinstance(syncday, dict): continue
        if not any(map(lambda (x,y):y, syncday.items())): continue
        synctime = config.get(path, "synctime")
        if not synctime or not re.match(r'^\d\d:\d\d$', synctime): continue
        dow = ','.join(map(lambda (x,y):x, filter(lambda (x,y):y, syncday.items())))
        hour, minute = map(lambda x:int(x), synctime.split(':'))
        oscar.log.debug(u"path=%s day=%s time=%02d:%02d" % (path.decode("utf-8"), dow, hour,minute))
        sched.add_cron_job(sync, day_of_week=dow, hour=hour, minute=minute, args=[path])
    return sched

def schedule_sync():
    smbconf_time = os.stat(_smb_conf).st_mtime
    sched = setup_new_scheduler()
    sched.start()
    try:
        while True:
            new_smbconf_time = os.stat(_smb_conf).st_mtime
            if new_smbconf_time > smbconf_time:
                sched.shutdown()
                sched = setup_new_scheduler()
                sched.start()
                smbconf_time = new_smbconf_time
            time.sleep(10)
    except KeyboardInterrupt:
        sched.shutdown()

def run(args):
    if len(args.base_dir) > 0:
        for base_dir in args.base_dir:
            sync(base_dir)
    else:
        oscar.set_share_registry(samba.ShareRegistry(_smb_conf))
        schedule_sync()
