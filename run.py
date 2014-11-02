#!/usr/bin/env python


from pyympd.cherry import start_cherrypy_debug_server


import os
htdoc_path = "./ympd/htdocs"
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))


if __name__ == "__main__":
    start_cherrypy_debug_server(htdocs_path=os.path.join(curdir, htdoc_path),
                                http_host="127.0.0.1",
                                http_port=8080,
                                mpd_host="mpdserver",
                                mpd_port=6600,
                                mpd_password="password")
