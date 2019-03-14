from flask import Flask, request, Response, abort
import json
from . import blockchainApi
from .. instance import config
from noobcash import app
from threading import Thread
from time import sleep
import requests

LOCALHOST="127.0.0.1"

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
        config.nodeIdCounter += 1
        newNodeId = config.nodeIdCounter
        ipAddr = request.remote_addr
        walletId = request.get_json()["walletId"]
        port = request.environ['REMOTE_PORT']
        entryValue = {"ipAddr": ipAddr, "port" : port, "pubWalletId" : walletId}
        entry = {newNodeId : entryValue}
        #blockchain.setIp(entry)
        #config.routingTable.update(entry)
        if config.nodeIdCounter == config.NUMBER_OF_NODES:
            def threadFn():
                sleep(0.1) #wait a bit to make sure that the listener is started
                routingTable = {}
                for i in range(0, config.NUMBER_OF_NODES):
                    #ipEntry = blockchain.getIp(i)
                    #routingTable.update(ipEntry)
                    print("")
                for i in range(1, config.NUMBER_OF_NODES):
                    #ipEntry = blockchain.getIp(i)
                    #url = ipEntry["ipAddress"] + ":" + ipEntry["port"]
                    #r = requests.post(url, json= {"routingTable" : routingTable})  
                    print("")
                return 
                
            thread = Thread(target=threadFn)
            thread.start()
        response = Response(json.dumps({"nodeId" : newNodeId}), status=200, mimetype="application/json")
        return response
    else:
        routingTable = request.get_json()["routingTable"]
        for key, value in routingTable:
            print(key)
            print(value)
            #blockchain.setIp({key: value})
        return response
