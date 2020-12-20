import requests
import json
import time
import uvicorn
from blockchain_model import Block, Blockchain
from fastapi import FastAPI, Request
from hashlib import sha256
from pydantic import BaseModel
app = FastAPI()

blockchain = Blockchain()
blockchain.create_genesis_block()
peers = set()


@app.post('/')
async def index(request: Request):
    data = await request.json()
    print(data)

@app.post('/new_transaction')
async def new_transaction(request: Request):
    data = await request.json()
    required_fields = ['author', 'content']
    for field in required_fields:
        if not data.get(field):
            return "Invalid transaction data"
    data["timestamp"] = time.time()
    blockchain.add_new_transaction(data)
    
    return "Success", 201


@app.get('/chain')
async def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    
    return {"length":len(chain_data),
            "chain":chain_data,
            "peers":list(peers)}

@app.get('/mine')
async def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            announce_new_block(blockchain.last_block.index)
    
    return f"Block #{blockchain.last_block.index} has been mined."

@app.post('/register_node')
async def register_new_piers(request: Request):
    data = await request.json()
    node_address = data["node_address"]
    peers.add(node_address)
    return await get_chain()

@app.post('/register_with')
async def register_with_existing_node(request: Request):
    data = await request.json()
    node_address = data["node_address"]
    data = {"node_address": str(request.url)}
    headers = {"Content-Type":"application/json"}
    resp = requests.post(node_address + '/register_node', data=json.dumps(data), headers=headers)
    if resp.status_code == 200:
        global blockchain
        global peers
        chain_dump = data['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(data['peers'])
        return "Registered succesfully, 200"
    else:
        return resp.content, resp.status_code


@app.post('/add_block')
async def verify_and_add_block(request: Request):
    data = await request.json()
    block = Block(index=data["index"],
                  transactions=data["transactions"],
                  timestamp=data["timestamp"],
                  previous_hash=data["previous_hash"],
                  nonce=data["nonce"])
    proof = data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by node, 400"
    
    return "Block added to the chain, 201"

@app.get('/pending_tx')
async def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain

def consensus():
    """
    Our naive consnsus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

uvicorn.run(app)
