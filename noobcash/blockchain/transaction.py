import typing
import hashlib
from noobcash.blockchain import util, wallet
from noobcash.blockchain.util import uitob, dtob


class TransactionOutput:

    def __init__(self, index: int, recipient: bytes, amount: float) -> None:
        # TODO OPT: Check that amount >= 0?
        index = int(index)
        if not (isinstance(recipient, bytes) and \
                (index in (0, 1))):
            raise TypeError
        self.index = index
        self.recipient = recipient
        self.amount = float(amount)

    # NOTE: We don't define __eq__() (and __hash__()) because it would require
    # knowledge of the transaction of origin, which we currently don't store
    # locally.

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # NOTE: we can't easily have a proper binary encoding because the keys
        # (addresses) don't have a fixed size bytes representation
        return self.dumps().encode()

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        """Dump to JSON-serializable object"""
        return {
            "index": self.index,
            "recipient": self.recipient.decode(),
            "amount": self.amount
        }

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo())

    @classmethod
    def loadb(cls, b: bytes) -> 'TransactionOutput':
        """Load from bytes"""
        return cls.loads(b.decode())

    @classmethod
    def loado(cls, o: typing.Mapping[str, typing.Any]) -> 'TransactionOutput':
        """Load from JSON-serializable object"""
        return cls(index=o["index"],
                   recipient=o["recipient"].encode(),
                   amount=o["amount"])

    @classmethod
    def loads(cls, s: str) -> 'TransactionOutput':
        """Load from string"""
        return cls.loado(util.loads(s))


class TransactionInput:

    def __init__(self, transaction_id: bytes, index: int):
        # TODO OPT: Check that len(transaction_id) == 256 // 8?
        index = int(index)
        if not (isinstance(transaction_id, bytes) and \
                (index in (0, 1))):
            raise TypeError
        self.transaction_id = transaction_id    # the id of the feeding transaction
        self.index = index

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionInput):
            return False
        return other.transaction_id == self.transaction_id and \
               other.index == self.index

    def __hash__(self) -> int:
        return int.from_bytes(self.dumpb(), byteorder="big")

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # TODO OPT: this could have a proper binary encoding
        return self.dumps().encode()

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        """Dump to JSON-serializable object"""
        return {
            "transaction_id": self.transaction_id,
            "index": self.index
        }

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo())

    @classmethod
    def loadb(cls, b: bytes) -> 'TransactionInput':
        """Load from bytes"""
        return cls.loads(b.decode())

    @classmethod
    def loado(cls, o: typing.Mapping[str, typing.Any]) -> 'TransactionInput':
        """Load from JSON-serializable object"""
        return TransactionInput(o["transaction_id"].encode(),
                                o["index"])

    @classmethod
    def loads(cls, s: str) -> 'TransactionInput':
        """Load from string"""
        return cls.loado(util.loads(s))


