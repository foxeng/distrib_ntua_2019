from noobcash.blockchain import wallet, util
from noobcash.blockchain.wallet import PrivateKey, PublicKey
from noobcash.blockchain.transaction import Transaction
from noobcash.blockchain.block import Block


NODE_IDS = list(range(3))
OUR_NODE_ID = NODE_IDS[0]

privkeys = {}
TEST_MESSAGE = b"This is a test message"


def test_util():
    r = util.get_db()
    r.flushdb()

    util.set_nodes(len(NODE_IDS))
    assert util.get_nodes() == len(NODE_IDS)


def test_wallet():
    wallet.generate_wallet(OUR_NODE_ID)
    signature = wallet.sign(TEST_MESSAGE)
    assert wallet.get_public_key().verify(TEST_MESSAGE, signature)

    node_id1 = NODE_IDS[1]
    privkeys[node_id1] = PrivateKey()
    pubkey = privkeys[node_id1].public_key()
    wallet.set_public_key(node_id1, pubkey)
    signature = privkeys[node_id1].sign(TEST_MESSAGE)
    assert wallet.get_public_key(node_id1).verify(TEST_MESSAGE, signature)

    assert PublicKey.loadb(pubkey.dumpb()) == pubkey
    assert PublicKey.loads(pubkey.dumps()) == pubkey

    node_id2 = NODE_IDS[2]
    privkeys[node_id2] = PrivateKey()
    wallet.set_public_key(node_id2, privkeys[node_id2].public_key())


def test_transaction():
    gt = Transaction.genesis()
    assert gt.is_genesis()
    assert gt.verify()

    assert Transaction.loadb(gt.dumpb()) == gt
    assert Transaction.loads(gt.dumps()) == gt

    recipient2 = wallet.get_public_key(NODE_IDS[2])
    t = Transaction(recipient=recipient2,
                    amount=12.5,
                    inputs=[
                        TransactionInput(gt.id, 0),
                        TransactionInput((12345).to_bytes(256 // 8, byteorder="big"), 1)
                    ],
                    input_amount=42)
    assert not t.is_genesis()
    assert t.verify()
    assert t.outputs[1].amount == 42 - 12.5

    assert Transaction.loadb(t.dumpb()) == t
    assert Transaction.loads(t.dumps()) == t

    t.amount += 1
    assert not t.verify()


def test_block():
    # TODO
    pass


def test_blockchain():
    # TODO
    pass
