import typing
import time
import hashlib
import sys
import subprocess
from transaction import Transaction
import util
from util import uitob


class Block:
    # NOTE: These should be set properly from blockchain (initialize them to an
    # invalid value here instead?)
    CAPACITY: int = 5
    DIFFICULTY: int = 4

    def __init__(self,
                 index: int,
                 previous_hash: bytes,
                 timestamp: typing.Optional[int] = None,
                 transactions: typing.Optional[typing.List[Transaction]] = None,   # TODO: Or specify them using add_transaction() only?
                 nonce: typing.Optional[int] = None,
                 current_hash: typing.Optional[bytes] = None) -> None:
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = int(time.time()) if timestamp is None else timestamp
        self.transactions = [] if transactions is None else transactions
        self.nonce = nonce
        self.current_hash = current_hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return False
        return self.current_hash == other.current_hash

    def __hash__(self) -> int:
        # NOTE: this will throw if the block hasn't been finalized
        return int.from_bytes(self.current_hash, byteorder="big")   # type: ignore

    # TODO: This probably won't be needed and a Block will only be created when there are enough transactions
    def add_transaction(self, t: Transaction) -> bool:
        if len(self.transactions) >= Block.CAPACITY:
            return False
        # TODO: Check that there is no inter-dependence? (to facilitate the new block use-case)
        self.transactions.append(t)
        return True

    def finalize(self) -> int:
        """
        Mine the block

        Spawns a miner process responsible for mining the block, broadcasting it
        upon success as well as storing it in redis. The difficulty is passed as
        the first command line argument and the (partial) block is fed to the
        standard input, JSON-serialized with dumps().

        :returns: the pid of the spawned process
        """
        python = sys.executable if sys.executable else 'python3'
        p = subprocess.Popen(args=[python, 'miner.py', str(Block.DIFFICULTY)],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        p.stdin.write(self.dumps())
        p.stdin.close()
        return p.pid

    def _partial_hash(self):   # TODO OPT: annotate this (what's the type of hashlib.sha256()?)
        """Return a hash object updated with the fixed part of the block"""
        h = hashlib.sha256()
        h.update(uitob(self.index))
        h.update(self.previous_hash)
        h.update(uitob(self.timestamp))
        for t in self.transactions:
            h.update(t.id)
        return h

    def hash(self) -> bytes:
        h = self._partial_hash()
        # NOTE: this will throw if the block hasn't been finalized
        h.update(uitob(self.nonce)) # type: ignore
        # TODO OPT: self.current_hash = digest?
        return h.digest()

    def _check_difficulty(self) -> bool:
        target = (1 << (256 - Block.DIFFICULTY)) - 1
        # NOTE: this will throw if the block hasn't been finalized
        return self.current_hash <= target.to_bytes(256 // 8, byteorder="big")  # type: ignore

    def verify(self) -> bool:
        # TODO OPT: Is there anything else to verify?
        if len(self.transactions) != Block.CAPACITY:
            return False
        if not all(t.verify() for t in self.transactions):
            return False
        if self.hash() != self.current_hash:
            return False
        if not self._check_difficulty():
            return False
        return True

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # NOTE: we can't easily have a proper binary encoding because
        # transactions don't have a fixed size bytes representation
        return self.dumps().encode()

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        """Dump to JSON-serializable object"""
        return {
            "index": self.index,
            "previous_hash": self.previous_hash.decode(),
            "timestamp": self.timestamp,
            "transactions": [t.dumpo() for t in self.transactions],
            "nonce": self.nonce,
            # NOTE: this will throw if the block hasn't been finalized
            "current_hash": self.current_hash.decode()  # type: ignore
        }

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo())

    @classmethod
    def loadb(cls, b: bytes) -> 'Block':
        """Load from bytes"""
        return cls.loads(b.decode())

    @classmethod
    def loado(cls, o: typing.Mapping[str, typing.Any]) -> 'Block':
        """Load from JSON-serializable object"""
        return cls(index=o["index"],
                   previous_hash=o["previous_hash"].encode(),
                   timestamp=o["timestamp"],
                   transactions=[Transaction.loado(t) for t in o["transactions"]],
                   nonce=o["nonce"],
                   current_hash=o["current_hash"].encode())

    @classmethod
    def loads(cls, s: str) -> 'Block':
        """Load from string"""
        return cls.loado(util.loads(s))
