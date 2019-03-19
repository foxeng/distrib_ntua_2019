import json
import requests

from flask import Flask, request, Response, abort
from . import blockchainApi
from instance import config
from noobcash import app
from threading import Thread
from time import sleep
from noobcash.blockchain import wallet, blockchain
from noobcash.blockchain import util

LOCALHOST="127.0.0.1"

@app.before_first_request
def _initialization():
    print("FOO")
    if (config.IS_NODE_0) == True:

        print("I am Node 0")
        util.set_nodes(config.NUMBER_OF_NODES)
        util.set_node_id(0)
        wallet.generate_wallet(0)
        blockchain.generate_genesis()
        #app.run()
    else:
        node_0_url = config.NODE_0_IP_ADDRESS + ":" + config.NODE_0_PORT
        r = requests.get(node_0_url + "initialiasation")
        nodeId = r.json()["nodeId"]
        util.set_node_id(nodeId)
        print("sad")
        wallet.generate_wallet(nodeId)
        #app.run()    


@app.route("/")
def welcome():
    return("<h1> We are rolling </h1>")

#listener = Flask(__name__)
@app.route("/transaction", methods=['POST'])
def lstTransaction():
    if request.remote_addr == LOCALHOST:
        dst = (request.get_json()["dst"])
        value = float(request.get_json()["amount"])
        blockchainApi.newCreatedTransaction(dst, value)
        return "<h1> Transaction Noted </h1> "
    else:
        transData = request.get_json()["transData"]
        blockchainApi.newReceivedTransaction(transData)
        return "<h1> Response to be implemented </h1>"


@app.route("/block", methods=['POST', 'GET'])
def lstNewBlock():
    if request.method == 'POST':
        blockData = request.get_json()["blockData"]
        blockchainApi.newReceivedBlock(blockData)
        return "<h1> Response to be implemented </h1>"
    elif request.method == 'GET':
        blockId = request.get_json()["blockId"]
        blockStr = blockchainApi.getBlock(blockId)
        response = Response(json.dumps({"block" : blockStr}), status=200, mimetype="application/json")
        return response
    else:
        abort(405)
    return ""

@app.route("/balance")
def lstBalance():
    if request.remote_addr != LOCALHOST:
        return abort(403)
    else:
        walletId = request.get_json()["walletId"]
        balance = blockchainApi.getBalance(walletId)
        response = Response(json.dumps({"balance" : balance}), status=200, mimetype="application/json")
        return response

@app.route("/history")
def lstHistory():
    if request.remote_addr != LOCALHOST:
        return abort(403)
    else:
        blockStr = blockchainApi.getBlock(None)
        response = Response(json.dumps({"block" : blockStr}), status=200, mimetype="application/json")
        return response

@app.route("/initialisation", methods=['GET', 'POST'])
def lstInitialisation():
    if config.IS_NODE_0 == True:
        newNodeId = blockchainApi.incNodeCounter()
        ipAddr = request.remote_addr
        port = request.environ['REMOTE_PORT']
        entryValue = {"ipAddr": ipAddr, "port" : port}
        entry = {newNodeId : entryValue}
        blockchainApi.setIp(entry)
        if blockchainApi.getNodeCounter() == blockchainApi.getTotalNodes() - 1:
            def threadFn():
                sleep(0.1) #wait a bit to make sure that the listener is started
                routingTable = {}
                for i in range(0, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    routingTable.update(ipEntry)
                for i in range(1, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    url = ipEntry["ipAddress"] + ":" + ipEntry["port"]
                    r = requests.post(url, json= {"routingTable" : routingTable})  
                
                for i in range (1, blockchainApi.getTotalNodes()):
                    blockchainApi.generateTransaction(i, 100.0)
                return 
                
            thread = Thread(target=threadFn)
            thread.start()
        response = Response(json.dumps({"nodeId" : newNodeId}), status=200, mimetype="application/json")
        return response
    else:
        routingTable = request.get_json()["routingTable"]
        for key, value in routingTable:
            blockchainApi.setIp({key: value})
        return response
