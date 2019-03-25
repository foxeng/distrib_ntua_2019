import json
from threading import Thread
from os import environ
from time import sleep

import requests
from flask import Flask, request, Response, abort
from instance import config
from noobcash.listener import blockchainApi
from noobcash.blockchain import wallet, blockchain, util
from noobcash.chatter import chatter


LOCALHOST = "127.0.0.1"
app = Flask(__name__, instance_relative_config=True)
# TODO OPT: Configuration from config.py, silent=False and remove the 'from
# instance import config' above


@app.before_first_request
def _initialization():
    if config.IS_NODE_0:
        print("I am Node 0")
        print(config.NUMBER_OF_NODES)
        blockchain.initialize(config.NUMBER_OF_NODES, 0, config.CAPACITY, config.DIFFICULTY)
        blockchainApi.setIp({0: {'ipAddr': config.NODE_0_IP_ADDRESS, 'port': config.NODE_0_PORT}})
    else:
        node_0_url = "http://" + config.NODE_0_IP_ADDRESS + ":" + config.NODE_0_PORT
        r = requests.get(node_0_url + "/initialisation",
                         json={"port": environ.get('FLASK_RUN_PORT')})
        nodeId = r.json()["nodeId"]
        blockchain.initialize(config.NUMBER_OF_NODES, nodeId, config.CAPACITY, config.DIFFICULTY)
        print(nodeId)
        pubKey = wallet.get_public_key().dumps()
        r = requests.post(node_0_url + "/finalisation", json={"nodeId": nodeId, "pubKey": pubKey})


@app.route("/")
def welcome():
    return "<h1> We are rolling </h1>\n"


@app.route("/transaction", methods=['GET', 'POST'])
def lstTransaction():
    if request.method == 'GET':
        # Client requesting generation of a new transaction
        dst = request.get_json()["dst"]
        value = float(request.get_json()["amount"])
        # Should block, the client can wait and we ought to give some feedback
        res = blockchainApi.newCreatedTransaction(dst, value)
        return "OK" if res else "Transaction could not be satisfied"
    else:
        # Transaction heard on the network
        transData = request.get_json()["transData"]
        # Shouldn't block
        Thread(target=blockchainApi.newReceivedTransaction, args=(transData, )).start()
        return "<h1> Response to be implemented </h1>"


@app.route("/block", methods=['POST', 'GET'])
def lstNewBlock():
    if request.method == 'POST':
        # Block heard on the network
        blockData = request.get_json()["blockData"]
        # TODO OPT: Also provide the node id of the sender (not easy if >1
        # servers running on the same host because then how do we identify
        # which of them it was? (the port they make the requests from is
        # arbitrary))
        # Shouldn't block
        Thread(target=blockchainApi.newReceivedBlock, args=(blockData, )).start()
        return "<h1> Response to be implemented </h1>"
    else:
        # Query for a block on our chain
        def sendBlockAsync(blockId):
            b = blockchainApi.getBlock(blockId)
            # TODO OPT: Only send the block back to the peer who requested it
            # instead of broadcasting it (not easy if >1 servers running on the
            # same host because then how do we identify which of them it was?
            # (the port they make the requests from is arbitrary))
            if b is not None:
                chatter.broadcast_block(b, util.get_peer_ids())

        blockId = request.get_json()["block"]
        # Asynchronously send the block in a new request, not the response
        Thread(target=sendBlockAsync, args=(blockId, )).start()
        return "<h1> Response to be implemented </h1>"


@app.route("/balance")
def lstBalance():
    if request.remote_addr != LOCALHOST:
        # Only servicing the local client
        abort(403)
    else:
        balance = blockchainApi.getBalance()
        return Response(json.dumps({"balance": balance}), status=200, mimetype="application/json")


@app.route("/history")
def lstHistory():
    if request.remote_addr != LOCALHOST:
        # Only servicing the local client
        abort(403)
    else:
        blockStr = blockchainApi.getBlock().dumps() # not None because we assume that at least the
                                                    # genesis block has been stored
        return Response(json.dumps({"block": blockStr}), status=200, mimetype="application/json")


@app.route("/initialisation", methods=['GET'])
def lstInitialisation():
    if config.IS_NODE_0:
        newNodeId = blockchainApi.incNodeCounter()
        ipAddr = request.remote_addr
        port = request.get_json()["port"]
        entryValue = {"ipAddr": ipAddr, "port": port}
        entry = {newNodeId: entryValue}
        blockchainApi.setIp(entry)
        return Response(json.dumps({"nodeId": newNodeId}), status=200, mimetype="application/json")
    else:
        abort(403)


@app.route("/finalisation", methods=['POST'])
def lstFinalise():
    if config.IS_NODE_0:
        nodeId = request.get_json()["nodeId"]
        pubKeyStr = request.get_json()["pubKey"]
        tempKey = wallet.PublicKey.loads(pubKeyStr)
        wallet.set_public_key(nodeId, tempKey)
        print(blockchainApi.getTotalNodes())
        if blockchainApi.getNodeCounter() == blockchainApi.getTotalNodes() - 1:
            def threadFn():
                sleep(0.1)  # wait a bit to make sure that the listener is started
                routingTable = {}
                for i in range(0, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    pubKey = wallet.get_public_key(i).dumps()
                    ipEntry.update({"pubKey": pubKey})
                    routingTable.update({i: ipEntry})
                for i in range(1, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    url = "http://" + ipEntry["ipAddr"] + ":" + str(ipEntry["port"] + \
                              "/finalisation")
                    print("Sending to {} the routing table {}".format(i, routingTable))
                    requests.post(url, json={"routingTable": routingTable})

            def thread2Fn():
                sleep(1)
                print("Sending Blockchain")
                blockchain.dump()
                print("Blockchain Sent")

            def thread3Fn():
                sleep(2)
                for i in range(1, blockchainApi.getTotalNodes()):
                    blockchainApi.generateTransaction(i, 100.0)

            thread1 = Thread(target=threadFn)
            thread1.start()
            thread2 = Thread(target=thread2Fn)
            thread2.start()
            thread3 = Thread(target=thread3Fn)
            thread3.start()
        return "<h1> PubKey from {} Noted</h1>".format(nodeId)
    else:
        routingTable = request.get_json()["routingTable"]
        for key, value in routingTable.items():
            pubKey = wallet.PublicKey.loads(value.pop("pubKey"))
            blockchainApi.setIp({key: value})
            wallet.set_public_key(key, pubKey)
            print(pubKey)
        return "<h1> Routing Table Received </h1>"
