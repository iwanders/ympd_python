
import os
from .ympd_backend import ympdBackend, Heartbeat
import cherrypy
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


class websocketAlternative:
    # host the content with static dir handling.
    def __init__(self, htdocs_path):
        self.htdocs_path = htdocs_path
        self._cp_config = {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(htdocs_path),
                      "tools.staticdir.index": "index.html",
                        # use filter, ensure js/mpd.js is dynamically served.
                        # https://stackoverflow.com/a/16398813
                      "tools.staticdir.match": ".*(?<!mpd\.js)$",
                        }
        # Create a queue to store the to-be-delivered messages in.
        self.msgs = Queue()

    def mpd_js(self, *args, **kwargs):
        """
            Monkey patch our alternative websocket implementation into the
            mpd.js that's about to be served and used.
        """
        # get the original javascript.
        with open(os.path.join(self.htdocs_path, "js", "mpd.js")) as f:
            d = f.read()

        # retrieve the payload
        dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir, "ympd_no_websocket.js")) as f:
            payload = f.read()

        # insert our websocket alternative.
        insert_here = "function webSocketConnect() {"
        d = d.replace(insert_here, payload + "\n" + insert_here)

        # ensure the websocket alternative is used:
        d = d.replace("new WebSocket", "new WebSocketAlternative")
        return d
    mpd_js.exposed = True


    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def ws(self):
        """
            This is our alternative websocket endpoint.
            Data is json.
            Possible options payloads:
                 - {"ws_msg":msg_data}
                    As if a frame was transmitted over the websocket.
                 - {"ws_open":[]}
                    As if the websocket was just opened, calls beat and
                    song changed
                 - {"cmd_beat":[]}
                    Beats the backend, as a replacement for the threaded
                    pacemaker the websocket implementation uses.
            Always returns list of messages:
                [msg1, msg2, ... , msgN], or [] in case no messages.
        """
        data = cherrypy.request.json

        self.mpd_ensure_connection()

        if "ws_msg" in data and self.is_connected():
            msg = data["ws_msg"]
            self.received_message(msg)

        if ("ws_open" in data) and self.is_connected():
            self._mpd_song_changed()
            self.beat()

        if ("cmd_beat" in data) and self.is_connected():
            self.beat()

        # Append all the messages that are currently available.
        r = []
        while (not self.msgs.empty()):
            r.append(self.msgs.get(False))
        # print("Sending {}".format(r))
        return r
    ws.exposed = True

    # used by the backend to send a message over the websocket.
    def send(self, msg):
        self.msgs.put(msg)

    # hook into the dispatcher such that we can return 'self' as dispatcher
    # for js/mpd.js... The staticdir handles all other files.
    def _cp_dispatch(self, vpath):
        print(vpath)
        if (len(vpath) >= 1) and (vpath[0] == "js") and (vpath[1] == "mpd.js"):
            return self

    # when proactively closed, but we cannot really relay this message to the
    # client...
    def close(self, code=500, reason=None):
        ympdBackend.shutdown(self)

    def close_connection(self):
        pass

class ympdNoWebSocket(websocketAlternative, ympdBackend):

    def __init__(self, mpd_host, mpd_port, mpd_password=None,
                 *args, **kwargs):
        # call the super class to initiate websocket stuffs.
        websocketAlternative.__init__(self, *args, **kwargs)
        # pass on the mpd information to the backend.
        ympdBackend.__init__(self, mpd_host, mpd_port, mpd_password)
        self.terminated = False

    def closed(self, code, reason=None):
        ympdBackend.shutdown(self)
        self.terminated = True
        websocketAlternative.closed(self, code, reason)

    def received_message(self, message):
        # pass this through to the backend
        ympdBackend.received_message(self, message)

def ympdNoWebSocket_wrap(mpd_host, mpd_port, mpd_password=None):
    # returns a function which can be instantiated by the webserver to create
    # the non-websocket backend.

    def foo(*args, **kwargs):
        z = ympdNoWebSocket(mpd_host, mpd_port, mpd_password, *args, **kwargs)
        # don't need the pacemaker here, we rely on the javascript for that.
        # z.set_pacemaker(Heartbeat(z))
        return z
    return foo
