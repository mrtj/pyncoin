# pychain/server.py

''' Implements the web server controller interface. '''

from flask import Flask, request, jsonify, abort
from blockchain import Block, Blockchain

class BlockchainFlask(Flask):

    def __init__(self, *args):
        super().__init__(*args)
        self.blockchain = None
        self.p2p_application = None

app = BlockchainFlask(__name__)

@app.route('/blocks')
def blocks():
    print('/blocks')
    return jsonify(app.blockchain.as_list())

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    print('/mineBlock')
    new_block = app.blockchain.generate_next(request.form['data'])
    return jsonify(new_block.as_dict())

@app.route('/peers')
def get_peers():
    print('/peers')
    return jsonify(app.p2p_application.peers())

@app.route('/addPeer', methods=['POST'])
def add_peer():
    address = request.form['peer']
    print('addPeer: {}'.format(address))
    app.p2p_application.connect_to_peer(address)
    return jsonify(True)
