from noobcash.blockchain import blockchain, transaction

def newReceivedTransaction(transJson):
    #print("newReceivedTransaction Called with transString:")
    #print(transJson)
    trans = blockchain.Transaction.loads(transJson)
    blockchain.new_recv_transaction(trans)


def newCreatedTransaction(dst, value):
    trans = transaction.Transaction(dst.encode('utf-8'), value, None)
    blockchain.new_recv_transaction(trans)
    # print("newCreatedTransaction Called with dst: {} & value {}:".format(dst, value))



def newReceivedBlock(blockString):
    #print("newReceivedBlocked called with blockString:")
    #print(blockString)
    block = blockchain.Block.loads(blockString)
    blockchain.new_recv_block(block)


def getBlock(blockId):
    if blockId is not None:
        blockId = blockId.encode('utf-8')
    blockString = blockchain.get_block(blockId).dumps
    #print("getBlock called with blockId"  + str(blockId))
    #blockString = "This string contains the block in a string format of the block with id {}".format(blockId)
    return blockString


def getBalance(walletId):
    #print("getBalance called with walletId"  + walletId)
    balance = blockchain.get_balance()
    # balance = 100 + int(walletId)
    return balance

