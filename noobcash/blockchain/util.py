import struct
import json
import functools


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