class Transaction:

    def __init__(self,
                 recipient: bytes,
                 amount: float,
                 inputs: typing.Sequence[TransactionInput],
                 input_amount: typing.Optional[float] = None,
                 sender: typing.Optional[bytes] = None,
                 outputs: typing.Optional[typing.Sequence[TransactionOutput]] = None,
                 id_: typing.Optional[bytes] = None,
                 signature: typing.Optional[bytes] = None) -> None:
        """
        Create a new transaction to send coins.

        There are 2 use cases:
        - Creating a new transaction to send some coins: input_amount should be
        specified and equal the sum of the amounts of the outputs referenced by
        inputs. All other optional arguments should not be specified.
        - Creating a Transaction for an existing transaction (eg deserializing):
        sender, outputs, id_ and signature should be specified (input_amount is
        ignored).
        """
        if not (isinstance(recipient, bytes) and \
                isinstance(inputs, list) and \
                all(isinstance(i, TransactionInput) for i in inputs)):
            raise TypeError
        self.recipient = recipient  # TODO OPT: is this necessary?
        self.amount = float(amount) # TODO OPT: is this necessary?
        self.inputs = inputs

        if sender is None and outputs is None and id_ is None and signature is None:
            self.sender = wallet.get_public_key().dumpb()
            self.outputs = [
                TransactionOutput(0, self.recipient, self.amount),
                TransactionOutput(1, self.sender, float(input_amount) - self.amount)
            ]
            self.id = self.hash()
            self.signature = wallet.sign(self.id)
        else:
            if not (isinstance(sender, bytes) and \
                    isinstance(outputs, list) and \
                    all(isinstance(o, TransactionOutput) for o in outputs) and \
                    isinstance(id_, bytes) and \
                    isinstance(signature, bytes)):
                raise TypeError
            self.sender = sender
            self.outputs = outputs
            self.id = id_
            self.signature = signature

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return int.from_bytes(self.id, byteorder="big")

    def hash(self) -> bytes:
        # NOTE: this is necessary because:
        # - __hash__() must return an int
        # - hash() truncates the value returned from __hash__()
        h = hashlib.sha256()
        h.update(self.sender)
        h.update(self.recipient)
        h.update(dtob(self.amount))
        for i in self.inputs:
            h.update(i.transaction_id)
            h.update(uitob(i.index))
        for o in self.outputs:
            h.update(uitob(o.index))
            h.update(o.recipient)
            h.update(dtob(o.amount))

        return h.digest()

    @staticmethod
    def genesis() -> 'Transaction':
        recipient = wallet.get_public_key(0).dumpb()
        amount = 100 * util.get_nodes()
        gt = Transaction(recipient=recipient,
                         amount=amount,
                         inputs=[TransactionInput(b"0", 0)],
                         input_amount=amount)
        gt.sender = b"0"
        gt.outputs = [
            TransactionOutput(0, recipient, amount),
            TransactionOutput(1, b"0", 0)
        ]
        gt.id = gt.hash()
        gt.signature = b"0"
        return gt

    def is_genesis(self) -> bool:
        recipient = wallet.get_public_key(0).dumpb()
        if self.recipient != recipient:
            return False
        amount = 100 * util.get_nodes()
        if self.amount != amount:
            return False
        if self.inputs != [TransactionInput(b"0", 0)]:
            return False
        if self.sender != b"0":
            return False
        if len(self.outputs) != 2:
            return False
        out0 = self.outputs[0]
        if not (out0.index == 0 and \
                out0.recipient == recipient and \
                out0.amount == amount):
            return False
        out1 = self.outputs[1]
        if not (out1.index == 1 and \
                out1.recipient == b"0" and \
                out1.amount == 0):
            return False
        if self.id != self.hash():
            return False
        if self.signature != b"0":
            return False

        return True

    def verify(self) -> bool:
        # TODO OPT: Need to check anything else?
        if self.is_genesis():
            return True
        # # of inputs > 0
        if not self.inputs:
            return False
        # # of outputs == 2
        if len(self.outputs) != 2:
            return False
        # outputs[i].index == i for i = 0, 1
        if not all(o.index == i for i, o in enumerate(self.outputs)):
            return False
        # all amounts >= 0
        if not (self.amount < 0 and all(o.amount >= 0 for o in self.outputs)):
            return False
        # amount = outputs[0].amount
        if self.amount != self.outputs[0].amount:
            return False
        # hash check
        if self.hash() != self.id:
            return False
        # signature check
        key = wallet.PublicKey.loadb(self.sender)
        if not key.verify(self.id, self.signature):
            return False

        return True

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # NOTE: we can't easily have a proper binary encoding because the keys
        # (addresses) don't have a fixed size bytes representation
        return self.dumps().encode()

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        """Dump to JSON-serializable object"""
        return {
            "sender": self.sender.decode(),
            "recipient": self.recipient.decode(),
            "amount": self.amount,
            "inputs": [i.dumpo() for i in self.inputs],
            "outputs": [o.dumpo() for o in self.outputs],
            "id": self.id.decode(),
            "signature": self.signature.decode()
        }

    def dumps(self) -> str:
        """Dump to string"""
        return util.dumps(self.dumpo())

    @classmethod
    def loadb(cls, b: bytes) -> 'Transaction':
        """Load from bytes"""
        return cls.loads(b.decode())

    @classmethod
    def loado(cls, o: typing.Mapping[str, typing.Any]) -> 'Transaction':
        """Load from JSON-serializable object"""
        return cls(sender=o["sender"].encode(),
                   recipient=o["recipient"].encode(),
                   amount=o["amount"],
                   inputs=[TransactionInput.loado(i) for i in o["inputs"]],
                   outputs=[TransactionOutput.loado(out) for out in o["outputs"]],
                   id_=o["id"].encode(),
                   signature=o["signature"].encode())

    @classmethod
    def loads(cls, s: str) -> 'Transaction':
        """Load from string"""
        return cls.loado(util.loads(s))
