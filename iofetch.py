#!/usr/bin/env python34
# -*- coding: utf-8 -*-

# This file is part of ABYSS.
# ABYSS Broadcast Your Streaming Successfully 
#
# ABYSS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ABYSS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ABYSS.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (c) 2016 David Testé

#######################################################################
# TODO:
# - Add IP address fetching (from GUI)
# - Add input checker (for scanning network in console mode) 
#######################################################################

from os import listdir
from os import system
from os import path

hostaddr = [192,168,1,None]

IPSCAN_FILEPATH =r'/tmp/ipscan'
NO_HOST_MSG = 'No host reachable on'
HOST_MSG = '-**- IP available -**-\n'

# Device information :
CLASS = 'class'
CLASS_AUDIO = 'audio'
CLASS_VIDEO = 'video'
COMM = 'comm'
COMM_USB = 'usb'
COMM_IP = 'ip'
DESCRIP = 'description'
GSTELEM = 'gstelement'
GSTINIT = None
TYPE = 'type'
TYPE_IN = 'input'
TYPE_OUT = 'output'

total_ip = []

part_a = []
part_b = []
current_part = part_a

for item in hostaddr:
    if item or item == 0:
        current_part.append(item)
    else:
        current_part = part_b

part_a_str = [str(i) for i in part_a]
subnet = '.'.join(part_a_str) + '.'


def find_audio():
    """
    Looks for all input/output audio device available,
    based on pulseaudio server.

    Returns a dict formatted like:
    {device_name : {descrip : device_descrip,
                    class : CLASS_AUDIO,
                    type : in/out,
                    gstelement : None}}
    """
    AUDIO_DEV_LIST_PATH = r'/tmp/audio_dev'
    audio_dev = {}
    cmd = 'pactl list > ' + AUDIO_DEV_LIST_PATH + ' 2>&1'
    
    system(cmd)
    audio_dev = parse_pactl_list(AUDIO_DEV_LIST_PATH, audio_dev)

##    print ('--**-- AUDIO DEVICES --**--\n', audio_dev)
    return audio_dev

def parse_pactl_list(filepath, output_dict,):
    """
    Parses file created during CDL 'pactl list'.

    Returns output_dict.
    """
    INPUT = 'alsa_input'
    OUTPUT = 'alsa_output'
    NAME_LINE = 'Name: '
    DESCRIP_LINE = 'Description: '
    dev_name = ''
    dev_descrip = ''
    is_input = False
    is_output = False
    
    with open(filepath, 'r') as f:
        for line in f:
            if NAME_LINE in line:
                dev_name = line[(len(NAME_LINE) + 1):].rstrip()
                if INPUT in dev_name: is_input = True
                elif OUTPUT in dev_name: is_output = True
            elif DESCRIP_LINE in line :
                dev_descrip = line[(len(DESCRIP_LINE) + 1):].rstrip()

            if dev_name and dev_descrip:
                if is_input:
                    entry = {dev_name : {DESCRIP : dev_descrip,
                                         CLASS : CLASS_AUDIO,
                                         TYPE : TYPE_IN,
                                         GSTELEM : GSTINIT,}}
                if is_output:
                    entry = {dev_name : {DESCRIP : dev_descrip,
                                         CLASS : CLASS_AUDIO,
                                         TYPE : TYPE_OUT,
                                         GSTELEM : GSTINIT,}}
                output_dict.update(entry)
                dev_name = ''
                dev_descrip = ''
                is_input = False
                is_output = False
    return output_dict
                
def find_usbcam():
    """
    Looks for all USB camera currently connected.

    Return a dict formatted like: {device_name : device_path}.
    {device_location : {descrip : device_descrip,
                        class : CLASS_VIDEO
                        comm : COMM_USB
                        type : in/out
                        gstelement : None}}
    """
    DEVICE_ID_PATH = r'/dev/v4l/by-id/'
    DEVICE_RAW_PATH = r'/dev/'
    VIDEO_DEVICE_PATH = r'/sys/class/video4linux/'
    video_dev = {}
    
    # Using /dev/videoX name
    dev_list = [DEVICE_RAW_PATH + dev for dev in listdir(DEVICE_RAW_PATH)
                if CLASS_VIDEO in dev]
    dev_infopath = [VIDEO_DEVICE_PATH + dev for dev in listdir(VIDEO_DEVICE_PATH)]
    for dev in dev_infopath:
        dev_namepath = path.realpath(dev) + r'/name'
