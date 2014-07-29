#-*- coding: utf-8 -*-
'''
Created on 2014/06/25

@author: shimarin
'''
import os,time,multiprocessing,logging
import pyinotify,apscheduler.schedulers.background,apscheduler.executors.pool,apscheduler.triggers.cron,apscheduler.triggers.interval
import oscar,samba,walk,cleanup,consume

oscar_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_smb_conf = os.path.join(oscar_dir, "etc/smb.conf")
_smb_conf_time = None

def parser_setup(parser):
    parser.add_argument("-w", "--walk-interval", type=int, default=8)
    parser.add_argument("-c", "--consume-interval", type=int, default=60)
    parser.add_argument("-l", "--consume-limit", type=int, default=1000)
    parser.set_defaults(func=run,name="watch")

def get_path_map():
    global _smb_conf_time
    _smb_conf_time = os.stat(_smb_conf).st_mtime
    path_map = {}
    for share_name in oscar.share_names():
        share = oscar.get_share(share_name)
        path_map[share.path] = share
    return path_map

def get_path_set(path_map):
    return set(map(lambda (x,y):x, path_map.items()))

def is_path_set_uptodate():
    return os.stat(_smb_conf).st_mtime <= _smb_conf_time

def process_file_event(share, event_mask, event_pathname):
    if (event_mask & pyinotify.IN_CLOSE_WRITE) or (event_mask & pyinotify.IN_MOVED_TO): # @UndefinedVariable
        oscar.log.debug(u"Adding %s to %s" % (event_pathname.decode("utf-8"), share.name))
        with oscar.context(share.path) as context:
            walk.enqueue(context, share.path, event_pathname)
    elif (event_mask & pyinotify.IN_DELETE) or (event_mask & pyinotify.IN_MOVED_FROM): # @UndefinedVariable
        file_id = oscar.sha1(event_pathname)
        oscar.log.debug(u"Removing %s from %s(%s)" % (event_pathname.decode("utf-8"), share.name, file_id))
        with oscar.context(share.path) as context:
            with oscar.command(context, "delete") as command:
                command.add_argument("table", "FileQueue")
                command.add_argument("key", file_id)
                command.execute()
            with oscar.command(context, "delete") as command:
                command.add_argument("table", "Files")
                command.add_argument("key", file_id)
                command.execute()

def process_dir_event(share, event_mask, event_pathname):
    pass

def process_event(share, event_mask, event_pathname):

    if event_mask & pyinotify.IN_ISDIR: # @UndefinedVariable
        process_dir_event(share, event_mask, event_pathname)
    else:
        process_file_event(share, event_mask, event_pathname)

def watch():
    def callback(event):
        if not isinstance(event, pyinotify.Event): return
        if event.mask & pyinotify.IN_IGNORED: return # @UndefinedVariable
        if oscar.log.isEnabledFor(logging.DEBUG):
            oscar.log.debug(event)
        for path,share in path_map.items():
            if not event.pathname.startswith(path + '/'): continue
            if not os.path.isdir(share.path): continue
            try:
                process_event(share, event.mask, event.pathname[len(share.path) + 1:])
            except IOError:
                oscar.log.error("IOError (share deleted, perhaps)")
    
    def exclude(path):
        return path.endswith("/.oscar") # excluded if True

    path_map = get_path_map()
    path_set = get_path_set(path_map)
    last_check_time = time.time()
    if oscar.log.isEnabledFor(logging.DEBUG):
        oscar.log.debug(path_set)
    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, default_proc_fun=callback)
    mask = pyinotify.IN_CLOSE_WRITE|pyinotify.IN_MOVED_FROM|pyinotify.IN_MOVED_TO|pyinotify.IN_MOVED_TO|pyinotify.IN_CREATE|pyinotify.IN_DELETE  # @UndefinedVariable
    wm.add_watch(list(path_set), mask, rec=True,auto_add=True,exclude_filter=exclude)
    
    while True:
        if notifier.check_events(5000):
            notifier.read_events()
            notifier.process_events()
        current_time = time.time()
        if current_time - last_check_time > 5.0:
            last_check_time = current_time
            if not is_path_set_uptodate(): # smb.conf has been updated
                new_path_map = get_path_map()
                new_path_set = get_path_set(new_path_map)
                paths_to_be_added = new_path_set.difference(path_set)
                paths_to_be_removed = path_set.difference(new_path_set)
                for path in paths_to_be_added:
                    wm.add_watch(path, mask, rec=True, auto_add=True, exclude_filter=exclude)
                for path in paths_to_be_removed:
                    wd = wm.get_wd(path)
                    if wd: wm.rm_watch(wd, rec=True, quiet=True)
                path_map = new_path_map
                path_set = new_path_set
                if oscar.log.isEnabledFor(logging.DEBUG):
                    oscar.log.debug(path_set)

def perform_walk():
    for path in get_path_map():
        try:
            with oscar.context(path) as context:
                walk.walk(context, path)
        except IOError:
            oscar.log.error("IOError (share deleted, perhaps)")

def perform_consume(limit):
    #oscar.log.debug("limit:%d" % limit)
    for path in get_path_map():
        consume.consume(path, limit, multiprocessing.cpu_count() + 1)

def run(args):
    oscar.set_share_registry(samba.ShareRegistry(_smb_conf))
    sched = apscheduler.schedulers.background.BackgroundScheduler(coalesce=True)
    sched.add_executor(apscheduler.executors.pool.ProcessPoolExecutor())
    oscar.log.info("Adding walk/cleanup job at interval %d hours" % args.walk_interval)
    sched.add_job(perform_walk, apscheduler.triggers.interval.IntervalTrigger(hours=args.walk_interval))
    oscar.log.info("Adding consume job at interval %d seconds" % args.consume_interval)
    sched.add_job(perform_consume, apscheduler.triggers.interval.IntervalTrigger(seconds=args.consume_interval), args=[args.consume_limit])
    oscar.log.info("Starting job schedulers...")
    sched.start()
    try:
        oscar.log.info("Start watching directories")
        watch()
    except KeyboardInterrupt:
        oscar.log.info("Shutting down job scheduler...")
        sched.shutdown()
    except:
        oscar.log.exception("watch")

