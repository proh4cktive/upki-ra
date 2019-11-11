# -*- coding: utf-8 -*-
import base64

from flask import jsonify, request
from flask import current_app
from flask import Blueprint

client_api = Blueprint('client_api', __name__)

def send_error(msg):
    """Send back error in json
    """
    return jsonify({'status': 'error', 'message': str(msg)})

@client_api.route('/renew', methods=['GET'])
def renew():
    """Certificate renewal point
    Client identity is get using TLS client certificate DN value
    """
    try:
        nginx_dn = request.headers['SSL-Client-DN']
        # Nginx build DN using ',' and in reverse order
        infos = nginx_dn.split(',')
        infos.reverse()
        dn = '/'.join(infos)
        data = current_app.ra.renew_node('{d}'.format(d=dn))
    except Exception as err:
        return send_error(err)

    data['status'] = 'success'

    return jsonify(data)
