# -*- coding: utf-8 -*-
import base64

from flask import jsonify, request, send_file
from flask import current_app
from flask import Blueprint
from flask_cors import cross_origin

public_api = Blueprint('public_api', __name__)

def send_error(msg):
    """Send back error in json
    """
    return jsonify({'status': 'error', 'message': str(msg)})

@public_api.route('/certs/<node>', methods=['GET'])
@cross_origin()
def retrieve(node):
    """Certificate Distribution point
    Certificate Revokation List Distribution point
    """
    try:
        if node == 'ca.crt':
            ca = current_app.ra.get_ca()
            # CA certificate should be accessible directly
            return Response(ca, mimetype='application/x-x509-ca-cert')
        elif node == 'crl.pem':
            crl = current_app.ra.get_crl()
            # CRL should be accessible directly
            return Response(crl, mimetype='application/pkix-crl')
        else:
            try:
                dn = base64.b64decode(node).decode("utf-8")
                certificate = current_app.ra.download_node({'dn': dn})
            except Exception as err:
                return send_error(err)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'certificate': certificate})

@public_api.route('/ocsp', methods=['POST'])
def ocsp():
    """Online Certificate Status Protocol endpoint
    """
    data = request.get_json()
    try:
        result = current_app.ra.check_ocsp(data)
    except Exception as err:
        return send_error(err)

    try:
        ocsp_response = base64.decodebytes(result['response'])
    except Exception as err:
        return send_error(err)

    # OCSP answer are binary
    return send_file(ocsp_response, mimetype="application/ocsp-response")

@public_api.route('/certify', methods=['POST'])
@cross_origin()
def certify():
    """CSR signing endpoint, Simple Certificate Enrollement revisited ;)
    Only works for new csr (renew requires TLS, see client API)
    Is based on 'clients' configuration option:
        - "all" will accept and register any new CSR incoming (insecure)
        - "register" will only accept registered nodes
        - "manual" will deactivate this endpoint
    """
    data = request.get_json()
    try:
        result = current_app.ra.sign_node(data)
    except Exception as err:
        return send_error(err)

    try:
        result['certificate']
        result['profile']
        result['dn']
    except KeyError:
        return send_error(err)

    return jsonify({'status': 'success', 'certificate': result['certificate'], 'dn': result['dn'], 'profile': result['profile']})

@public_api.route('/magic/<profile>', methods=['POST'])
@cross_origin()
def magic(profile):
    """Magic openssl kungfu command generator
    """
    data = request.get_json()
    try:
        result = current_app.ra.generate_command(profile, data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'command': result})
