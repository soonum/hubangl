#!/usr/bin/env python34
# -*- coding: utf-8 -*-

# This file is part of HUBAngl.
# HUBAngl Uses Broadcaster Angle 
#
# HUBAngl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HUBAngl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HUBAngl.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (c) 2016 David Testé

# Input type
YESNO = 'yesno'
IP_ADDR = 'ip_addr'
NUMBER = 'number'

def is_ipaddr(user_input):
    """
    Checks if `user_input` is an IPV4 address.

    Returns True if it's an IPV4 address, False otherwise.
    """
    pass

    
def inputchk(msg, intype=YESNO, *pargs, **kargs):
    """
    Checks user input based on input type `intype`.

    Returns a correctly formatted user input.
    """
    is_bad_input = True

    user_inp = (input(msg)).lower()
    while is_bad_input:
        if intype == YESNO:
            if (user_inp == 'y' or
                    user_inp == 'yes' or
                    user_inp == 'n' or
                    user_inp == 'no'):
                is_bad_input = False
            else:
                print('Please type: y, yes, n, no : ', end='')
                user_inp = (input()).lower()
        elif intype == NUMBER:
            if user_inp.isdigit():
                is_bad_input = False
            else:
                print('Please type a number : ', end='')
                user_inp = (input()).lower()
        elif intype == IP_ADDR:
            if is_ipaddr(user_inp):
                is_bad_input = False
            else:
                print('Please type a correct IPV4 address : ')
                user_inp = input()
    else:
        return user_inp


        
def tester():
    """
    Tests functions of utils module.
    """
    # Input checker `inputchk` section
    INPUT_TEST = 'input test : '
    MSG_YESNO = YESNO + ' ' + INPUT_TEST
    MSG_NUMBER = NUMBER + ' ' + INPUT_TEST
    MSG_IP_ADDR = IP_ADDR + ' ' + INPUT_TEST
    inputchk_tests = [(MSG_YESNO, YESNO),
                       (MSG_NUMBER, NUMBER),
                       (MSG_IP_ADDR, IP_ADDR),]
    for msg, input_type in inputchk_tests:
        user_input = inputchk(msg, intype=input_type)
        if user_input:
            print(msg, '\t\t[OK]')
        else:
            print(msg, '\t\t[FAIL]')
        
if __name__ == '__main__':
    tester()