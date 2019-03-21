import json
import requests

from flask import Flask, request, Response, abort
from . import blockchainApi
from instance import config
from noobcash import app
from threading import Thread
from os import environ
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
        blockchain.initialize(config.NUMBER_OF_NODES, config.NODE_ID, config.CAPACITY, config.DIFFICULTY)
        #util.set_node_id(0)
        #wallet.generate_wallet(0)
        #blockchain.generate_genesis()
        blockchainApi.setIp({ 0 :{'ipAddr': config.NODE_0_IP_ADDRESS, 'port': config.NODE_0_PORT}})
        #app.run()
    else:
        node_0_url = "http://" + config.NODE_0_IP_ADDRESS + ":" + config.NODE_0_PORT
        r = requests.get(node_0_url + "/initialisation", json= {"port" : environ.get('FLASK_RUN_PORT')})
        nodeId = r.json()["nodeId"]
        blockchain.initialize(config.NUMBER_OF_NODES, nodeId, config.CAPACITY, config.DIFFICULTY)
        #util.set_node_id(nodeId)
        print(nodeId)
        #wallet.generate_wallet(nodeId)
        pubKey = wallet.get_public_key().dumps()
        r = requests.post(node_0_url + "/finalisation", json = {"nodeId" : nodeId, "pubKey" : pubKey}) 
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
        # Does the client send the walletId ?
        #walletId = request.get_json()["walletId"]
        #balance = blockchainApi.getBalance(walletId)
        balance = blockchain.get_balance()
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

@app.route("/initialisation", methods=['GET'])
def lstInitialisation():
    if config.IS_NODE_0 == True:
        newNodeId = blockchainApi.incNodeCounter()
        ipAddr = request.remote_addr
        port = request.get_json()["port"]
        entryValue = {"ipAddr": ipAddr, "port" : port}
        entry = {newNodeId : entryValue}
        blockchainApi.setIp(entry)
        response = Response(json.dumps({"nodeId" : newNodeId}), status=200, mimetype="application/json")
        return response
    else:
        return abort(403)       

@app.route("/finalisation", methods = ['POST'])
def lstFinalise():
    if config.IS_NODE_0 == True:
        nodeId = request.get_json()["nodeId"]
        tempKey = wallet.PublicKey
        pubKeyStr = request.get_json()["pubKey"]
        tempKey = tempKey.loads(pubKeyStr)
        wallet.set_public_key(nodeId, tempKey)
        blockchainApi.generateTransaction(nodeId, 100.0, True)
        if blockchainApi.getNodeCounter() == blockchainApi.getTotalNodes() - 1:
            def threadFn():
                sleep(0.1) #wait a bit to make sure that the listener is started
                routingTable = {}
                for i in range(0, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    pubKey = wallet.get_public_key(i).dumps()
                    ipEntry.update({"pubKey" : pubKey})
                    routingTable.update({i : ipEntry})
                for i in range(1, blockchainApi.getTotalNodes()):
                    ipEntry = blockchainApi.getIp(i)
                    url = "http://" + ipEntry["ipAddr"] + ":" + str(ipEntry["port"] + "/finalisation")
                    r = requests.post(url, json= {"routingTable" : routingTable})  
                return

            def thread2Fn():
                sleep(0.3)
                print("Sending Blockchain")
                blockchain.dump()
                print("Blockchain Sent")
                return

            thread1 = Thread(target=threadFn)
            thread1.start()
            thread2 = Thread(target=thread2Fn)
            thread2.start()
            
        return ("<h1> PubKey from {} Noted</h1>".format(nodeId))
    else:
        routingTable = request.get_json()["routingTable"]
        for key, value in routingTable.items():
            pubKey = wallet.PublicKey.loads(value.pop("pubKey"))
            blockchainApi.setIp({key: value})
            wallet.set_public_key(key,pubKey)
            print(pubKey)
        return("<h1> Routing Table Received </h1>")
