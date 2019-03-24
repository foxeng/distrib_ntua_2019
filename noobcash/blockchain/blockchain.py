from typing import Set, Dict, List, Optional, Mapping, Tuple
import logging
import time
import os
import signal
from noobcash.blockchain import wallet, block, util
from noobcash.blockchain.block import Block
from noobcash.blockchain.transaction import Transaction, TransactionInput, TransactionOutput
from noobcash.chatter import chatter


# Storage
# - Blocks (tree)
#       key: blockchain:blocks
#       value: map [current_hash: bytes] -> [Block]
#       locking: yes
# - Last block
#       key: blockchain:last_block
#       value: block_id: bytes
#       locking: yes
# - Main branch
#       key: blockchain:main_branch
#       value: set [current_hash: bytes]
#       locking: yes
# - Miner PID
#       key: blockchain:miner_pid
#       value: miner_pid: int
#       locking: yes
# - Orphan blocks (pool)
#       key: blockchain:orphan_blocks:<prev_block_id>
#       value: set [Block]
#       locking: yes (a single lock for the whole pool)
# - Transaction pool
#       key: blockchain:tx_pool
#       value: map [transaction_id: Transaction] -> [Transaction]
#       locking: yes
# - UTXO-block (block accuracy)
#       key: blockchain:utxo-block:<block_id>
#       value: map [input: TransactionInput] -> [TransactionOutput]
#       locking: yes (a single lock for all the blocks)
# - UTXO-transaction (transaction accuracy)
#       key: blockchain:utxo-tx
#       value: map [input: TransactionInput] -> [TransactionOutput]
#       locking: yes

# NOTE: Locks should always be acquired in the order specified above (it's
# alphabetical) to avoid deadlocks
# NOTE: We don't store orphan transactions (we reject them instead). They are
# not strictly necessary: a transaction is orphan if it reaches us before one it
# depends on. If at least one node receives the two in the right order, they
# will end up in its pool and eventually in the chain. If all the nodes reject
# the would-be-orphan, it's as if it never happened and the client can retry it
# after a while. There shouldn't be any problem in our scale.


# TODO OPT: In need of a big refactor
# TODO OPT: Wrap calls to redis. Having redis keys as strings all over the place
# is looking for trouble (especially since redis won't complain for a
# non-existent key with most of the commands)
# TODO OPT: Optimize (eg start with minimizing the calls to redis)
# TODO OPT: Define custom exceptions and use them
# TODO OPT: Get rid of the locks. Look into redis transactions or redis EVAL


def initialize(nodes: int, node_id: int, capacity: int, difficulty: int) -> None:
    # NOTE: Totally undefined behaviour if called more than once (all hell
    # breaks loose)
    # TODO OPT: Somehow check if initialization has already happened? But how to
    # separate initialization between different runs of the application?
    # TODO OPT: Need to do anything else?
    log_fmt = "[%(levelname)s] %(relativeCreated)d %(module)s:%(funcName)s:%(lineno)d: %(message)s"
    logging.basicConfig(filename=os.path.dirname(__file__) + "/blockchain.log",
                        filemode="w",           # overwrite last log
                        format=log_fmt,
                        level=logging.DEBUG)    # log messages of all levels

    r = util.get_db()
    r.flushdb()

    logging.debug("Initializing with %d nodes, node id %d, capacity %d, difficulty %d",
                  nodes,
                  node_id,
                  capacity,
                  difficulty)
    util.set_nodes(nodes)
    wallet.generate_wallet(node_id)
    if node_id == 0:
        _generate_genesis()
    block.set_capacity(capacity)
    block.set_difficulty(difficulty)


def _generate_genesis() -> None:
    """Generate the genesis block and initialize the chain with it"""
    logging.debug("Generating the genesis block")
    new_recv_block(Block.genesis())


