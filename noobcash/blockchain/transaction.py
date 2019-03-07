import typing
import hashlib
import wallet
import util
from util import uitob, dtob


# TODO: wallet.PublicKey instead of bytes for sender and recipient?


class TransactionOutput:

    def __init__(self, index: int, recipient: bytes, amount: float) -> None:
        self.index = index
        self.recipient = recipient
        self.amount = amount

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

    def __init__(self, transaction_id: bytes, prev_out: TransactionOutput):
        self.transaction_id = transaction_id
        self.prev_out = prev_out

    def dumpb(self) -> bytes:
        """Dump to bytes"""
        # TODO OPT: this could have a proper binary encoding
        return self.dumps().encode()

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        """Dump to JSON-serializable object"""
        return {
            "transaction_id": self.transaction_id,
            "index": self.prev_out.index
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
        # TODO: ask the blockchain for the prev_out
        pass

    @classmethod
    def loads(cls, s: str) -> 'TransactionInput':
        """Load from string"""
        return cls.loado(util.loads(s))


class Transaction:
    # TODO: how is equality defined?

    def __init__(self,
                 recipient: bytes,
                 amount: float,
                 inputs: typing.Sequence[TransactionInput],
                 sender: typing.Optional[bytes] = None,
                 outputs: typing.Optional[typing.Sequence[TransactionOutput]] = None,
                 id_: typing.Optional[bytes] = None,
                 signature: typing.Optional[bytes] = None):
        """
        Create a new transaction to send coins.

        Either specify all of outputs, id_ and signature or none of them to
        determine them from the the rest of the arguments (eg, when creating
        a new transaction).
        """
        self.sender = wallet.get_public_key().dumpb() if sender is None else sender
        self.recipient = recipient  # TODO OPT: is this necessary?
        self.amount = amount    # TODO OPT: is this necessary?
        self.inputs = inputs

        # TODO OPT: implement basic assertions like input_amount >= amount and
        # that the sender is the previous recipient? Only as a sanity check,
        # these are the blockchain's responsibility.
        if outputs is not None:
            self.outputs = outputs
        else:
            input_amount = sum(t.prev_out.amount for t in inputs)
            self.outputs = [
                TransactionOutput(0, self.recipient, amount),
                TransactionOutput(1, self.sender, input_amount - amount)
            ]

        self.id = self.hash() if id_ is None else id_

        if signature is not None:
            self.signature = signature
        else:
            self.signature = wallet.sign(self.id)

    def verify(self) -> bool:
        if self.hash() != self.id:
            return False
        key = wallet.PublicKey.loadb(self.sender)
        return key.verify(self.id, self.signature)

    def hash(self) -> bytes:
        h = hashlib.sha256()
        h.update(self.sender)
        h.update(self.recipient)
        h.update(dtob(self.amount))
        for i in self.inputs:
            h.update(i.transaction_id)
            h.update(uitob(i.prev_out.index))
        for o in self.outputs:
            h.update(uitob(o.index))
            h.update(o.recipient)
            h.update(dtob(o.amount))

        return h.digest()

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
                   outputs=[TransactionOutput.loado(o_) for o_ in o["outputs"]],
                   id_=o["id"].encode(),
                   signature=o["signature"].encode())

    @classmethod
    def loads(cls, s: str) -> 'Transaction':
        """Load from string"""
        return cls.loado(util.loads(s))
