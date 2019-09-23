# -*- coding: utf-8 -*-
import base64

from flask import jsonify, request
from flask import current_app
from flask import Blueprint

# from flask_login import login_required, current_user

private_api = Blueprint('private_api', __name__)

def send_error(msg):
    """Send back error in json
    """
    return jsonify({'status': 'error', 'message': str(msg)})

@private_api.route('/options', methods=['GET'])
def all_options():
    try:
        options = current_app.ra.get_options()
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'options': options})

@private_api.route('/nodes', methods=['GET'])
def list_nodes():
    try:
        data = current_app.ra.list_nodes()
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'nodes': data})

@private_api.route('/nodes', methods=['POST'])
def register_nodes():
    data = request.get_json()
    try:
        node = current_app.ra.register_node(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node is registered', 'node': node})

@private_api.route('/sign', methods=['POST'])
def sign_nodes():
    data = request.get_json()
    try:
        current_app.ra.sign_node(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node is signed'})

@private_api.route('/revoke', methods=['POST'])
def revoke_node():
    data = request.get_json()
    try:
        current_app.ra.revoke_node(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node revoked'})

@private_api.route('/unrevoke', methods=['POST'])
def unrevoke_node():
    data = request.get_json()
    try:
        current_app.ra.unrevoke_node(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node unrevoked'})

@private_api.route('/nodes/<dn>', methods=['PUT'])
def update_node(dn):
    data = request.get_json()
    try:
        data['requested_dn'] = base64.b64decode(dn).decode("utf-8")
    except Exception as err:
        return send_error(err)
    
    try:
        current_app.ra.update_node(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node updated'})

@private_api.route('/nodes/<dn>', methods=['DELETE'])
def remove_nodes(dn):
    try:
        dn = base64.b64decode(dn).decode("utf-8")
    except Exception as err:
        return send_error(err)
    
    try:
        current_app.ra.remove_node({'DN': dn, 'Serial': None})
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Node removed'})

@private_api.route('/profiles', methods=['GET'])
def list_profiles():
    try:
        data = current_app.ra.list_profiles()
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'profiles': data})

@private_api.route('/profiles', methods=['POST'])
def add_profile():
    data = request.get_json()
    try:
        current_app.ra.add_profile(data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Profile created'})

@private_api.route('/profiles/<name>',methods=['PUT'])
def update_profile(name):
    data = request.get_json()
    try:
        current_app.ra.update_profile(name, data)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Profile updated'})

@private_api.route('/profiles/<name>',methods=['DELETE'])
def remove_profile(name):
    try:
        current_app.ra.remove_profile(name)
    except Exception as err:
        return send_error(err)

    return jsonify({'status': 'success', 'message': 'Profile removed'})
