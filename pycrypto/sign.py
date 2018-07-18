# https://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/

from Crypto.PublicKey import RSA

class TrustA:
    def __init__(self):
        self.key = RSA.generate(1024)
        self.pubkey = self.key.publickey()
        self.s_key = self.key.exportKey()

    def sign(self, data):
        enc = self.pubkey.encrypt(data, 0)
        return (data, enc[0], self.s_key)

    @staticmethod
    def verify(bundle):
        data, enc, s_key = bundle
        key = RSA.importKey(s_key)
        dec = key.decrypt(enc)
        return data == dec

class TrustB:
    def __init__(self):
        self.key = RSA.generate(1024)
        self.pubkey = self.key.publickey()

    def sign(self, data):
        sig = self.key.sign(data, 0)
        return (data, sig, self.pubkey.exportKey())

    @staticmethod
    def verify(bundle):
        data, sig, s_key = bundle
        key = RSA.importKey(s_key)
        return key.verify(data, sig)

if __name__ == '__main__':
    m = "Hello world".encode('utf8')
    d1 = TrustA().sign(m)
    d2 = TrustB().sign(m)

    print(TrustA.verify(d1))
    print(TrustB.verify(d2))

    sig = d2[1][0]
    print(type(sig))
    print(sig)
    print(len(str(sig)))

