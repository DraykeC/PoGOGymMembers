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

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

log = logging.getLogger(__name__)

TIMESTAMP = '\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000'
web_dir = "web"

numbertoteam = {  # At least I'm pretty sure that's it. I could be wrong and then I'd be displaying the wrong owner team of gyms.
    0: 'None',
    1: 'Mystic',
    2: 'Valor',
    3: 'Instinct',
}
numToTeamCol = {

    0: '\x1b[0;37;40mNone\x1b[0m',
    1: '\x1b[0;36;40mMystic\x1b[0m',
    2: '\x1b[0;31;40mValor\x1b[0m',
    3: '\x1b[0;33;40mInstinct\x1b[0m',
}
numbertocolour = {
    0: "rgba(0,0,0,.4)",
    1: "rgba(74, 138, 202, .6)",
    2: "rgba(240, 68, 58, .6)",
    3: "rgba(254, 217, 40, .6)",
}

def prestige_to_level(prestige):
    if prestige >= 50000:
        return 10
    elif prestige >= 40000:
        return 9
    elif prestige >= 30000:
        return 8
    elif prestige >= 20000:
        return 7
    elif prestige >= 16000:
        return 6
    elif prestige >= 12000:
        return 5
    elif prestige >= 8000:
        return 4
    elif prestige >= 4000:
        return 3
    elif prestige >= 2000:
        return 2
    else:
        return 1


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
    
    try:
        os.makedirs(web_dir)
    except OSError:
        if not os.path.isdir(web_dir):
            raise
    
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

    pokemonsJSON = json.load(open('data/pokemon.json'))
    movesJSON = json.load(open('data/moves.json'))
    
    config = init_config()
    if not config:
        return

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)


    # instantiate pgoapi
    api = pgoapi.PGoApi()

    # parse position
    position = util.get_pos_by_name(config.location)
    if not position:
        log.error('Your given location could not be found by name')
        return
    elif config.test:
        return
        
    with open('data/response_dict.json') as data_file:    
        response_dict = json.load(data_file)
        
    map_objects = response_dict.get('responses', {}).get('GET_MAP_OBJECTS', {})
    status = map_objects.get('status', None)
    cells = map_objects['map_cells']

    #insert detail info about gym to fort
    # for cell in cells:
        # if 'forts' in cell:
            # for fort in cell['forts']:
                # if fort.get('type') != 1:
                    # req = api.create_request()
                    # req.get_gym_details(gym_id=fort.get('id'),
                                             # player_latitude=lng,
                                             # player_longitude=lat,
                                             # gym_latitude=fort.get('latitude'),
                                             # gym_longitude=fort.get('longitude'))
                    # response_gym_details = req.call()
                    # fort['gym_details'] = response_gym_details.get('responses', {}).get('GET_GYM_DETAILS', None)
                    # gym_data_cells = "data/forts.json"
                    # with open(gym_data_cells, 'a') as outfile:
                        # json.dump(cell['forts'], outfile)
                        
    # gym_details_loaded = []
    # with open('data/gym_details.json') as data_file:    
        # for line in data_file:
            # gym_details_loaded.append(json.load(line))
    
    # with open('data/gym_details.json', 'r') as data_file:    
        # gym_details_loaded = json.load(data_file)
    gym_details_loaded = []
    for filename in os.listdir("data/gyms/"):
        if 'gym_' in filename:
            with open("data/gyms/{}".format(filename)) as gym_file:
                gym_details_loaded.append(json.load(gym_file))
    
    # if ('name' in fort['gym_details']):
        # gym_data_cells = "data/gyms/gym_{}.json".format(fort['id'])
        # with open(gym_data_cells, 'w') as outfile:
            # json.dump(fort['gym_details'], outfile)
    
    #print('Response dictionary (loaded): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(cells)))
    #print('***********************************')
    #print('***********************************')
    #print('Response dictionary (loaded): \n\r{}'.format(pprint.PrettyPrinter(indent=2).pformat(gym_details_loaded)))

    #gyms = {}
    #gyms[Fort.FortId] = [Fort.Team, Fort.Latitude,Fort.Longitude, Fort.GymPoints]
    
    
    for gym in gym_details_loaded:
        print("Gym is: {} - {} with picture from {}").format(gym.get('name','GYM WITHOUT NAME??'), gym.get('description', '-'), gym.get('urls',['-'])[0])
        fortdata = gym['gym_state']['fort_data']
        #print("It's owned by {} and has prestige {} [ID: {}]").format(numbertoteam[fortdata['owned_by_team']], fortdata['gym_points'], fortdata['id'])
        gymLevel=prestige_to_level(fortdata['gym_points'])
        teamID = fortdata.get('owned_by_team',0)
        print("It's owned by {} and has prestige {} (Level {}) [ID: {}]").format(numToTeamCol[teamID], fortdata['gym_points'], gymLevel, fortdata['id'])
        
        colour = numbertocolour[fortdata['owned_by_team']]

        webpage = "{web_dir}/gym_{id}.html".format(web_dir=web_dir, id=fortdata['id'])
        with open(webpage, 'w') as outfile:
            outfile.truncate()
            outfile.writelines("""<!DOCTYPE html>
            <html>
            <head>
            <link rel="stylesheet" href="styles.css">
            </head>
            <body id="{owner}">""".format(owner=numbertoteam[teamID]))
            outfile.writelines("<h1>{gymName}</h1>".format(gymName=gym.get('name','GYM WITHOUT NAME??')))
            outfile.writelines("<h2>{gymDesc}</h2>".format(gymDesc=gym.get('description','(no description)')))
            outfile.writelines('<img id="main" src="{img}" width="25%" />'.format(img=gym.get('urls',['-'])[0]))
            outfile.writelines('<h2 style="{gym_colour}">Level {gym_level} {owner} gym</h2>'.format(gym_colour=numbertocolour[teamID],gym_level=gymLevel,owner=numbertoteam[teamID]))
            outfile.writelines('<table cols="7" rows="{tableRows}" id="t01">'.format(tableRows=gymLevel+1))
            outfile.writelines('<tr><th>Pokemon</th><th>Nickname</th><th>CP</th><th>Owner</th><th>Quick move</th><th>Charge move</th></tr>')

        #print("colour: {}".format(colour))
        #for mem in gym['gym_state']['memberships']:
        for index in range(len(gym['gym_state']['memberships'])):
            mem = gym['gym_state']['memberships'][index]
            poke = mem['pokemon_data']
            trainer = mem['trainer_public_profile']
            pokename = pokemonsJSON[str(poke['pokemon_id'])]
            pokenick = (poke.get('nickname', pokename)).encode('utf-8')
            
            move1 = '-'
            move1type = '-'
            move2 = '-'
            move2type = '-'
            
            for move in movesJSON:
                if move['id'] == poke['move_1']:
                    move1 = move.get('name','UNKNOWN')
                    move1type = move.get('type','UNKNOWN') #need a better moves.json with types (and damage/dps)
                if move['id'] == poke['move_2']:
                    move2 = move.get('name','UNKNOWN')
                    move2type = move.get('type','UNKNOWN') #need a better moves.json with types (and damage/dps)
            IVAtk=poke.get('individual_attack',0)
            IVDef=poke.get('individual_defense',0)
            IVSta=poke.get('individual_stamina',0)
            Percent = ((IVAtk+IVDef+IVSta)*100)/45
            #print("Member {} {}".format(index, pprint.PrettyPrinter(indent=2).pformat(mem)))
            print("Pokemon {num}:\n\r{pokemon_id} ({cp}CP) {nick} owned by {trainer_id} (L{trainer_level})".format(num=index+1, pokemon_id=pokename,cp=poke['cp'],trainer_id=trainer['name'],trainer_level=trainer['level'], nick=pokenick))
            print("HP: {hp} IVs {Percent}%: {IVAtk}Atk {IVDef}Def {IVSta}Sta".format(hp=poke['stamina']/2,IVAtk=IVAtk,IVDef=IVDef,IVSta=IVSta,Percent=Percent))
            print("Moves: {mv1} ({mv1t}), {mv2} ({mv2t})".format(mv1=move1, mv1t=move1type, mv2=move2, mv2t=move2type))
            
            with open(webpage, 'a') as outfile:
                outfile.writelines('<tr>\n\r<td><img src="pokemon/{pokeid:>03}.gif" alt="{poketype}"></td>'.format(pokeid=poke.get('pokemon_id','Egg'), poketype=pokename))
                outfile.writelines('<td>{pokenick}</td><td>{cp}</td><td>{owner} (L.{trainer_level})</td><td>{mv1} ({mv1t})</td><td>{mv2} ({mv2t})</td></tr>'.format(pokenick=pokenick, cp=poke.get('cp','0'), owner=trainer.get('name','MISSINGNO.'), trainer_level=trainer.get('level','0'),mv1=move1, mv1t=move1type, mv2=move2, mv2t=move2type))
            
            
