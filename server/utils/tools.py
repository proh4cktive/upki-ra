# -*- coding:utf-8 -*-

import re
import sys
import types
import validators

from .common import Common

# if sys.version_info[0] == 3:
#     STRING_TYPE = str,
#     INTEGER_TYPE = int,
#     CLASS_TYPE = type,
#     TEXT_TYPE = str
#     BINARY_TYPE = bytes

#     MAXSIZE = sys.maxsize
# else:
#     STRING_TYPE = basestring,
#     INTEGER_TYPE = (int, long)
#     CLASS_TYPE = (type, types.ClassType)
#     TEXT_TYPE = unicode
#     BINARY_TYPE = str
#     # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
#     class X(object):
#         def __len__(self):
#             return 1 << 31
#     try:
#         len(X())
#     except OverflowError:
#         # 32-bit
#         MAXSIZE = int((1 << 31) - 1)
#     else:
#         # 64-bit
#         MAXSIZE = int((1 << 63) - 1)
#     del X

class Tools(Common):
    def __init__(self, logger):
        try:
            super(Tools, self).__init__(logger)
        except Exception as err:
            raise Exception(err)

        self._fuzz   = False
        self._email  = False
        self._ca     = False
        
        # Define allowed values
        self._profile_types = ['user','server','email']
        self._fields = ['C','ST','L','O','OU','CN','emailAddress']
        self.allowedType = [
            "server",
            "client",
            "email",
            "objsign",
            "sslCA",
            "emailCA"
        ]
        self.allowedUsage = [
            "digitalSignature",
            "nonRepudiation",
            "keyEncipherment",
            "dataEncipherment",
            "keyAgreement",
            "keyCertSign",
            "cRLSign",
            "encipherOnly",
            "decipherOnly"
        ]
        self.allowedExtendedUsage = [
            "serverAuth",
            "clientAuth",
            "codeSigning",
            "emailProtection",
            "timeStamping",
            "OCSPSigning",
            "ipsecIKE",
            "msCodeInd",
            "msCodeCom",
            "msCTLSign",
            "msEFS"
        ]

        self.allowed_digest  = ['md5','sha1','sha256','sha512']
        self.allowed_keyLen  = [1024,2048,4096]
        self.allowed_keyType = ['rsa','dsa']

        self.subject = []

    def load_profile(self, name, data):
        if name in ['ca','ra','admin']:
            raise Exception('Sorry this name is reserved')

        if not (re.match('^[\w\-_\(\)]+$', name) is not None):
            raise Exception('Invalid profile name')

        self.output('Loading profile {p}'.format(p=name), level="DEBUG")
        
        try:
            self.domain = data['domain']
            if not validators.domain(data['domain']):
                raise Exception('Domain is invalid')
        except KeyError:
            pass
        try:
            self.keyType = data['keyType']
            if self.keyType not in self.allowed_keyType:
                raise Exception('Unsupported key type')
        except KeyError:
            pass
        try:
            self.keyLen = int(data['keyLen'])
            if self.keyLen not in self.allowed_keyLen:
                raise Exception('Unsupported key length')
        except KeyError:
            pass
        except ValueError:
            pass
        try:
            self.version = data['version']
        except KeyError:
            self.version = 3
        try:
            self.duration = int(data['duration'])
            if not validators.between(data['duration'],1,36500):
                raise Exception('Duration is invalid')
        except KeyError:
            pass
        except ValueError:
            pass
        try:
            self.digest = data['digest']
            if self.digest not in self.allowed_digest:
                raise Exception('Unsupported digest algorithm')
            if self.digest in ['md5','sha1']:
                self.output('Note that {d} is now considered INSECURE !'.format(d=self.digest), level="WARNING")
        except KeyError:
            pass
        try:
            if not isinstance(data['keyUsage'], list):
                raise Exception('Key usages values are incorrect')
            self.keyUsage = data['keyUsage']
            for usage in self.keyUsage:
                if usage not in self.allowedUsage:
                    raise Exception('Unsupported key usage')
        except KeyError:
            pass
        try:
            if not isinstance(data['extendedKeyUsage'], list):
                raise Exception('Extended key usages values are incorrect')
            self.extendedKeyUsage = data['extendedKeyUsage']
            for usage in self.extendedKeyUsage:
                if usage not in self.allowedExtendedUsage:
                    raise Exception('Unsupported extended key usage')
        except KeyError:
            pass
        try:
            if not isinstance(data['certType'], list):
                raise Exception('Certificate type values are incorrect')
            self.certType = data['certType']
            for ctype in self.certType:
                if ctype not in self.allowedType:
                    raise Exception('Unsupported certificate Type')
        except KeyError:
            pass
        try:
            self.crl = data['crl']
        except KeyError:
            pass
        try:
            self.ocsp = data['ocsp']
        except KeyError:
            pass
        try:
            if not isinstance(data['subject'], list):
                raise Exception('Subject values are incorrect')
            for item in data['subject']:
                if not isinstance(item, dict):
                    raise Exception('Subject entries are incorrect')
                for (key, value) in item.items():
                    break
                if (key, value) not in self.subject:
                    self.subject.append((key, value))
        except KeyError:
            pass
        try:
            self.altnames = data['altnames']
        except KeyError:
            pass

        return data

    # def to_bytes(self, obj, encoding='ascii'):
    #     if isinstance(obj, BINARY_TYPE):
    #         return obj

    #     if isinstance(obj, TEXT_TYPE):
    #         try:
    #             return obj.encode(encoding)
    #         except UnicodeEncodeError as err:
    #             raise err
    #     else:
    #         # Convert to bytes array
    #         b = bytearray()
    #         return b.extend(str(obj))

    def _get_dn(self, x509_obj, profile=None):
        """Convert x509 subject object in standard string
        """
        dn = ''
        if profile is None:
            subject = x509_obj.get_subject()
            for couple in subject.get_components():
                value = '='.join(couple)
                dn += '/{e}'.format(e=value)
            return dn
        
        try:
            data = self._storage.get_node(x509_obj, profile=profile)
        except Exception as err:
            raise Exception('Unable to get DN: {e}'.format(e=err))

        dn = data['DN']
        
        return dn

    def _get_cn(self, dn):
        """Retrieve the CN value from complete DN
        perform validity check on CN found
        """
        try:
            cn = str(dn).split('CN=')[1]
        except Exception:
            raise Exception('Unable to get CN from DN string')

        # Ensure cn is valid
        if (cn is None) or not len(cn):
            raise Exception('Empty CN option')
        if not (re.match('^[\w\-_\.@]+$', cn) is not None):
            raise Exception('Invalid CN')

        return cn

    def _check_node_params(self, params):
        data = dict({})
        try:
            data['profile'] = params['Profile']
        except KeyError:
            raise Exception('Missing profile option')

        if data['profile'] not in self.profiles.keys():
            raise Exception('Invalid profile type: {}'.format(self.profiles.keys()))

        try:
            data['dn'] = params['DN']
        except KeyError:
            raise Exception('Missing DN option')

        try:
            data['cn'] = params['CN']
        except KeyError:
            raise Exception('Missing CN option')

        try:
            cn = self._get_cn(data['dn'])
        except Exception as err:
            raise Exception('Unable to find CN')

        if cn != data['cn']:
            raise Exception('CN Mismatch')

        try:
            data['domain'] = params['Domain']
        except KeyError:
            raise Exception('Missing Domain option')

        try:
            data['keyType'] = params['KeyType']
        except KeyError:
            raise Exception('Missing Key Type option')

        try:
            data['keyLen'] = params['KeyLen']
        except KeyError:
            raise Exception('Missing Key Length option')

        try:
            data['duration'] = params['Duration']
        except KeyError:
            raise Exception('Missing Duration option')

        try:
            data['digest'] = params['Digest']
        except KeyError:
            raise Exception('Missing Digest option')

        try:
            data['sans'] = params['SANS']
        except KeyError:
            data['sans'] = []

        return data

    # def _build_name(self, name):
    #     if (self.domain is not None) and ('.' not in name):
    #         if ('client' in self.certType) or ('email' in self.certType):
    #             name = "{c}@{d}".format(c=name, d=self.domain)
    #         else:
    #             name = "{c}.{d}".format(c=name, d=self.domain)

    #     return name

    def _build_sans(self, sans):
        for i,s in enumerate(sans):
            if validators.email(s):
                sans[i] = "email:{s}".format(s=s)
            elif validators.domain(s):
                sans[i] = "DNS:{s}".format(s=s)
            elif validators.url(s):
                sans[i] = "URI:{s}".format(s=s)
            elif validators.ipv4(s):
                sans[i] = "IP:{s}".format(s=s)
            else:
                # sans[i] = "otherName:{s}".format(s=s)
                # otherName is not supported by openssl by default
                sans[i] = "DNS:{s}".format(s=s)

        return ','.join(sans)