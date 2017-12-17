
import os
from .ympd_backend import ympdBackend, Heartbeat

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

    def mpd_js(self, *args, **kwargs):
        with open(os.path.join(self.htdocs_path, "js", "mpd.js")) as f:
            d = f.read()
        return d
    mpd_js.exposed = True

    def _cp_dispatch(self, vpath):
        if (len(vpath) >= 1) and (vpath[0] == "js") and (vpath[1] == "mpd.js"):
            return self

class ympdNoWebSocket(websocketAlternative, ympdBackend):

    def __init__(self, mpd_host, mpd_port, mpd_password=None,
                 *args, **kwargs):
        # call the super class to initiate websocket stuffs.
        websocketAlternative.__init__(self, *args, **kwargs)
        # pass on the mpd information to the backend.
        ympdBackend.__init__(self, mpd_host, mpd_port, mpd_password)
        print("called")

    def closed(self, code, reason=None):
        ympdBackend.shutdown(self)
        websocketAlternative.closed(self, code, reason)

    def received_message(self, message):
        # pass this through to the backend
        ympdBackend.received_message(self, message)
