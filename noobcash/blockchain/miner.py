import sys
import time
from noobcash.blockchain.block import Block
from noobcash.blockchain.util import uitob


# TODO: Is killing this process while mining ok (see redis)? Do we need to
# implement a SIGTERM handler to terminate gracefully?


def _check_difficulty(digest: bytes, difficulty: int) -> bool:
    target = (1 << (256 - difficulty)) - 1
    return digest <= target.to_bytes(256 // 8, byteorder="big")


if __name__ == "__main__":
    DIFFICULTY = int(sys.argv[1])
    # If '-echo' is specified as a second command line argument, echo to stdout
    # rather than broadcasting on the network (for testing purposes)
    ECHO = sys.argv[2] == "-echo" if len(sys.argv) > 2 else False

    block = Block.loads(sys.stdin.read())
    block.timestamp = int(time.time())

    h = block._partial_hash()

    # TODO OPT: Profile and probably reimplement / optimize this (a DIFFICULTY
    # of up to ~20 is no problem, takes 1-2 seconds only)

    nonce = 0   # TODO OPT: Initialize nonce to a random value instead?
    while True:
        h2 = h.copy()
        h2.update(uitob(nonce))
        digest = h2.digest()
        if _check_difficulty(digest, DIFFICULTY):
            block.nonce = nonce
            block.current_hash = digest
            if ECHO:
                print(block.dumps())
            else:
                # TODO: Broadcast the block. Send it to ourselves as well?
                raise NotImplementedError

            break
        else:
            nonce += 1
