import struct
import json
import functools
import redis


# Storage
# - Node id         util:node_id         unsigned int
# - Nodes           util:nodes           unsigned int


# Use these to have a compact and cacheable json representation
dumps = functools.partial(json.dumps, separators=(',', ':'), sort_keys=True)
loads = json.loads

UI = struct.Struct("!I")
D = struct.Struct("!d")


def uitob(i: int) -> bytes:
    """unsigned int to bytes"""
    return UI.pack(i)


def dtob(d: float) -> bytes:
    """double to bytes"""
    return D.pack(d)


def btoui(b: bytes) -> int:
    """bytes to unsigned int"""
    return UI.unpack(b)[0]


def btod(b: bytes) -> float:
    """bytes to double"""
    return D.unpack(b)[0]


def get_db(db=0):   # TODO OPT: annotate this (what's the return value of redis.Redis()?)
    return redis.Redis(db=db)


def get_ip():   # TODO: Argument(s) and return value(s)
    # TODO
    raise NotImplementedError


def set_ip():   # TODO: Argument(s) and return value(s)
    # TODO
    raise NotImplementedError


def get_node_id() -> int:
    r = get_db()
    return btoui(r.get("util:node_id"))


def set_node_id(node_id: int) -> None:
    r = get_db()
    r.set("util:node_id", uitob(node_id))


def get_nodes() -> int:
    r = get_db()
    return btoui(r.get("util:nodes"))


def set_nodes(nodes: int) -> None:
    r = get_db()
    r.set("util:nodes", uitob(nodes))
