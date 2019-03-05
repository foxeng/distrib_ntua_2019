import typing
import json
import redis
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


class PublicKey:
    # TODO OPT: cache key both as an object and serialized to avoid extra conversions
    def __init__(self, key: rsa.RSAPublicKeyWithSerialization):
        self.key_size = key.key_size
        self._key = key

    def verify(self, message: bytes, signature: bytes) -> bool:
        try:
            self._key.verify(signature, message,
                             padding.PSS(padding.MGF1(SHA256()), padding.PSS.MAX_LENGTH), SHA256())
            return True
        except InvalidSignature:
            return False

    def dumpb(self) -> bytes:
        return self._key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def dumpo(self) -> str:
        return self.dumpb().decode()

    def dumps(self) -> str:
        return json.dumps(self.dumpo()) # json is not really necessary here

    @staticmethod
    def loadb(b: bytes) -> 'PublicKey':
        return PublicKey(key=serialization.load_pem_public_key(b, default_backend()))

    @staticmethod
    def loado(o: str) -> 'PublicKey':
        return PublicKey.loadb(o.encode())

    @staticmethod
    def loads(s: str) -> 'PublicKey':
        return PublicKey.loado(json.loads(s))   # json is not really necessary here


class PrivateKey:
    # TODO OPT: cache key both as an object and serialized to avoid extra conversions
    def __init__(self, key_size: int = 4096, key: rsa.RSAPrivateKeyWithSerialization = None):
        self.key_size = key_size
        if key is not None:
            self._key = key
        else:
            self._key = rsa.generate_private_key(65537, key_size, default_backend())

    def public_key(self) -> 'PublicKey':
        return PublicKey(key=self._key.public_key())

    def sign(self, message: bytes) -> bytes:
        return self._key.sign(message, padding.PSS(padding.MGF1(SHA256()), padding.PSS.MAX_LENGTH),
                              SHA256())

    def dumpb(self) -> bytes:
        return self._key.private_bytes(serialization.Encoding.PEM,
                                       serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption())

    def dumpo(self) -> str:
        return self.dumpb().decode()

    def dumps(self) -> str:
        return json.dumps(self.dumpo())    # json is not really necessary here

    @staticmethod
    def loadb(b: bytes) -> 'PrivateKey':
        return PrivateKey(key=serialization.load_pem_private_key(b, None, default_backend()))

    @staticmethod
    def loado(o: str) -> 'PrivateKey':
        return PrivateKey.loadb(o.encode())

    @staticmethod
    def loads(s: str) -> 'PublicKey':
        return PrivateKey.loado(json.loads(s))  # json is not really necessary here


def _get_db():
    return redis.Redis(db=0)


def generate_wallet(node_id: int, key_size: int = 4096) -> None:
    privkey = PrivateKey(key_size)
    pubkey = privkey.public_key()
    r = _get_db()
    r.set("node_id", node_id)
    r.set("privkey", privkey.dumpb())
    r.hset("pubkeys", node_id, pubkey.dumpb())


def sign(message: bytes) -> bytes:
    r = _get_db()
    return PrivateKey.loadb(r.get("privkey")).sign(message)


def get_public_key(node_id: typing.Optional[int] = None) -> PublicKey:
    # TODO OPT: Cache keys locally to avoid contacting redis
    r = _get_db()
    if node_id is None:
        node_id = r.get("node_id")
    return PublicKey.loadb(r.hget("pubkeys", node_id))


def set_public_key(node_id: int, key: PublicKey) -> None:
    r = _get_db()
    r.hset("pubkeys", node_id, key.dumpb())
