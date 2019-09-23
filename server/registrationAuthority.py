# -*- coding:utf-8 -*-

import os
import zmq
import json
import subprocess

import server

class RegistrationAuthority(server.utils.Tools):
    def __init__(self, logger, path, host, port):
        try:
            super(RegistrationAuthority, self).__init__(logger)
        except Exception as err:
            raise Exception(err)

        try:
            remote = "tcp://{h}:{p}".format(h=host,p=port)
        except KeyError:
            remote = "/tmp/server.sock"

        self._path    = path
        self._ca_url  = remote
        self.nodes    = dict({})
        self.profiles = dict({})
        
        try:
            # First get CA certificate
            ca_pem = self.get_ca()
            with open(os.path.join(self._path, 'ca.crt'), 'wt') as raw:
                raw.write(ca_pem)
            self.output('CA certificate stored in {p}ca.crt'.format(p=self._path))
        except Exception as err:
            raise Exception('Unable to retrieve CA certificate: {e}'.format(e=err))

        try:
            # Then generate and retrieve CRL
            crl_done = self._send('generate_crl')
            crl_pem  = self.get_crl()
            with open(os.path.join(self._path, 'crl.pem'), 'wt') as raw:
                raw.write(crl_pem)
        except Exception as err:
            raise Exception('Unable to retrieve CRL: {e}'.format(e=err))

        try:
            # Finally store all profiles
            self.list_profiles()
        except Exception as err:
            raise Exception('Unable to list profiles: {e}'.format(e=err))

        if not os.path.isdir(self._path):
            try:
                os.makedirs(self._path)
            except Exception as err:
                raise Exception('Unable to create certificates directory')

    def register(self, seed):
        try:
            generated_dn = self._send('register', params={'seed': seed})
        except Exception as err:
            raise Exception('Error on registration process: {e}'.format(e=err))

        for (profile, name) in [('user','ra'), ('server','certificates'), ('admin','admin')]:
            try:
                cn = self._get_cn(generated_dn[name])
            except Exception as err:
                raise Exception('Unable to extract CN: {e}'.format(e=err))
            try:
                # Build openssl command
                cmd = self.generate_command(profile, {'cn': cn}, filename=name)
            except Exception as err:
                raise Exception('Error on generation process: {e}'.format(e=err))

            try:
                # Execute command generated
                self.output('Command generated:\n{c}'.format(c=cmd), level="INFO")
                p = subprocess.Popen(cmd, cwd=self._path, shell=True, stdout=subprocess.PIPE, executable='/bin/bash')
                p.wait()
            except Exception as err:
                raise Exception('Unable to generate RA keychain: {e}'.format(e=err))

            # All done for certificate requests and private key
            self.output('{n} Private key and Certificate Request saved in {p}{n}.key and {p}{n}.csr'.format(n=name, p=self._path))
            with open(os.path.join(self._path, '{n}.csr'.format(n=name)), 'rt') as raw:
                csr = raw.read()

            try:
                # Sign Certificate Request
                data = self.sign_node({'CSR': csr})
            except Exception as err:
                raise Exception('Error on signing process: {e}'.format(e=err))

            # Write certificate received
            with open(os.path.join(self._path, '{n}.crt'.format(n=name)), 'wt') as raw:
                raw.write(data['certificate'])

            self.output('{n} Certificate saved in {p}{n}.crt'.format(n=name, p=self._path))

        try:
            check = self._send('done', params=seed)
        except Exception as err:
            raise Exception('Unable to send done flag: {e}'.format(e=err))

        return True

    def get_options(self):
        try:
            data = self._send('get_options')
        except Exception as err:
            raise Exception(err)

        return data

    def generate_crl(self):
        try:
            data = self._send('generate_crl')
        except Exception as err:
            raise Exception(err)

        return data

    def check_ocsp(self, data):
        try:
            result = self._send('check_ocsp', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def get_ca(self):
        try:
            data = self._send('get_ca')
        except Exception as err:
            raise Exception(err)

        return data

    def get_crl(self):
        try:
            data = self._send('get_crl')
        except Exception as err:
            raise Exception(err)

        return data

    def download_node(self, data):
        try:
            data['dn']
        except KeyError:
            raise Exception('Missing DN value')
        
        try:
            result = self._send('download_node', params=data['dn'])
        except Exception as err:
            raise Exception(err)

        return result

    def generate_command(self, profile, data, filename=None):
        try:
            cn = data['cn']
        except KeyError:
            raise Exception('Missing CN value')
        
        try:
            # Get profile infos
            profile_data = self.profiles[profile]
        except KeyError:
            raise Exception('Invalid profile type')

        try:
            # Get node infos
            node_data = self._send('get_node', params={'cn': cn, 'profile': profile})
        except Exception as err:
            raise Exception(err)

        if filename is None:
            filename = "{p}.{n}".format(p=profile, n=cn)

        cmd = 'openssl req -new -{d} -nodes -newkey {kt}:{kl} -keyout {n}.key -subj "{s}"'.format(d=profile_data['digest'], kt=profile_data['keyType'], kl=profile_data['keyLen'], n=filename, s=node_data['DN'])
        if len(node_data['Sans']):
            sans = self._build_sans(node_data['Sans'])
            cmd += ' -reqexts SAN -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\\nsubjectAltName={san}"))'.format(san=sans)
        
        cmd += " -out {n}.csr".format(n=filename)
        
        return cmd

    def sign_node(self, data):
        try:
            data['CSR']
        except KeyError:
            raise Exception('Missing certificate request')
        try:
            # Get node infos
            results = self._send('sign', params={'csr':data['CSR']})
        except Exception as err:
            raise Exception(err)

        return results

    def list_profiles(self):
        try:
            data = self._send('list_profiles')
        except Exception as err:
            raise Exception(err)
        
        for name, profile in data.items():
            # Setup correct name
            profile['name'] = name
            # Store profiles for next time
            if name not in self.profiles.keys():
                self.profiles[name] = profile

        return list(self.profiles.values())

    def add_profile(self, params):
        try:
            data = self._send('add_profile', params=params)
        except Exception as err:
            raise Exception(err)

        return data

    def update_profile(self, name, params):

        original = params.get('origName')

        if original not in self.profiles.keys():
            raise Exception('Invalid profile type')

        try:
            data = self._send('update_profile', params=params)
        except Exception as err:
            raise Exception(err)

        # Profile has been updated successfuly
        try:
            del self.profiles[original]
        except KeyError:
            pass

        return data

    def remove_profile(self, name):
        if name not in self.profiles.keys():
            raise Exception('Invalid profile type')

        try:
            data = self._send('remove_profile', params={'name': name})
        except Exception as err:
            raise Exception(err)

        # Profile has been removed successfuly
        try:
            del self.profiles[name]
        except KeyError:
            pass

        return data


    def list_nodes(self):
        try:
            self.nodes = self._send('list_nodes')
        except Exception as err:
            raise Exception(err)

        return self.nodes

    def register_node(self, params):
        try:
            data = self._check_node_params(params)
        except Exception as err:
            raise Exception(err)

        try:
            data = self._send('register', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def update_node(self, params):
        try:
            data = self._check_node_params(params)
        except Exception as err:
            raise Exception(err)

        try:
            data = self._send('update', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def renew_node(self, dn):
        try:
            data = self._send('renew', params={'dn': dn})
        except Exception as err:
            raise Exception(err)

        return data

    def revoke_node(self, params):
        data = dict({})

        try:
            data['dn'] = params['DN']
        except KeyError:
            raise Exception('Missing DN option')

        try:
            data['reason'] = params['Reason']
        except KeyError:
            raise Exception('Missing DN option')

        try:
            data = self._send('revoke', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def unrevoke_node(self, params):
        data = dict({})

        try:
            data['dn'] = params['DN']
        except KeyError:
            raise Exception('Missing DN option')

        try:
            data = self._send('unrevoke', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def remove_node(self, params):
        data = dict({})

        try:
            data['dn'] = params['DN']
        except KeyError:
            raise Exception('Missing DN option')

        try:
            data['serial'] = params['Serial']
        except KeyError:
            raise Exception('Missing serial option')

        try:
            data = self._send('delete', params=data)
        except Exception as err:
            raise Exception(err)

        return data

    def _send(self, task, params=None):
        if task is None:
            raise Exception('Can not send empty event')

        try:
            context = zmq.Context()
            self.output("Connect socket use ZMQ version {v}".format(v=zmq.zmq_version()), level="DEBUG")
            backend_socket = context.socket(zmq.REQ)
            backend_socket.connect('{s}'.format(s=self._ca_url))
            self.output("Socket connected to {host}".format(host=self._ca_url), level="DEBUG")
            backend_socket.send_json({'TASK': task, 'PARAMS':params})
        except zmq.ZMQError as err:
            raise Exception("Stalker process failed with: {e}".format(e=err))
        except AttributeError as err:
            raise Exception("Missing config options: {e}".format(e=err))
        except Exception as err:
            raise Exception("Error on connection: {e}".format(e=err))

        try:
            answer = backend_socket.recv_json()
        except zmq.ZMQError as e:
            raise Exception('ZMQ Error: {err}'.format(err=e))
        except ValueError:
            raise Exception('Received unparsable message')
        except SystemExit:
            raise Exception('Poison listener...')
        
        try:
            evt = answer['EVENT']
        except KeyError:
            raise Exception('Invalid message')

        try:
            data = answer['DATA']
        except KeyError:
            data = None
        except ValueError:
            raise Exception('Received unparsable data')

        if evt == 'UPKI ERROR':
            try:
                msg = answer['MSG']
            except Exception:
                raise Exception('CA Invalid error message')
            raise Exception('CA ERROR: {m}'.format(m=msg))

        try:
            backend_socket.close()
        except Exception as err:
            raise Exception('Unable to close socket: {e}'.format(e=err))

        return data