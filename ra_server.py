#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import logging
import argparse
import datetime

from flask import Flask
from flask_cors import CORS

from server.core import PHKLogger
from server import RegistrationAuthority


def main(argv):

    # Define vars
    DEBUG = True
    BASE_DIR      = os.path.join(os.path.expanduser("~"), '.upki/')
    LOG_FILE      = ".ra.log"
    LOG_PATH      = os.path.join(BASE_DIR, LOG_FILE)
    LOG_LEVEL     = logging.INFO
    VERBOSE       = True
    CA_HOST       = '127.0.0.1'
    CA_PORT       = 5000
    WEB_HOST      = '127.0.0.1'
    WEB_PORT      = 8000

    parser = argparse.ArgumentParser(description="µPki [maɪkroʊ ˈpiː-ˈkeɪ-ˈaɪ] is a small PKI in python that should let you make basic tasks without effort.")
    parser.add_argument("-d", "--dir", help="Define a default directory for files (default: {d})".format(d=BASE_DIR), default=BASE_DIR)
    parser.add_argument("-i", "--ip", help="Define CA server IP (default: {i})".format(i=CA_HOST), default=CA_HOST)
    parser.add_argument("-p", "--port", help="Define CA server port (default: {p})".format(p=CA_PORT), default=CA_PORT)

    # Allow subparsers
    subparsers = parser.add_subparsers(title='commands')

    parser_init = subparsers.add_parser('init', help="Initialize your RA.")
    parser_init.set_defaults(which='init')

    parser_register = subparsers.add_parser('register', help="Enable the 0MQ server in clear-mode. This allow to setup your RA certificates.")
    parser_register.set_defaults(which='register')
    parser_register.add_argument("-s", "--seed", help="Allow RA registration against CA", required=True)

    parser_crl = subparsers.add_parser('crl', help="Enable the 0MQ server in clear-mode. This allow to setup your RA certificates.")
    parser_crl.set_defaults(which='crl')

    parser_listen = subparsers.add_parser('listen', help="Enable the RA 0MQ server in TLS. This enable interactions by events emitted from RA.")
    parser_listen.set_defaults(which='listen')
    parser_listen.add_argument("-i", "--web-ip", help="Define web RA listening IP (default: {i})".format(i=WEB_HOST), default=WEB_HOST)
    parser_listen.add_argument("-p", "--web-port", help="Define web RA listening port (default: {p})".format(p=WEB_PORT), default=WEB_PORT)

    args = parser.parse_args()

    try:
        # User MUST call upki with a command
        args.which
    except AttributeError:
        parser.print_help()
        sys.exit(1)

    if args.dir:
        BASE_DIR = args.dir if args.dir.endswith('/') else "{p}/".format(p=args.dir)

    # Ensure directory exists
    if not os.path.isdir(BASE_DIR):
        try:
            os.makedirs(BASE_DIR)
        except OSError as err:
            raise Exception(err)

    

    try:
        # Generate logger object
        logger = PHKLogger(LOG_PATH, LOG_LEVEL, proc_name="upki_ra", verbose=VERBOSE)
    except Exception as err:
        raise Exception('Unable to setup logger: {e}'.format(e=err))
    
    # Meta information
    dirname = os.path.dirname(__file__)

    # Retrieve all metadata from project
    with open(os.path.join(dirname, '__metadata.py'), 'rt') as meta_file:
        metadata = dict(re.findall(r"^__([a-z]+)__ = ['\"]([^'\"]*)['\"]", meta_file.read(), re.M))
    
    logger.info("\t\t..:: µPKI Registration Authority ::..", color="WHITE", light=True)
    logger.info("version: {v}".format(v=metadata['version']), color="WHITE")

    if args.ip:
        CA_HOST = args.ip
    if args.port:
        CA_PORT = args.port

    try:
        # Init PKI connection
        logger.debug('Start uPKI Registration Authority')
        server_ra = RegistrationAuthority(logger, BASE_DIR, CA_HOST, CA_PORT)
    except Exception as err:
        raise Exception('Unable to initialize RA: {e}'.format(e=err))

    # Specific behaviour when seed is set
    if args.which == 'register':
        try:
            # Only launch register part
            if server_ra.register(args.seed):
                logger.info('You should now run:')
                logger.info('sudo chgrp www-data {p}'.format(p=os.path.join(BASE_DIR, 'certificates.*')), color="WHITE", light=True)
                logger.info('sudo chmod 640 {p}'.format(p=os.path.join(BASE_DIR, 'certificates.*')), color="WHITE", light=True)
                logger.info('sudo service nginx restart', color="WHITE", light=True)
                logger.info('All good !')
        except Exception as err:
            logger.critical('Unable to register RA: {e}'.format(e=err))
            sys.exit(1)

        sys.exit(0)

    elif args.which == 'crl':
        try:
            # Generate CRL file
            server_ra.generate_crl()
        except Exception as err:
            raise Exception('Unable to generate CRL: {e}'.format(e=err))

        logger.info('CRL auto generated at {t}'.format(t=datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%Y")))
        sys.exit(0)

    elif args.which == 'listen':

        if args.web_ip:
            WEB_HOST = args.web_ip
        if args.web_port:
            WEB_PORT = args.web_port

        # Start Web app
        app = Flask(__name__)
        # app.secret_key = 'XXXXXXXXXXXXXXXXXXXXXXX'

        # Setup CORS
        CORS(app)

        # Register RA
        with app.app_context():
            app.ra = server_ra

        from server.routes.publicAPI import public_api
        from server.routes.clientAPI import client_api
        from server.routes.privateAPI import private_api

        app.register_blueprint(public_api)
        app.register_blueprint(client_api, url_prefix='/clients')
        app.register_blueprint(private_api, url_prefix='/private')

        try:
            logger.debug('Start WEB interface')
            app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG, use_reloader=False)
        except (SystemExit, KeyboardInterrupt):
            logger.critical('Bye!')
        except Exception as err:
            logger.critical('Unable to run WEB app: {e}'.format(e=err))

# Gunicorn entry point generator
def server(*args, **kwargs):
    sys.argv = ['--gunicorn']
    for k in kwargs:
        sys.argv.append("--" + k)
        sys.argv.append(kwargs[k])
    return main(sys.argv)


# Standard entry point
if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.stdout.write('\nBye.\n')
