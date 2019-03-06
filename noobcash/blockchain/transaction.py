import typing
import struct
import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import Hash, SHA256
import wallet
from util import uitob, dtob


# TODO: wallet.PublicKey instead of bytes for sender and recipient?


class TransactionOutput:
    _struct = struct.Struct("!I ")
    def __init__(self, index: int, recipient: bytes, amount: float) -> None:
        self.index = index
        self.recipient = recipient
        self.amount = amount

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        return {
            "index": self.index,
            "recipient": self.recipient.decode(),
            "amount": self.amount
        }

    def dumps(self) -> str:
        return json.dumps(self.dumpo())

    @staticmethod
    def loado(o: typing.Mapping[str, typing.Any]) -> 'TransactionOutput':
        return TransactionOutput(index=o["index"],
                                 recipient=o["recipient"].encode(),
                                 amount=o["amount"])

    @staticmethod
    def loads(s: str) -> 'TransactionOutput':
        o = json.loads(s)
        return TransactionOutput.loado(o)


class TransactionInput:
    def __init__(self, transaction_id: bytes, prev_out: TransactionOutput):
        self.transaction_id = transaction_id
        self.prev_out = prev_out

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
        return {
            "transaction_id": self.transaction_id,
            "index": self.prev_out.index
        }

    def dumps(self) -> str:
        return json.dumps(self.dumpo())

    @staticmethod
    def loado(o: typing.Mapping[str, typing.Any]) -> 'TransactionInput':
        # TODO: ask the blockchain for the prev_out
        pass

    @staticmethod
    def loads(s: str) -> 'TransactionInput':
        return TransactionInput.loado(json.loads(s))


class Transaction:
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
        if sender is not None:
            self.sender = sender
        else:
            self.sender = wallet.get_public_key().dumpb()
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

        if id_ is not None:
            self.id = id_
        else:
            digest = Hash(SHA256(), default_backend())
            digest.update(self.sender)
            digest.update(self.recipient)
            digest.update(dtob(self.amount))
            for i in self.inputs:
                digest.update(i.transaction_id)
                digest.update(uitob(i.prev_out.index))
            for o in self.outputs:
                digest.update(uitob(o.index))
                digest.update(o.recipient)
                digest.update(dtob(o.amount))
            self.id = digest.finalize()

        if signature is not None:
            self.signature = signature
        else:
            self.signature = wallet.sign(self.id)

    def verify(self) -> bool:
        key = wallet.PublicKey.loadb(self.sender)
        return key.verify(self.id, self.signature)

    def dumpo(self) -> typing.Mapping[str, typing.Any]:
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
        return json.dumps(self.dumpo())

    @staticmethod
    def loado(o: typing.Mapping[str, typing.Any]) -> 'Transaction':
        return Transaction(sender=o["sender"].encode(),
                           recipient=o["recipient"].encode(),
                           amount=o["amount"],
                           inputs=[TransactionInput.loado(i) for i in o["inputs"]],
                           outputs=[TransactionOutput.loado(o_) for o_ in o["outputs"]],
                           id_=o["id"].encode(),
                           signature=o["signature"].encode())

    @staticmethod
    def loads(s: str) -> 'Transaction':
        return Transaction.loado(json.loads(s))
