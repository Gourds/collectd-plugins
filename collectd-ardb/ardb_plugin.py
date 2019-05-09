'''
Version:collectd (1.0)
yum install collectd-python
https://collectd.org/documentation/manpages/collectd-python.5.shtml
https://pythonhosted.org/collectd/
pip install redis
'''

import collectd
import socket
import redis

VERBOSE_LOGGING = 'info'  # True or False
PLUGIN_NAME = 'ardb_plugin'
INTERVAL = 5 # seconds
_v = 0
_foo = None

def log_verbose(msg):
    if VERBOSE_LOGGING == 'dev':
        print('Ardb plugin [Log]: %s' % msg)
    else:
        collectd.info('Ardb plugin [Log]: %s' % msg)

def fetch_info(conf):
    try:
        if 'auth' in conf.keys():
            data_dict = redis.StrictRedis(host=conf['host'],port=int(conf['port']),password=conf['auth']).info()
            log_verbose('Ardb Connectd Success Without Password...')
        else:
            data_dict = redis.StrictRedis(host=conf['host'],port=int(conf['port'])).info()
            log_verbose('Ardb Connectd Success With Password...')
    except socket.error, e:
        log_verbose('Ardb Connectd Failed...')
    # except :
    #     log_verbose('Connectd other err')
    return data_dict

def parse_info(info_lines):
    info = {}
    for line in info_lines:
        if "" == line or line.startswith('#'):
            continue
        if ':' not in line:
            return
        key, val = line.split(':')
        if ',' in val:
            split_val = val.split(',')
            for sub_val in split_val:
                k, _, v = sub_val.rpartition('=')
                sub_key = "{0}_{1}".format(key, k)
                info[sub_key] = v
        else:
            info[key] = val
    return info

def configure_callback(configobj):
    global _foo
    log_verbose('Ardb: Configure with: key=%s, children=%r' % (configobj.key, configobj.children))
    config = {c.key.lower(): c.values[0] for c in configobj.children}
    _foo = config
    data = fetch_info(_foo)



def read_callback():
    data = fetch_info(conf)
    log_verbose('spam(foo=%s):  Reading data (data (data=%r)' % (_foo, data))
    for vl in data:
        try:
            int(data[vl])
            log_verbose('Succeed get Key:%s Value: %s' % (vl, data[vl]))
            data_dispatch(vl,data[vl])
        except:
            pass

def data_dispatch(key,value,type='gauge'):
    val = collectd.Values(type=type)
    val.plugin = PLUGIN_NAME
    val.type_instance = key
    val.values = [value]
    val.dispatch()


collectd.register_config(configure_callback)
collectd.register_read(read_callback, INTERVAL)


if __name__ == '__main__':
    conf = {'host': '10.0.1.42', 'port': 16379}

    data1=fetch_info(conf)
    print data1
    read_callback()
    # print data1
    #print read_callback(fetch_info(conf))
