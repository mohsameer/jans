
import pydevd
import debugpy

import os
import re
import base64
import json
import socket
import ssl
import urllib.request

from collections import OrderedDict
from pathlib import Path

from setup_app.pylib.pyDes import triple_des, ECB, PAD_PKCS5

from setup_app import paths
from setup_app import static
from setup_app.config import Config

class Crypto64:

    def get_ssl_subject(self, ssl_fn):
        cert_info = ssl._ssl._test_decode_cert(ssl_fn)    
        retDict = {}
        for subj in cert_info["subject"]:
            retDict[subj[0][0]] = subj[0][1]
        return retDict

    def obscure(self, data=""):
        engine = triple_des(Config.encode_salt, ECB, pad=None, padmode=PAD_PKCS5)
        data = data.encode('utf-8')
        en_data = engine.encrypt(data)
        encoded_pw = base64.b64encode(en_data)
        return encoded_pw.decode('utf-8')

    def unobscure(self, data=""):
        engine = triple_des(Config.encode_salt, ECB, pad=None, padmode=PAD_PKCS5)
        cipher = triple_des(Config.encode_salt)
        decrypted = cipher.decrypt(base64.b64decode(data), padmode=PAD_PKCS5)
        return decrypted.decode('utf-8')

    def gen_cert(self, suffix, password, user='root', cn=None, truststore_fn=None):
        self.logIt('Generating Certificate for %s' % suffix)
        key_with_password = os.path.join(Config.certFolder, suffix + '.key.orig')
        key_without_password = os.path.join(Config.certFolder, suffix + '.key.noenc')
        key = '%s/%s.key' % (Config.certFolder, suffix)
        csr = '%s/%s.csr' % (Config.certFolder, suffix)
        public_certificate = '%s/%s.crt' % (Config.certFolder, suffix)
        if not truststore_fn:
            truststore_fn = Config.default_trust_store_fn

        if Config.profile == static.SetupProfiles.DISA_STIG:
            self.run([paths.cmd_openssl,
                  'genrsa',
                  '-out',
                  key_without_password,
                  ])

            self.run([paths.cmd_openssl,
                  'pkey',
                  '-in',
                  key_without_password,
                  '-out',
                  key_with_password,
                  '-des3',
                  '-passout',
                  'pass:%s' % password,
                  ])

            # remove unencrypted key
            os.remove(key_without_password)

        else:

            self.run([paths.cmd_openssl,
                      'genrsa',
                      '-des3',
                      '-out',
                      key_with_password,
                      '-passout',
                      'pass:%s' % password,
                      '2048'
                      ])

        self.run([paths.cmd_openssl,
                  'rsa',
                  '-in',
                  key_with_password,
                  '-passin',
                  'pass:%s' % password,
                  '-out',
                  key
                  ])

        certCn = cn
        if certCn == None:
            certCn = Config.hostname

        self.run([paths.cmd_openssl,
                  'req',
                  '-new',
                  '-key',
                  key,
                  '-out',
                  csr,
                  '-subj',
                  '/C=%s/ST=%s/L=%s/O=%s/CN=%s/emailAddress=%s' % (Config.countryCode, Config.state, Config.city, Config.orgName, certCn, Config.admin_email)
                  ])
        self.run([paths.cmd_openssl,
                  'x509',
                  '-req',
                  '-days',
                  '365',
                  '-in',
                  csr,
                  '-signkey',
                  key,
                  '-out',
                  public_certificate
                  ])
        self.run([paths.cmd_chown, '%s:%s' % (user, user), key_with_password])
        self.run([paths.cmd_chmod, '700', key_with_password])
        self.run([paths.cmd_chown, '%s:%s' % (user, user), key])
        self.run([paths.cmd_chmod, '700', key])

        alias = "%s_%s" % (Config.hostname, suffix)
        self.delete_key(alias, truststore_fn)
        self.import_cert_to_java_truststore(alias, public_certificate)

    def gen_ca(self, ca_suffix='ca'):
        self.logIt('Generating CA Certificate')

        out_dir = os.path.join(Config.output_dir, 'CA')
        self.run([paths.cmd_mkdir, '-p', out_dir])

        ca_key_fn = os.path.join(out_dir, ca_suffix+'.key')
        ca_crt_fn = os.path.join(out_dir, ca_suffix+'.crt')

        self.run([paths.cmd_openssl, 'req',
                  '-newkey', 'rsa:2048', '-nodes',
                  '-keyform', 'PEM',
                  '-keyout', ca_key_fn,
                  '-x509',
                  '-days', '3650',
                  '-outform', 'PEM',
                  '-out', ca_crt_fn,
                  '-subj', '/C={}/ST={}/L={}/O={}/CN={}/emailAddress={}'.format(Config.countryCode, Config.state, Config.city, Config.orgName, Config.hostname, Config.admin_email)
                  ])

        return ca_key_fn, ca_crt_fn


    def gen_key_cert_from_ca(self, fn_suffix, ca_suffix='ca', cn=None):
        if not cn:
            cn = Config.hostname
        out_dir = os.path.join(Config.output_dir, 'CA')
        ca_key_fn = os.path.join(out_dir, ca_suffix+'.key')
        ca_crt_fn = os.path.join(out_dir, ca_suffix+'.crt')

        key_fn = os.path.join(out_dir, fn_suffix+'.key')
        self.run([paths.cmd_openssl, 'genrsa', '-out', key_fn, '2048'])

        csr_fn = os.path.join(out_dir, fn_suffix+'.csr')
        self.run([paths.cmd_openssl, 'req', '-new',
            '-key', key_fn,
            '-out', csr_fn,
            '-subj', '/C={}/ST={}/L={}/O={}/CN={}/emailAddress={}'.format(Config.countryCode, Config.state, Config.city, Config.orgName, cn, Config.admin_email)
            ])

        crt_fn = os.path.join(out_dir, fn_suffix+'.crt')
        self.run([paths.cmd_openssl, 'x509', '-req',
            '-in', csr_fn,
            '-CA', ca_crt_fn,
            '-CAkey', ca_key_fn,
            '-set_serial', '101',
            '-days', '365',
            '-outform', 'PEM',
            '-out', crt_fn
            ])

        return key_fn, csr_fn, crt_fn


    def prepare_base64_extension_scripts(self, extensions=[]):

