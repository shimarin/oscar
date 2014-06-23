# -*- coding: utf-8 -*-
import os,shutil,ConfigParser
import oscar,init,config

_ignoreable_sections = ["static","global","homes","printers"]
_share_folder_base = "/var/lib/oscar"

class ShareRegistry(oscar.ShareRegistry):
    def __init__(self, smbconf_file):
        self.smbconf_timestamp = None
        self.smbconf = None
        self.smbconf_file = smbconf_file

    def _get_parser(self):
        timestamp = os.stat(self.smbconf_file).st_mtime
        if not self.smbconf or not self.smbconf_timestamp or self.smbconf_timestamp < timestamp:
            self.smbconf = ConfigParser.SafeConfigParser({"guest ok":"no","writable":"no","locking":"yes","valid users":None})
            self.smbconf.read(self.smbconf_file)
        self.smbconf_timestamp = timestamp
        return self.smbconf

    def _get(self, section, option):
        return self._get_parser().get(section, option)

    def _sections(self):
        return self._get_parser().sections()

    def share_exists(self, name):
        if isinstance(name, unicode): name = name.encode("utf-8")
        return name not in _ignoreable_sections and self._get_parser().has_section(name)

    def _get_share(self, name, parser):
        if name in _ignoreable_sections or not parser.has_section(name): return None
        path = parser.get(name, "path")
        guest_ok = parser.getboolean(name, "guest ok")
        writable = parser.getboolean(name, "writable")
        comment = parser.get(name, "comment") if parser.has_option(name, "comment") else (u"共有フォルダ" if guest_ok else u"アクセス制限された共有フォルダ")
        locking = parser.getboolean(name, "locking")
        valid_users = parser.get(name, "valid users")
        return oscar.Share(name, path, guest_ok=guest_ok, writable=writable, comment=comment,locking=locking,valid_users=valid_users)

    def get_share(self, name):
        if isinstance(name, unicode): name = name.encode("utf-8")
        parser = self._get_parser()
        return self._get_share(name, parser)

    def share_names(self):
        share_list = []
        parser = self._get_parser()
        for section in filter(lambda x:x not in _ignoreable_sections, self._sections()):
            share = self._get_share(section, parser)
            if share.locking:  # ignore locking = no shares
                share_list.append(share.name)
        return share_list

    def register_share(self, share) :
        raise Exception("Operation not permitted")

def create_share_folder(share_name, options=None, share_dir = None):
    if oscar.get_share(share_name):
        return (False, "SHAREALREADYEXISTS")
    if share_dir:
        base_dir = os.path.dirname(share_dir)
    else:
        base_dir = _share_folder_base
        share_dir = os.path.join(base_dir, share_name)
    if os.path.exists(share_dir):
        return (False, "DIRALREADYEXISTS")
    if not os.path.isdir(base_dir) and not os.access(base_dir, os.W_OK):
        return (False, "NOACCESS")
    os.mkdir(share_dir)
    init.init(share_dir)
    if options:
        config.put_all(share_dir, options)
    # TODO: update smb.conf
    return (True, None)

def delete_share_folder(share_name):
    share = oscar.get_share(share_name)
    if not share: return (False, "SHARENOTEXIST")
    share_dir = share.real_path()
    if not os.path.isdir(share_dir): return (False, "DIRNOTEXIST")
    # TODO: should move to some trash dir instead of deleting it directly
    shutil.rmtree(share_dir, ignore_errors=True)
    # TODO: update smb.conf
    return (True, None)

def update_share_folder(share_name, options):
    share = oscar.get_share(share_name)
    if not share: return (False, "SHARENOTEXIST")
    share_dir = share.real_path()
    if not os.path.isdir(share_dir): return (False, "DIRNOTEXIST")
    config.put_all(share_dir, options)
    return (True, None)

def create_user(user_name, options=None):
    return (False, "TBD")

def delete_user(user_name):
    return (False, "TBD")

def update_user(user_name, options):
    return (False, "TBD")
