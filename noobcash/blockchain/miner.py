import sys
import os
import logging
import time
from noobcash.blockchain.block import Block
from noobcash.blockchain import util, blockchain
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
    # If '-echo' is specified as a second command line argument, just print the
    # block to stdout (don't add it to the local blockchain and don't broadcast
    # it on the network)
    ECHO = sys.argv[2] == "-echo" if len(sys.argv) > 2 else False

    logging.debug("Miner %d DIFFICULTY %d ECHO %s", os.getpid(), DIFFICULTY, str(ECHO))

    b = Block.loads(sys.stdin.read())
    b.timestamp = int(time.time())

    h = b._partial_hash()

    logging.debug("Miner %d prev %s", os.getpid(), util.bintos(b.previous_hash))

    # TODO OPT: Profile and probably reimplement / optimize this (a DIFFICULTY
    # of up to ~20 is no problem, takes 1-2 seconds only)

    tstart = time.time()
    nonce = 0   # TODO OPT: Initialize nonce to a random value instead?
    while True:
        h2 = h.copy()
        h2.update(util.uitob(nonce))
        digest = h2.digest()
        if _check_difficulty(digest, DIFFICULTY):
            logging.debug("Miner %d finished (nonce %d, current %s, mining time %f)", os.getpid(),
                          nonce, util.bintos(digest), time.time() - tstart)
            b.nonce = nonce
            b.current_hash = digest
            r = util.get_db()
            if not ECHO:
                # Insert the block into our blockchain before clearing
                # miner_pid, so that a new miner will built on this block
                blockchain.new_recv_block(b, util.get_node_id())
            # Clear miner_pid to allow for another miner to start. We delay
            # broadcasting the block because it is an expensive procedure and
            # it shouldn't block a new miner from starting
            with r.lock("blockchain:miner_pid:lock"):
                r.delete("blockchain:miner_pid")
            logging.debug("Miner %d cleared", os.getpid())
            if ECHO:
                print(b.dumps())
            else:
                logging.debug("Miner %d broadcasting", os.getpid())
                # NOTE: We do a blocking broadcast, because otherwise the
                # process will just terminate before actually making the
                # requests (the requests are still sent concurrently).
                # NOTE: If this takes a long time, miner processes are likely
                # to gather if we are saturated with new transactions, since
                # at this point we have cleared miner_pid and a new miner is
                # free to start
                chatter.broadcast_block(b, util.get_peer_ids(), blocking=True)

            break
        else:
            nonce += 1
