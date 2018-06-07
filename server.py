# pychain/server.py

from flask import Flask, request, jsonify
from pychain.pychain import Block, BlockChain

app = Flask(__name__)
blockchain = BlockChain()

@app.route('/blocks')
def blocks():
    return jsonify(blockchain.as_list())

@app.route('/mineBlock', methods=['POST'])
def mine_block():
    data = request.form['data']
    new_block = blockchain.generate_next(data)
    return jsonify(new_block.as_dict())
