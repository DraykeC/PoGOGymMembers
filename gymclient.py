#!/usr/bin/env python
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
"""

import os
import sys
import json
import time
import pprint
import logging
import getpass
import argparse
import platform

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util


log = logging.getLogger(__name__)

TIMESTAMP = '\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000'

def get_encryption_lib_path():
    lib_folder_path = os.path.join(
        os.path.dirname(__file__), "pgoapi\lib")
    lib_path = ""
    # win32 doesn't mean necessarily 32 bits
    if sys.platform == "win32":
        if platform.architecture()[0] == '64bit':
            lib_path = os.path.join(lib_folder_path, "encrypt64bit.dll")
        else:
            lib_path = os.path.join(lib_folder_path, "encrypt32bit.dll")

    elif sys.platform == "darwin":
        lib_path = os.path.join(lib_folder_path, "libencrypt-osx-64.so")

    elif os.uname()[4].startswith("arm") and platform.architecture()[0] == '32bit':
        lib_path = os.path.join(lib_folder_path, "libencrypt-linux-arm-32.so")

    elif sys.platform.startswith('linux'):
        if platform.architecture()[0] == '64bit':
            lib_path = os.path.join(lib_folder_path, "libencrypt-linux-x86-64.so")
        else:
            lib_path = os.path.join(lib_folder_path, "libencrypt-linux-x86-32.so")

    elif sys.platform.startswith('freebsd-10'):
        lib_path = os.path.join(lib_folder_path, "libencrypt-freebsd10-64.so")

    else:
        err = "Unexpected/unsupported platform '{}'".format(sys.platform)
        log.error(err)
        raise Exception(err)

    if not os.path.isfile(lib_path):
        err = "Could not find {} encryption library {}".format(sys.platform, lib_path)
        log.error(err)
        raise Exception(err)

    return lib_path

def send_map_request(api, position):
    try:
        api_copy = api.copy()
        api_copy.set_position(*position)
        api_copy.get_map_objects(latitude=f2i(position[0]),
                                 longitude=f2i(position[1]),
                                 since_timestamp_ms=TIMESTAMP,
                                 cell_id=util.get_cell_ids(position[0], position[1]))
        return api_copy.call()
    except Exception as e:
        log.warning("Uncaught exception when downloading map " + str(e))
        return False


def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load   = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",
        required=required("auth_service"))
    parser.add_argument("-u", "--username", help="Username", required=required("username"))
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
    parser.add_argument("-o", "--offline", help="Run in offline mode", action='store_true')
    parser.set_defaults(DEBUG=False, TEST=False)
    config = parser.parse_args()

    # Passed in arguments shoud trump
    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = str(load[key])

    if config.__dict__["password"] is None:
        log.info("Secure Password Input (if there is no password prompt, use --password <pw>):")
        config.__dict__["password"] = getpass.getpass()

    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None

    return config


def main():
    # log settings
    # log format
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    data_path = os.path.join(os.path.dirname(__file__), "data")
    gyms_path = os.path.join(data_path, "gyms")
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    if not os.path.exists(gyms_path):
        os.makedirs(gyms_path)

    # instantiate pgoapi
    api = pgoapi.PGoApi()

    # parse position
    position = util.get_pos_by_name(config.location)
    if not position:
        log.error('Your given location could not be found by name')
        return
    elif config.test:
        return

    # set player position on the earth
    api.set_position(*position)

    #if not api.login(config.auth_service, config.username, config.password, app_simulation = True):
    #    return
        
    # new authentication initialitation
    api.set_authentication(provider = config.auth_service, username = config.username, password =  config.password)

    # provide the path for your encrypt dll
    encryptPath = get_encryption_lib_path()
    api.activate_signature(encryptPath)

    # get player profile call (single command example)
    # ----------------------
    #response_dict = api.get_player()
    #print('Response dictionary (get_player): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))
    
    # sleep 200ms due to server-side throttling
    #time.sleep(0.2)

    # get player profile + inventory call (thread-safe/chaining example)
    # ----------------------
    #req = api.create_request()
    #req.get_player()
    #req.get_inventory()
    #response_dict = req.call()
    #print('Response dictionary (get_player + get_inventory): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))
	
    # sleep 200ms due to server-side throttling
    #time.sleep(0.2)
	
    #print('cellids:\n\r{}'.format(util.get_cell_ids(position[0],position[1])))
    #get gym info
    lat= position[0]
    lng= position[1]
    cell_ids = util.get_cell_ids(lat, lng)
    timestamps = [0,] * len(cell_ids)
    response_dict = api.get_map_objects(latitude = util.f2i(lat), longitude = util.f2i(lng), since_timestamp_ms = timestamps, cell_id = cell_ids)

    response_json = os.path.join(data_path, "response_dict.json")
    with open(response_json, 'w') as outfile:
        outfile.truncate()
        json.dump(response_dict, outfile)
    
    
    map_objects = response_dict.get('responses', {}).get('GET_MAP_OBJECTS', {})
    status = map_objects.get('status', None)
    cells = map_objects['map_cells']

    time.sleep(2);
    
    #insert detail info about gym to fort
    for cell in cells:
        if 'forts' in cell:
            for fort in cell['forts']:
                print ('id {} type {} points {}'.format(fort.get('id'),fort.get('type'),fort.get('gym_points')))
                #if fort.get('type') != 1:
                if 'gym_points' in fort:
                    req = api.create_request()
                    req.get_gym_details(gym_id=fort.get('id'),
                                             player_latitude=lng,
                                             player_longitude=lat,
                                             gym_latitude=fort.get('latitude'),
                                             gym_longitude=fort.get('longitude'))
                    response_gym_details = req.call()
                    fort['gym_details'] = response_gym_details.get('responses', {}).get('GET_GYM_DETAILS', None)
                    if ('name' in fort['gym_details']):
                        gym_data_cells = os.path.join(gyms_path, "gym_{}.json".format(fort['id']))
                        with open(gym_data_cells, 'w') as outfile:
                            json.dump(fort['gym_details'], outfile)
                    else:
                        print('***NO GYM DETAILS - HANDLE WHY?');
                        print('{}'.format(pprint.PrettyPrinter(indent=1).pformat(fort['gym_details'])));
                        print('{}'.format(pprint.PrettyPrinter(indent=1).pformat(fort)));
                        print('***NO GYM DETAILS - HANDLE WHY?');
                    time.sleep(2);
    user_data_cells = os.path.join(data_path, "cells.json")
    with open(user_data_cells, 'w') as outfile:
        outfile.truncate()
        json.dump(cells, outfile)
    
    
	#if (response_dict['responses']):
    #        if 'status' in response_dict['responses']['GET_MAP_OBJECTS']:
    #            if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 1:
    #                for map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
    #                    if 'wild_pokemons' in map_cell:
    #                        for pokemon in map_cell['wild_pokemons']:
    #                            pokekey = get_key_from_pokemon(pokemon)
    #                            pokemon['hides_at'] = time.time() + pokemon['time_till_hidden_ms']/1000
    #                            poi['pokemons'][pokekey] = pokemon
    

if __name__ == '__main__':
    main()
