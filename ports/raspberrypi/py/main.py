# ---------------------------------------
#  _____  __  __ _______        __   ___  
# |  __ \|  \/  |__   __|      /_ | / _ \ 
# | |__) | \  / |  | |    __   _| || | | |
# |  ___/| |\/| |  | |    \ \ / / || | | |
# | |    | |  | |  | |     \ V /| || |_| |
# |_|    |_|  |_|  |_|      \_/ |_(_)___/ 
# ----------------------------------------
#  Version 1.0
#  Raspbian Lite version February 2020
#  Python 3.7
#  Filename : main.py

from gps import GPS
import logging
from machine import reset, SDCard
from network import WLAN, STA_IF
from os import remove
from post import *
from utime import sleep
import os
from wifi_connect import *
from gc import collect
from gdt import GDT

# import encry

ap_blacklist = ["xfinitywifi", "CableWiFi", "Omni10_Setup_B3B", "Regions Guest", "lululemonwifi", "Google Home.k"]



# Create a station object to store our connection
station = WLAN(STA_IF)

# activate station
station.active(True)



# pmt.conf is kept in the PMT git repo, go there
logging.openPMTDir()

with open("pmt.conf", 'rt') as fp:
    pmt_config = eval(fp.read())

try:
    post_url = "{0}/api/post.php".format(pmt_config['post_url'] if pmt_config['post_url'][-1] != "/" else pmt_config['post_url'][:-1])
    gps_interval = pmt_config['gps_interval']
    enc_key = pmt_config['encryption_key']
except KeyError as e:
    print(e)
    raise



# put python into runtime directory
logging.openRuntimeDir()

default = "pmt.log"
wifi = "wifi.log"
archive = "data.log"
unsent = "buffer.log"
blacklist = "blacklist.log"
current_ap = "SSID.log"
unsent_buffer_ptr = "buffer_pointer.log"

# create file should it not already exist,
# append mode should it already contain contents
with open(blacklist, "a+"):
    pass

defaultLogger = logging.getLogger("Default_Logger", default)
defaultLogger.setLevel(logging.DEBUG)

wifiLogger = logging.getLogger("WiFi_Connection_Logger", wifi)
wifiLogger.setLevel(logging.DEBUG)

archiveLogger = logging.getLogger("Archive", archive)
archiveLogger.setLevel(logging.DEBUG)

unsentLogger = logging.getLogger("Unsent", unsent)
unsentLogger.setLevel(logging.DEBUG)

blacklistLogger = logging.getLogger("Blacklist", blacklist)
blacklistLogger.setLevel(logging.DEBUG)

apLogger = logging.getLogger("Current_SSID", current_ap)
apLogger.setLevel(logging.DEBUG)

pointerLogger = logging.getLogger("BufferPointer", unsent_buffer_ptr)
pointerLogger.setLevel(logging.DEBUG)



# GPS PINOUT:
# TODO: Insert pinout
# instantiate GPS class
gps = GPS()
data = ""



# Accelerometer PINOUT:
# TODO: Insert pinout



with open(unsent_buffer_ptr, 'a+') as fp:
    total_bytes_read = int(fp.read()) if fp.read() != '' else 0

posted = False


collect()
# setup core WDT for partial reset (temporary)
# wdt = WDT(timeout=((5+gps_interval)*1000))
gdt = GDT(5+gps_interval, station, logger=blacklistLogger)

while True:
    [GPSdata, speed] = gps.get_RMCdata(defaultLogger)
    if not (GPSdata == {}):
        data=','.join(list(GPSdata.values()))+','

        #TODO: remove print
        print(data)
        archiveLogger.write(data)
        unsentLogger.write("{0}{1}".format(len(data), data))
        defaultLogger.info(data)
    else:
        #TODO: remove print
        print("No GPS data.")
        defaultLogger.info("No GPS data.")
        data = ""

    if station.isconnected():
        # enc_data = encry.encrypt(enc_key, rawData)
        posted = post_data(data, post_url, station, defaultLogger)
        
        msg = "SSID: {0} Connected, POST: {1}\r\n".format(str(apSSID), posted)
        wifiLogger.write(msg)
        # del enc_data
        # collect()

        data_points = ""
        with open(unsent_buffer_ptr, 'r') as fp:
            total_bytes_read = fp.read()
            total_bytes_read = int(total_bytes_read) if total_bytes_read != '' else 0

        with open(unsent, 'r') as fp:
            for i in range(15):
                file_ptr.seek(total_bytes_read)
                size = file_ptr.read(2)
                size = int(size) if size != '' else 0

                if size == 0:
                    remove(unsent)
                    total_bytes_read = 0
                    pointerLogger.overwrite(str(total_bytes_read))
                    break
                
                raw_data = file_ptr.read(int(size))
                total_bytes_read+=(2+size)

                if data == raw_data:
                    continue
                else:
                    data_points = "{0}{1}".format(data_points, raw_data)
                    del raw_data
                    collect()

            gdt.feed()
            print("Fed GDT after reading from buffer")

            if data_points != "":
                # enc_data = encry.encrypt(enc_key, rawData)
                posted = post_data(data_points, post_url, station, defaultLogger)

                msg = "SSID: {0} Connected, POST: {1}\r\n".format(str(apSSID), posted)
                wifiLogger.write(msg)
                # del enc_data

            if posted:
                pointerLogger.overwrite(str(total_bytes_read))

            del data_points
            collect()

    with open(blacklist, 'r') as fp:
        ap_list = fp.read()
        ap_list = ap_list.split("\n")
        ap_blacklist = ap_blacklist + list(set(ap_list[:-1]) - set(ap_blacklist))

    if (speed is not None) and (speed <= 10.00):
        if not station.isconnected():
            try:
                # @param nets: tuple of obj(ssid, bssid, channel, RSSI, authmode, hidden)
                nets = station.scan()
            except RuntimeError as e:
                #TODO: remove print
                print("Warning: {0}".format(str(e)))
                defaultLogger.warning(str(e)) 
            # get only open nets
            openNets = [n for n in nets if n[4] == 0]

            for onet in openNets:
                if onet[0].decode("utf-8") not in ap_blacklist:
                    # Try to connect to WiFi access point
                    apSSID = onet[0]
                    apLogger.overwrite(apSSID.decode("utf-8"))
                    #TODO: remove print
                    print ("Connecting to {0} ...\n".format(str(onet[0],"utf-8")))
                    wifiLogger.info("Connecting to {0} ...\n".format(str(onet[0],"utf-8")))
                    station.connect(onet[0])
                    while not station.isconnected():
                        sleep(0.5)
                    if station.isconnected():
                        connected = station_connected(station, post_url, gdt, wifiLogger)
                        if not connected:
                            blacklistLogger.write_line(apSSID.decode("utf-8"))
                            #TODO: remove print
                            print("Unable to Connect")
                            wifiLogger.warning("Unable to Connect")
                            break
    elif (speed is not None) and (speed > 10.00):
        remove(blacklist)

        # re-create file for initial read
        with open(blacklist, "a+"):
            pass

    sleep(gps_interval)

    #reset WDT to avoid Software Reset 0xc
    gdt.feed()
    print("Fed GDT in FSM")