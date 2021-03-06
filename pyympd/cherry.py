import cherrypy
import os
import sys

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.manager import WebSocketManager

from .ympdwebsocket import ympdWebSocket_wrap
from .ympd_no_websocket import ympdNoWebSocket, ympdNoWebSocket_wrap

class Root(object):

    def __init__(self):
        self.handlers = []
        cherrypy.engine.subscribe('stop', self.stop)

    @cherrypy.expose
    def ws(self):
        # Path on which the websocket is created.
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))
        handler = cherrypy.request.ws_handler
        self.handlers.append(handler)
    ws._cp_config = {'tools.staticdir.on': False}

    def stop(self):
        # lets try to kill all handlers.
        print("Got kill signal")
        for handler in self.handlers:
            print("Killing handlers")
            handler.shutdown()


def start_cherrypy_debug_server(htdocs_path,
                                http_host, http_port,
                                mpd_host, mpd_port=6600, mpd_password=None):

    # set cherrypy configuration.
    cherrypy.config.update({'server.socket_port': http_port})
    cherrypy.config.update({'server.socket_host': http_host})

    if (not os.path.isdir(htdocs_path)):
        print("=" * 80 + """
  The ympd htdocs dir is not available: perhaps the git submodule is missing?
""" + "=" * 80)
        sys.exit(1)

    # Add the websocket requirements.
    a = WebSocketPlugin(cherrypy.engine)
    a.manager = WebSocketManager()
    a.subscribe()
    cherrypy.tools.websocket = WebSocketTool()


    web_root = Root()

    # get a function to instantiate the websocket with the correct settings.
    ympd_websocket = ympdWebSocket_wrap(mpd_host, mpd_port, mpd_password)

    # Run a no-websocket alternative at http://hostname:port/nows/
    nowebsocket = ympdNoWebSocket_wrap(mpd_host, mpd_port, mpd_password)
    web_root.nows = nowebsocket(htdocs_path)
    # this implementation uses POST requests communicate.
    # Takes a little bit longer for the UI to update, but it should get through
    # firewalls and proxies where the websocket cannot.

    cherrypy.quickstart(web_root, '/', config={
                '/ws': {'tools.websocket.on': True,
                        'tools.websocket.handler_cls': ympd_websocket},
                '/': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(htdocs_path),
                      "tools.staticdir.index": "index.html"},
            }
            )
