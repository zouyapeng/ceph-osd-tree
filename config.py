# -*- coding: utf-8 -*-
import ConfigParser

class Config(object):
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/opt/ceph-osd-tree/config')
        self.host = self.config.get('BaseConfig', 'ceph_rest_host')
        self.port = self.config.getint('BaseConfig', 'ceph_rest_port')
        self.interval = self.config.getint('BaseConfig', 'interval')
        self.restart_interval = self.config.getint('BaseConfig', 'restart_interval')

    def get_contact_email(self):
        return self.config.get('Contacts', 'email').split(',')

    def get_contact_telephone(self):
        contacts = self.config.get('Contacts', 'telephone')
        return contacts

    def set_daemon_pid(self, pid):
        self.config.set('BaseConfig', 'daemon_pid', pid)
        with open('/opt/ceph-osd-tree/config', 'wb') as configfile:
            self.config.write(configfile)
            configfile.close()

    def get_daemon_pid(self):
        return self.config.getint('BaseConfig', 'daemon_pid')

    def get_max_sms_num(self):
        return self.config.getint('BaseConfig', 'max_send_num')

    def set_max_sms_num(self, var):
        self.config.set('BaseConfig', 'max_send_num', var)
        with open('/opt/ceph-osd-tree/config', 'wb') as configfile:
            self.config.write(configfile)
            configfile.close()

    def get_event_done(self):
        return self.config.getint('BaseConfig', 'done')

    def set_event_done(self, var):
        self.config.set('BaseConfig', 'done', var)
        self.config.set('BaseConfig', 'max_send_num', 3)
        with open('/opt/ceph-osd-tree/config', 'wb') as configfile:
            self.config.write(configfile)
            configfile.close()

