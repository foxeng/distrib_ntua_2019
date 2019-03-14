from noobcash import app
import noobcash.listener
from noobcash.blockchain import wallet, blockchain
from .instance import config
from noobcash.blockchain import util
import requests # This is different from flask request
# We suppose that the total number of nodes is known before hands

# Handles the initialisation phase
if __name__ == '__main__':
    if (config.IS_NODE_0) == True:
        print("I am Node 0")
        wallet.generate_wallet(0)
        blockchain.generate_genesis()
        app.run()
    else:
        node_0_url = config.NODE_0_IP_ADDRESS + ":" + config.NODE_0_PORT
        r = requests.get(node_0_url + "initialiasation", json={"pubWalletId": config.WALLET_ID})
        nodeId = r.json()["nodeId"]
        util.set_node_id(nodeId)
        print("sad")
        wallet.generate_wallet(nodeId)
        app.run()
    
    # To do start client
    # if node != 0 
    # post an initialization to node 0 
    # the node 0 responds by sending a copy of the blockchain
    # node 0 GET a handshake with his id to node 0
    # and start their listener 
    # repeat the process for all nodes
    # when all the nodes are completed, node 0 
    # sends a INIT_READ GET request to all other nodes, 
    # and then the rest of the nodes can start their client 