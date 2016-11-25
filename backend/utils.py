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

import re

# Input type
YESNO = 'yesno'
IP_ADDRESS = 'ip_address'
NUMBER = 'number'
# Messages printed to stdout
OK_MSG = '\t\t[OK]'
FAIL_MSG = '\t\t[FAIL]'
TEST_INFO_MSG = 'Testing :'
TEST_SECTION_END_MSG = '-*-*- End of testing section -*-*- ' + '-'*40


def is_ipaddr(user_input,
              netmask_required=False,
              netmask_range=[0, 32],
              debug=True):
    """
    Checks if `user_input` is an IPV4 address.

    Returns True if it's an IPV4 address, False otherwise.
    """
    SLASH = '/'
    IPV4_LEN = 4
    # Messages printed to stdout
    IS_NOT_NUMB_MSG = '[ERROR] Value typed are not integer'
    NO_NETMASK_MSG = ('[ERROR] No netmask provided :: '
                      + 'input must be <ip address>/<netmask>')
    NOT_ENOUGH_FIELDS_MSG = ('[ERROR] Not enough fields provided :: '
                             + 'input must be like "192.168.1.35"')
    WRONG_NETMASK_MSG = ('[ERROR] Wrong value for netmask :: '
                         + 'input must be between '
                         + str(netmask_range[0])
                         + ' and '
                         + str(netmask_range[1]))
    WRONG_IP_MSG = ('[ERROR] Wrong value for IP field :: '
                    + 'inputs must be between 0 and 255')

    ip_address = None

    if netmask_required and SLASH not in user_input:
            if debug:
                print(NO_NETMASK_MSG)
            return False
    elif SLASH in user_input:
        ip_address, netmask = user_input.split('/')
        if not netmask.isdigit():
            if debug:
                print(IS_NOT_NUMB_MSG)
            return False
        if int(netmask) < netmask_range[0] or int(netmask) > netmask_range[1]:
            if debug:
                print(WRONG_NETMASK_MSG)
            return False

    if ip_address:
        retvalue = has_valid_ip(ip_address)
    else:
        retvalue = has_valid_ip(user_input)

    return retvalue


def has_valid_ip(ip_string):
    """
    Check if `ip_string` is a valid ip address format.

    Note: Only IPV4 is valid for v1.0
    """
    IPV4_LEN = 4
    ipfields = ip_string.split(".")
    port = None

    if len(ipfields) < IPV4_LEN:
        raise ValueError

    if ":" in ipfields[-1]:
        ipfields[-1], port = ipfields[-1].split(":")

    for field in ipfields:
        if not field.isdigit():
            raise ValueError

        if not(int(field) >= 0 and int(field) <= 255):
            raise ValueError
    else:
        return True, port


def get_port(ip_string):
    """
    Return the port of a valid ip address.
    """
    retvalue, port = has_valid_ip(ip_string)
    if retvalue and port:
        return port


def inputchk(msg, intype=YESNO, verbose=False, input_test=None,
             *pargs, **kargs):
    """
    Checks user input based on input type `intype`.

    `msg` prints message to stdout to inform user before typing.
    `intype` sets the kind of handling for string that just have been typed.
    `verbose` prints message at stdout if set to `True`.
    `input_test` is a defined string passed by a tester function.

    Returns a correctly formatted user input.
    """
    is_bad_input = True

    if not input_test:
        user_inp = (input(msg)).lower()
    else:
        user_inp = input_test

    while is_bad_input:
        if intype == YESNO:
            if (user_inp == 'y' or
                    user_inp == 'yes' or
                    user_inp == 'n' or
                    user_inp == 'no'):
                is_bad_input = False
            else:
                if input_test:
                    return is_bad_input
                print('Please type: y, yes, n, no : ', end='')
                user_inp = (input()).lower()
        elif intype == NUMBER:
            if user_inp.isdigit():
                is_bad_input = False
            else:
                if input_test:
                    return is_bad_input
                print('Please type a number : ', end='')
                user_inp = (input()).lower()
        elif intype == IP_ADDRESS:
            if is_ipaddr(user_inp):
                is_bad_input = False
            else:
                if input_test:
                    return is_bad_input
                print('Please type a correct IPV4 address : ', end='')
                user_inp = input()
        else:
            print('[ERROR] Input type -> "', input_type,
                  '" doesn\'t exist.', sep='')
    else:
        return user_inp


