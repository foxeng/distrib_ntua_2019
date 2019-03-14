import requests
from multiprocessing.pool import ThreadPool

def send_post_request(node_id, payload, arg):
    r = requests.post(get_ip(node_id)["ipAddr"] + ":" + get_ip(node_id)["port"] + "/" + arg, json=payload)

def send_get_request(node_id, payload, arg):
    r =  requests.get(get_ip(node_id)["ipAddr"] + ":" + get_ip(node_id)["port"] + "/" + arg, data=payload)

def broadcast_transaction(trans_data, node_ids):
    payload = {"transData" : trans_data.dumps()}
    p = ThreadPool(len(node_ids))
    results = p.map(send_post_request, node_ids, payload, "transaction")

def broadcast_block(block_data, node_ids):
    payload = {"blockData" : block_data.dumps()}
    p = ThreadPool(len(node_ids))
    results = p.map(send_post_request, node_ids, payload, "block")

def get_blockid(blockId, node_ids):
    payload = {"block" : blockId}
    p = ThreadPool(len(node_ids))
    results = p.map(send_get_request, node_ids, payload, "block")
   
