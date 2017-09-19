#!/usr/bin/python
from __future__ import division
import smbus
import RPi.GPIO as GPIO
import ConfigParser
import json
import sys
import time
import datetime
import subprocess
from influxdb import InfluxDBClient 


FREQUENCY_SECONDS      = 300
RETRY_SECONDS          = 1
FANON_TEMP             = 35

influxconfig = ConfigParser.ConfigParser()

influxconfig.read("/etc/gateway-to-influxdb/gateway-to-influxdb.conf")

srv_name = influxconfig.get('server', 'name')
srv_port = influxconfig.getint('server', 'port')
srv_user = influxconfig.get('server', 'user')
srv_passwd = influxconfig.get('server', 'passwd')
db_name = influxconfig.get('database', 'name')

influxclient = InfluxDBClient(srv_name, srv_port, srv_user, srv_passwd, db_name)

GPIO.setmode (GPIO.BCM)
fan = 18
GPIO.setup(fan, GPIO.OUT)

#Voltage section --------------------------------


bus = smbus.SMBus(1)

# I2C address
DEVICE_ADDRESS = 0x68

# Voltage dividers
DIVIDER_R1 = 6800
DIVIDER_R2 = 3600
DIVIDER_R3 = 470

# ADC reference
ADC_REF = 2048  # mV

# Config register bits
BIT_G0 = 0
BIT_G1 = 1
BIT_S0 = 2
BIT_S1 = 3
BIT_OC = 4
BIT_C0 = 5
BIT_C1 = 6
BIT_RDY = 7

# Conversion mode
CONVERSION_MODE_ONESHOT = 0
CONVERSION_MODE_CONT = 1 << BIT_OC

# Sample rate / accuracy
SAMPLE_RATE_240SPS = 0  # 12 bits
SAMPLE_RATE_60SPS = 1 << BIT_S0  # 14 bits
SAMPLE_RATE_15SPS = 1 << BIT_S1  # 16 bits

# PGA gain selection
PGA_GAIN_1 = 0
PGA_GAIN_2 = 1 << BIT_G0
PGA_GAIN_4 = 1 << BIT_G1
PGA_GAIN_8 = (1 << BIT_G1) | (1 << BIT_G0)

# Start a conversion in one shot mode
START_CONVERSION = 1 << BIT_RDY



def get_voltage(measurement, bit):
    # Write configuration
    v2 = measurement * ADC_REF / (2**bit)
    total_r = DIVIDER_R1 + DIVIDER_R2 + DIVIDER_R3
    return v2 / (DIVIDER_R2 / total_r) * 2
#END Voltage Section --------------------------------

try:
    while True:
        busconfig = START_CONVERSION | CONVERSION_MODE_ONESHOT | SAMPLE_RATE_15SPS | PGA_GAIN_1
        bus.write_byte(DEVICE_ADDRESS, busconfig)
        time.sleep(0.15)
        data = bus.read_i2c_block_data(DEVICE_ADDRESS, 0x00, 3)
        value = (data[0] << 8) + data[1]
        sh21tval = subprocess.check_output("/usr/local/sbin/sht21 S", shell=True)
        sh21ttemp = float(sh21tval[0:4])
        sh21thum = float(sh21tval[5:8])
        voltval = round((get_voltage(value, 16) / 1000), 4)
        
        if sh21ttemp >= FANON_TEMP :
                GPIO.output(fan, 1)
        else:
                GPIO.output(fan, 0)
        
        time.sleep(4.45)
        
        json_body = [
            {
                "measurement": "gateways",
                "tags": {
                    "host": "Gateway2"
                },
                "fields": {
                    "temp": sh21ttemp,
                    "hum": sh21thum,
                    "volt": voltval,                  
                }
            }
        ] 
        # Append the data in the influxdb
        try:
                influxclient.write_points(json_body)
        except:
                print 'Append error, logging in again'
                time.sleep(RETRY_SECONDS)
                continue



except KeyboardInterrupt:
    GPIO.cleanup()
    print 'exit and GPIO cleanup'
    
