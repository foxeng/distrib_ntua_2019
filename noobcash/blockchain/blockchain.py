import typing
import os
import signal
from noobcash.blockchain import wallet, block, util
from noobcash.blockchain.block import Block
from noobcash.blockchain.transaction import Transaction, TransactionInput, TransactionOutput


# Storage
# - Pending transactions (pool)             blockchain:tx_pool                          map [transaction_id: Transaction] -> [Transaction]
# - UTXO-block (block accuracy)             blockchain:utxo-block:<block_id>            map [input: TransactionInput] -> [TransactionOutput]
# - UTXO-transaction (transaction accuracy) blockchain:utxo-tx                          map [input: TransactionInput] -> [TransactionOutput]
# - Last block                              blockchain:last_block                       block_id: bytes
# - Miner PID                               blockchain:miner_pid                        miner_pid: int
# - Blocks (tree)                           blockchain:blocks                           map [current_hash: bytes] -> [Block]
# - Orphan blocks (pool)                    blockchain:orphan_blocks:<prev_block_id>    set [Block]
# - Main branch                             blockchain:main_branch                      set [current_hash: bytes]

# NOTE: We don't store orphan transactions (we reject them instead). They are
# not strictly necessary: a transaction is orphan if it reaches us before one it
# depends on. If at least one node receives the two in the right order, they
# will end up in its pool and eventually in the chain. If all the nodes reject
# the would-be-orphan, it's as if it never happened and the client can retry it
# after a while. There shouldn't be any problem in our scale.


# TODO: In terrible need of a refactor


def initialize(nodes: int, node_id: int, capacity: int, difficulty: int) -> None:
    # TODO OPT: Need to do anything else?
    r = util.get_db()
    r.flushdb()

    util.set_nodes(nodes)
    wallet.generate_wallet(node_id)
    if node_id == 0:
        generate_genesis()
    block.set_capacity(capacity)
    block.set_difficulty(difficulty)


def get_block(block_id: typing.Optional[bytes] = None) -> Block:
    """If block_id is None, return the last block in the chain"""
    r = util.get_db()
    if block_id is None:
        block_id = r.get("blockchain:last_block")
    blockb = r.hget("blockchain:blocks", block_id)
    return Block.loadb(blockb)


def get_balance(node_id: typing.Optional[int] = None) -> float:
    """If node_id is None, return current node's balance"""
    keyb = wallet.get_public_key(node_id).dumpb()
    r = util.get_db()
    balance = 0.0
    for outb in r.hvals("blockchain:utxo-tx"):
        out = TransactionOutput.loadb(outb)
        if out.recipient == keyb:
            balance += out.amount
    return balance


def generate_transaction(recipient_id: int, amount: float) -> bool:
    """If possible (there are enough UTXOs) generate a new transaction giving
    amount NBC to recipient and the change back to us"""
    sender = wallet.get_public_key().dumpb()
    recipient = wallet.get_public_key(recipient_id).dumpb()
    r = util.get_db()
    inputs: typing.List[TransactionInput] = []
    input_amount = 0.0
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
                r.hmset("blockchain:utxo-tx", {TransactionInput(t.id, o.index).dumpb(): o.dumpb() \
                        for o in t.outputs})
                _check_for_new_block()

                # TODO: Broadcast t
                return True

    return False


def generate_genesis() -> None:
    """Generate the genesis block and initialize the chain with it"""
    genesis = Block.genesis()
    r = util.get_db()
    r.hset("blockchain:blocks", genesis.current_hash, genesis.dumpb())
    _set_last_block(genesis)


def dump() -> None:
    """Broadcast every block in the main branch"""
    r = util.get_db()
    chain: typing.List[Block] = []
    b = Block.loadb(r.hget("blockchain:blocks", r.get("blockchain:last_block")))
    while not b.is_genesis():
        chain.append(b)
        b = Block.loadb(r.hget("blockchain:blocks", b.previous_hash))

    for b in reversed(chain):
        # TODO: Broadcast b
        raise NotImplementedError


