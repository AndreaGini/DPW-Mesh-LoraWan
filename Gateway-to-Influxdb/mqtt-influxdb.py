#!/usr/bin/python

import ConfigParser
import json
import sys
import time
import paho.mqtt.client as paho
from influxdb import InfluxDBClient 


config = ConfigParser.ConfigParser()

config.read("/etc/mqtt-influx/mqtt-influx.conf")

srv_name = config.get('server', 'name')
srv_port = config.getint('server', 'port')
srv_user = config.get('server', 'user')
srv_passwd = config.get('server', 'passwd')
db_name = config.get('database', 'name')
mqtt_name = config.get('mqtt', 'name')
mqtt_port = config.getint('mqtt', 'port')
mqtt_user = config.get('mqtt', 'user')
mqtt_passwd = config.get('mqtt', 'passwd')


clientinflux = InfluxDBClient(srv_name, srv_port, srv_user, srv_passwd, db_name)

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))
 
def on_message(client, userdata, msg):
    m = json.loads(str(msg.payload))    
    n = json.dumps(m)
    o = json.loads(n)
    r = json.dumps( o['fields'])
    p = json.loads(r)
    json_body = [
        {
                "measurement": "remote_sensors",
                "tags": {
                    "host": o['devaddr']
            },
            "fields": {
                "L1": p['line1'],
                "L2": p['line2'],
                "L3": p['line3'],
            }
        }
    ]
    try:
        clientinflux.write_points(json_body)
    except:
        print 'Append error, logging in again'
try:
    client = paho.Client()
    client.username_pw_set(mqtt_user,mqtt_passwd)
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(mqtt_name, mqtt_port)
    client.subscribe("out/#" )
    
    client.loop_forever()
    
except KeyboardInterrupt:
    print 'exit keyboard interrupted'
