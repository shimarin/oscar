# -*- coding: utf-8 -*-
import os,shutil,configobj,getpass,json,pwd
import pypassdb.passdb
import oscar,init,config,truncate

_ignoreable_sections = ["static","global","homes","printers"]
_share_folder_base = "/var/lib/oscar"

def get_share_folder_base():
    return _share_folder_base

def set_share_folder_base(share_folder_base):
    _share_folder_base = share_folder_base

def reload_samba():
    os.system("sudo -b -n smbcontrol smbd reload-config")

class ShareRegistry(oscar.ShareRegistry):
    def __init__(self, smbconf_file):
        self.smbconf_timestamp = None
        self.smbconf = None
        self.smbconf_file = smbconf_file

    def _get_empty_conf(self):
        parser = configobj.ConfigObj(encoding="utf-8")
        parser.initial_comment.append("oscar share config file included from smb.conf")
        return parser

    def _get_parser(self):
        if not os.path.exists(self.smbconf_file):
            parser = self._get_empty_conf()
            parser.write(open(self.smbconf_file, "w"))

        timestamp = os.stat(self.smbconf_file).st_mtime
        if not self.smbconf or not self.smbconf_timestamp or self.smbconf_timestamp < timestamp:
            #self.smbconf = ConfigParser.SafeConfigParser({"guest ok":"no","writable":"no","locking":"yes","valid users":None})
            #self.smbconf.readfp(codecs.open(self.smbconf_file, "r", "utf-8"))
            self.smbconf = configobj.ConfigObj(self.smbconf_file,encoding="utf-8")
        self.smbconf_timestamp = timestamp
        return self.smbconf

    def _get(self, section, option):
        return self._get_parser()[section][option]

    def _sections(self):
        return self._get_parser().keys()

    def share_exists(self, name):
        if isinstance(name, str): name = name.decode("utf-8")
        return name not in _ignoreable_sections and name in self._get_parser()

    def _set_default_values(self, section):
        section.setdefault(u"guest ok", "no")
        section.setdefault(u"writable", "no")
        section.setdefault(u"locking", "yes")

    def _get_share(self, name, parser):
        if name in _ignoreable_sections: return None
        section = parser.get(name)
        if not section:
            oscar.log.warn(u"Section %s not found" % name)
            return None
        self._set_default_values(section)
        path = section[u"path"].encode("utf-8") # should be str
        if not os.path.isdir(path):
            oscar.log.warn("Physical path %s not found" % path)
            return None
        guest_ok = section.as_bool(u"guest ok")
        writable = section.as_bool(u"writable")
        comment = section.get(u"comment")
        locking = section.as_bool(u"locking")
        valid_users = section.get(u"valid users")
        options = config.get(path)
        return oscar.Share(name, path, guest_ok=guest_ok, writable=writable, comment=comment,locking=locking,valid_users=valid_users,options=options)

    def get_share(self, name):
        if isinstance(name, str): name = name.decode("utf-8")
        parser = self._get_parser()
        return self._get_share(name, parser)

    def share_names(self):
        share_list = []
        parser = self._get_parser()
        for section in filter(lambda x:x not in _ignoreable_sections, self._sections()):
            share = self._get_share(section, parser)
            if share and share.locking:  # ignore locking = no shares
                share_list.append(share.name)
        return share_list

    def _save(self, parser=None):
        if parser == None:
            parser = self._get_parser()
        parser.write(open(self.smbconf_file + ".tmp", "w"))
        shutil.copyfile(self.smbconf_file, self.smbconf_file + ".bak")
        shutil.move(self.smbconf_file + ".tmp", self.smbconf_file)
        self.smbconf_timestamp = os.stat(self.smbconf_file).st_mtime
        reload_samba()

    def register_share(self, share) :
        parser = self._get_parser()
        if share.name in parser: return False
        section = {u"path":share.path.decode("utf-8"),u"force user":getpass.getuser(),u"veto files":u".oscar"}
        if share.comment and share.comment != "": section[u"comment"] = share.comment
        if share.writable: section[u"writable"] = "yes"
        if share.guest_ok: section[u"guest ok"] = "yes"
        parser[share.name] = section
        self._save(parser)
        return True
    
    def remove_share(self, share_name):
        if isinstance(share_name, str): share_name = share_name.decode("utf-8")
        parser = self._get_parser()
        if share_name not in parser: return False
        del parser[share_name]
        self._save(parser)
        os.system("sudo /etc/init.d/oscar-watcher restart") # TODO: discover some better way
        return True
    
    def update_share(self, share):
        parser = self._get_parser()
        if share.name not in parser: return False
        section = parser[share.name]
        if share.comment and share.comment != "": 
            section[u"comment"] = share.comment
        elif u"comment" in section:
            del section[u"comment"]
        # TODO: other properties...
        self._save(parser)
        return True