#        debugpy.breakpoint();

        self.logIt("Preparing scripts")
        # Remove extensionFolder when all scripts are moved to script_catalog_dir
        for path_ in (Config.extensionFolder, Config.script_catalog_dir):
            extension_path = Path(path_)
            for ep in extension_path.glob("**/*"):
                if ep.is_file() and ep.suffix.lower() in ['.py', '.java']:
                    extension_type = ep.relative_to(path_).parent.as_posix().lower().replace(os.path.sep, '_').replace('-','_')
                    extension_name = ep.stem.lower()
                    extension_script_name = '{}_{}'.format(extension_type, extension_name)

                    self.logIt('extension_script_name = {}'.format(extension_script_name))

                    if extensions and extension_script_name in extensions:
                        continue

                    # Prepare key for dictionary
                    base64_script_file = self.generate_base64_file(ep.as_posix(), 1)
                    self.logIt('base64_script_file = {}'.format(base64_script_file))

                    Config.templateRenderingDict[extension_script_name] = base64_script_file

        self.logIt("Config.templateRenderingDict = {}".format(Config.templateRenderingDict))


    def generate_base64_file(self, fn, num_spaces):
        self.logIt('Loading file %s' % fn)
        plain_file_b64encoded_text = None
        try:
            plain_file_text = self.readFile(fn, rmode='rb')
            plain_file_b64encoded_text = base64.b64encode(plain_file_text).decode('utf-8').strip()
        except:
            self.logIt("Error loading file", True)

        if num_spaces > 0:
            plain_file_b64encoded_text = self.reindent(plain_file_b64encoded_text, num_spaces)

        return plain_file_b64encoded_text

    def generate_base64_ldap_file(self, fn):
        return self.generate_base64_file(fn, 1)

    def import_key_cert_into_keystore(self, suffix, keystore_fn, keystore_pw, in_key, in_cert, alias=None, store_type=None):

        if not store_type:
            store_type = Config.default_store_type

        self.logIt("Creating keystore %s" % suffix)
        # Convert key to pkcs12
        pkcs_fn = '%s/%s.pkcs12' % (Config.certFolder, suffix)
        self.run([paths.cmd_openssl,
                  'pkcs12', '-export',
                  '-inkey', in_key,
                  '-in', in_cert,
                  '-out', pkcs_fn,
                  '-name', alias or Config.hostname,
                  '-passout', 'pass:%s' % keystore_pw
                  ])

        # Import p12 to keystore
        import_cmd = [Config.cmd_keytool,
                  '-importkeystore',
                  '-srckeystore', '%s/%s.pkcs12' % (Config.certFolder, suffix),
                  '-srcstorepass', keystore_pw,
                  '-srcstoretype', 'PKCS12',
                  '-destkeystore', keystore_fn,
                  '-deststorepass', keystore_pw,
                  '-deststoretype', store_type,
                  '-noprompt'
                  ]
        if alias:
            import_cmd += ['-alias', alias]

        self.run(import_cmd)

    def gen_openid_jwks_jks_keys(self, jks_path, jks_pwd, key_expiration=None, dn_name=None, key_algs=None, enc_keys=None):
        self.logIt("Generating oxAuth OpenID Connect keys")

        if dn_name == None:
            dn_name = Config.default_openid_jks_dn_name

        if key_algs == None:
            key_algs = Config.default_sig_key_algs

        if key_expiration == None:
            key_expiration = Config.default_key_expiration

        if not enc_keys:
            enc_keys = Config.default_enc_key_algs

        args = [Config.cmd_java,
                '-Dlog4j.defaultInitOverride=true',
                "-cp", Config.non_setup_properties['oxauth_client_jar_fn'],
                Config.non_setup_properties['key_gen_path'],
                '-key_ops_type', 'ALL',
                '-keystore', jks_path,
                '-keypasswd', jks_pwd,
                '-sig_keys', '%s' % key_algs,
                '-enc_keys', '%s' % enc_keys,
                '-dnname', '"%s"' % dn_name,
                '-expiration', '%s' % key_expiration]

        if jks_path.lower().endswith('.jks'):
            args += ['-keystore_type', 'JKS']

        cmd = " ".join([Config.cmd_java,
                        "-Dlog4j.defaultInitOverride=true",
                        "-cp", self.get_key_gen_client_cmd(), 
                        Config.non_setup_properties['key_gen_path'],
                        '-key_ops_type', 'ALL',
                        "-keystore",
                        jks_path,
                        "-keypasswd",
                        jks_pwd,
                        "-sig_keys",
                        "%s" % key_algs,
                        "-enc_keys",
                        "%s" % enc_keys,
                        "-dnname",
                        '"%s"' % dn_name,
                        "-expiration",
                        "%s" % key_expiration])

        output = self.run([cmd], shell=True)

        if output:
            return output.splitlines()

    def gen_openid_data_store_keys(self, data_store_path, data_store_pwd, key_expiration=None, dn_name=None, key_algs=None, enc_keys=None):
        self.logIt("Generating oxAuth OpenID Connect keys")

        if dn_name == None:
            dn_name = Config.default_openid_jks_dn_name

        if key_algs == None:
            key_algs = Config.default_sig_key_algs

        if key_expiration == None:
            key_expiration = Config.default_key_expiration

        if not enc_keys:
            enc_keys = Config.default_enc_key_algs

        args = [Config.cmd_java,
                        "-Dlog4j.defaultInitOverride=true",
                        "-cp", self.get_key_gen_client_cmd(),
                        Config.non_setup_properties['key_gen_path'],
                        '-key_ops_type', 'ALL',
                        "-keystore",
                        data_store_path,
                        "-keypasswd",
                        data_store_pwd,
                        "-sig_keys",
                        "%s" % key_algs,
                        "-enc_keys",
                        "%s" % enc_keys,
                        "-dnname",
                        '"%s"' % dn_name,
                        "-expiration",
                        "%s" % key_expiration]

        output = self.run([' '.join(args)], shell=True)

        if output:
            return output.splitlines()

    def export_openid_key(self, jks_path, jks_pwd, cert_alias, cert_path):
        self.logIt("Exporting oxAuth OpenID Connect keys")

        cmd = " ".join([Config.cmd_java,
                        "-Dlog4j.defaultInitOverride=true",
                        "-cp", self.get_key_gen_client_cmd(),
                        Config.non_setup_properties['key_export_path'],
                        '-key_ops_type', 'ALL',
                        "-keystore",
                        jks_path,
                        "-keypasswd",
                        jks_pwd,
                        "-alias",
                        cert_alias,
                        "-exportfile",
                        cert_path])
        self.run(['/bin/sh', '-c', cmd])

    def write_openid_keys(self, fn, jwks):
        self.logIt("Writing oxAuth OpenID Connect keys")

        if not jwks:
            self.logIt("Failed to write oxAuth OpenID Connect key to %s" % fn)
            return

        self.backupFile(fn)

        try:
            jwks_text = '\n'.join(jwks)
            self.writeFile(fn, jwks_text)
            self.run([Config.cmd_chown, 'jetty:jetty', fn])
            self.run([Config.cmd_chmod, '600', fn])
            self.logIt("Wrote oxAuth OpenID Connect key to %s" % fn)
        except:
            self.logIt("Error writing command : %s" % fn, True)



    def generate_base64_string(self, lines, num_spaces):
        if not lines:
            return None

        plain_text = ''.join(lines)
        plain_b64encoded_text = base64.encodebytes(plain_text.encode('utf-8')).decode('utf-8').strip()

        if num_spaces > 0:
            plain_b64encoded_text = self.reindent(plain_b64encoded_text, num_spaces)

        return plain_b64encoded_text

    def encode_passwords(self):
        self.logIt("Encoding passwords")

        try:
            if Config.get('ldapPass'):
                Config.encoded_ox_ldap_pw = self.obscure(Config.ldapPass)
            if Config.get('cb_password'):
                Config.encoded_cb_password = self.obscure(Config.cb_password)
            if not Config.get('opendj_truststore_pass'):
                Config.opendj_truststore_pass = os.urandom(6).hex()
            Config.opendj_truststore_pass_enc = self.obscure(Config.opendj_truststore_pass)
        except:
            self.logIt("Error encoding passwords", True, True)

    def encode_test_passwords(self):
        self.logIt("Encoding test passwords")
        hostname = Config.hostname.split('.')[0]
        try:
            Config.templateRenderingDict['oxauthClient_2_pw'] = Config.templateRenderingDict['oxauthClient_2_inum'] + '-' + hostname
            Config.templateRenderingDict['oxauthClient_2_encoded_pw'] = self.obscure(Config.templateRenderingDict['oxauthClient_2_pw'])

            Config.templateRenderingDict['oxauthClient_3_pw'] =  Config.templateRenderingDict['oxauthClient_3_inum'] + '-' + hostname
            Config.templateRenderingDict['oxauthClient_3_encoded_pw'] = self.obscure(Config.templateRenderingDict['oxauthClient_3_pw'])

            Config.templateRenderingDict['oxauthClient_4_pw'] = Config.templateRenderingDict['oxauthClient_4_inum'] + '-' + hostname
            Config.templateRenderingDict['oxauthClient_4_encoded_pw'] = self.obscure(Config.templateRenderingDict['oxauthClient_4_pw'])
        except:
            self.logIt("Error encoding test passwords", True)

    def get_server_certificate(self, host):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.SSLContext()
        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.connect((host, 443))
        cert_der = ssl_sock.getpeercert(True)
        return ssl.DER_cert_to_PEM_cert(cert_der)

    def download_ob_cert(self, ob_cert_fn=None):
        self.logIt("Downloading Openbanking Certificate from {}".format(Config.jwks_uri))
        if not ob_cert_fn:
            ob_cert_fn = Config.ob_cert_fn

        try:
            req = urllib.request.Request(Config.jwks_uri)
            with urllib.request.urlopen(req) as f:
                data = f.read().decode('utf-8')
            keys = json.loads(data)

            with open(ob_cert_fn, 'w') as w:
                w.write('-----BEGIN CERTIFICATE-----\n')
                w.write(keys["keys"][0]["x5c"][0])
                w.write('\n-----END CERTIFICATE-----')
        except Exception as e:
            print("{}Can't download certificate{}".format(static.colors.DANGER, static.colors.ENDC))
            print(e)

    def remove_pcks11_keys(self, keys=['server-cert', 'admin-cert', 'dummy']):
        output = self.run([Config.cmd_keytool, '-list', '-keystore', 'NONE', '-storetype', 'PKCS11', '-storepass', 'changeit'])
        for l in output.splitlines():
            ls = l.strip()
            if ls.startswith(tuple(keys)):
                alias = ls.split(',')[0]
                if alias in keys:
                    self.run([Config.cmd_keytool, '-delete', '-alias', alias, '-keystore', 'NONE', '-storetype', 'PKCS11', '-storepass', 'changeit'])

    def delete_key(self, alias, truststore_fn=None):
        if not truststore_fn:
            truststore_fn = Config.default_trust_store_fn

        if truststore_fn == Config.default_trust_store_fn and alias in Config.non_setup_properties['java_truststore_aliases']:
            self.run([Config.cmd_keytool, "-delete", "-trustcacerts", "-alias", alias,
                    "-keystore", truststore_fn,
                    "-storepass", "changeit", "-noprompt"])

    def export_cert_from_store(self, alias, truststore_fn, storepass, target_fn):
        self.logIt("Exporting certificate from {} to {} with alias {}".format(truststore_fn, target_fn, alias))
        cmd = [Config.cmd_keytool, "-exportcert", "-rfc",
                    "-alias", alias,
                    "-keystore", truststore_fn,
                    "-storepass", storepass,
                    "-file", target_fn]

        cmd += self.get_keytool_provider(as_list=True)
        self.run(cmd)

    def import_cert_to_java_truststore(self, alias, cert_fn):
        self.run([Config.cmd_keytool, '-import', '-trustcacerts',
                    '-keystore', Config.default_trust_store_fn,
                    '-storepass', 'changeit','-noprompt',
                    '-alias', alias,
                    '-file', cert_fn])

    def obtain_java_cacert_aliases(self):
        output = self.run([Config.cmd_keytool, '-list',
                    '-keystore', Config.default_trust_store_fn,
                    '-storepass', 'changeit', '-noprompt'])

        for l in output.splitlines():
            ls = l.strip().rstrip(',')
            if ls.endswith('trustedCertEntry'):
                sep = ls.split(',')
                Config.non_setup_properties['java_truststore_aliases'].append(sep[0])

    def get_keytool_provider(self, as_list=False):