def _check_for_new_block() -> None:
    """Check if there are at least CAPACITY transactions that can go in a new
    block (ie transactions in the pool with all their inputs in
    UTXO-block[last_block]. If so, start mining a new block."""
    CAPACITY = block.get_capacity()

    r = util.get_db()
    tx_pool = {Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")}
    if len(tx_pool) < CAPACITY:
        return

    last_block = Block.loadb(r.hget("blockchain:blocks", r.get("blockchain:last_block")))
    utxo_block = "blockchain:utxo-block:".encode() + last_block.current_hash
    new_block_tx: typing.List[Transaction] = []
    # NOTE: Since there are >= CAPACITY transactions in the pool, and we don't mind transaction
    # inter-dependence in the same block, a new block can be created, so this loop will terminate
    while True:
        for t in tx_pool:
            # Search for t.inputs in UTXO-block[last_block] as well as in new_block_tx
            if all(r.hexists(utxo_block, i.dumpb()) or \
                   any(nt.id = i.transaction_id for nt in new_block_tx) for i in t.inputs):
                new_block_tx.append(t)
                if len(new_block_tx) == CAPACITY:
                    new_block = Block(index=last_block.index + 1,
                                      previous_hash=last_block.current_hash,
                                      transactions=new_block_tx)
                    # NOTE: We don't delete the new block_tx from the pool, because mining might
                    # fail. They will be deleted eventually when they enter the main branch.
                    miner_pid = new_block.finalize()
                    r.set("blockchain:miner_pid", miner_pid)
                    return
        tx_pool.difference_update(new_block_tx)


def _set_last_block(last_block: Block) -> None:
    r = util.get_db()
    r.set("blockchain:last_block", last_block.current_hash)

    # Check if we were mining. If so, kill the miner
    miner_pid = r.get("blockchain:miner_pid")
    if miner_pid is not None:
        os.kill(miner_pid, signal.SIGTERM)
        r.delete("blockchain:miner_pid")


def new_recv_transaction(t: Transaction) -> bool:
    # TODO: Make this atomic
    # TODO OPT: Reimplement this with a Lua script to use with redis EVAL

    if not t.verify():
        return False

    # OK 8  Reject if we already have matching tx in the pool, or in a block in the main branch
    # TODO: This is not really necessary, since if t is already in the pool, its referenced txos
    # won't be found in UTXO-transaction
    r = util.get_db()
    if r.hexists("blockchain:tx_pool", t.id):
        return False
    # NOTE: When receiving a new transaction, both queries and updates are done
    # against UTXO-transaction
    referenced_txos = [i.dumpb() for i in t.inputs] # not empty because t.inputs != []
    prev_outb = r.hmget("blockchain:utxo-tx", *referenced_txos)
    if any(i is None for i in prev_outb):
        return False
    prev_outputs = [TransactionOutput.loadb(outb) for outb in prev_outb]

    # OK 14 Reject if the sum of input values < sum of output values
    input_amount = sum(i.amount for i in prev_outputs)
    output_amount = sum(o.amount for o in t.outputs)
    if input_amount != output_amount:
        return False

    # OK 16 Verify the scriptPubKey accepts for each input; reject if any are bad
    if any(o.recipient != t.sender for o in prev_outputs):
        return False

    # OK 17 Add to transaction pool[7]
    r.hset("blockchain:tx_pool", t.id, t.dumpb())

    # OK 18 "Add to wallet if mine"
    r.hdel("blockchain:utxo-tx", *referenced_txos)
    # NOTE: Not empty because t.outputs != []
    new_utxos = {TransactionInput(t.id, o.index).dumpb(): o.dumpb() for o in t.outputs}
    r.hmset("blockchain:utxo-tx", new_utxos)

    _check_for_new_block()

    return True


def new_recv_block(recv_block: Block) -> bool:
    # TODO: Make this atomic
    # TODO OPT: Reimplement this with a Lua script to use with redis EVAL

    if not recv_block.verify():
        return False

    # OK 2  Reject if duplicate of block we have in any of the three categories
    r = util.get_db()
    if r.hexists("blockchain:blocks", recv_block.current_hash) or \
       r.sismember("blockchain:orphan_blocks:".encode() + recv_block.previous_hash,
                   recv_block.dumpb()):
        return False

    # Handle the genesis block
    if recv_block.is_genesis():
        r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
        r.set("blockchain:last_block", recv_block.current_hash)
        t = recv_block.transactions[0]
        o = t.outputs[0]
        ib = TransactionInput(t.id, o.index).dumpb()
        ob = o.dumpb()
        r.hset("blockchain:utxo-block:".encode() + recv_block.current_hash, ib, ob)
        r.hset("blockchain:utxo-tx", ib, ob)
        r.sadd("blockchain:main_branch", recv_block.current_hash)
        return True

    # WP 11 Check if prev block (matching prev hash) is in main branch or side branches. If not, add
    #       this to orphan blocks, then query peer we got this from for 1st missing orphan block in
    #       prev chain; done with block
    prev_blockb = r.hget("blockchain:blocks", recv_block.previous_hash)
    if prev_blockb is None:
        r.sadd("blockchain:orphan_blocks:".encode() + recv_block.previous_hash, recv_block.dumpb())
        # TODO: Request b.previous_hash (from everyone or from the one we got this from?)
        return False

    prev_block = Block.loadb(prev_blockb)
    if recv_block.index != prev_block.index + 1:
        return False

    # WP 15 Add block into the tree. There are three cases: 1. block further extends the main
    #       branch; 2. block extends a side branch but does not add enough difficulty to make
    #       it become the new main branch; 3. block extends a side branch and makes it the new
    #       main branch.
    last_block = r.hget("blockchain:blocks", r.get("blockchain:last_block"))
    if recv_block.previous_hash == last_block.current_hash:
        # OK Case 1 (b.previous_hash == last_block):
        # TODO OPT: This can be factored out to validate_block()
        referenced_txos: typing.Set[bytes] = set()  # the utxos from UTXO-block spent in recv_block
        new_utxos: typing.Mapping[bytes, bytes] = {}
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
            # OK 2  For each input, if we are using the nth output of the earlier transaction, but
            #       it has fewer than n+1 outputs, reject.
            # OK 4  Verify crypto signatures for each input; reject if any are bad
                if o.recipient != t.sender:
                    return False
            # OK 5  For each input, if the referenced output has already been spent by a transaction
            #       in the main branch, reject
            # OK 7  Reject if the sum of input values < sum of output values
                input_amount += o.amount
            if input_amount != sum(o.amount for o in t.outputs):
                return False

            new_utxos.update({TransactionInput(t.id, o.index).dumpb(): o.dumpb() \
                    for o in t.outputs})

        # OK 4  For each transaction, "Add to wallet if mine"
        # TODO OPT: This can be factored out to set_utxo_block()
        utxo_prev_block = r.dump("blockchain:utxo-block:".encode() + recv_block.previous_hash)
        r.restore("blockchain:utxo-block:".encode() + recv_block.current_hash, 0, utxo_prev_block,
                  replace=True)
        # NOTE: referenced_txos and new_utxos are not empty since we got here
        r.hdel("blockchain:utxo-block:".encode() + recv_block.current_hash, *referenced_txos)
        r.hmset("blockchain:utxo-block:".encode() + recv_block.current_hash, new_utxos)

        # OK 5  For each transaction in the block, delete any matching transaction from the pool
        #       : delete all tx in the pool that have common inputs with the tx in the block,
        #       and their children, recursively
        tx_pool = {Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")}
        # TODO OPT: This can be factored out to rebuild_tx_pool()
        conflicting_tx: typing.Set[Transaction] = set()
        new_conflicting_tx = {t for t in tx_pool if \
                any(i.dumpb() in referenced_txos for i in t.inputs)}
        while new_conflicting_tx:
            conflicting_tx |= new_conflicting_tx
            tx_pool -= new_conflicting_tx
            new_conflicting_tx_ids = {t.id for t in new_conflicting_tx}
            new_conflicting_tx = {t for t in tx_pool if \
                    any(i.transaction_id in new_conflicting_tx_ids for i in t.inputs)}
        if conflicting_tx:
            r.hdel("blockchain:tx_pool", *conflicting_tx)

        # TODO OPT: This can be factored out to rebuild_utxo_tx()
        # Rebuild UTXO-tx: re-initialize it as a copy of UTXO-block[recv_block] and simulate
        # adding all tx still in the pool
        r.delete("blockchain:utxo-tx")
        utxo_tx = {TransactionInput.loadb(i): TransactionOutput.loadb(o) for i, o \
                in r.hgetall("blockchain:utxo-block:".encode() + recv_block.current_hash).items()}
        while tx_pool:
            tx_to_remove: typing.Set[Transaction] = set()
            for t in tx_pool:
                if all(i in utxo_tx for i in t.inputs):
                    for i in t.inputs:
                        del utxo_tx[i]
                    for o in t.outputs:
                        utxo_tx[TransactionInput(t.id, o.index)] = o
                    tx_to_remove.add(t)
            tx_pool -= tx_to_remove
        # NOTE: utxo_tx is not empty because UTXO-block[recv_block] is not empty
        r.hmset("blockchain:utxo-tx", {i.dumpb(): o.dumpb() for i, o in utxo_tx.items()})

        # Add block to main branch
        r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
        r.sadd("blockchain:main_branch", recv_block.current_hash)

        _set_last_block(recv_block)
    elif recv_block.index <= last_block.index:
        # OK Case 2 (b.previous_hash != last_block && b.index <= last_block.index)
        # : Add it without doing any validation because validating this now would require a lot of
        # work (actually simulating adding this to its prev as if extending the main branch).
        r.hset("blockchain:blocks", recv_block.current_hash, recv_block.dumpb())
    else:
        # WP Case 3 (b.previous_hash != last_block && b.index > last_block.index)
        # OK 1  Find the fork block on the main branch which this side branch forks off of
        #       : Ascend the side branch, the fork block is the first to be in the main branch
        old_side_branch = [recv_block]    # the Blocks in the old side branch
        fork_block = Block.loadb(r.hget("blockchain:blocks", recv_block.previous_hash))
        while not r.sismember("blockchain:main_branch", fork_block.current_hash):
            old_side_branch.append(fork_block)
            fork_block = Block.loadb(r.hget("blockchain:blocks", fork_block.previous_hash))
        old_side_branch.reverse()   # starting from the child of the fork block
        # OK 2  Redefine the main branch to only go up to this fork block
        #       : Ascend from last_block up to the fork block, removing blocks from main_branch
        #       along the way
        old_main_branch: typing.List[Block] = []    # the Blocks in the old main branch
        b = Block.loadb(r.hget("blockchain:blocks", last_block.current_hash))
        while b != fork_block:
            old_main_branch.append(b)
            r.srem("blockchain:main_branch", b.current_hash)    # TODO: Defer this if possible
            b = Block.loadb(r.hget("blockchain:blocks", b.previous_hash))
        old_main_branch.reverse()   # starting from the child of the fork block
        # WP 3  For each block on the side branch, from the child of the fork block to the leaf, add
        #       to the main branch:
        # referenced_txos for all blocks in the old side branch
        osb_referenced_txos: typing.Set[bytes] = set()
        for b in old_side_branch:
            # OK 1  Do "branch" checks 3-11
            #       : Why? we did them when first receiving the block. What could have changed?
            # WP 2  For all the transactions:
            # TODO OPT: This can be factored out to validate_block()
            referenced_txos: typing.Set[bytes] = set()  # the utxos from UTXO-block spent in b
            new_utxos: typing.Mapping[bytes, bytes] = {}
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
                # OK 2  For each input, if we are using the nth output of the earlier transaction,
                #       but it has fewer than n+1 outputs, reject.
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

            # NOTE: This actually adds more than we need, but it's harmless. We only need the UTXOs
            # from the fork block and up which are spent in the old side branch, but this also adds
            # UTXOs from the old side branch itself
            osb_referenced_txos |= referenced_txos

            # OK 5  For each transaction, "Add to wallet if mine"
            #       : Update UTXO-block[current_hash]: delete inputs and add outputs from the tx
            #       in the block
            # TODO: Defer these if possible
            # TODO OPT: This can be factored out to set_utxo_block()
            utxo_prev_block = r.dump("blockchain:utxo-block:".encode() + b.previous_hash)
            r.restore("blockchain:utxo-block:".encode() + b.current_hash, 0, utxo_prev_block,
                      replace=True)
            # NOTE: referenced_txos and new_utxos are not empty since we got here
            r.hdel("blockchain:utxo-block:".encode() + b.current_hash, *referenced_txos)
            r.hmset("blockchain:utxo-block:".encode() + b.current_hash, new_utxos)

            # Add b to main_branch
            r.sadd("blockchain:main_branch", b.current_hash)    # TODO: Defer this if possible

        #    4  If we reject at any point, leave the main branch as what it was originally, done
        #       with block
        #       TODO: Taken care of with a transaction rollback? Nothing to do if nothing written ;)

        # OK 5  For each block in the old main branch, from the leaf down to the child of the fork
        #       block:
        tx_pool = {Transaction.loadb(tb) for tb in r.hvals("blockchain:tx_pool")}
        for b in reversed(old_main_branch):
            # OK 1  For each non-coinbase transaction in the block:
            for t in b.transactions:
                # OK 1  Apply "tx" checks 2-9, except in step 8, only look in the transaction pool
                #       for duplicates, not the main branch
                #       : Why? these have been checked already. There can't be double spending
                #       transactions in the pool as it is at this point (current as of the old main
                #       branch) + the old main branch, because they wouldn't have gotten there in
                #       the first place.
                # OK 2  Add to transaction pool if accepted, else go on to next transaction
                tx_pool.add(t)

        # OK 6  For each block in the new main branch, from the child of the fork node to the leaf:
            # OK 1  For each transaction in the block, delete any matching transaction from the
            #       transaction pool
        #       : delete all tx in the pool that have common inputs with the tx in the blocks in
        #       the old side branch and their children, recursively
        # TODO OPT: This can be factored out to rebuild_tx_pool()
        conflicting_tx: typing.Set[Transaction] = set()
        new_conflicting_tx = {t for t in tx_pool if \
                any(i.dumpb() in osb_referenced_txos for i in t.inputs)}
        while new_conflicting_tx:
            conflicting_tx |= new_conflicting_tx
            tx_pool -= new_conflicting_tx
            new_conflicting_tx_ids = {t.id for t in new_conflicting_tx}
            new_conflicting_tx = {t for t in tx_pool if \
                    any(i.transaction_id in new_conflicting_tx_ids for i in t.inputs)}
        if conflicting_tx:
            r.hdel("blockchain:tx_pool", *conflicting_tx)

        # TODO OPT: This can be factored out to rebuild_utxo_tx()
        # Rebuild UTXO-tx: reinitialize it as a copy of UTXO-block[recv_block] and simulate
        # adding all tx still in the pool
        r.delete("blockchain:utxo-tx")
        utxo_tx = {TransactionInput.loadb(i): TransactionOutput.loadb(o) for i, o \
                in r.hgetall("blockchain:utxo-block:".encode() + recv_block.current_hash).items()}
        while tx_pool:
            tx_to_remove: typing.Set[Transaction] = set()
            for t in tx_pool:
                if all(i in utxo_tx for i in t.inputs):
                    for i in t.inputs:
                        del utxo_tx[i]
                    for o in t.outputs:
                        utxo_tx[TransactionInput(t.id, o.index)] = o
                    tx_to_remove.add(t)
            tx_pool -= tx_to_remove
        # NOTE: utxo_tx is not empty because UTXO-block[recv_block] is not empty
        r.hmset("blockchain:utxo-tx", {i.dumpb(): o.dumpb() for i, o in utxo_tx.items()})

        _set_last_block(recv_block)

    # OK 19 For each orphan block for which this block is its prev, run all these steps (including
    #       this one) recursively on that orphan
    orphanb = r.spop("blockchain:orphan_blocks:".encode() + recv_block.current_hash)
    while orphanb is not None:
        new_recv_block(Block.loadb(orphanb))
    r.delete("blockchain:orphan_blocks:".encode() + recv_block.current_hash)

    _check_for_new_block()

    return True
