# pychain/server.py

''' Implements the web server controller interface. '''

from flask import Flask, request, jsonify, abort
from blockchain import Block, Blockchain, get_blockchain
from p2p import application as p2p_application
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

@app.route('/blocks')
def blocks():
    print('/blocks')
    return jsonify(get_blockchain().as_list())

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    print('/mineBlock')
    new_block = get_blockchain().generate_next(request.form['data'])
    return jsonify(new_block.as_dict())

@app.route('/peers')
def get_peers():
    print('/peers')
    return jsonify(p2p_application.peers())

@app.route('/addPeer', methods=['POST'])
def add_peer():
    address = request.form['peer']
    print('addPeer: {}'.format(address))
    p2p_application.connect_to_peer(address)
    return jsonify(True)