#        provider_dict  = OrderedDict([('-storetype', Config.default_store_type)])
        provider_dict  = OrderedDict()

        if Config.profile == static.SetupProfiles.DISA_STIG:
            provider_dict['-providername'] = 'BCFIPS'
            provider_dict['-providerpath'] = '{}:{}'.format(Config.bc_fips_jar, Config.bcpkix_fips_jar)
            provider_dict['-providerclass'] = 'org.bouncycastle.jcajce.provider.BouncyCastleFipsProvider'

        if as_list:
            ret_val = []
            for item in provider_dict.items():
                ret_val.append(item[0])
                ret_val.append(item[1])
            return ret_val

        return provider_dict

    def get_key_gen_client_cmd(self):
        if Config.profile == static.SetupProfiles.DISA_STIG:
            client_cmd = '{}:{}:{}'.format(
                        Config.non_setup_properties['jans_auth_client_noprivder_jar_fn'],
                        Config.bc_fips_jar,
                        Config.bcpkix_fips_jar
                        )
        else:
            client_cmd = Config.non_setup_properties['jans_auth_client_jar_fn']
        return client_cmd

    def gen_openid_data_store_keys(self, data_store_path, data_store_pwd, key_expiration=None, dn_name=None, key_algs=None, enc_keys=None):
        self.logIt("Generating oxAuth OpenID Connect keys")

        if dn_name == None:
            dn_name = Config.default_openid_jks_dn_name

        if key_algs == None:
            key_algs = Config.default_sig_key_algs

        if key_expiration == None:
            key_expiration = Config.default_key_expiration

        if not enc_keys:
            enc_keys = Config.default_enc_key_algs

        args = [Config.cmd_java,
                        "-Dlog4j.defaultInitOverride=true",
                        "-cp", self.get_key_gen_client_cmd(),
                        Config.non_setup_properties['key_gen_path'],
                        '-key_ops_type', 'ALL',
                        "-keystore",
                        data_store_path,
                        "-keypasswd",
                        data_store_pwd,
                        "-sig_keys",
                        "%s" % key_algs,
                        "-enc_keys",
                        "%s" % enc_keys,
                        "-dnname",
                        '"%s"' % dn_name,
                        "-expiration",
                        "%s" % key_expiration]

        output = self.run([' '.join(args)], shell=True)

        if output:
            return output.splitlines()

