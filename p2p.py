# pychain/p2p.py

import json

from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
from gevent import socket
from collections import OrderedDict

from blockchain import Block, Blockchain, get_blockchain

class Message:

    QUERY_LATEST = 0
    QUERY_ALL = 1
    RESPONSE_BLOCKCHAIN = 2

    def __init__(self, message_type, data):
        self.message_type = message_type
        self.data = data

    def as_dict(self):
        return {
            'type': self.message_type,
            'data': self.data
        }

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_dict(json_obj):
        return Message(json_obj['type'], json_obj['data'])

    @staticmethod
    def from_json(json_str):
        return Message.from_dict(json.loads(json_str))

    @staticmethod
    def query_chain_length_message():
        return Message(Message.QUERY_LATEST, None)

    @staticmethod
    def query_all_message():
        return Message(Message.QUERY_ALL, None)

    @staticmethod
    def response_chain_message(blockchain):
        return Message(Message.RESPONSE_BLOCKCHAIN, blockchain.as_list())

    @staticmethod 
    def response_latest_message(blockchain):
        return Message(Message.RESPONSE_BLOCKCHAIN, [blockchain.get_latest()])

    def write(self, ws):
        ws.send(self.as_json())

    def broadcast(self, app):
        pass

class BlockchainApplication(WebSocketApplication):

    blockchain = get_blockchain()

    def on_open(self):
        print('Connection opened')
        self.ws.send(Message.query_chain_length_message().as_json())

    def on_message(self, message_str):
        if message_str is None:
            print('Empty message received')
            return
        print('Received message: {}'.format(message_str))
        message = Message.from_json(message_str)
        if message.message_type == Message.QUERY_LATEST:
            self.send_message(Message.response_latest_message(BlockchainApplication.blockchain))
        elif message.message_type == Message.QUERY_ALL:
            self.send_message(Message.response_chain_message(BlockchainApplication.blockchain))
        elif message.message_type == Message.RESPONSE_BLOCKCHAIN:
            if not isinstance(message.data, list):
                print('Invalid blocks received: {}'.format(message.data))
            else:
                self.handle_blockchain_response(message.data)
        else:
            print('Unknown message type: {}'.format(message.message_type))

    def on_close(self, reason):
        print('Connection closed with reason: {}'.format(reason))

    def broadcast(self, message):
        for client in self.ws.handler.server.clients.values():
            client.ws.send(message.as_json())

    def send_message(self, message):
        self.ws.send(message.as_json())

    def handle_blockchain_response(self, received_blocks):
        if not received_blocks:
            print('received block chain size of 0')
            return
        latest_block_received = received_blocks[-1]
        if not Block.is_valid_block_structure(latest_block_received):
            print('block structure is not valid')
            return
        latest_block_held = BlockchainApplication.blockchain.get_latest()
        if latest_block_received.index > latest_block_held.index:
            print('blockchain possibly behind. We got: {} Peer got: {}'
                    .format(latest_block_held.index, latest_block_held.index))
            if latest_block_held.hash == latest_block_received.previous_hash:
                if BlockchainApplication.blockchain.add_block(latest_block_received):
                    self.broadcast(Message.response_latest_message(BlockchainApplication.blockchain))
            elif len(received_blocks) == 1:
                print('We have to query the chain from our peer')
                self.broadcast(Message.query_all_message())
            else:
                print('Received blockchain is longer than current blockchain')
                BlockchainApplication.blockchain.replace(received_blocks)
        else:
            print('received blockchain is not longer than received blockchain. Do nothing')

class BlockchainServer(WebSocketServer):

    def peers(self):
        return ['{}:{}'.format(client.address[0], client.address[1]) for client in self.clients.values()]

    def connect_to_peer(self, address):
        print('Creating socket connection...')
        sock = socket.create_connection(address)
        print('handling new socket...')
        self.handle(sock, address)

server = BlockchainServer(
    ('', 8001),
    Resource(OrderedDict([('/', BlockchainApplication)]))
)

