# -*- coding: utf-8 -*-
import base64

from flask import jsonify, request
from flask import current_app
from flask import Blueprint

from server.utils import TLSAuth

def send_error(msg):
    """Send back error in json
    """
    return jsonify({'status': 'error', 'message': str(msg)})

upki_auth = TLSAuth()
client_api = Blueprint('client_api', __name__)

@client_api.before_request
@upki_auth.tls_protected()
def before_request():
    """ Protect all the client endpoints """
    pass

@client_api.route('/renew', methods=['GET'])
def renew():
    """Certificate renewal point
    Client identity is get using TLS client certificate DN value
    """
    try:
        nginx_dn = request.headers['SSL-Client-DN']
        # Handle new Nginx version: build DN using ',' and in reverse order
        if nginx_dn and not nginx_dn.startswith('/'):
            infos = nginx_dn.split(',')
            infos.reverse()
            dn = '/{i}'.format(i='/'.join(infos))
        data = current_app.ra.renew_node(dn)
    except Exception as err:
        return send_error(err)

    data['status'] = 'success'

    return jsonify(data)
