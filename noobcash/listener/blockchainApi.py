from noobcash.blockchain import blockchain, util


def newReceivedTransaction(transJson):
    # TODO OPT: Gracefully handle (ie do nothing, just catch it) any exception
    # thrown by loads()
    trans = blockchain.Transaction.loads(transJson)
    blockchain.new_recv_transaction(trans)


def newCreatedTransaction(dst, value):
    blockchain.generate_transaction(int(dst), float(value))


def generateTransaction(node_id, value, flag=False):
    blockchain.generate_transaction(node_id, value, flag)


def newReceivedBlock(blockString):
    # TODO OPT: Gracefully handle (ie do nothing, just catch it) any exception
    # thrown by loads()
    block = blockchain.Block.loads(blockString)
    blockchain.new_recv_block(block)


def getBlock(blockId=None):
    if blockId is not None:
        blockId = util.stobin(blockId)
    return blockchain.get_block(blockId)


def getBalance():
    return blockchain.get_balance()


def setIp(entry):
    util.set_ip(entry)


def getIp(entry):
    return util.get_ip(entry)


def getTotalNodes():
    return util.get_nodes()


def incNodeCounter():
    return util.incr_registered_nodes()


def getNodeCounter():
    return util.get_registered_nodes()