def asciiconvert(user_input, enable_spechar=True):
    """
    Converts user-input string into ASCII.

    Returns a string with ASCII chars only
    """
    SPECHAR_RE = r'[\s.?!:;§*^¨%$\|\[\]\(\)\{\}+=`~\'\"\\&]*'
    accented_chars = [(r'[àäâ]*', 'a'),
                      (r'[éèëê]*', 'e'),
                      (r'[ìîï]*', 'i'),
                      (r'[òöô]*', 'o'),
                      (r'[ùûü]*', 'u'),
                      (r'[ÿŷỳ]*', 'y')]

    if not enable_spechar:
        spechar = re.compile(SPECHAR_RE)
        ans = spechar.findall(user_input)
        if ans:
            # Replacing all occurrences by an empty string
            user_input = spechar.sub('', user_input, count=0)
            re.purge()

    for pattern, repl in accented_chars:
        accented = re.compile(pattern)
        # Replacing all occurrences by a non-accented char
        user_input = accented.sub(repl, user_input, count=0)
        re.purge()

    return user_input


def _asciiconvert_tester(verbose=False):
    """
    Tests `asciiconvert` function when utils.py is launched as standalone.
    """
    # TODO: Has to be implemented


def _is_ipaddr_tester(verbose=False):
    """
    Tests `is_ipaddr` function when utils.py is launched as standalone.

    If `verbose` is set to `True`, it prints each succeed steps,
    otherwise it prints only in case of failing.
    If test fails, it prints to stdout where the testing loop stopped.
    """

    def ip_loop(test_ip_dict, verbose, noted=False, debug=False):
        """
        Loops over a dict of IPs and prints messages on stdout.

        Set `noted` to `True` to reverse boolean logic (False = True).
        It's used to make bad inputs pass the test since `is_ipaddr`
        function would return `False` in case of bad input.

        It also check if there is string 'mask' in the dict key so as to
        set `netmask_required` to `True` in `is_ipaddr` calling.
        """
        for key in test_ip_dict:
            for item in test_ip_dict[key]:
                if 'mask' in key:
                    result = is_ipaddr(item, 
                                       netmask_required=True,
                                       debug=False)
                else:
                    result = is_ipaddr(item, debug=False)

                if noted:
                    result = not result
                if result:
                    if verbose:
                        print(TEST_INFO_MSG, key, item, OK_MSG)
                else:
                    print(TEST_INFO_MSG, key, item, FAIL_MSG)
        else:
            if verbose:
                print(TEST_SECTION_END_MSG)

    # Good inputs section vars :
    ip_ok1 = '0.0.0.0'
    ip_ok2 = '192.168.1.1'
    ip_ok3 = '255.255.255.255'
    mask_ok1 = '/0'
    mask_ok2 = '/24'
    mask_ok3 = '/32'
    good_ip_only = [ip_ok1, ip_ok2, ip_ok3]
    good_mask = [mask_ok1, mask_ok2, mask_ok3]
    good_ip_mask = [ip + mask for ip in good_ip_only for mask in good_mask]
    good_inputs = {'good_ip_only': good_ip_only,
                   'good_ip_mask': good_ip_mask}
    # Bad inputs section vars :
    ip_bad1 = '192.168.1.256'
    ip_bad2 = '192.168.999.1'
    ip_bad3 = '192.444.128.60'
    ip_bad4 = '555.333.777.888'
    ip_bad_len1 = '192.168.1.'
    ip_bad_len2 = '192.168..'
    ip_bad_len3 = '192.'
    ip_bad_len4 = '192'
    ip_bad_neg1 = '-192.168.1.1'
    ip_bad_neg2 = '192.168.-128.50'
    ip_bad_str = '192.abc.1.50'
    mask_bad1 = '/33'
    mask_bad2 = '/-1'
    mask_bad_empty = '/'
    mask_bad_str = '/abc'
    bad_ip_only = [ip_bad1, ip_bad2, ip_bad3, ip_bad4,
                   ip_bad_len1, ip_bad_len2, ip_bad_len3, ip_bad_len4,
                   ip_bad_neg1, ip_bad_neg2,
                   ip_bad_str]
    bad_mask = [mask_bad1, mask_bad2, mask_bad_empty, mask_bad_str]
    bad_mask_good_ip = [ip + mask for mask in bad_mask for ip in good_ip_only]
    bad_inputs = {'bad_ip_only': bad_ip_only,
                  'bad_mask_good_ip': bad_mask_good_ip}

    ip_loop(good_inputs, verbose)
    ip_loop(bad_inputs, verbose, noted=True)


