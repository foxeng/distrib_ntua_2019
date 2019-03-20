from noobcash.blockchain.wallet import PrivateKey

PRIVKEYSB = [
    b'-----BEGIN PRIVATE KEY-----\n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\nPZHiMx0c4CYfAEf/CN0Pv1O7uHqDJjci\n-----END PRIVATE KEY-----\n',
    b'-----BEGIN PRIVATE KEY-----\n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\nx66KqohtK0H7JTK6BcmxrpEFMvzOE1n3/g==\n-----END PRIVATE KEY-----\n',
    b'-----BEGIN PRIVATE KEY-----\n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\njAJ5iE9qo8SrGMKoeg7zV7dDbgpn42Z8\n-----END PRIVATE KEY-----\n',
    b'-----BEGIN PRIVATE KEY-----\n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\nI2zPEZvXSD3V+FaTqLNEWRQbI7Jo\n-----END PRIVATE KEY-----\n',
    b'-----BEGIN PRIVATE KEY-----\n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\ncrq1OqfhVa4dQZ9Z1MqsNw7zR6GV\n-----END PRIVATE KEY-----\n'
]
PRIVKEYS = [PrivateKey.loadb(kb) for kb in PRIVKEYSB]
PUBKEYS = [k.public_key() for k in PRIVKEYS]
PUBKEYSB = [k.dumpb() for k in PUBKEYS]

NODES = len(PRIVKEYSB)
NODE_ID = 0
CAPACITY = 3
DIFFICULTY = 4

