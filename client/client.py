import sys
import requests
from ast import literal_eval


def print_transaction_inputs(data):
    print("\t\tinputs:")
    for dict_item in data:
        print("\n\t\t\ttransaction_input")
        for key in dict_item:
            print("\t\t\t{}: {},".format(key,str(dict_item[key])[:100]))

def print_transaction_outputs(data):
    print("\t\toutputs:")
    for dict_item in data:
        print("\n\t\t\ttransaction_output")
        for key in dict_item:
            print("\t\t\t{}: {},".format(key,str(dict_item[key])[:100]))

def print_block(data):
    print("Last validated Block:")
    print("\tindex: {},".format(data["index"]))
    print("\tprevious_hash: {},".format(data["previous_hash"]))
    print("\ttimestamp: {},".format(data["timestamp"]))
    print("\ttransactions:")
    for dict_item in data["transactions"]:
        print("\n\t\ttransaction")
        for key in dict_item:
            if key == 'inputs':
                print_transaction_inputs(dict_item[key])
            elif key == 'outputs':
                print_transaction_outputs(dict_item[key])
            else:
                print("\t\t{}: {},".format(key,str(dict_item[key])[:100]))
    print("\tnonce: {},".format(data["nonce"]))
    print("\tcurrent_hash: {},".format(data["current_hash"]))

def err_print(status_code):
    if not (status_code == requests.codes.ok):
        print("Some error occurred\n")
        quit()

if sys.argv[1] == 't':
    payload = {
        "dst": int(sys.argv[2]),
        "amount": int(sys.argv[3])
    }
    r = requests.get("http://localhost:" + sys.argv[4] + "/transaction", json=payload)
    err_print(r.status_code)

elif sys.argv[1] == 'view':
    r =  requests.get("http://localhost:" + sys.argv[2] + "/history")
    err_print(r.status_code)
    print_block(literal_eval(r.json()["block"]))

elif sys.argv[1] == 'balance':
    r =  requests.get("http://localhost:" + sys.argv[2] + "/balance")
    err_print(r.status_code)
    print("balance:",r.json()["balance"])

elif sys.argv[1] == '-r':
    filename = sys.argv[2]
    with open(filename, 'r') as f:
        for line in f:
            line = line[2:]
            fields = line.split()
            payload = {
                "dst": int(fields[0]),
                "amount": int(fields[1])
            }
            r = requests.get("http://localhost:" + sys.argv[3] + "/transaction", json=payload)
            err_print(r.status_code)

elif sys.argv[1] == 'help':
    print("t <recipient_address> <amount>: send to recipient_address the amount of NBC coins from the wallet of sender_address.\n")
    print("view: view last transactions of noobcash blockchain's last validated block.\n")
    print("balance: view wallet's balance.")
