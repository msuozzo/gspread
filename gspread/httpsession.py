# -*- coding: utf-8 -*-

"""
gspread.httpsession
~~~~~~~~~~~~~~~~~~~

This module contains a class for working with http sessions.

"""

try:
    import httplib as client
    from urlparse import urlparse
    from urllib import urlencode
except ImportError:
    from http import client
    from urllib.parse import urlparse
    from urllib.parse import urlencode

from os import errno
from ssl import SSLError
from socket import timeout as SocketTimeout

try:
    unicode
except NameError:
    basestring = unicode = str


from .exceptions import HTTPError, TimeoutError


class HTTPSession(object):

    """Handles HTTP activity while keeping headers persisting across requests.

       :param headers: (optional) A dict with initial headers.
       :param timeout: (optional) An integral number of seconds to wait for an
                                    HTTP response before timing out.
    """

    def __init__(self, headers=None, timeout=None):
        self.headers = headers or {}
        self.connections = {}
        self.timeout = timeout

    def request(self, method, url, data=None, headers=None):
        if data and not isinstance(data, basestring):
            data = urlencode(data)

        if data is not None:
            data = data.encode()

        # If we have data and Content-Type is not set, set it...
        if data and not headers.get('Content-Type', None):
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        # If connection for this scheme+location is not established, establish
        # it.
        uri = urlparse(url)
        addr = uri.scheme + uri.netloc
        if addr not in self.connections:
            conn_class = client.HTTPSConnection if uri.scheme == 'https' else client.HTTPException
            self.connections[addr] = conn_class(uri.netloc, timeout=self.timeout)

        request_headers = self.headers.copy()

        if headers:
            for k, v in headers.items():
                if v is None:
                    del request_headers[k]
                else:
                    request_headers[k] = v

        self.connections[addr].request(method, url, data, headers=request_headers)
        try:
            response = self.connections[addr].getresponse()
        except (SocketTimeout, SSLError) as err:
            # Adapted from the requests package
            #TODO: Python 3 system EAGAIN handling
            blocking_errnos = (errno.EAGAIN, errno.EWOULDBLOCK)
            if any((
                    isinstance(err, SocketTimeout),        # Python 3
                    hasattr(err, 'errno') \
                        and err.errno in blocking_errnos,  # Python 2 EAGAIN
                    'timed out' in str(err),               # Python 2.7 SSL
                    'did not complete (read)' in str(err)  # Python 2.7> SSL
                    )):
                raise TimeoutError('Request timed out')

        if response.status > 399:
            raise HTTPError(response.status, "%s: %s" % (response.status, response.read()))
        return response

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('DELETE', url, **kwargs)

    def post(self, url, data=None, headers={}):
        return self.request('POST', url, data=data, headers=headers)

    def put(self, url, data=None, **kwargs):
        return self.request('PUT', url, data=data, **kwargs)

    def add_header(self, name, value):
        self.headers[name] = value
