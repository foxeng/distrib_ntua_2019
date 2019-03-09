import typing
from . import wallet
from .block import Block
from .transaction import Transaction, TransactionOutput
from . import util


# Storage
# - Pending transactions (pool)     blockchain:pending_tx       map [TODO] -> [Transaction]
# - Orphan transactions (pool)      blockchain:orphan_tx        map [TODO] -> [Transaction]
# - Last block                      blockchain:last_block       block_id: bytes
# - Blocks (tree)                   blockchain:blocks           map [block_id: bytes] -> [Block]
# - Orphan blocks (pool)            blockchain:orphan_blocks    map [TODO] -> [Block]
# - UTXOs (pool per node)           blockchain:utxo             map [transaction_id:index: bytes:int] -> [TransactionOutput]

# TODO: Do we ever need to descend the chain from the top?


def get_utxo(transaction_id: bytes, index: int) -> typing.Optional[TransactionOutput]:
    """
    Return TransactionOutput from transaction transaction_id with the specified
    index if it is unspent, else None.
    """
    r = util.get_db()
    outb = r.hget("blockchain:utxo", transaction_id + str(index).encode())
    return TransactionOutput.loadb(outb)


def get_block(block_id: typing.Optional[bytes] = None) -> typing.Optional[Block]:
    """If block_id is None, return the last block in the chain"""
    # TODO OPT: Only look for blocks on the main branch?
    r = util.get_db()
    if block_id is None:
        block_id = r.get("blockchain:last_block")
    blockb = r.hget("blockchain:blocks", block_id)
    return Block.loadb(blockb)


def get_balance(node_id: typing.Optional[int] = None) -> float:
    """If node_id is None, return current node's balance"""
    key = wallet.get_public_key(node_id).dumpb()
    r = util.get_db()
    balance = 0.0
    for _, outb in r.hscan_iter("blockchain:utxo"):
        out = TransactionOutput.loadb(outb)
        if out.recipient == key:
            balance += out.amount
    return balance


def new_recv_transaction(t: Transaction):   # TODO: Return value
    # TODO
    raise NotImplementedError


def new_recv_block(b: Block):   # TODO: Return value
    # TODO
    raise NotImplementedError
