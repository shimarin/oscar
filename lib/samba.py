# -*- coding: utf-8 -*-
import os,ConfigParser
import oscar

_ignoreable_sections = ["static","global","homes","printers"]

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

    def register_share(self, share):
        raise Exception("Operation not permitted")
