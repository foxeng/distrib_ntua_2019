import requests

def err_print(status_code):
    if not (status_code == requests.codes.ok):
        print("Some error occurred\n")
        quit()

def broadcast_transaction(trans_data):
    payload = {"transData" : trans_data.dumps()}
    ip_addresses = get_ips()
    for ip in ip_addresses:
        r = requests.post(ip + ":5000/transaction", json=payload)
        err_print(r.status_code)

def broadcast_block(block_data):
    payload = {"blockData" : block_data.dumps()}
    ip_addresses = get_ips()
    for ip in ip_addresses:
        r = requests.post(ip + ":5000/block", json=payload)
        err_print(r.status_code)

def get_blockid(blockId):
    payload = {"block" : blockId}
    ip_addresses = get_ips()
    for ip in ip_addresses:
        r =  requests.get(ip + ":5000/block", data=payload)
        err_print(r.status_code)

#def get_ips():
#   TODO
#returns a list of all ip addresses except from local ip
