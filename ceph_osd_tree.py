# -*- coding: utf-8 -*-
import sys, os
import time
import logging
import datetime
import smtplib
import pprint
import httplib
import urllib
import json


from email.mime.text import MIMEText
from config import Config
from ceph_api import ceph_osd_tree

EMAIL_ME = 'Ceph(IDC)<yapeng.zou@newtouch.cn>'
LOCALTION = '周浦数据中心'

def send_sms(text, mobile):
    logging.info('发送短信给联系人 %s' % mobile)
    params = urllib.urlencode({'apikey': '7cb9926b9a3328e9df96d59eafea7e30', 'tpl_id':1186931, 'tpl_value': urllib.urlencode(text), 'mobile':mobile})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    conn = httplib.HTTPSConnection('sms.yunpian.com', port=443, timeout=30)
    conn.request("POST", '/v1/sms/tpl_send.json', params, headers)
    response = conn.getresponse()
    response_str = response.read()
    conn.close()
    return response_str

def send_email(message, contacts):
    logging.info(u'发送邮件给联系人 %s' % contacts)
    content = message
    to_list = contacts
    me = EMAIL_ME
    msg = MIMEText(content, _subtype='plain', _charset='utf-8')
    msg['Subject'] = "Ceph OSD Down"
    msg['From'] = me
    msg['To'] = ";".join(to_list)
    try:
        server = smtplib.SMTP()
        server.connect("mail.newtouch.cn")
        server.login("yapeng.zou@newtouch.cn", "zyp794150896")
        server.sendmail(me, to_list, msg.as_string())
        server.close()
    except Exception, e:
        pass


def make_ceph_osd_down_message(re_list, down, total):
    email_message = 'Hi!\n\n'
    email_message += 'Localtion : %s\n' % ('IDC')
    email_message += 'Time : %s\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    email_message += 'Down / Total : %d / %d\n\n' % (down, total)
    code = ''
    for re_node in re_list:
        code += '%d,'% re_node['id']
        email_message += '{\n'
        email_message += '    ID : %d\n' % (re_node['id'])
        email_message += '    host : %s\n' % (re_node['host'])
        email_message += '    name : %s\n' % (re_node['name'])
        email_message += '    status : %s\n' % (re_node['status'])
        email_message += '}\n'

    code = code.rstrip(',')
    sms_message = {'#code#':code,'#app#': LOCALTION}
    return email_message, sms_message

def ceph_osd_restart_down(node_list):
    for node in node_list:
        logging.info(u'正在重启 % s在 %s' % (node['name'], node['host']))
        cmd = "ssh root@%s '/etc/init.d/ceph restart %s' > /dev/null 2>1&" % (node['host'], node['name'])
        # print cmd
        os.system(cmd)


def ceph_osd_tree_check_down_one(host, port):
    osd_tree = ceph_osd_tree(host, port)
    if osd_tree is None:
        return 0, 0, None

    nodes_osds = osd_tree['output']['nodes']
    host = None
    re_list = []
    total_num = 0
    down_num = 0

    for node_osd in nodes_osds:
        status = node_osd.get('status', False)
        if status is False:
            host = node_osd.get('name', None)
        elif 'down' == status:
            re_node = {}
            re_node[u'host'] = host
            re_node[u'id'] = node_osd['id']
            re_node[u'name'] = node_osd['name']
            re_node[u'status'] = node_osd['status']
            re_list.append(re_node)
            total_num += 1
            down_num += 1
        else:
            total_num += 1
            continue

    return down_num, total_num, re_list

def main_loop():
    while True:
        config = Config()
        down_num, total_num, re_list = ceph_osd_tree_check_down_one(config.host, config.port)

        if re_list is None:
	    logging.info(u'Ceph REST API 异常！')
            time.sleep(config.interval)
            continue
        elif down_num == 0:
	    logging.info(u'Ceph OSD全部正常！')
            time.sleep(config.interval)
            continue
        else:
            logging.info(u'检测到下面这些OSD目前处于DOWN状态：%s！' % [node['name'] for node in re_list])
            ceph_osd_restart_down(re_list)
            logging.info(u'等待%d秒' % config.restart_interval)
            time.sleep(config.restart_interval)
            logging.info(u'再次检查！')
            down_num, total_num, re_list = ceph_osd_tree_check_down_one(config.host, config.port)
            if re_list is None:
                time.sleep(config.interval - config.restart_interval)
                continue
            elif down_num == 0:
                time.sleep(config.interval)
                continue
            else:
                logging.info(u'依旧检测到下面这些OSD目前处于DOWN状态：%s' % [node['name'] for node in re_list])
                if config.get_event_done() == 1:
                    logging.info(u'已经有人在处理了，不再报警！')
                else:
                    email_message, sms_message = make_ceph_osd_down_message(re_list, down_num, total_num)
                    send_email(email_message, config.get_contact_email())
                    left_sms_num = config.get_max_sms_num()
                    if left_sms_num != 0:
                        re = send_sms(sms_message, config.get_contact_telephone())
                        re = json.loads(re)
                        if re['msg'] == 'OK':
                            logging.info(u'短信发送成功！')
                            left_sms_num -= 1
                            config.set_max_sms_num(left_sms_num)
                        else:
                            logging.info(u'短信发送存在异常！\n%s' % re)
                    else:
                        logging.info(u'已经发了3条短信了，不在继续发送！')


            time.sleep(config.interval)

def daemon_stop(config):
    pid = config.get_daemon_pid()
    try:
        os.kill(pid, 9)
        logging.info(u'停止监控程序!')
    except Exception:
        logging.info(u'无法停止监控程序，可能监控程序还没有运行!')

def daemon_start(config):
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)
    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent, print eventual PID before
            config.set_daemon_pid(pid)
            logging.info(u'启动监控程序（PID %d）' % pid)
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)
    # start the daemon main loop
    time.sleep(1)
    main_loop()
