# -*- coding: utf-8 -*-

from flask import request
from flask import Response

class TLSAuth(object):
    """Global class for TLS client access management
    works with flask request headers
    Ideas from https://github.com/stef/flask-tlsauth
    """
    def __init__(self, groups=[], verify='SSL-Client-Verify', dn='SSL-Client-DN'):
        """Build the global class parameters
        Set verify header fill by nginx/apache using 'verify' parameter
        Set dn header fill by nginx/apache using 'dn' parameter
        """
        if not isinstance(groups, list):
            raise ValueError('Groups must be list object')

        # Set class variables
        self.__header_verify = verify
        self.__header_dn = dn
        self.groups = groups

    def __unauth(self):
        return Response('Forbidden', 403)

    def tls_private(self, unauth=None, groups=None):
        """Method restricting access to members of groups only.
        Groups can be set specifically using parameter,
        or default groups set on class initialisation will be used.
        """
        if not unauth:
            unauth = self.__unauth
        if not groups:
            groups = self.groups

        def decor(func):
            def tls_wrapper(*args, **kwargs):
                verified = request.headers.get(self.__header_verify, False)
                dn = request.headers.get(self.__header_dn, None)
                # Add support for nginx version newer than 1.11.6
                # Compliance with RFC 2253 (RFC 4514) format
                if dn and not dn.startswith('/'):
                    infos = dn.split(',')
                    infos.reverse()
                    dn = '/{i}'.format(i='/'.join(infos))
                # If client is verified and dn in authorized groups
                if verified and dn and (dn in groups):
                    return func(*args, **kwargs)
                return unauth(*args, **kwargs)
            
            return tls_wrapper

        return decor

    def tls_protected(self, unauth=None):
        """Method restricting access to all user with valid certificate
        """
        if not unauth:
            unauth = self.__unauth
        
        def decor(func):
            def tls_wrapper(*args, **kwargs):
                verified = request.headers.get(self.__header_verify, False)
                # If client is verified and dn in authorized groups
                if verified:
                    return func(*args, **kwargs)
                return unauth(*args, **kwargs)
            
            return tls_wrapper

        return decor
