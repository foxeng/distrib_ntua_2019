import sys
import os
import logging
import time
from noobcash.blockchain.block import Block
from noobcash.blockchain import util
from noobcash.chatter import chatter


def _check_difficulty(digest: bytes, difficulty: int) -> bool:
    target = (1 << (256 - difficulty)) - 1
    return digest <= target.to_bytes(256 // 8, byteorder="big")


if __name__ == "__main__":
    logging.basicConfig(filename=os.path.dirname(__file__) + "/miner.log",
                        filemode="a",
                        level=logging.DEBUG)

    logging.debug("Miner %d started", os.getpid())

    DIFFICULTY = int(sys.argv[1])
    # If '-echo' is specified as a second command line argument, echo to stdout
    # rather than broadcasting on the network (for testing purposes)
    ECHO = sys.argv[2] == "-echo" if len(sys.argv) > 2 else False

    logging.debug("Miner %d DIFFICULTY %d ECHO %s", os.getpid(), DIFFICULTY, str(ECHO))

    b = Block.loads(sys.stdin.read())
    b.timestamp = int(time.time())

    h = b._partial_hash()

    logging.debug("Miner %d prev %s", os.getpid(), util.bintos(b.previous_hash))

    # TODO OPT: Profile and probably reimplement / optimize this (a DIFFICULTY
    # of up to ~20 is no problem, takes 1-2 seconds only)

    nonce = 0   # TODO OPT: Initialize nonce to a random value instead?
    while True:
        h2 = h.copy()
        h2.update(util.uitob(nonce))
        digest = h2.digest()
        if _check_difficulty(digest, DIFFICULTY):
            logging.debug("Miner %d finished (nonce %d, current %s)", os.getpid(), nonce,
                          util.bintos(digest))
            b.nonce = nonce
            b.current_hash = digest
            r = util.get_db()
            with r.lock("blockchain:miner_pid:lock"):
                r.delete("blockchain:miner_pid")
            logging.debug("Miner %d cleared", os.getpid())
            if ECHO:
                print(b.dumps())
            else:
                logging.debug("Miner %d broadcasting to 0-%d", os.getpid(), util.get_nodes())
                # TODO OPT: Call new_recv_block(b) instead of sending the block
                # to ourself? Is it enough?
                # NOTE: We do a blockcing broadcast, because otherwise the process will just
                # terminate before actually making the requests
                chatter.broadcast_block(b, list(range(util.get_nodes())), blocking=True)

            break
        else:
            nonce += 1
