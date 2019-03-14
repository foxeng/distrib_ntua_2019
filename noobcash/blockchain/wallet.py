import typing
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from noobcash.blockchain import util


# Storage
# - Private key     wallet:privkey  PrivateKey
# - Public keys     wallet:pubkeys  map [node_id: int] -> [PublicKey]


class PublicKey:

    # TODO OPT: cache key both as an object and serialized to avoid extra conversions
    def __init__(self, key: rsa.RSAPublicKeyWithSerialization) -> None:
        if not isinstance(key, rsa.RSAPublicKeyWithSerialization):
            raise TypeError
        self._key = key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PublicKey):
            return False
        return other.dumpb() == self.dumpb()

    def __hash__(self) -> int:
        return int.from_bytes(self.dumpb(), byteorder="big")

    def verify(self, message: bytes, signature: bytes) -> bool:
        # NOTE: we use hashlib instead of cryptography's SHA256 because it's
        # much faster
        h = hashlib.sha256()
        h.update(message)
        try:
            self._key.verify(signature,
                             h.digest(),
                             padding.PSS(padding.MGF1(SHA256()), padding.PSS.MAX_LENGTH),
                             Prehashed(SHA256()))
            return True
        except InvalidSignature:
            return False

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # NOTE: We use PEM, which is already base64
        return self._key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def dumpo(self) -> str:
        """Dump to JSON-serializable object"""
        return self.dumpb().decode()

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo()) # json is not really necessary here

    @classmethod
    def loadb(cls, b: bytes) -> 'PublicKey':
        """Load from bytes"""
        return cls(key=serialization.load_pem_public_key(b, default_backend()))

    @classmethod
    def loado(cls, o: str) -> 'PublicKey':
        """Load from JSON-serializable object"""
        return cls.loadb(o.encode())

    @classmethod
    def loads(cls, s: str) -> 'PublicKey':
        """Load from string"""
        return cls.loado(util.loads(s))   # json is not really necessary here


class PrivateKey:

    # TODO OPT: cache key both as an object and serialized to avoid extra conversions
    def __init__(self,
                 key_size: int = 4096,
                 key: rsa.RSAPrivateKeyWithSerialization = None) -> None:
        if key is None:
            self._key = rsa.generate_private_key(65537, key_size, default_backend())
        else:
            if not isinstance(key, rsa.RSAPrivateKeyWithSerialization):
                raise TypeError
            self._key = key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrivateKey):
            return False
        return other.dumpb() == self.dumpb()

    def __hash__(self) -> int:
        return int.from_bytes(self.dumpb(), byteorder="big")

    def public_key(self) -> 'PublicKey':
        return PublicKey(key=self._key.public_key())

    def sign(self, message: bytes) -> bytes:
        # NOTE: we use hashlib instead of cryptography's SHA256 because it's
        # much faster
        h = hashlib.sha256()
        h.update(message)
        return self._key.sign(h.digest(),
                              padding.PSS(padding.MGF1(SHA256()), padding.PSS.MAX_LENGTH),
                              Prehashed(SHA256()))

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # NOTE: We use PEM, which is already base64
        return self._key.private_bytes(serialization.Encoding.PEM,
                                       serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption())

    def dumpo(self) -> str:
        """Dump to JSON-serializable object"""
        return self.dumpb().decode()

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo())    # json is not really necessary here

    @classmethod
    def loadb(cls, b: bytes) -> 'PrivateKey':
        """Load from bytes"""
        return cls(key=serialization.load_pem_private_key(b, None, default_backend()))

    @classmethod
    def loado(cls, o: str) -> 'PrivateKey':
        """Load from JSON-serializable object"""
        return cls.loadb(o.encode())

    @classmethod
    def loads(cls, s: str) -> 'PrivateKey':
        """Load from string"""
        return cls.loado(util.loads(s))  # json is not really necessary here


def generate_wallet(node_id: int, key_size: int = 4096) -> None:
    privkey = PrivateKey(key_size)
    pubkey = privkey.public_key()
    r = util.get_db()
    util.set_node_id(node_id)
    r.set("wallet:privkey", privkey.dumpb())
    r.hset("wallet:pubkeys", node_id, pubkey.dumpb())


def sign(message: bytes) -> bytes:
    r = util.get_db()
    return PrivateKey.loadb(r.get("wallet:privkey")).sign(message)


def get_public_key(node_id: typing.Optional[int] = None) -> PublicKey:
    # TODO OPT: Cache keys locally to avoid contacting redis
    r = util.get_db()
    if node_id is None:
        node_id = util.get_node_id()
    return PublicKey.loadb(r.hget("wallet:pubkeys", node_id))


def set_public_key(node_id: int, key: PublicKey) -> None:
    r = util.get_db()
    r.hset("wallet:pubkeys", node_id, key.dumpb())
