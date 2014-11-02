import cherrypy
import os

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.manager import WebSocketManager

from .ympdwebsocket import ympdWebSocket_wrap


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

    # Add the websocket requirements.
    a = WebSocketPlugin(cherrypy.engine)
    a.manager = WebSocketManager()
    a.subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    # get a function to instantiate the websocket with the correct settings.
    ympd_websocket = ympdWebSocket_wrap(mpd_host, mpd_port, mpd_password)

    cherrypy.quickstart(Root(), '/', config={
                '/ws': {'tools.websocket.on': True,
                        'tools.websocket.handler_cls': ympd_websocket},
                '/': {'tools.staticdir.on': True,
                    'tools.staticdir.dir': os.path.join(htdocs_path),
                    "tools.staticdir.index": "index.html"}})
