import sys
from block import Block
from util import uitob


# TODO: Is killing this process while mining ok (see redis)? Do we need to implement a SIGTERM
# handler to terminate gracefully?


def _check_difficulty(digest: bytes, difficulty: int) -> bool:
    target = (1 << (256 - difficulty)) - 1
    return digest <= target.to_bytes(256 // 8, byteorder="big")


if __name__ == "__main__":
    DIFFICULTY = int(sys.argv[1])
    block = Block.loads(sys.stdin.read())

    h = block._partial_hash()

    # TODO: Profile and probably reimplement / optimize this

    nonce = 0
    while True:
        h2 = h.copy()
        h2.update(uitob(nonce))
        digest = h2.digest()
        if _check_difficulty(digest, DIFFICULTY):
            block.nonce = nonce
            block.current_hash = digest
            # TODO: Broadcast the block

            # TODO: Store the new block. Or send the block to ourself as well?
            break
        else:
            nonce += 1
