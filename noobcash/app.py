from noobcash import app
from noobcash.listener import listener

if __name__ == '__main__':
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
    app.run()