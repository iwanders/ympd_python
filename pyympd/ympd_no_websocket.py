
import os
from .ympd_backend import ympdBackend, Heartbeat
import cherrypy
from queue import Queue


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
        self.msgs = Queue()

    def mpd_js(self, *args, **kwargs):
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
        d = d.replace("new WebSocket", "WebSocketAlternative")
        return d
    mpd_js.exposed = True


    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def ws(self):
        data = cherrypy.request.json
        if "ws_msg" in data:
            msg = data["ws_msg"]
            self.received_message(msg)

        if ("ws_open" in data):
            pass

        if ("ws_get" in data):
            pass

        # Append all the messages.
        r = []
        while (not self.msgs.empty()):
            r.append(self.msgs.get(False))
        # r = list(self.msgs)
        # self.msgs = Queue()
        return r
    ws.exposed = True

    def send(self, msg):
        self.msgs.put(msg)

    def _cp_dispatch(self, vpath):
        print(vpath)
        if (len(vpath) >= 1) and (vpath[0] == "js") and (vpath[1] == "mpd.js"):
            return self

class ympdNoWebSocket(websocketAlternative, ympdBackend):

    def __init__(self, mpd_host, mpd_port, mpd_password=None,
                 *args, **kwargs):
        # call the super class to initiate websocket stuffs.
        websocketAlternative.__init__(self, *args, **kwargs)
        # pass on the mpd information to the backend.
        ympdBackend.__init__(self, mpd_host, mpd_port, mpd_password)
        self.terminated = False
        print("called")

    def closed(self, code, reason=None):
        ympdBackend.shutdown(self)
        self.terminated = True
        websocketAlternative.closed(self, code, reason)

    def received_message(self, message):
        # pass this through to the backend
        ympdBackend.received_message(self, message)

def ympdNoWebSocket_wrap(mpd_host, mpd_port, mpd_password=None):
    # returns a function which can be instantiated by the webserver to create a
    # websocket.

    def foo(*args, **kwargs):
        z = ympdNoWebSocket(mpd_host, mpd_port, mpd_password, *args, **kwargs)
        z.set_pacemaker(Heartbeat(z))
        return z
    return foo