##        print('dev_namepath =', dev_namepath)
        with open(dev_namepath, 'r') as f:
            dev_name = f.readline().rstrip()
##            print('dev_name =', dev_name)
        for i in dev_list:
            splitted = i.split('/')
            if splitted[-1] in dev:
                video_dev.update({i : {DESCRIP : dev_name,
                                       CLASS : CLASS_VIDEO,
                                       COMM : COMM_USB,
                                       TYPE: TYPE_IN,
                                       GSTELEM : GSTINIT,}})
##    print ('--**-- USB VIDEO DEVICES --**--\n', video_dev)
    return video_dev  
    
    
def scan_subnet(partial_IP):
    """
    Scans the entire subnet of partial_IP.
    partial_IP has to be passed as a list (e.g. :[192,168,0]) 

    Yields a list of all connected devices on a given subnet.
    """
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#    - Make 'fping' dependance of the software
#    - Add an user interface to scan_subnet to handle the iterator
#      (so as to scan one subnet at a time based on user decision
#       e.g. button 'Next subnet' in GUI)
#    - Gather results of all IP found in one list of lists
#      (or dict of lists with key = subnet) when scan ends.
#      --> easy retreiving of all IP in GUI
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    netmask = 24
    avail_ip = []
    length = len(partial_IP)
    partial_IP_str = [str(i) for i in partial_IP]
    subnet_str = '.'.join(partial_IP_str) + '.'
    cmd_first = 'fping -c 1 -q -a -g '
    cmd_mid = ''
    cmd_last = '/' + str(netmask) + '> ' + IPSCAN_FILEPATH + ' 2>&1'
    
    if length == 1:

        pass

##        full_cmd = cmd_first + cmd_mid + cmd_last
##        print (subnet_str)
##        print (full_cmd)
##        print('Scanning network...')
##        system(full_cmd)
    elif length == 2:
        print('Scanning network...')
        for i in range(255):
            cmd_mid = subnet_str + str(i) + '.0'
            full_cmd = cmd_first + cmd_mid + cmd_last
            system(full_cmd)
            has_no_host = True
            avail_ip = parse_scan_result(IPSCAN_FILEPATH,
                                         NO_HOST_MSG,
                                         HOST_MSG,
                                         cmd_mid,)
            yield
    elif length == 3:
        cmd_mid = subnet_str + '0'
        full_cmd = cmd_first + cmd_mid + cmd_last
        print('Scanning network...')
        system(full_cmd)
        avail_ip = parse_scan_result(IPSCAN_FILEPATH,
                                     NO_HOST_MSG,
                                     HOST_MSG,
                                     cmd_mid,) 

def parse_scan_result(path, no_host_msg, host_msg, subnet):
    """Parse tmp file created during scanning a subnet."""
    result_list = []
    has_no_host = True
    with open(path, 'r') as scan_result:
        for line in scan_result:
            if 'min/avg/max' in line:
                splitted = line.split(':')
                result_list.append(splitted[0].rstrip(' '))
                has_no_host = False
        if has_no_host:
            print(no_host_msg, subnet)
        else:
            print(host_msg, '\n'.join(result_list), sep='')
    return result_list


def update_deviceinfo(device_dict, field, *pargs, update_msg=None, **kargs):
    """
    Update dict containing device's information.
    In v1.0 field must be a one element dict.
    """
    cond = len(field)
    if field and cond == 1:
        device_dict.update(field)
        print(update_msg)
    else:
        print('[INFO] Updating dict failed - \'field\' is empty or have length > 1')

    
##find_audio()
##find_usbcam()
##exit() # -->[DEBUG]<--

# Use iterator manually via CDL
# -----------------------------
user_scan = input('Scan network ?[y/n] ')
##user_scan = raw_input('Scan network ? [y/n] ') # Python 2.X compatibility
if (user_scan == 'y'
        or user_scan == 'Y'
        or user_scan == 'yes'
        or user_scan == 'Yes'):
    user_scan = True
    ip_iter = scan_subnet(part_a)
    while user_scan:
        try:
            next(ip_iter)
            user_scan = input('Scan next subnet ?[y/n] ')
##            user_scan = raw_input('Scan next subnet ? [y/n] ') 
            if user_scan == 'y':
                user_scan = True                
            elif user_scan == 'n':
                user_scan = False
                print('Scan aborted')
        except:
            print('Scan completed')
            break
elif user_scan == 'n':
    print('Scan canceled')
    pass
        