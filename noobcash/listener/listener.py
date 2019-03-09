from flask import Flask, jsonify, request, Response, abort
import json
from . import blockchainApi

from noobcash import app

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
        if request.remote_addr != LOCALHOST:
            return abort(405)
        else:
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