TRANSACTION_DATA = [
    {   # #0 0 -> 1: 100
        "recipient": 1,    # node id
        "amount": 100,
        "inputs": [
            {
                "transaction_id": -1,   # the genesis transaction
                "index": 0
            }
        ],
        "input_amount": 100 * NODES
    },
    {   # #1 1 -> 0: 12.5 (easier to calculate a whole transaction early on)
        "recipient": 0,
        "amount": 12.5,
        "inputs": [
            {
                "transaction_id": 0,    # not the actual id, but an index into this list
                "index": 0
            }
        ],
        "sender": 1,
        "outputs": [
            {
                "index": 0,
                "recipient": 0,
                "amount": 12.5
            },
            {
                "index": 1,
                "recipient": 1,
                "amount": 100 - 12.5
            }
        ],
        # NOTE: The following must be updated if there's any change in the previous transactions
        "id_": b"\x85\xd0Ed\xd5x\xd2\x8a\xa1\xa7'\x82\xd7eS\xfdf\xc9)\xec9\x19x\x16AH\x95A\x19\x8a\x8bA",
        "signature": b'S\xb4\x1eC\x9ea\xd1m*3o\xcd\xb0\xaf\xf7\x13\x03\x81S\x86\x1d\xf6\xd5\xee\xb2\x85\xaeN\xee\xa6\xe4z=bW\x9e\xc4\x16\x12Z\x85\xbd{\xa1\xf1Q2 \xff\xcb\x82\xbe\x881M4\x97\x98\x11\x85\xcc\x12e\x1a`\x0f"8\xeb1\xab\x92\x9cT\x8cNQ5\xf8t\xa6\tJ`\xec\xd2\x93\xe0sH\xd8\xe1E\x87T\x18s\xc2n\xc8\x8d\xa4\xeaE\x84FS4.\x86\x18\xa3\xb7\xf7.\xdeds\x19\x87\x86\x1dD\x1d~~\x96\xe1\x99,\xa2\xe2\x957\xe1\xdf\xa2\xd0I\x89\x05ca\xed\xc3,f/\xb7\x12\r\xa8U\xac\xbfX\xb7\x9d\xda\xbd\xc7e\xc26\xc3%\xb5\xfd\xe7*_]\x8d:p6j\xc6\xeeb\xb0\xdd\xc4\xf9\xe3\x94\xb3HM \xdano+9 rlv\xea\x08=\x16a\xc6i\xa7U6?ZX\xd0^\xd9F\xfb"\xc6\x95\xd7!\xf6\xc01\xfa\x85\x13\xcee\xa2\x19\x1b\xd4\xa2\xe4\x9e\xedn\xa8\x8d0C\xbb\x8f\xd3\x99\xcd\x05\x8ez\xbfecf[y\xaf\x17G\x90\x8e\x88"\xde\x8aZfq\xd2\x83\x94\x9e\x8f\xeb\x121\xa3\xd7\xf8\xba\xb9\xcaOM\x9a\xf8\xc0\x90\xdc\x1b\x800\x17\x95\xfa\x87\x83+\t\x01\x8f\x06\x99\r\xf6\x0e\t\\\xf9\x19\xdd\x13mB\xdb\xf7.{\x0e\xe2\xe8\x19\xf1\xe2\x1a\xdf\x8c\xcaj\xda[\xba^5\xf3>\x07\xb6m}\xc8[\xd6\x12l\xdc\xa8\xb3\xf0t\x1e\x97\x80\xfeX\x16\r\x81\xb1q\xdf\xb0M\x06\xc5\xf8\x7f\nWs\xbe\xb4>R%\xb2\xbe\x9f\x8a\x97\xd0\x9b\x12\xaf\x1a\x90\xa2\xf7w\x14]\xf1\xf4\xc9\xc5\xc4bz\xe7\x01\xd4\xc6\x8eG<F\xea%[\xa6~r\xd9/T\x04WHHl\x81\x88o,\x9a\rH\x16\xf4Y\xf2*3X9E\xd8\x1d\xc8\x1a\r\xca\xed2\xf5\xa6\x82\x03\x04 \xa0n\xee\xa84\xd6O]]U\x9dj\xf86r\x9c\xb6\xe7_p\x91a1"2\xca\x0b;\xf5B\x95\xff\xf6\x8fB3\xddX-q\x12\xa3\xe0\xe7*\x18A?\x9b\x7faC\xe8Q\xed\xc7%\xbb\x1e\xac='
    },
    {   # #2 0 -> 2: 100
        "recipient": 2,
        "amount": 100,
        "inputs": [
            {
                "transaction_id": 0,
                "index": 1
            }
        ],
        "input_amount": 100 * NODES - 100
    },
    {   # #3 0 -> 3: 100
        "recipient": 3,
        "amount": 100,
        "inputs": [
            {
                "transaction_id": 2,
                "index": 1
            }
        ],
        "input_amount": 100 * NODES - 2 * 100
    },
    {   # #4 0 -> 4: 100
        "recipient": 4,
        "amount": 100,
        "inputs": [
            {
                "transaction_id": 3,
                "index": 1
            }
        ],
        "input_amount": 100 * NODES - 3 * 100
    },
    {   # #5 0 -> 1: 7
        "recipient": 1,
        "amount": 7,
        "inputs": [
            {
                "transaction_id": 1,
                "index": 0
            },
            {
                "transaction_id": 4,
                "index": 1
            }
        ],
        "input_amount": 100 + 12.5
    },
    {   # #6 0 -> 2: 8
        "recipient": 2,
        "amount": 8,
        "inputs": [
            {
                "transaction_id": 5,
                "index": 1
            }
        ],
        "input_amount": 100 + 12.5 - 7
    },
    {   # #7 3 -> 2: 6
        "recipient": 2,
        "amount": 6,
        "inputs": [
            {
                "transaction_id": 3,
                "index": 0
            }
        ],
        "sender": 3,    # the right transaction will be created if we specify only the sender
        "input_amount": 100
    },
    {   # #8 2 -> 4: 4
        "recipient": 4,
        "amount": 4,
        "inputs": [
            {
                "transaction_id": 7,
                "index": 0
            }
        ],
        "sender": 2,
        "input_amount": 6
    },
    {   # #9 0 -> 2: 7
        "recipient": 2,
        "amount": 7,
        "inputs": [
            {
                "transaction_id": 6,
                "index": 1
            }
        ],
        "input_amount": 100 + 12.5 - 7 - 8
    }
]

BLOCK_DATA = {
    "valid": [
        {
            "index": 1,
            "previous_hash": -1,    # the genesis block
            "transactions": [0, 2, 3]   # indices into TRANSACTION_DATA
        },
        {
            "index": 2,
            "previous_hash": 0,    # not the actual hash, but an index into this list
            "transactions": [1, 4, 5]
        }
    ],
    "invalid": [
        {
            "index": 12345,
            "previous_hash": 0,
            "transactions": [1, 4, 5]
        },
        {
            "index": 2,
            "previous_hash": 0,
            "transactions": [1] * CAPACITY
        },
        {
            "index": 2,
            "previous_hash": 0,
            "transactions": [1, 2, 3]
        },
        {
            "index": 2,
            "previous_hash": 0,
            "transactions": [5, 4, 1]
        }
    ]
}