def _inputchk_tester(interactive=False, verbose=False):
    """
    Tests `inputchk` function when utils.py is launched as standalone
    It performs only YESNO and NUMBER input tests when `interactive` is
    set to `False` since IP_ADDRESS input type is tested in another test unit.

    If `verbose` is set to `True`, it prints each succeed steps,
    otherwise it prints only in case of failing.
    If test fails, it prints to stdout where the testing loop stopped.
    """
    def input_loop(input_dict, verbose):
        """
        Loops over a dict of inputs and prints messages on stdout.

        Set `noted` to `True` to reverse boolean logic (False = True).
        It's used to make bad inputs pass the test since `is_ipaddr`
        function would return `False` in case of bad input.
        """
        for key in input_dict:
            for item in input_dict[key]:
                result = inputchk('', intype=key, input_test=item)
                if result:
                    if verbose:
                        print(TEST_INFO_MSG, key, item, OK_MSG)
                else:
                    print(TEST_INFO_MSG, key, item, FAIL_MSG)
        else:
            if verbose:
                print(TEST_SECTION_END_MSG)

    INPUT_TEST = 'input test : '
    MSG_YESNO = YESNO + ' ' + INPUT_TEST
    MSG_NUMBER = NUMBER + ' ' + INPUT_TEST
    MSG_IP_ADDRESS = IP_ADDRESS + ' ' + INPUT_TEST
    inputchk_tests = [(MSG_YESNO, YESNO),
                      (MSG_NUMBER, NUMBER),
                      (MSG_IP_ADDRESS, IP_ADDRESS)]
    # Good inputs section vars :
    yesno_ok1 = 'y'
    yesno_ok2 = 'yes'
    yesno_ok3 = 'n'
    yesno_ok4 = 'no'
    numb_ok1 = '1'
    numb_ok2 = '123456789'
    good_inputs = {YESNO: [yesno_ok1, yesno_ok2, yesno_ok3, yesno_ok4],
                   NUMBER: [numb_ok1, numb_ok2]}
    # Bad inputs section vars :
    yesno_bad1 = 'abc'
    yesno_bad2 = '123'
    yesno_bad3 = 'yy'
    yesno_bad4 = 'nn'
    yesno_bad5 = 'ye'
    yesno_bad6 = 'nn'
    numb_bad1 = 'spam'
    numb_bad2 = '-1'
    bad_inputs = {YESNO: [yesno_bad1, yesno_bad2, yesno_bad3,
                          yesno_bad4, yesno_bad5, yesno_bad6],
                  NUMBER: [numb_bad1, numb_bad2]}

    if interactive:
        for msg, input_type in inputchk_tests:
            user_input = inputchk(msg, intype=input_type)
            if user_input:
                if verbose:
                    print(msg, '\t\t[OK]')
            else:
                if verbose:
                    print(msg, '\t\t[FAIL]')
    else:
        # If good_inputs pass the test, it returns a string
        input_loop(good_inputs, verbose)
        # If bad_inputs pass the test, it return `True`
        input_loop(bad_inputs, verbose)


if __name__ == '__main__':
    asciiconvert('?te!s$\\^*t', enable_spechar=False)
    _is_ipaddr_tester(verbose=True)
    _inputchk_tester(verbose=True)
