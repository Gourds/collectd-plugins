# redis-collectd-plugin - pika_info.py
#

import collectd
import socket
import re

# Verbose logging on/off. Override in config by specifying 'Verbose'.
VERBOSE_LOGGING = False
INTERVAL = 5 # seconds
CONFIGS = []


def fetch_info(conf):
    """Connect to Redis server and request info"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((conf['host'], conf['port']))
        log_verbose('Connected to Pika at %s:%s' % (conf['host'], conf['port']))
    except socket.error, e:
        collectd.error('pika_info plugin: Error connecting to %s:%d - %r'
                       % (conf['host'], conf['port'], e))
        return None
    fp = s.makefile('r')
    if conf['auth'] != None:
        s.sendall('auth %s\r\n' % (conf['auth']))
        status_line = fp.readline()
    s.sendall('info\r\n')
    #data = s.recv(1024)
    status_line = fp.readline()
    log_verbose('Gourds-Debug %s' % status_line)
    content_length = int(status_line[1:-1])  # status_line looks like: $<content_length>
    log_verbose('Gourds-Debug-Content_length: %s' % content_length)
    data = fp.read(content_length)
    s.close()
    linesep = '\r\n' if '\r\n' in data else '\n'  # assuming all is done in the same connection...
    data_dict = parse_info(data.split(linesep))
    #log_verbose(data_dict)
    return data_dict

def parse_info(info_lines):
    """Parse info response from Redis"""
    info = {}
    for line in info_lines:
        log_verbose('Gourds_parse_info %s' % line)
        if "" == line or line.startswith('#'):
            continue
#        if ':' not in line:
        if ':' not in line or len(line.split(':')) > 2:
            log_verbose('pika_info plugin: Bad format for info line: %s' % line)
            continue
        key, val = line.split(':')
        if ',' in val:
            split_val = val.split(',')
            for sub_val in split_val:
                k, _, v = sub_val.rpartition('=')
                sub_key = "{0}_{1}".format(key, k)
                info[sub_key] = v
        else:
            info[key] = val
    # compatibility with pre-2.6 redis (used changes_since_last_save)
    info["changes_since_last_save"] = info.get("changes_since_last_save", info.get("rdb_changes_since_last_save"))
    return info


def configure_callback(conf):
    """Receive configuration block"""
    host = None
    port = None
    auth = None
    cluster = True
    instance = None
    pika_info = {}

    for node in conf.children:
        key = node.key.lower()
        val = node.values[0]
        log_verbose('Analyzing config %s key (value: %s)' % (key, val))
        if key == 'host':
            host = val
        elif key.startswith('#'):
            pass
        elif key == 'port':
            port = int(val)
        elif key == 'auth':
            auth = val
        elif key == 'cluster':
            cluster = bool(node.values[0])
        elif key == 'verbose':
            global VERBOSE_LOGGING
            VERBOSE_LOGGING = bool(node.values[0]) or VERBOSE_LOGGING
        elif key == 'instance':
            instance = val
        else:
            log_verbose('Matching expression found: key: %s - value: %s' % (key, val))
            pika_info[key, val] = True
    log_verbose('Configured with host=%s, port=%s, instance name=%s, using_auth=%s, cluster=%s, pika_info_len=%s' % (host, port, instance, auth!=None, cluster, len(pika_info)))
    CONFIGS.append({'host': host, 'port': port, 'auth': auth, 'instance': instance, 'cluster': cluster, 'pika_info': pika_info})
    log_verbose(CONFIGS)


def dispatch_value(info, key, type, plugin_instance=None, type_instance=None):
    """Read a key from info response data and dispatch a value"""
    if key not in info:
        collectd.warning('pika_info plugin: Info key not found: %s, Instance: %s' % (key, plugin_instance))
        return
    if plugin_instance is None:
        plugin_instance = 'unknown redis'
        collectd.error('pika_info plugin: plugin_instance is not set, Info key: %s' % key)
    if not type_instance:
        type_instance = key
    try:
        value = int(info[key])
    except ValueError:
        value = float(info[key])
    except TypeError:
        log_verbose('No info for key: %s' % key)
        return
    log_verbose('Sending value: %s=%s' % (type_instance, value))
    #val = collectd.Values(type=type,type_instance=type_instance)
    #val.plugin = 'pika_info'
    val = collectd.Values(plugin='pika_info')
    val.type = 'gauge'
    val.type_instance = type_instance
    val.plugin_instance = plugin_instance
    val.values = [value]
    val.dispatch()


def read_callback(data=None):
    for conf in CONFIGS:
        get_metrics(conf)

def write_callback(val, data=None):
    for i in val.values:
        print "%s (%s): %f" % (val.plugin, val.type, i)

def get_metrics(conf):
    info = fetch_info(conf)
    if not info:
        collectd.error('redis plugin: No info received')
        return
    plugin_instance = conf['instance']
    if plugin_instance is None:
        plugin_instance = '{host}:{port}'.format(host=conf['host'], port=conf['port'])
    for keyTuple, val in conf['pika_info'].iteritems():
        key, val = keyTuple
        if key == 'total_connections_received' and val == 'counter':
            #dispatch_value(info, 'total_connections_received', 'counter', plugin_instance, 'connections_received')
            pass
        elif key == 'total_commands_processed' and val == 'counter':
            #dispatch_value(info, 'total_commands_processed', 'counter', plugin_instance, 'commands_processed')
            pass
        else:
            dispatch_value(info, key, val, plugin_instance)
            pass


def log_verbose(msg):
    if VERBOSE_LOGGING == False:
        pass
    else:
        collectd.info('pika plugin [verbose]: %s' % msg)


# register callbacks
collectd.register_config(configure_callback)
collectd.register_read(read_callback, INTERVAL)
#collectd.register_write(write_callback)
