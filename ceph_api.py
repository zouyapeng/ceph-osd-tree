# -*- coding: utf-8 -*-
import json
import requests

def ceph_osd_tree(host, port):
    url = "http://{0}:{1}".format(host, port) +\
          "/api/v0.1/osd/tree"
    headers = {'Accept': 'application/json'}
    try:
        re = requests.get(url, headers=headers, timeout=5)
    except Exception,e:
        return None

    return json.loads(re.text)