def get_block(block_id: Optional[bytes] = None) -> Optional[Block]:
    """If block_id is None, return the last block in the chain,
    This doesn't use any locks"""
    if block_id is not None and not isinstance(block_id, bytes):
        raise TypeError
    if block_id is None:
        logging.debug("Last block requested")
    else:
        logging.debug("Block %s requested", util.bintos(block_id))

    r = util.get_db()
    if block_id is None:
        block_id = r.get("blockchain:last_block")
        if block_id is None:
            # The blockchain is empty
            logging.debug("Blockchain is empty")
            return None

    blockb = r.hget("blockchain:blocks", block_id)
    if blockb is None:
        # Requested block not found
        logging.debug("Block %s not found", util.bintos(block_id))
        return None

    logging.debug("Block %s retrieved", util.bintos(block_id))
    return Block.loadb(blockb)


def get_balance(node_id: Optional[int] = None) -> float:
    """If node_id is None, return current node's balance"""
    logging.debug("Balance requested for node %s", "local" if node_id is None else str(node_id))
    keyb = wallet.get_public_key(node_id).dumpb()
    r = util.get_db()
    with r.lock("blockchain:utxo-tx:lock"):
        utxo_tx = r.hvals("blockchain:utxo-tx")

    balance = 0.0
    for outb in utxo_tx:
        out = TransactionOutput.loadb(outb)
        if out.recipient == keyb:
            balance += out.amount
    logging.debug("Balance of node %s: %f", "local" if node_id is None else str(node_id), balance)
    return balance


def dump(mute: bool = False) -> List[Block]:
    """Broadcast every block in the main branch (if mute is False). Also return
    a list with these blocks (regardless of mute)."""
    logging.debug("Dump requested")
    chain: List[Block] = []
    # NOTE: No need to lock the blocks because once a block is validated, it is
    # never deleted and all the blocks in the main branch are validated
    b = get_block()
    while b is not None:
        chain.append(b)
        b = get_block(b.previous_hash)
    chain.reverse()

    if not mute:
        logging.debug("Broadcasting blocks")
        for b in chain:
            chatter.broadcast_block(b, util.get_peer_ids())

    logging.debug("%d blocks in the chain", len(chain))
    return chain


def generate_transaction(recipient_id: int, amount: float, mute: bool = False) -> bool:
    """If possible (there are enough UTXOs) generate a new transaction giving
    amount NBC to recipient and the change back to us. If mute is True don't
    broadcast it."""
    logging.debug("Transaction requested: %f NBC to node %d", amount, recipient_id)
    sender = wallet.get_public_key().dumpb()
    recipient = wallet.get_public_key(recipient_id).dumpb()
    r = util.get_db()
    inputs: List[TransactionInput] = []
    input_amount = 0.0
    with r.lock("blockchain:tx_pool:lock"), \
         r.lock("blockchain:utxo-tx:lock"):
        for ib, ob in r.hgetall("blockchain:utxo-tx").items():
            o = TransactionOutput.loadb(ob)
            if o.recipient == sender:
                inputs.append(TransactionInput.loadb(ib))
                input_amount += o.amount
                if input_amount >= amount:
                    t = Transaction(recipient=recipient,
                                    amount=amount,
                                    inputs=inputs,
                                    input_amount=input_amount)
                    # Add to transaction pool
                    r.hset("blockchain:tx_pool", t.id, t.dumpb())
                    # "Add to wallet if mine"
                    r.hdel("blockchain:utxo-tx", *(i.dumpb() for i in t.inputs))
                    r.hmset("blockchain:utxo-tx", {TransactionInput(t.id, o.index).dumpb(): \
                                                       o.dumpb() for o in t.outputs})
                    break
        else:
            # Not enough UTXOs
            logging.error("Cannot send %f NBC to node %d (not enough coins)", amount, recipient_id)
            return False

    logging.debug("Generated transaction %s", util.bintos(t.id))
    _check_for_new_block()
    if not mute:
        logging.debug("Broadcasting transaction %s", util.bintos(t.id))
        chatter.broadcast_transaction(t, util.get_peer_ids())
    return True


