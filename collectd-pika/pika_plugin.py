'''
Version:collectd (1.0)
yum install collectd-python
https://collectd.org/documentation/manpages/collectd-python.5.shtml
https://pythonhosted.org/collectd/
docker run  -d --name pika  -p 9221:9221 pikadb/pika pika -c ./conf/pika.conf
'''

import collectd
import socket


VERBOSE_LOGGING = True  # True or False
PLUGIN_NAME = 'pika'
INTERVAL = 5 # seconds
_v = 0
_foo = None

def log_verbose(msg):
    if VERBOSE_LOGGING == False:
        pass
    else:
        print('pika plugin [Log]: %s' % msg)

def fetch_info(conf):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((conf['host'], int(conf['port'])))
        collectd.info('Connectd Success...')
        log_verbose('Connected to Pika at %s:%s' % (conf['host'], conf['port']))
    except socket.error, e:
        collectd.info('Connectd Failed...')
        log_verbose('Connected Pika Error')
    except :
        collectd.info('Connectd other err')
    fp = s.makefile('r')
    if 'auth' in conf:
        s.sendall('auth %s\r\n' % (conf['auth']))
        status_line = fp.readline()
    else:
        s.sendall('info\r\n')
        status_line = fp.readline()
    log_verbose(status_line)
    collectd.info(status_line)
    content_length = int(status_line[1:-1])  # status_line looks like: $<content_length>
    data = fp.read(content_length)
    s.close()
    linesep = '\r\n' if '\r\n' in data else '\n'  # assuming all is done in the same connection...
    data_dict = parse_info(data.split(linesep))
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
    collectd.info('pika: Configure with: key=%s, children=%r' % (configobj.key, configobj.children))
    config = {c.key.lower(): c.values[0] for c in configobj.children}
    _foo = config
    data = fetch_info(_foo)



def read_callback():
    data = fetch_info(_foo)
    log_verbose('spam(foo=%s):  Reading data (data (data=%r)' % (_foo, data))
    for vl in data:
        try:
            int(data[vl])
            collectd.info('Succeed get Key:%s Value: %s' % (vl, data[vl]))
            log_verbose('Gourds Get Key: %s Value: %s' % (vl, data[vl]))
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
collectd.register_read(read_callback, 5)


if __name__ == '__main__':
    conf = {'host': '10.0.1.42', 'port': 9221}
    data1=fetch_info(conf)
    read_callback(data1)
    # print data1

    #print read_callback(fetch_info(conf))