# >>> from string import Template
# >>> s = Template('$who likes $what')
# >>> s.substitute(who='tim', what='kung pao')
# 'tim likes kung pao'
# >>> d = dict(who='tim')
# >>> Template('Give $who $100').substitute(d)
# Traceback (most recent call last):
# ...
# ValueError: Invalid placeholder in string: line 1, col 11
# >>> Template('$who likes $what').substitute(d)
# Traceback (most recent call last):
# ...
# KeyError: 'what'
# >>> Template('$who likes $what').safe_substitute(d)
# 'tim likes $what'
            
        print("*********\n\r\n\r")
    
    # for gym_key in gyms:
        # gym = gyms[gym_key]
        # color = numbertocolour[gym[0]]
        # icon = 'static/forts/'+numbertoteam[gym[0]]+'_large.png'
        # pokeMarkers.append({
            # 'icon': 'static/forts/' + numbertoteam[gym[0]] + '.png',
            # 'type': 'gym',
            # 'key': gym_key,
            # 'disappear_time': -1,
            # 'lat': gym[1],
            # 'lng': gym[2],
            # 'infobox': "<div><center><small>Gym owned by:</small><br><b style='color:" + color + "'>Team " + numbertoteam[gym[0]] + "</b><br><img id='" + numbertoteam[gym[0]] + "' height='100px' src='"+icon+"'><br>Prestige: " + str(gym[3]) + "</center>"
        # })
    
if __name__ == '__main__':
    main()
