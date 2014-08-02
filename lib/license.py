# -*- coding: utf-8 -*-
import os,base64
import rsa

lib_dir = os.path.dirname(os.path.abspath(__file__))
license_file = os.path.normpath(os.path.join(lib_dir, "../etc/%s.txt" % __name__))
privatekey_file = os.path.join(lib_dir, "private.key")

_pk = "MEgCQQChvFeiMviXgB4RU9LIGJQ4DfxwPobNZHj6LqJYAAeOuwAmj4hpTLNolMNeyxy16p79MF2Om4KRuN8bnK8kVkuvAgMBAAE="

license_string = None
license_mtime = None

def parser_setup(parser):
    parser.add_argument('license_string', nargs="?")
    parser.add_argument("--generate-key", action="store_true")
    parser.set_defaults(func=run,name="license")

def get_license_string():
    if not os.path.isfile(license_file): return None
    try:
        with open(license_file) as f:
            license_string = f.readline().strip()
            signature = base64.b64decode(f.readline())
        pubkey = rsa.PublicKey.load_pkcs1(base64.b64decode(_pk), "DER")
        rsa.verify(license_string, signature, pubkey)
    except:
        return None
    return license_string.decode("utf-8")

def run(args):
    if args.generate_key:
        print "Generating key pair..."
        (pubkey, privkey) = rsa.newkeys(512)
        print base64.b64encode(pubkey.save_pkcs1("DER"))
        with open(privatekey_file, "w") as f:
            f.write(base64.b64encode(privkey.save_pkcs1("DER")))
    else:
        pubkey = rsa.PublicKey.load_pkcs1(base64.b64decode(_pk), "DER")
        if os.path.isfile(privatekey_file):
            privkey = rsa.PrivateKey.load_pkcs1(base64.b64decode(open(privatekey_file).read()), "DER")
            
    if args.license_string:
        license_string = args.license_string.strip()
        print license_string
        print base64.b64encode(rsa.sign(args.license_string, privkey, "SHA-1"))
        return
    
    #else
    print get_license_string()