def _check_for_new_block() -> None:
    """Check if there are at least CAPACITY transactions that can go in a new
    block (ie transactions in the pool with all their inputs in
    UTXO-block[last_block]. If so, start mining a new block.
    Should be called with no locks held."""
    logging.debug("Checking for new block")
    CAPACITY = block.get_capacity()

    r = util.get_db()
    with r.lock("blockchain:last_block:lock"), \
         r.lock("blockchain:miner_pid:lock"), \
         r.lock("blockchain:tx_pool:lock"), \
         r.lock("blockchain:utxo-block:lock"):
        # NOTE: If a miner is running, we expect it to add a new block, so we
        # abort. If mining succeeds, this function will be called again by
        # new_recv_block(). If it fails (another valid block is received) this
        # will again be called by new_recv_block()
        miner_pidb = r.get("blockchain:miner_pid")
        if miner_pidb is not None:
            logging.debug("Miner already running with PID %d", util.btoui(miner_pidb))
            return

        tx_pool = {Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")}
        if len(tx_pool) < CAPACITY:
            logging.debug("Cannot create new block yet (not enough transactions)")
            return

        last_block = get_block()
        utxo_block = {TransactionInput.loadb(i): TransactionOutput.loadb(o) for i, o \
            in r.hgetall("blockchain:utxo-block:".encode() + last_block.current_hash).items()}
        new_block_tx: List[Transaction] = []
        # NOTE: Since there are >= CAPACITY transactions in the pool, and we
        # don't mind transaction inter-dependence in the same block, a new
        # block can be created, so this loop will terminate
        while True:
            for t in tx_pool:
                # Search for t.inputs in UTXO-block[last_block] as well as in new_block_tx
                if all(i in utxo_block or \
                       any(nt.id == i.transaction_id for nt in new_block_tx) for i in t.inputs):
                    new_block_tx.append(t)
                    if len(new_block_tx) == CAPACITY:
                        new_block = Block(index=last_block.index + 1,
                                          previous_hash=last_block.current_hash,
                                          transactions=new_block_tx)
                        # NOTE: We don't delete the new block_tx from the pool, because
                        # mining might fail. They will be deleted eventually when they
                        # enter the main branch.
                        miner_pid = new_block.finalize()
                        r.set("blockchain:miner_pid", util.uitob(miner_pid))
                        logging.debug("Miner started with PID %d", miner_pid)
                        return
            tx_pool.difference_update(new_block_tx)


def _set_last_block_unlocked(r, last_block: Block) -> None:
    """Should be called with the last_block lock held. Takes care of locking
    (and unlocking) the miner_pid lock"""
    logging.debug("Setting last block to %s", util.bintos(last_block.current_hash))
    r.set("blockchain:last_block", last_block.current_hash)

    # Check if we were mining. If so, kill the miner
    with r.lock("blockchain:miner_pid:lock"):
        miner_pidb = r.get("blockchain:miner_pid")
        if miner_pidb is not None:
            miner_pid = util.btoui(miner_pidb)
            os.kill(miner_pid, signal.SIGTERM)
            r.delete("blockchain:miner_pid")
            logging.debug("Killed the miner with PID %d", miner_pid)


def new_recv_transaction(t: Transaction) -> bool:
    logging.debug("Received transaction %s", util.bintos(t.id))
    if not t.verify():
        logging.debug("Transaction %s rejected (failed verification)", util.bintos(t.id))
        return False

    r = util.get_db()
    # OK 8  Reject if we already have matching tx in the pool, or in a block in the main branch
    referenced_txos = [i.dumpb() for i in t.inputs] # not empty because t.inputs != []
    with r.lock("blockchain:tx_pool:lock"), \
         r.lock("blockchain:utxo-tx:lock"):
        # NOTE: When receiving a new transaction, both queries and updates are
        # done against UTXO-transaction
        prev_outb = r.hmget("blockchain:utxo-tx", *referenced_txos)
        if any(i is None for i in prev_outb):
            logging.debug("Transaction %s rejected (UTXO not found)", util.bintos(t.id))
            return False
        prev_outputs = [TransactionOutput.loadb(outb) for outb in prev_outb]

        # OK 14 Reject if the sum of input values < sum of output values
        input_amount = sum(i.amount for i in prev_outputs)
        output_amount = sum(o.amount for o in t.outputs)
        if input_amount != output_amount:
            logging.debug("Transaction %s rejected (input amount != output amount)",
                          util.bintos(t.id))
            return False

        # OK 16 Verify the scriptPubKey accepts for each input; reject if any are bad
        if any(o.recipient != t.sender for o in prev_outputs):
            logging.debug("Transaction %s rejected (spending another's UTXO)", util.bintos(t.id))
            return False

        # OK 17 Add to transaction pool[7]
        r.hset("blockchain:tx_pool", t.id, t.dumpb())

        # OK 18 "Add to wallet if mine"
        r.hdel("blockchain:utxo-tx", *referenced_txos)
        # NOTE: Not empty because t.outputs != []
        new_utxos = {TransactionInput(t.id, o.index).dumpb(): o.dumpb() for o in t.outputs}
        r.hmset("blockchain:utxo-tx", new_utxos)

    logging.debug("Transaction %s accepted", util.bintos(t.id))
    _check_for_new_block()
    return True


def _validate_block_unlocked(r, b: Block) -> Optional[Tuple[Set[bytes], Dict[bytes, bytes]]]:
    """Should be called with the utxo-block lock held"""
    referenced_txos: Set[bytes] = set()  # the utxos from UTXO-block spent in block
    new_utxos: Dict[bytes, bytes] = {}
    for t in b.transactions:
        input_amount = 0.0
        for i in t.inputs:
            # Search for i in UTXO-block
            ib = i.dumpb()
            ob = r.hget("blockchain:utxo-block:".encode() + b.previous_hash, ib)
            if ob is None:
                # Not found in UTXO-block, search in new_utxos
                ob = new_utxos.get(ib)
                if ob is None:
                    logging.debug("Block %s rejected (UTXO not found)", util.bintos(b.current_hash))
                    return None
                del new_utxos[ib]
            else:
                # Avoid double-spending of a utxo from UTXO-block in the block
                if ib in referenced_txos:
                    logging.debug("Block %s rejected (double spending in the block)",
                                  util.bintos(b.current_hash))
                    return None
                referenced_txos.add(ib)
            o = TransactionOutput.loadb(ob)

            if o.recipient != t.sender:
                logging.debug("Block %s rejected (spending another's UTXO)",
                              util.bintos(b.current_hash))
                return None
            input_amount += o.amount

        if input_amount != sum(o.amount for o in t.outputs):
            logging.debug("Block %s rejected (input amount != output amount)",
                          util.bintos(b.current_hash))
            return None

        new_utxos.update({TransactionInput(t.id, o.index).dumpb(): o.dumpb() \
                for o in t.outputs})

    return (referenced_txos, new_utxos)


def _create_utxo_block_unlocked(r,
                                curr_block: Block,
                                referenced_txos: Set[bytes],
                                new_utxos: Mapping[bytes, bytes]) -> None:
    """Create utxo-block for block b as a copy of utxo-block of its previous
    block, with referenced_txos removed and new_utxos added. Should be called
    with the utxo-block lock held. referenced_txos and new_utxos should not be
    empty."""
    utxo_prev_block = r.dump("blockchain:utxo-block:".encode() + curr_block.previous_hash)
    r.restore(name="blockchain:utxo-block:".encode() + curr_block.current_hash,
              ttl=0,
              value=utxo_prev_block,
              replace=True)
    r.hdel("blockchain:utxo-block:".encode() + curr_block.current_hash, *referenced_txos)
    r.hmset("blockchain:utxo-block:".encode() + curr_block.current_hash, new_utxos)


def _rebuild_tx_pool_unlocked(r,
                              tx_pool: Mapping[bytes, Transaction],
                              b: Block) -> Dict[bytes, Transaction]:
    """Rebuild the tx_pool (ie keep only the valid transactions)
    using utxo-block of b to check for transaction validity. Return
    the updated transaction pool. Should be called with the
    utxo-block and tx_pool locks held."""
    utxo_block = {TransactionInput.loadb(i): TransactionOutput.loadb(o) for i, o \
        in r.hgetall("blockchain:utxo-block:".encode() + b.current_hash).items()}
    def is_unspent(txin: TransactionInput) -> bool:
        if txin in utxo_block:
            return True
        prev_tx = tx_pool.get(txin.transaction_id)
        if prev_tx is None:
            return False
        return all(is_unspent(i) for i in prev_tx.inputs)

    tx_to_remove: Set[Transaction] = set()
    for t in tx_pool.values():
        # A transaction is valid only if all its inputs are either in UTXO-block
        # or are outputs of other valid transactions in the pool
        if not all(is_unspent(i) for i in t.inputs):
            tx_to_remove.add(t)
    tx_pool = {tid: t for tid, t in tx_pool.items() if t not in tx_to_remove}
    if tx_to_remove:
        r.hdel("blockchain:tx_pool", *(t.id for t in tx_to_remove))

    return tx_pool


def _rebuild_utxo_tx_unlocked(r, b: Block, tx_pool: Mapping[bytes, Transaction]) -> None:
    """Reinitialize UTXO-tx as a copy of UTXO-block[b] and simulate adding all
    transactions in tx_pool. Should be called with the utxo-block and the
    utxo-tx locks held."""
    r.delete("blockchain:utxo-tx")
    utxo_tx = {TransactionInput.loadb(i): TransactionOutput.loadb(o) for i, o \
        in r.hgetall("blockchain:utxo-block:".encode() + b.current_hash).items()}
    while tx_pool:
        tx_to_remove: Set[Transaction] = set()
        for t in tx_pool.values():
            if all(i in utxo_tx for i in t.inputs):
                for i in t.inputs:
                    del utxo_tx[i]
                for o in t.outputs:
                    utxo_tx[TransactionInput(t.id, o.index)] = o
                tx_to_remove.add(t)
        tx_pool = {tid: t for tid, t in tx_pool.items() if t not in tx_to_remove}
    # NOTE: utxo_tx is not empty because UTXO-block[recv_block] is not empty
    r.hmset("blockchain:utxo-tx", {i.dumpb(): o.dumpb() for i, o in utxo_tx.items()})


def new_recv_block(recv_block: Block, sender_id: Optional[int] = None, mute: bool = False) -> bool:
    """Handle a received block. Based on the bitcoin protocol rules for block
    handling at https://en.bitcoin.it/wiki/Protocol_rules."""
    logging.debug("Received block %s", util.bintos(recv_block.current_hash))
    if not recv_block.verify():
        logging.debug("Block %s rejected (failed verification)",
                      util.bintos(recv_block.current_hash))
        return False

    r = util.get_db()
    with r.lock("blockchain:blocks:lock"), \
         r.lock("blockchain:last_block:lock"), \
         r.lock("blockchain:main_branch:lock"), \
         r.lock("blockchain:orphan_blocks:lock"), \
         r.lock("blockchain:tx_pool:lock"), \
         r.lock("blockchain:utxo-block:lock"), \
         r.lock("blockchain:utxo-tx:lock"):

        # NOTE: Comments like the one below are references to the bitcoin
        # protocol rules
        # OK 2  Reject if duplicate of block we have in any of the three categories
        if r.hexists("blockchain:blocks", recv_block.current_hash) or \
           r.sismember("blockchain:orphan_blocks:".encode() + recv_block.previous_hash,
                       recv_block.dumpb()):
            logging.debug("Block %s rejected (already exists)",
                          util.bintos(recv_block.current_hash))
            return False

        # Handle the genesis block
        if recv_block.is_genesis():
            r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
            t = recv_block.transactions[0]
            o = t.outputs[0]
            ib = TransactionInput(t.id, o.index).dumpb()
            ob = o.dumpb()
            r.hset("blockchain:utxo-block:".encode() + recv_block.current_hash, ib, ob)
            r.hset("blockchain:utxo-tx", ib, ob)
            r.sadd("blockchain:main_branch", recv_block.current_hash)
            _set_last_block_unlocked(r, recv_block)
            logging.debug("Genesis block accepted")
            return True

        # OK 11 Check if prev block (matching prev hash) is in main branch or side branches. If not,
        #       add this to orphan blocks, then query peer we got this from for 1st missing orphan
        #       block in prev chain; done with block
        prev_blockb = r.hget("blockchain:blocks", recv_block.previous_hash)
        if prev_blockb is None:
            logging.debug("Block %s is orphan", util.bintos(recv_block.current_hash))
            r.sadd("blockchain:orphan_blocks:".encode() + recv_block.previous_hash,
                   recv_block.dumpb())
            # TODO OPT: Unlock before requesting the block (it could take some time, although
            # the response is asynchronous of course
            if not mute:
                logging.debug("Requesting block %s", util.bintos(recv_block.previous_hash))
                # TODO OPT: Only ask the node we got this from, not everyone, to
                # avoid the flood of incoming blocks later
                chatter.get_blockid(recv_block.previous_hash,
                                    [sender_id] if sender_id is not None else util.get_peer_ids())
            return False

        prev_block = Block.loadb(prev_blockb)
        logging.debug("Previous block %s", util.bintos(prev_block.current_hash))
        if recv_block.index != prev_block.index + 1:
            logging.debug("Block %s rejected (wrong index)", util.bintos(recv_block.current_hash))
            return False

        # OK 15 Add block into the tree. There are three cases: 1. block further extends the main
        #       branch; 2. block extends a side branch but does not add enough difficulty to make
        #       it become the new main branch; 3. block extends a side branch and makes it the new
        #       main branch.
        last_block = get_block()
        if recv_block.previous_hash == last_block.current_hash:
            # OK Case 1 (b.previous_hash == last_block):
            logging.debug("Block %s extends the main branch", util.bintos(recv_block.current_hash))
            txos = _validate_block_unlocked(r, recv_block)
            if txos is None:
                return False
            referenced_txos, new_utxos = txos
            """
            # NOTE: This is the body of _validate_block_unlocked, annotated, for reference
            referenced_txos: Set[bytes] = set()  # the utxos from UTXO-block spent in recv_block
            new_utxos: Dict[bytes, bytes] = {}
            # OK 1  For all but the coinbase transaction, apply the following:
            for t in recv_block.transactions:
                # OK 1  For each input, look in the main branch to find the referenced output
                #       transaction. Reject if the output transaction is missing for any input.
                input_amount = 0.0
                for i in t.inputs:
                    # Search for i in UTXO-block
                    ib = i.dumpb()
                    ob = r.hget("blockchain:utxo-block:".encode() + recv_block.previous_hash, ib)
                    if ob is None:
                        # Not found in UTXO-block, search in new_utxos
                        ob = new_utxos.get(ib)
                        if ob is None:
                            return False
                        del new_utxos[ib]
                    else:
                        # Avoid double-spending of a utxo from UTXO-block in the block
                        if ib in referenced_txos:
                            return False
                        referenced_txos.add(ib)
                    o = TransactionOutput.loadb(ob)
                # OK 2  For each input, if we are using the nth output of the earlier transaction,
                #       but it has fewer than n+1 outputs, reject.
                # OK 4  Verify crypto signatures for each input; reject if any are bad
                    if o.recipient != t.sender:
                        return False
                # OK 5  For each input, if the referenced output has already been spent by a
                #       transaction in the main branch, reject
                # OK 7  Reject if the sum of input values < sum of output values
                    input_amount += o.amount
                if input_amount != sum(o.amount for o in t.outputs):
                    return False

                new_utxos.update({TransactionInput(t.id, o.index).dumpb(): o.dumpb() \
                        for o in t.outputs})
            """

            # OK 4  For each transaction, "Add to wallet if mine"
            # NOTE: referenced_txos and new_utxos are not empty since we got here
            _create_utxo_block_unlocked(r, recv_block, referenced_txos, new_utxos)

            # OK 5  For each transaction in the block, delete any matching transaction from the pool
            #       : of the transactions in the pool, keep only the ones that are valid using the
            #       new utxo-block to check for validity
            tx_pool = {t.id: t for t in \
                          [Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")]}
            # NOTE: There can't be double spending in the tx pool as it is now
            tx_pool = _rebuild_tx_pool_unlocked(r, tx_pool, recv_block)

            _rebuild_utxo_tx_unlocked(r, recv_block, tx_pool)

            # Add block to main branch
            r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
            r.sadd("blockchain:main_branch", recv_block.current_hash)

            _set_last_block_unlocked(r, recv_block)
            logging.debug("Block %s accepted", util.bintos(recv_block.current_hash))
        elif recv_block.index <= last_block.index:
            # OK Case 2 (b.previous_hash != last_block && b.index <= last_block.index)
            # : Add it without doing any validation because validating this now would require a lot
            # of work (actually simulating adding this to its prev as if extending the main branch).
            logging.debug("Block %s extends a side branch (not changing main)",
                          util.bintos(recv_block.current_hash))
            r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
        else:
            # OK Case 3 (b.previous_hash != last_block && b.index > last_block.index)
            # OK 1  Find the fork block on the main branch which this side branch forks off of
            #       : Ascend the side branch, the fork block is the first to be in the main branch
            logging.debug("Block %s extends a side branch (changing main)",
                          util.bintos(recv_block.current_hash))
            old_side_branch = [recv_block]    # the Blocks in the old side branch
            fork_block = Block.loadb(r.hget("blockchain:blocks", recv_block.previous_hash))
            while not r.sismember("blockchain:main_branch", fork_block.current_hash):
                old_side_branch.append(fork_block)
                fork_block = Block.loadb(r.hget("blockchain:blocks", fork_block.previous_hash))
            old_side_branch.reverse()   # starting from the child of the fork block
            # OK 2  Redefine the main branch to only go up to this fork block
            #       : Ascend from last_block up to the fork block
            old_main_branch: List[Block] = []    # the Blocks in the old main branch
            b = Block.loadb(r.hget("blockchain:blocks", last_block.current_hash))
            while b != fork_block:
                old_main_branch.append(b)
                b = Block.loadb(r.hget("blockchain:blocks", b.previous_hash))
            old_main_branch.reverse()   # starting from the child of the fork block
            logging.debug("Fork block %s", util.bintos(fork_block.current_hash))
            # OK 3  For each block on the side branch, from the child of the fork block to the leaf,
            #       add to the main branch:
            for osbi, b in enumerate(old_side_branch):
                # OK 1  Do "branch" checks 3-11
                #       : Why? we did them when first receiving the block. What could have changed?
                # OK 2  For all the transactions:
                txos = _validate_block_unlocked(r, b)
                if txos is None:
                    # Delete invalid blocks and abort
                    invalid_ids = [invalid.current_hash for invalid in old_side_branch[osbi:]]
                    r.hdel("blockchain:blocks", *invalid_ids)
                    return False
                referenced_txos, new_utxos = txos
                """
                # NOTE: This is the body of _validate_block_unlocked, annotated, for reference
                referenced_txos: Set[bytes] = set()  # the utxos from UTXO-block spent in b
                new_utxos: Dict[bytes, bytes] = {}
                for t in b.transactions:
                    # WP 1  For each input, look in the main branch to find the referenced output
                    #       transaction. Reject if the output transaction is missing for any input.
                    #       : Search for the referenced outputs in UTXO-block[previous_hash]
                    input_amount = 0.0
                    for i in t.inputs:
                        # Search for i in UTXO-block
                        ib = i.dumpb()
                        ob = r.hget("blockchain:utxo-block:".encode() + b.previous_hash, ib)
                        if ob is None:
                            # Not found in UTXO-block, search in new_utxos
                            ob = new_utxos.get(ib)
                            if ob is None:
                                # TODO: Undo any changes, delete invalid blocks and reject
                                raise NotImplementedError
                            del new_utxos[ib]
                        else:
                            # Avoid double-spending in the block
                            if ib in referenced_txos:
                                # TODO: Undo any changes, delete invalid blocks and reject
                                raise NotImplementedError
                            referenced_txos.add(ib)
                        o = TransactionOutput.loadb(ob)
                    # OK 2  For each input, if we are using the nth output of the earlier
                    #       transaction, but it has fewer than n+1 outputs, reject.
                    # WP 4  Verify crypto signatures for each input; reject if any are bad
                    #       : Check that t.sender == o.recipient for each utxo referenced
                        if o.recipient != t.sender:
                            # TODO: Undo any changes, delete invalid blocks and reject
                            raise NotImplementedError
                    # OK 5  For each input, if the referenced output has already been spent by a
                    #       transaction in the main branch, reject
                    # WP 7  Reject if the sum of input values < sum of output values
                    #       : Check that sum(inputs) == sum(outputs)
                        input_amount += o.amount
                    if input_amount != sum(o.amount for o in t.outputs):
                        # TODO: Undo any changes, delete invalid blocks and reject
                        raise NotImplementedError

                    new_utxos.update({TransactionInput(t.id, o.index).dumpb(): o.dumpb() for o \
                            in t.outputs})
                """

                # OK 5  For each transaction, "Add to wallet if mine"
                # NOTE: referenced_txos and new_utxos are not empty since we got here
                _create_utxo_block_unlocked(r, b, referenced_txos, new_utxos)

            # OK 5  For each block in the old main branch, from the leaf down to the child of the
            #       fork block:
            tx_pool = {t.id: t for t in \
                          [Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")]}
            for b in reversed(old_main_branch):
                # OK 1  For each non-coinbase transaction in the block:
                for t in b.transactions:
                    # OK 1  Apply "tx" checks 2-9, except in step 8, only look in the transaction
                    #       pool for duplicates, not the main branch
                    #       : Why? these have been checked already. There can't be double spending
                    #       transactions in the pool as it is at this point (current as of the old
                    #       main branch) + the old main branch, because they wouldn't have gotten
                    #       there in the first place.
                    # OK 2  Add to transaction pool if accepted, else go on to next transaction
                    tx_pool[t.id] = t

            # OK 6  For each block in the new main branch, from the child of the fork node to the
            #       leaf:
                # OK 1  For each transaction in the block, delete any matching transaction from the
                #       transaction pool
            #       : Of the transactions in the pool, keep only the ones that are valid using the
            #       new utxo-block to check for validity
            # NOTE: There can't be double spending in the tx pool as it is now,
            # because it consists of the tx in the previous tx pool and all the
            # tx in the old main branch, and all of these have already been
            # checked for double spending
            tx_pool = _rebuild_tx_pool_unlocked(r, tx_pool, recv_block)

            _rebuild_utxo_tx_unlocked(r, recv_block, tx_pool)

            # Update main_branch
            for b in old_main_branch:
                r.srem("blockchain:main_branch", b.current_hash)
            for b in old_side_branch:
                r.sadd("blockchain:main_branch", b.current_hash)

            r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
            _set_last_block_unlocked(r, recv_block)
            logging.debug("Block %s accepted", util.bintos(recv_block.current_hash))

        orphans = [Block.loadb(orphb) for orphb in \
                       r.smembers("blockchain:orphan_blocks:".encode() + recv_block.current_hash)]
        r.delete("blockchain:orphan_blocks:".encode() + recv_block.current_hash)

    logging.debug("Block acceptance time: %f", time.time() - recv_block.timestamp)

    # OK 19 For each orphan block for which this block is its prev, run all these steps (including
    #       this one) recursively on that orphan
    for orphan in orphans:
        new_recv_block(orphan)

    _check_for_new_block()
    return True
