import ws4py
import ws4py.websocket
import mpd  # https://pypi.python.org/pypi/python-mpd2/
import json
import threading
import time
import os
import socket
import errno

# this file should not include webserver like modules. (Cherrypy, asyncio, etc)


# from libmpdclient2
MPD_PLAYBACK_STATE = {"unknown": 0, "stop": 1, "play": 2, "pause": 3}


class ympdWebSocket(ws4py.websocket.WebSocket):

    # define MAX_SIZE 1024 * 100
    # define MAX_ELEMENTS_PER_PAGE 512
    MAX_ELEMENTS_PER_PAGE = 512  # from the ympd server.

    DEFAULT_STATUS_PERIOD = 0.1  # update interval between unsolicited status.

    def __init__(self, mpd_host, mpd_port, mpd_password=None,
                 *args, **kwargs):
        print(
            "Websocket spawned for: {}:{} (password: {})".format(
                mpd_host,
                mpd_port,
                mpd_password))

        # call the super class to initiate websocket stuffs.
        super(ympdWebSocket, self).__init__(*args, **kwargs)

        self.host = mpd_host
        self.port = mpd_port
        self.password = mpd_password

        self.c = mpd.MPDClient()

        self.pacemaker = False
        self.status_period = self.DEFAULT_STATUS_PERIOD

        self.mpd_status = {}
        self.mpd_status["songid"] = -1

        self.mpd_lock = threading.Lock()
        self.mpd_connect()

    def received_message(self, message):
        # called when we receive a message.
        command, payload = self.parse_command(message)
        command_list = {
            "MPD_API_GET_QUEUE": self._MPD_API_GET_QUEUE,
            "MPD_API_GET_BROWSE": self._MPD_API_GET_BROWSE,
            # MPD_API_GET_MPDHOST
            "MPD_API_ADD_TRACK": self._MPD_API_ADD_TRACK,
            "MPD_API_ADD_PLAY_TRACK": self._MPD_API_ADD_PLAY_TRACK,
            "MPD_API_ADD_PLAYLIST": self._MPD_API_ADD_PLAYLIST,
            "MPD_API_PLAY_TRACK": self._MPD_API_PLAY_TRACK,
            "MPD_API_RM_TRACK": self._MPD_API_RM_TRACK,
            "MPD_API_RM_ALL": self._MPD_API_RM_ALL,
            "MPD_API_SEARCH": self._MPD_API_SEARCH,
            "MPD_API_SET_VOLUME": self._MPD_API_SET_VOLUME,
            "MPD_API_SET_PAUSE": self._MPD_API_SET_PAUSE,
            "MPD_API_SET_PLAY": self._MPD_API_SET_PLAY,
            "MPD_API_SET_STOP": self._MPD_API_SET_STOP,
            "MPD_API_SET_SEEK": self._MPD_API_SET_SEEK,
            "MPD_API_SET_NEXT": self._MPD_API_SET_NEXT,
            "MPD_API_SET_PREV": self._MPD_API_SET_PREV,
            # MPD_API_SET_MPDHOST
            # MPD_API_SET_MPDPASS
            "MPD_API_UPDATE_DB": self._MPD_API_UPDATE_DB,
            "MPD_API_TOGGLE_RANDOM": self._MPD_API_TOGGLE_RANDOM,
            "MPD_API_TOGGLE_CONSUME": self._MPD_API_TOGGLE_CONSUME,
            "MPD_API_TOGGLE_SINGLE": self._MPD_API_TOGGLE_SINGLE,
            "MPD_API_TOGGLE_CROSSFADE": self._MPD_API_TOGGLE_CROSSFADE,
            "MPD_API_TOGGLE_REPEAT": self._MPD_API_TOGGLE_REPEAT,
        }
        if command in command_list:
            try:
                self.mpd_lock.acquire()
                command_list[command](payload)
            except mpd.CommandError as e:
                self.send(json.dumps({"type": "error", "data": str(e)}))
            except mpd.ConnectionError as e:
                self.mpd_connected = False
                print("Destroying this connection")
                # self.close_connection()
                try: 
                    self.send(json.dumps({"type": "error", "data": str(e)}))
                except socket.error as e:
                    print("Error during closing ws: {}".format(str(e)))
            finally:
                self.mpd_lock.release()

        else:
            self.send(json.dumps({"type": "error",
                                  "data": "Unhandled command: {}".format(
                                        command)}))
            print("Unhandled command {},{}".format(command, repr(payload)))

    def closed(self, code, reason=None):
        # called when we get closed.
        print("Websocket was closed")
        self.shutdown()
        super(ympdWebSocket, self).closed(code, reason)

    def shutdown(self):
        if (self.pacemaker):
            self.pacemaker.stop()

        try:
            self.c.close()
            self.c.disconnect()
        except mpd.ConnectionError as e:
            print(str(e))
        except socket.error as e:
            # Handle beat when socket is already closed.
            print("While closing, encountered: {}".format(str(e)))
        finally:
            # Correctly release this instance.
            self.server_terminated = True
            self.close_connection()
            self.close()

    def mpd_toggle_pause(self):
        foo = self.c.status()
        if (foo["state"] == "play"):
            self.c.pause(1)
        elif (foo["state"] == "pause"):
            self.c.pause(0)

    def mpd_toggle_repeat(self):
        self.c.repeat(0 if self.c.status()['repeat'] == '1' else 1)

    def mpd_toggle_crossfade(self):
        self.c.crossfade(0 if self.c.status()['xfade'] == '1' else 1)

    def mpd_toggle_consume(self):
        self.c.consume(0 if self.c.status()['consume'] == '1' else 1)

    def mpd_toggle_random(self):
        self.c.random(0 if self.c.status()['random'] == '1' else 1)

    def mpd_toggle_single(self):
        self.c.single(0 if self.c.status()['single'] == '1' else 1)

    def mpd_connect(self):
        try:
            self.mpd_lock.acquire()
            self.c.connect(self.host, self.port)
            self.c.password(self.password)
            self.mpd_connected = True
        except socket.error as e:
            self.send(json.dumps({"type": "error", "data": str(e)}))
        finally:
            self.mpd_lock.release()

    def _mpd_get_status(self):
        mpd_status = self.c.status()
        # print(mpd_status)
        if (("songid" in mpd_status) and ("songid" in self.mpd_status)):
            if mpd_status["songid"] != self.mpd_status["songid"]:
                self._mpd_song_changed()
        self.mpd_status = mpd_status

    def _mpd_song_changed(self):
        self._MPD_EMIT_SONG_CHANGE()

    def set_pacemaker(self, pacemaker):
        self.pacemaker = pacemaker
        self.pacemaker.set_frequency(self.status_period)
        self.pacemaker.start()

    # called periodically by the pacemaker.
    def beat(self):
        try:
            self.mpd_lock.acquire()
            self._mpd_get_status()
            self._MPD_EMIT_STATUS()
        except mpd.CommandError as e:
            self.send(json.dumps({"type": "error", "data": str(e)}))
        except mpd.ConnectionError as e:
            self.send(json.dumps({"type": "error", "data": str(e)}))
            print("Destroying this connection")
            # self.close_connection()
            try: 
                self.close(1001, "Connection to MPD lost.")  # kill ws.
            except socket.error as e:
                print("Error during closing ws: {}".format(str(e)))

        except RuntimeError as e:
            # Handle beat when socket is already closed.
            # RuntimeError: Cannot send on a terminated websocket
            self.shutdown()
        except socket.error as e:
            # Handle beat when socket is already closed.
            # error: [Errno 104] Connection reset by peer
            self.shutdown()
        finally:
            self.mpd_lock.release()

    # below follow yMPD thingies.
    def _MPD_API_GET_QUEUE(self, payload):

        def fix_metadata(entry):
            res = {"pos": int(entry["pos"]), "id": int(entry["id"])}
            # Functions to 'fix' various paramters as received from mpd.
            #   key: (fix_function, defaultvalue, [possible names])
            fix_map = {"duration": (int, 0, ["duration", "time"]),
                       "title": (str, os.path.basename(entry["file"]),
                                 ["title", "name"])}
            for k in fix_map.keys():
                set_key = False
                for valid_key in fix_map[k][2]:
                    if (set_key):
                        continue
                    if (valid_key in entry):
                        res[k] = fix_map[k][0](entry[valid_key])
                        set_key = True
                if (not set_key):  # set default.
                    res[k] = fix_map[k][1]

            return res

        # mpd_put_queue(char *buffer, unsigned int offset)
        index = int(payload)
        playlist = self.c.playlistinfo(
            (index * self.MAX_ELEMENTS_PER_PAGE,
             (index + 1) * self.MAX_ELEMENTS_PER_PAGE))

        reduced = [fix_metadata(entry) for entry in playlist]
        # return {\"type\":\"queue\",\"data\":[ ".....
        return_value = {"type": "queue", "data": reduced}
        self.send(json.dumps(return_value))

    def _MPD_API_GET_BROWSE(self, payload):
        page = int(payload[0:payload.find(',')])
        path = payload[payload.find(',') + 1:]
        listing = self.c.lsinfo(path)

        reduced = listing[page * self.MAX_ELEMENTS_PER_PAGE:
                          (page + 1) * self.MAX_ELEMENTS_PER_PAGE]
        # print(reduced)
        new_data = []
        for j in reduced:
            if ("directory" in j):
                # print (j["directory"])
                # filter if a folder in the path starts with a dot.
                if (j["directory"].find("/.") != -1):
                    continue
                new_data.append({"type": "directory", "dir": j["directory"]})
            if ("file" in j):
                if ("title" in j):
                    new_data.append({"type": "song",
                                     "uri": j["file"],
                                     "duration": int(j["time"]),
                                     "title": j["title"]})
                else:
                    new_data.append({"type": "song",
                                     "uri": j["file"],
                                     "duration": int(j["time"]),
                                     "title": os.path.basename(j["file"])})
            if("playlist" in j):
                new_data.append({"type": "playlist", "plist": j["playlist"]})

        return_value = {"type": "browse", "data": new_data}
        # print(return_value)
        self.send(json.dumps(return_value))

    def _MPD_API_ADD_TRACK(self, payload):
        # adds track to playlist.
        self.c.add(payload)
        self._MPD_API_GET_QUEUE(0)

    def _MPD_API_ADD_PLAY_TRACK(self, payload):
        # adds track to playlist.
        id = self.c.addid(payload)
        self.c.playid(id)
        self._mpd_song_changed()
        self._MPD_API_GET_QUEUE(0)

    def _MPD_API_RM_TRACK(self, payload):
        # adds track to playlist.
        self.c.deleteid(payload)

    def _MPD_API_SET_PLAY(self, payload):
        self.c.play()
        self._mpd_song_changed()

    def _MPD_API_SET_PAUSE(self, payload):
        self.mpd_toggle_pause()  # don't wait for status update.
        self._MPD_EMIT_STATUS()

    def _MPD_API_SET_PREV(self, payload):
        self.c.previous()

    def _MPD_API_SET_NEXT(self, payload):
        self.c.next()

    def _MPD_API_SET_STOP(self, payload):
        self.c.stop()

    def _MPD_API_SET_VOLUME(self, payload):
        self.c.setvol(payload)

    def _MPD_API_PLAY_TRACK(self, payload):
        self.c.playid(int(payload))
        self._mpd_song_changed()

    def _MPD_API_TOGGLE_CROSSFADE(self, payload):
        self.mpd_toggle_crossfade()

    def _MPD_API_TOGGLE_REPEAT(self, payload):
        self.mpd_toggle_repeat()

    def _MPD_API_TOGGLE_RANDOM(self, payload):
        self.mpd_toggle_random()

    def _MPD_API_TOGGLE_CONSUME(self, payload):
        self.mpd_toggle_consume()

    def _MPD_API_TOGGLE_SINGLE(self, payload):
        self.mpd_toggle_single()

    def _MPD_API_RM_ALL(self, payload):
        self.c.clear()
        self._mpd_song_changed()  # don't wait for status update.
        self._MPD_API_GET_QUEUE(0)

    def _MPD_API_UPDATE_DB(self, payload):
        self.c.update()

    def _MPD_API_ADD_PLAYLIST(self, payload):
        self.c.load(payload)

    def _MPD_API_SET_SEEK(self, payload):
        songid, seek = payload.split(',')
        self.c.seekid(songid, seek)

    def _MPD_API_SEARCH(self, payload):
        res = self.c.search("any", payload)

        reduced = []
        for entry in res:
            reduced.append({"type": "song",
                            "uri": entry["file"],
                            "duration": entry['time'],
                            "title": entry['title'] if 'title' in entry
                            else os.path.basename(entry['file'])})
        return_value = {"type": "search", "data": reduced}
        self.send(json.dumps(return_value))
        pass

    def _MPD_EMIT_STATUS(self):
        # print("pushing status")
        status = self.mpd_status
        currentsong = self.c.currentsong()
        state_data = {"state": MPD_PLAYBACK_STATE[status["state"]],
                      "volume": int(status["volume"]),
                      "repeat": int(status["repeat"]),
                      "single": int(status["single"]),
                      "crossfade": int(status["xfade"]),
                      "consume": int(status["consume"]),
                      "random": int(status["random"])}

        # if a a song is in the pause / play, we consider it active.
        if ("pos" in currentsong and "elapsed" in status):
            # a song is active.
            active_song = {"elapsedTime": int(float(status["elapsed"])),
                           "currentsongid": int(status["songid"]),
                           "songpos": int(currentsong["pos"]),
                           "totalTime": int(currentsong["time"]) if "time" in
                           currentsong else 0}
        else:
            # there is no song 'active'
            active_song = {"elapsedTime": 0,
                           "currentsongid": 0,
                           "songpos": 0,
                           "totalTime": 0}
        state_data.update(active_song)
        return_value = {"type": "state", "data": state_data}
        self.send(json.dumps(return_value))

    def _MPD_EMIT_SONG_CHANGE(self):
        currentsong = self.c.currentsong()
        return_value = {"type": "song_change",
                        "data": {"pos": 0,
                                 "title": " ",
                                 "artist": " ",
                                 "album": " "}}

        return_value["data"].update(currentsong)
        self.send(json.dumps(return_value))

    @staticmethod
    def parse_command(message):
        text = str(message)
        commapos = text.find(',')
        if (commapos != -1):
            return (text[0:commapos], text[commapos + 1:])
        else:
            return (text, None)


# Adapted from ws4py heartbeat code. Periodically send the status.
class Heartbeat(threading.Thread):

    def __init__(self, websocket):
        threading.Thread.__init__(self)
        self.websocket = websocket
        self.frequency = 1.0
        self.running = True

    def set_frequency(self, frequency):
        self.frequency = frequency

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.stop()

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            time.sleep(self.frequency)
            if (self.websocket.terminated or not self.running):
                break

            try:
                # send the status.
                self.websocket.beat()
            except ws4py.exc.WebSocketException as e:
                print(e)
                self.websocket.server_terminated = True
                self.websocket.close_connection()
                break


def ympdWebSocket_wrap(mpd_host, mpd_port, mpd_password=None):
    # returns a function which can be instantiated by the webserver to create a
    # websocket.

    def foo(*args, **kwargs):
        z = ympdWebSocket(mpd_host, mpd_port, mpd_password, *args, **kwargs)
        z.set_pacemaker(Heartbeat(z))
        return z
    return foo
