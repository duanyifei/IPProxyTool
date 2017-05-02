#-*- coding: utf-8 -*-

import os
import json
from urllib2 import urlopen
import web
import sys
import config
import utils

from proxy import Proxy
from sqlhelper import SqlHelper

cur_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_path = os.path.join(cur_path, 'static')
if not os.path.exists(static_path):
    os.makedirs(static_path)

urls = (
    '/', 'index',
    '/insert', 'insert',
    '/select', 'select',
    '/delete', 'delete',
    '/refresh_proxy', 'refresh',
)

proxy_urls = [
    ("proxy_https.txt", "http://localhost:%s/select?https=yes" % config.data_port),
    ("proxy_all.txt", "http://localhost:%s/select" % config.data_port),
    ("proxy_anony1.txt", "http://localhost:%s/select?anonymity=1" % config.data_port),
    ("proxy_anony2.txt", "http://localhost:%s/select?anonymity=2" % config.data_port),
    ("proxy_anony3.txt", "http://localhost:%s/select?anonymity=3" % config.data_port),
]


def run_data_server():
    sys.argv.append('0.0.0.0:%s' % config.data_port)
    app = web.application(urls, globals())
    app.run()


class refresh(object):
    def GET(self):
        for filename, url in proxy_urls:
            resp = urlopen(url)
            data = resp.read()
            if data:
                data = json.loads(data)
            else:
                continue
            with open(os.path.join(static_path, filename), "w") as f:
                for item in data:
                    ip = item['ip']
                    port = item['port']
                    https = item['https']
                    protocal = 'https' if https == 'yes' else 'http'
                    f.write("{}\t{}\t{}\n".format(protocal, ip, port))
        return ""

class index(object):
    def GET(self):
        s = "Hello World!\n\n"
        urls = []
        for filename, url in proxy_urls:
            s += "http://localhost:%s/statis/%s\n" % (config.data_port, filename)
        return s


class insert(object):
    def GET(self):
        try:
            sql = SqlHelper()
            inputs = web.input()
            name = inputs.get('name')

            proxy = Proxy()
            proxy.set_value(
                    ip = inputs.get('ip'),
                    port = inputs.get('port'),
                    country = inputs.get('country', None),
                    anonymity = inputs.get('anonymity', None),
                    https = inputs.get('https', 'no'),
                    speed = inputs.get('speed', -1),
                    source = inputs.get('source', name),
            )

            utils.sql_insert_proxy(sql, name, proxy)

            command = "SELECT ip FROM {0} WHERE ip={1} AND port={2}".format(name, inputs.get('ip'), inputs.get('port'))
            res = sql.query_one(command)
            return res is None
        except:
            pass

        return False


class select(object):
    def GET(self):
        try:
            sql = SqlHelper()
            inputs = web.input()
            name = inputs.get('name', 'httpbin')
            anonymity = inputs.get('anonymity', None)
            https = inputs.get('https', None)
            order = inputs.get('order', 'speed')
            sort = inputs.get('sort', 'asc')
            count = inputs.get('count', 10000)

            command = ''
            if anonymity is None and https is None:
                command = "SELECT * FROM {name} ORDER BY {order} {sort} LIMIT {count}". \
                    format(name = name, order = order, sort = sort, count = count)
            elif anonymity is not None and https is None:
                command = "SELECT * FROM {name} WHERE anonymity=\'{anonymity}\' ORDER BY {order} {sort} " \
                          "LIMIT {count}". \
                    format(name = name, anonymity = anonymity, order = order, sort = sort, count = count)
            elif anonymity is None and https is not None:
                command = "SELECT * FROM {name} WHERE https=\'{https}\' ORDER BY {order} {sort} LIMIT {count}". \
                    format(name = name, https = https, order = order, sort = sort, count = count)
            elif anonymity is not None and https is not None:
                command = "SELECT * FROM {name} WHERE anonymity=\'{anonymity}\' AND https=\'{https}\' ORDER BY " \
                          "{order} {sort} limit {count}". \
                    format(name = name, anonymity = anonymity, https = https, order = order, sort = sort, count = count)
            result = sql.query(command)
            data = [{
                'id': item[0], 'ip': item[1], 'port': item[2], 'anonymity': item[4], 'https': item[5],
                'speed': item[6], 'save_time': str(item[8])
            } for item in result]

            data = json.dumps(data, indent = 4)
            return data
        except Exception, e:
            utils.log('select exception msg:%s' % e)
            pass

        return []


class delete(object):
    def GET(self):
        try:
            sql = SqlHelper()
            inputs = web.input()
            name = inputs.get('name')
            ip = inputs.get('ip')
            command = "DELETE FROM {0} WHERE ip=\'{1}\'".format(name, ip)
            sql.execute(command)

            command = "SELECT ip FROM {0} WHERE ip=\'{1}\'".format(name, ip)
            res = sql.query_one(command)
            return res is None
        except:
            pass
        return False
