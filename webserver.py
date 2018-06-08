# pychain/server.py

from flask import Flask, request, jsonify, abort
from blockchain import Block, Blockchain, get_blockchain
from p2p import server as p2p_server
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

@app.route('/blocks')
def blocks():
    return jsonify(get_blockchain().as_list())

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    new_block = get_blockchain().generate_next(request.form['data'])
    return jsonify(new_block.as_dict())

@app.route('/peers')
def get_peers():
    return jsonify(p2p_server.peers())

@app.route('/addPeer', methods=['POST'])
def add_peer():
    address = request.form['peer'].split(':')
    if len(address) < 2:
        abort(400)
    print('addPeer: {}'.format(address))
    p2p_server.connect_to_peer((address[0], address[1]))
    return jsonify(True)

server = WSGIServer(('', 5001), app)
