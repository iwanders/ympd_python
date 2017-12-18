import ws4py
import ws4py.websocket

from .ympd_backend import ympdBackend, Heartbeat

class ympdWebSocket(ws4py.websocket.WebSocket, ympdBackend):
    def __init__(self, mpd_host, mpd_port, mpd_password=None,
                 *args, **kwargs):
        # call the super class to initiate websocket stuffs.
        ws4py.websocket.WebSocket.__init__(self, *args, **kwargs)
        # pass on the mpd information to the backend.
        ympdBackend.__init__(self, mpd_host, mpd_port, mpd_password)

    def closed(self, code, reason=None):
        ympdBackend.shutdown(self)
        ws4py.websocket.WebSocket.closed(self, code, reason)

    def close(self):
        ws4py.websocket.WebSocket.close(self, 500, "close")

    def received_message(self, message):
        # pass this through to the backend
        ympdBackend.received_message(self, message)

def ympdWebSocket_wrap(mpd_host, mpd_port, mpd_password=None):
    # returns a function which can be instantiated by the webserver to create a
    # websocket.

    def foo(*args, **kwargs):
        z = ympdWebSocket(mpd_host, mpd_port, mpd_password, *args, **kwargs)
        z.set_pacemaker(Heartbeat(z))
        return z
    return foo
