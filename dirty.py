import time
from multiprocessing import Process

import api
import config
import location
import logic
import main
import pokemon_pb2

multi = False

argsStored = []
startTime = time.time()
accessToken = None
globalltype = None


def start():
    global argsStored
    while True:
        if accessToken is None or globalltype is None:
            refresh_access()
        location.set_location(argsStored.location)
        print '[+] Token:', accessToken[:40] + '...'
        prot1 = logic.gen_first_data(accessToken, globalltype)
        local_ses = api.get_rpc_server(accessToken, prot1)
        new_rcp_point = 'https://%s/rpc' % (local_ses.rpc_server,)
        work_stop(local_ses, new_rcp_point)


def refresh_access():
    global accessToken, globalltype
    accessToken, globalltype = main.get_acces_token(argsStored.username, argsStored.password, argsStored.type.lower())
    if accessToken is None:
        print '[-] access Token bad'
        raise RuntimeError


def walk_random():
    COORDS_LATITUDE, COORDS_LONGITUDE, COORDS_ALTITUDE = location.get_location_coords()
    COORDS_LATITUDE = location.l2f(COORDS_LATITUDE)
    COORDS_LONGITUDE = location.l2f(COORDS_LONGITUDE)
    COORDS_ALTITUDE = location.l2f(COORDS_ALTITUDE)
    COORDS_LATITUDE = COORDS_LATITUDE + config.steps
    COORDS_LONGITUDE = COORDS_LONGITUDE + config.steps
    location.set_location_coords(COORDS_LATITUDE, COORDS_LONGITUDE, COORDS_ALTITUDE)


def split_list(a_list):
    half = len(a_list) / 2
    return a_list[:half], a_list[half:]


def work_half_list(part, ses, new_rcp_point):
    for t in part:
        if config.debug:
            print '[!] farming pokestop..'
        work_with_stops(t, ses, new_rcp_point)


def work_stop(local_ses, new_rcp_point):
    while True:
        proto_all = logic.all_stops(local_ses)
        all_stops = api.use_api(new_rcp_point, proto_all)
        maps = pokemon_pb2.maps()
        maps.ParseFromString(all_stops)
        data_list = location.get_near(maps)
        data_list = sorted(data_list, key=lambda x: x[1])
        if len(data_list) > 0:
            print '[+] found: %s Pokestops near' % (len(data_list))
            if local_ses is not None and data_list is not None:
                print '[+] starting show'
                if multi:
                    a, b = split_list(data_list)
                    p = Process(target=work_half_list, args=(a, local_ses.ses, new_rcp_point))
                    o = Process(target=work_half_list, args=(a, local_ses.ses, new_rcp_point))
                    p.start()
                    o.start()
                    p.join()
                    o.join()
                    print '[!] farming done..'
                else:
                    for t in data_list:
                        if config.debug:
                            print '[!] farming pokestop..'
                        if not work_with_stops(t, local_ses.ses, new_rcp_point):
                            break
        else:
            walk_random()


def work_with_stops(current_stop, ses, new_rcp_point):
    Kinder = logic.gen_stop_data(ses, current_stop)
    tmp_api = api.use_api(new_rcp_point, Kinder)
    try:
        if tmp_api is not None:
            map = pokemon_pb2.map()
            map.ParseFromString(tmp_api)
            st = map.sess[0].status
            config.earned_xp += map.sess[0].amt
            if st == 4:
                print "[!] +%s (%s)" % (map.sess[0].amt, config.earned_xp)
            elif st == 3:
                print "[!] used"
            elif st == 2:
                print "[!] charging"
            elif st == 1:
                print "[!] walking.."
                expPerHour()
                time.sleep(14)
                work_with_stops(current_stop, ses, new_rcp_point)
            else:
                print "[?]:", st
        else:
            print '[-] tmp_api empty'
        return True
    except:
        print '[-] error work_with_stops - Trying to restart process'
        return False


def expPerHour():
    diff = time.time() - startTime
    minutesRun = diff / 60.
    hoursRun = minutesRun / 60.
    earned = float(config.earned_xp)
    if hoursRun > 0:
        expHour = int(earned / hoursRun)
    else:
        expHour = "n/a"
    print "[!] Gained: %s (%s exp/h)" % (config.earned_xp, expHour)
