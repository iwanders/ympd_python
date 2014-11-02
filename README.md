ympd_python
===========

This is a Python backend for https://github.com/notandy/ympd (http://www.ympd.org/).

Created out of the desire to use the excellent ympd frontend with a Python backend instead of requiring the original C backend.

Dependencies
------------
 - Python 2.7.3+ or 3.2.3+
 - ws4py: https://pypi.python.org/pypi/ws4py
 - python-mpd2: https://pypi.python.org/pypi/python-mpd2/
 - (cherrypy): https://pypi.python.org/pypi/CherryPy/


How-to
------
An example is given how to use the backend with CherryPy, this can be seen in pyympd/cherrypy.py. For a quickstart see run.py, change the parameters accordingly and it should work. The backend itself is not dependent on a specific webserver and uses only ws4py and python-mpd2 as dependencies.

Limitations
-----------
There is no support for changing the host, password and port in the webinterface.