class UserRegistry(oscar.UserRegistry):
    def __init__(self, passdb_file, smbusers):
        self.passdb_file = passdb_file
        self.smbusers = smbusers

    def _open_passdb(self):
        return pypassdb.passdb.passdb_open(self.passdb_file)
    
    def user_names(self):
        with self._open_passdb() as passdb:
            return map(lambda x:x.username, passdb)
    
    def user_exists(self, name):
        if isinstance(name, unicode): name = name.encode("utf-8")
        with self._open_passdb() as passdb:
            return name in passdb
    
    def _is_admin_user(self, acct_desc):
        return "admin" in acct_desc and acct_desc["admin"]

    def _acct_desc(self, user_record):
        if not user_record.acct_desc or user_record.acct_desc == "": return {}
        try:
            return json.loads(user_record.acct_desc)
        except ValueError:
            return {}

    def get_user(self, name):
        if isinstance(name, unicode): name = name.encode("utf-8")
        with self._open_passdb() as passdb:
            if name not in passdb: return None
            user = passdb[name]
            return oscar.User(user.username, self._is_admin_user(self._acct_desc(user)))

    def _update_smbusers(self, passdb):
        syetem_users = set(map(lambda x:x.pw_name.lower(), pwd.getpwall()))
        usermap = {}
        for user in filter(lambda x:x.username, passdb):
            # acct_descフィールド内のJSONデータを取得
            acct_desc = self._acct_desc(user)

            # 同名のUNIXユーザーが居る場合はmapしない
            if ("system_user" not in acct_desc or acct_desc["system_user"].lower() == user.username.lower()) and user.username.lower() in system_users: continue

            system_user = acct_desc["system_user"] if "system_user" in acct_desc and acct_desc["system_user"] else getpass.getuser()
            if system_user in usermap:
                usermap[system_user].append(user.username)
            else:
                usermap[system_user] = [user.username]
        with open(self.smbusers + ".tmp", "w") as smbusers:
            for system_user, users in usermap.items():
                smbusers.write("%s = " % system_user)
                smbusers.write(' '.join(users))
                smbusers.write("\n")
        if os.path.isfile(self.smbusers):
            shutil.copyfile(self.smbusers, self.smbusers + ".bak")
        shutil.move(self.smbusers + ".tmp", self.smbusers)
    
    def register_user(self, user, password):
        user_name = user.name.encode("utf-8") if isinstance(user.name, unicode) else user.name
        with self._open_passdb() as passdb:
            if user_name in passdb: return False
            user_record = pypassdb.user.User(user_name)
            acct_desc = {"admin":user.admin, "system_user":None} # "oscar_" + mhash.MHASH(mhash.MHASH_CRC32B, user_name).hexdigest()
            user_record.acct_desc = json.dumps(acct_desc)
            user_record.set_password(password)
            passdb.append(user_record)
            self._update_smbusers(passdb)

        reload_samba()
        return True
    
    def update_user(self, user, password = None):
        user_name = user.name.encode("utf-8") if isinstance(user.name, unicode) else user.name
        with self._open_passdb() as passdb:
            if not user_name in passdb: return False
            user_record = passdb[user_name]
            acct_desc = {"admin":user.admin, "system_user":None}
            user_record.acct_desc = json.dumps(acct_desc)
            if password: user_record.set_password(password)
            passdb[user_name] = user_record
        return True
    
    def remove_user(self, name):
        if isinstance(name, unicode): name = name.encode("utf-8")
        with self._open_passdb() as passdb:
            if name not in passdb: return False
            del passdb[name]
            self._update_smbusers(passdb)
        reload_samba()
        return True
    
    def admin_user_exists(self):
        with self._open_passdb() as passdb:
            return any(map(lambda x:self._is_admin_user(self._acct_desc(x)), passdb))
    
    def check_user_password(self, name, password):
        if isinstance(name, unicode): name = name.encode("utf-8")
        with self._open_passdb() as passdb:
            if name not in passdb: return False
            return passdb[name].check_password(password)

def create_share_folder(share_name, comment, options=None, share_dir = None):
    if oscar.get_share(share_name):
        return (False, "SHAREALREADYEXISTS")
    if share_dir:
        base_dir = os.path.dirname(share_dir)
    else:
        base_dir = _share_folder_base
        share_dir = os.path.join(base_dir, share_name.encode("utf-8") if isinstance(share_name,unicode) else share_name)
    if os.path.exists(share_dir):
        return (False, "DIRALREADYEXISTS")
    if not os.path.isdir(base_dir) and not os.access(base_dir, os.W_OK):
        return (False, "NOACCESS")
    os.mkdir(share_dir)
    init.init(share_dir)
    if options:
        config.put_all(share_dir, options)
    rst = oscar.register_share(oscar.Share(share_name, share_dir, comment=comment, guest_ok=True, writable=True))
    return (rst, None)

def delete_share_folder(share_name):
    share = oscar.get_share(share_name)
    if not share: return (False, "SHARENOTEXIST")
    if not os.path.isdir(share.path): return (False, "DIRNOTEXIST")
    rst = oscar.remove_share(share_name)
    shutil.rmtree(share.path, ignore_errors=True)
    return (rst, None)

def update_share_folder(share_name, comment, options):
    share = oscar.get_share(share_name)
    if not share: return (False, "SHARENOTEXIST")
    share_dir = share.real_path("/")
    if not os.path.isdir(share_dir): return (False, "DIRNOTEXIST")
    config.put_all(share_dir, options)
    share.comment = comment
    rst = oscar.update_share(share)
    return (rst, None)

def truncate_share_folder_index(share_name):
    share = oscar.get_share(share_name)
    if not share: return (False, "SHARENOTEXIST")
    if not os.path.isdir(share.path): return (False, "DIRNOTEXIST")
    rst = truncate.truncate(share.path)
    return (rst, None)

if __name__ == '__main__':
    pass
