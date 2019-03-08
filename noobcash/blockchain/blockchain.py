import typing
from block import Block
from transaction import Transaction, TransactionOutput


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
    # TODO:
    # - query blockchain:utxo for transaction_id:index
    raise NotImplementedError


def get_block(block_id: typing.Optional[bytes] = None) -> typing.Optional[Block]:
    """If block_id is None, return the last block in the chain"""
    # TODO: Only look for blocks on the main chain?
    raise NotImplementedError


def get_balance(node_id: typing.Optional[int] = None) -> float:
    """If node_id is None, return current node's balance"""
    # TODO:
    # - sum o.amount for o in blockchain:utxo where o.recipient == pubkeys[node_id]
    raise NotImplementedError


def new_recv_transaction(t: Transaction):   # TODO: Return value
    # TODO
    raise NotImplementedError


def new_recv_block(b: Block):   # TODO: Return value
    # TODO
    raise NotImplementedError
