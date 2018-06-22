# pyncoin/server.py

''' Implements the web server controller interface. '''

from decimal import Decimal

from flask import Flask, request, jsonify, abort
from blockchain import Block, Blockchain
from transaction import Transaction, UnspentTxOut
from utils import hex_to_bytes, bytes_to_hex, HttpError

class BlockchainFlask(Flask):

    def __init__(self, *args):
        super().__init__(*args)
        self.blockchain = None
        self.p2p_application = None
        self.wallet = None

app = BlockchainFlask(__name__)

# blockchain

@app.route('/blocks')
def blocks():
    return jsonify(app.blockchain.to_raw())

@app.route('/unspentTransactionOutputs')
def get_unspent_transaction_outputs():
    uTxOs = app.blockchain.unspent_tx_outs
    return jsonify(UnspentTxOut.to_raw_list(uTxOs))

# wallet

@app.route('/myUnspentTransactionOutputs')
def get_my_unspent_transaction_outputs():
    uTxOs = app.blockchain.my_unspent_tx_outs(app.wallet)
    return jsonify(UnspentTxOut.to_raw_list(uTxOs))

@app.route('/balance')
def get_balance():
    balance = app.blockchain.get_balance(app.wallet)
    return jsonify({'balance': balance})

@app.route('/address')
def get_address():
    address = bytes_to_hex(app.wallet.get_public_key())
    return jsonify({'address': address})

# p2p

@app.route('/peers')
def get_peers():
    return jsonify({'peers': app.p2p_application.peers()})

@app.route('/addPeer', methods=['POST'])
def add_peer():
    address = request.form['peer']
    print('addPeer: {}'.format(address))
    result = app.p2p_application.connect_to_peer(address)
    return jsonify({'peer_added':result})

# transactions

@app.route('/mineRawBlock', methods=['POST'])
def mine_raw_block():
    data = request.form['data']
    block = app.blockchain.generate_raw_next_block(data)
    return jsonify(block.to_raw() if block else None)

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    block = app.blockchain.generate_next_block(app.wallet)
    return jsonify(block.to_raw() if block else None)

@app.route('/mineTransaction', methods=['POST'])
def mine_transaction():
    address = hex_to_bytes(request.form['address'])
    amount = Decimal(request.form['amount'])
    block = app.blockchain.generate_next_with_transaction(app.wallet, address, amount)
    return jsonify(block.to_raw() if block else None)

@app.route('/sendTransaction', methods=['POST'])
def send_transaction():
    address = hex_to_bytes(request.form['address'])
    amount = Decimal(request.form['amount'])
    tx = app.blockchain.send_transaction(app.wallet, address, amount)
    return jsonify(tx.to_raw() if tx else None)

@app.route('/transactionPool')
def get_transaction_pool():
    txs = app.blockchain.tx_pool.transactions
    return jsonify(Transaction.to_raw_list(txs))

@app.errorhandler(HttpError)
def handle_http_error(error):
    response = jsonify(error.to_raw())
    response.status_code = error.status_code
    return response
