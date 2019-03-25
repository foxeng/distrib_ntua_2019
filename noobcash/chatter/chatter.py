from concurrent.futures import ThreadPoolExecutor
import itertools
import requests
from noobcash.blockchain.util import get_ip, bintos


def send_post_request(node_id, payload, arg):
    requests.post("http://" + get_ip(node_id)["ipAddr"] + ":" + get_ip(node_id)["port"] + \
                      "/" + arg, json=payload)


def send_get_request(node_id, payload, arg):
    requests.get("http://" + get_ip(node_id)["ipAddr"] + ":" + get_ip(node_id)["port"] + \
                     "/" + arg, json=payload)


# TODO OPT: Rename to multicast (since that's what it does)? Or leave out the
# node_ids and just broadcast to all the peers?
def broadcast_transaction(trans_data, node_ids, blocking=False):
    payload = {"transData": trans_data.dumps()}
    # TODO OPT: Use asyncio instead of threads?
    with ThreadPoolExecutor() as executor:
        executor.map(send_post_request,
                     node_ids, itertools.repeat(payload), itertools.repeat("transaction"))


# TODO OPT: Rename to multicast (since that's what it does)? Or leave out the
# node_ids and just broadcast to all the peers?
def broadcast_block(block_data, node_ids, blocking=False):
    payload = {"blockData": block_data.dumps()}
    # TODO OPT: Use asyncio instead of threads?
    with ThreadPoolExecutor() as executor:
        executor.map(send_post_request,
                     node_ids, itertools.repeat(payload), itertools.repeat("block"))


# TODO OPT: Rename to multicast (since that's what it does)? Or leave out the
# node_ids and just broadcast to all the peers?
def get_blockid(blockId, node_ids, blocking=False):
    payload = {"block": bintos(blockId)}
    # TODO OPT: Use asyncio instead of threads?
    with ThreadPoolExecutor() as executor:
        executor.map(send_get_request,
                     node_ids, itertools.repeat(payload), itertools.repeat("block"))
