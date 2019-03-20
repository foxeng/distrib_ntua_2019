from copy import deepcopy
import subprocess
import sys
from noobcash.blockchain import wallet, util, block, blockchain
from noobcash.blockchain.wallet import PrivateKey, PublicKey
from noobcash.blockchain.transaction import Transaction, TransactionInput, TransactionOutput
from noobcash.blockchain.block import Block
from noobcash.blockchain.test.test_data import *


transactions = []
blocks = {
    "valid": [],
    "invalid": []
}


def change_id(id_: int) -> None:
    r = util.get_db()
    r.set("wallet:privkey", PRIVKEYSB[id_])
    util.set_node_id(id_)


def test_util():
    r = util.get_db()
    r.flushdb()

    util.set_nodes(NODES)
    assert util.get_nodes() == NODES


def test_wallet():
    TEST_MESSAGE = b"This is a test message"

    wallet.generate_wallet(NODE_ID)
    signature = wallet.sign(TEST_MESSAGE)
    pubkey = wallet.get_public_key()
    assert pubkey.verify(TEST_MESSAGE, signature)
    assert PublicKey.loadb(pubkey.dumpb()) == pubkey
    assert PublicKey.loads(pubkey.dumps()) == pubkey

    # Load the predefined keys into a fresh wallet
    r = util.get_db()
    r.flushdb()
    util.set_nodes(NODES)
    util.set_node_id(NODE_ID)
    r.set("wallet:privkey", PRIVKEYSB[NODE_ID])
    for node_id, key in enumerate(PUBKEYS):
        wallet.set_public_key(node_id=node_id,
                              key=key)


def test_transaction():
    gt = Transaction.genesis()
    assert gt.is_genesis()
    assert gt.verify()
    assert Transaction.loadb(gt.dumpb()) == gt
    assert Transaction.loads(gt.dumps()) == gt

    # TODO: Create transactions with only sender specified in the data (change_id())
    for td in TRANSACTION_DATA:
        sender_id = td.get("sender")
        sender = PUBKEYSB[sender_id] if sender_id is not None else None
        tod = td.get("outputs")
        outputs = [
            TransactionOutput(index=tod[0]["index"],
                              recipient=PUBKEYSB[tod[0]["recipient"]],
                              amount=tod[0]["amount"]),
            TransactionOutput(index=tod[1]["index"],
                              recipient=PUBKEYSB[tod[1]["recipient"]],
                              amount=tod[1]["amount"])
        ] if tod is not None else None
        if sender is not None and outputs is None:
            # If only sender is specified (apart from the necessary parameters),
            # temporarily pretend to be sender
            change_id(sender_id)
        t = Transaction(recipient=PUBKEYSB[td["recipient"]],
                        amount=td["amount"],
                        inputs=[TransactionInput(
                            transaction_id=transactions[tid["transaction_id"]].id \
                                if tid["transaction_id"] >= 0 else gt.id,
                            index=tid["index"]) for tid in td["inputs"]],
                        input_amount=td.get("input_amount"),
                        sender=sender if outputs is not None else None,
                        outputs=outputs,
                        id_=td.get("id_"),
                        signature=td.get("signature"))
        if sender is not None and outputs is None:
            # Change back
            change_id(NODE_ID)
        transactions.append(t)

        assert not t.is_genesis()
        assert t.verify()
        assert ("input_amount" not in td) or (t.outputs[1].amount == td["input_amount"] - t.amount)
        assert Transaction.loadb(t.dumpb()) == t
        assert Transaction.loads(t.dumps()) == t

    t = deepcopy(transactions[0])
    t.recipient = PUBKEYSB[0]
    assert not t.verify()
    t = deepcopy(transactions[0])
    t.amount += 100
    assert not t.verify()
    t = deepcopy(transactions[0])
    t.inputs[0].index = 2
    assert not t.verify()
    t = deepcopy(transactions[0])
    t.outputs[1].amount = -12
    assert not t.verify()

def test_block():
    block.set_capacity(CAPACITY)
    block.set_difficulty(DIFFICULTY)
    assert block.get_capacity() == CAPACITY
    assert block.get_difficulty() == DIFFICULTY

    gb = Block.genesis()
    assert gb.is_genesis()
    assert gb.verify()
    assert Block.loadb(gb.dumpb()) == gb
    assert Block.loads(gb.dumps()) == gb

    for validity in ("valid", "invalid"):
        for bd in BLOCK_DATA[validity]:
            prev_block = blocks["valid"][bd["previous_hash"]] if bd["previous_hash"] >= 0 else gb
            # TODO: Test specifying a whole block
            b = Block(index=bd["index"],
                      previous_hash=prev_block.current_hash,
                      transactions=[transactions[i] for i in bd["transactions"]])
            python = sys.executable if sys.executable else 'python3'
            miner = subprocess.run(args=[python,
                                         "-m",
                                         "noobcash.blockchain.miner",
                                         str(DIFFICULTY),
                                         "-echo"],
                                   input=b.dumps(),
                                   stdout=subprocess.PIPE,
                                   check=True,
                                   universal_newlines=True)
            mined = Block.loads(miner.stdout)
            b.timestamp = mined.timestamp
            b.nonce = mined.nonce
            b.current_hash = mined.current_hash
            assert not mined.is_genesis()
            assert b.verify()
            assert mined.verify()
            assert Block.loadb(b.dumpb()) == mined
            assert Block.loads(mined.dumpb()) == b

            blocks[validity].append(b)

    b0 = blocks["valid"][0]
    b = deepcopy(b0)
    b.transactions = b.transactions[:len(b.transactions) - 1]
    assert not b.verify()
    b = deepcopy(b0)
    b.transactions[0].amount += 10
    assert not b.verify()
    b = deepcopy(b0)
    b.transactions[0].amount += 10
    assert not b.verify()
    b = deepcopy(b0)
    b.nonce += 12345
    assert not b.verify()
    b = deepcopy(b0)
    b.current_hash = b"0" * (256 // 8)
    assert not b.verify()


def test_blockchain():
    blockchain.generate_genesis()
    assert blockchain.get_block().is_genesis()
    assert blockchain.get_balance(0) == 100 * NODES
    assert blockchain.get_balance(1) == 0

    assert blockchain.get_block(b"foobar") is None

    # Adding blocks while the tx_pool is empty
    valid_blocks = blocks["valid"]
    invalid_blocks = blocks["invalid"]
    b0 = valid_blocks[0]
    assert blockchain.new_recv_block(b0)
    assert blockchain.get_block() == b0
    assert blockchain.get_block(b0.current_hash) == b0
    assert blockchain.get_balance(0) == 100 * (NODES - CAPACITY)
    assert blockchain.get_balance(1) == 100

    for b in invalid_blocks:
        assert not blockchain.new_recv_block(b)

    assert not blockchain.new_recv_block(b0)
    b1 = valid_blocks[1]
    assert blockchain.new_recv_block(b1)
    assert blockchain.get_balance(0) == 100 + 12.5 - 7
    assert blockchain.get_balance(1) == 100 - 12.5 + 7
    assert blockchain.get_balance(2) == 100

    # TODO: Receive some transactions (but not enough to fill a block)
    # TODO: Generate some transactions (but not enough to fill a block)
    # TODO: Add blocks on side branches (eventually doing a rebase)
