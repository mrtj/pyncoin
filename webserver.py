# pyncoin/server.py

''' Implements the web server controller interface. '''

from decimal import Decimal

from flask import Flask, request, jsonify, abort
from blockchain import Block, Blockchain
from utils import hex_to_bytes

class BlockchainFlask(Flask):

    def __init__(self, *args):
        super().__init__(*args)
        self.blockchain = None
        self.p2p_application = None
        self.wallet = None

app = BlockchainFlask(__name__)

@app.route('/blocks')
def blocks():
    print('/blocks')
    return jsonify(app.blockchain.to_raw())

@app.route('/peers')
def get_peers():
    print('/peers')
    return jsonify(app.p2p_application.peers())

@app.route('/addPeer', methods=['POST'])
def add_peer():
    address = request.form['peer']
    print('addPeer: {}'.format(address))
    result = app.p2p_application.connect_to_peer(address)
    return jsonify(result)

@app.route('/mineRawBlock', methods=['POST'])
def mine_raw_block():
    print('/mineRawBlock')
    data = request.form['data']
    block = app.blockchain.generate_raw_next_block(data)
    return jsonify(block.to_raw() if block else None)

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    print('/mineBlock')
    block = app.blockchain.generate_next_block(app.wallet)
    return jsonify(block.to_raw() if block else None)

@app.route('/mineTransaction', methods=['POST'])
def mine_transaction():
    print('/mineTransaction')
    address = hex_to_bytes(request.form['address'])
    amount = Decimal(request.form['amount'])
    block = app.blockchain.generate_next_with_transaction(app.wallet, address, amount)
    return jsonify(block.to_raw() if block else None)

@app.route('/balance')
def get_balance():
    print('/balance')
    balance = app.blockchain.get_balance(app.wallet)
    return jsonify({'balance': balance})
