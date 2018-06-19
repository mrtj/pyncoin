# pychain/p2p.py

''' Implements the p2p node of the blockchain. '''

import json

from blockchain import Block, Blockchain

from autobahn.twisted.websocket import WebSocketAdapterProtocol
from autobahn.websocket.protocol import WebSocketProtocol
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory, listenWS
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS

class Message:
    ''' Represents a message sent on the blockchain p2p protocol. '''

    # Message types:
    QUERY_LATEST = 0
    QUERY_ALL = 1
    RESPONSE_BLOCKCHAIN = 2

    def __init__(self, message_type, data):
        ''' Initializes the Message.
        Parameters:
            - message_type (int): The message type.
            - data (any): A json-serializable data object
        '''
        self.message_type = message_type
        self.data = data

    def as_dict(self):
        ''' Converts the Message to a dictionary. '''
        return {
            'type': self.message_type,
            'data': self.data
        }

    def as_json(self):
        ''' Converts the Message to a json string. '''
        return json.dumps(self.as_dict())

    def as_bin(self):
        ''' Converts the Message to a binary format. '''
        return self.as_json().encode('utf-8')

    @staticmethod
    def from_dict(json_obj):
        ''' Returns a new Message initialized from a dictionary. '''
        return Message(json_obj['type'], json_obj['data'])

    @staticmethod
    def from_json(json_str):
        ''' Returns a new Message initialized from a json string. '''
        return Message.from_dict(json.loads(json_str))

    @staticmethod
    def from_bin(json_bin):
        ''' Returns a new Message initialized from the binary format. '''
        return Message.from_json(json_bin.decode('utf-8'))

    @staticmethod
    def query_chain_length_message():
        ''' Creates a new "query latest block" message. '''
        return Message(Message.QUERY_LATEST, None)

    @staticmethod
    def query_all_message():
        ''' Creates a new "query blockchain" message. '''
        return Message(Message.QUERY_ALL, None)

    @staticmethod
    def response_chain_message(blockchain):
        ''' Creates a new "blockchain response" message. '''
        return Message(Message.RESPONSE_BLOCKCHAIN, blockchain.as_list())

    @staticmethod 
    def response_latest_message(blockchain):
        ''' Creates a new "latest block response" message. '''
        return Message(Message.RESPONSE_BLOCKCHAIN, [blockchain.get_latest().as_dict()])

# ----------------------------

class Engine:
    ''' The business logic of the p2p client that interacts with the 
    current copy of the blockchain.'''

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def handle_socket_open(self, channel):
        channel.send_message(Message.query_chain_length_message())

    def handle_socket_close(self, channel):
        pass

    def handle_message(self, channel, message):
        if message.message_type == Message.QUERY_LATEST:
            channel.send_message(Message.response_latest_message(self.blockchain))
        elif message.message_type == Message.QUERY_ALL:
            channel.send_message(Message.response_chain_message(self.blockchain))
        elif message.message_type == Message.RESPONSE_BLOCKCHAIN:
            if not isinstance(message.data, list):
                print('Invalid blocks received: {}'.format(message.data))
            else:
                received_blocks = [Block.from_dict(block_dict) for block_dict in message.data]
                self.handle_blockchain_response(channel, received_blocks)
        else:
            print('Unknown message type: {}'.format(message.message_type))

    def handle_blockchain_response(self, channel, received_blocks):
        if not received_blocks:
            print('received block chain size of 0')
            return
        latest_block_received = received_blocks[-1]
        if not latest_block_received.has_valid_structure():
            print('block structure is not valid')
            return
        latest_block_held = self.blockchain.get_latest()
        if latest_block_received.index > latest_block_held.index:
            print('blockchain possibly behind. We got: {} Peer got: {}'
                    .format(latest_block_held.index, latest_block_received.index))
            if latest_block_held.hash == latest_block_received.previous_hash:
                if self.blockchain.add_block(latest_block_received):
                    print('We are behind just one block, add it to our blockchain')
                    channel.broadcast(Message.response_latest_message(self.blockchain))
            elif len(received_blocks) == 1:
                print('We have to query the chain from our peer')
                channel.broadcast(Message.query_all_message())
            else:
                print('Received blockchain is longer than current blockchain')
                self.blockchain.replace(received_blocks)
        else:
            print('received blockchain is not longer than current blockchain. Do nothing')


class Broadcaster:
    ''' Administers the clients connected to this node and broadcasts messages to all of them.'''

    def __init__(self):
        self.clients = []

    def peers(self):
        return [client.peer for client in self.clients]

    def register_client(self, client):
        if client.peer not in self.peers():
            print("registered client {}".format(client.peer))
            self.clients.append(client)

    def unregister_client(self, client):
        if client.peer in self.peers():
            print("unregistered remote client {}".format(client.peer))
            self.clients.remove(client)

    def broadcast(self, message):
        print("broadcasting message '{}' ..".format(message.as_json()))
        if not self.clients:
            return
        preparedMsg = self.clients[0].factory.prepareMessage(message.as_bin())
        for client in self.clients:
            client.send_prepared_message(preparedMsg)
            print("message sent to client {}".format(client.peer))

class IChannel:
    ''' Abstract interface of a websocket communication channel. '''

    def send_message(self, message):
        raise AssertionError('IBlockchainTransport.sendMessage abstract method called.')

    def send_prepared_message(self, message):
        raise AssertionError('IBlockchainTransport.send_prepared_message abstract method called.')

    def broadcast(self, message):
        raise AssertionError('IBlockchainTransport.broadcast abstract method called.')

    def peer(self):
        raise AssertionError('IBlockchainTransport.broadcast abstract method called.')

# ---------

class BlockchainFactory:
    ''' Base class for ServerFactory and ClientFactory. 
    These classes create ServerProtocol or ClientProtocol instances. '''

    def __init__(self, engine, broadcaster):
        self.engine = engine
        self.broadcaster = broadcaster

class BlockchainPrototocol(WebSocketAdapterProtocol, WebSocketProtocol, IChannel):
    ''' Base class for both ServerProtocol and ClientProtocol. 
    This class is responsibile to handle a single peer, both as a server or as a client. '''

    def onConnect(self, response):
        print("Protocol connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.register_client(self)
        self.factory.engine.handle_socket_open(self)

    def onMessage(self, payload, isBinary):
        if not payload:
            print('Empty message received')
            return
        message = Message.from_bin(payload)
        print('Received message: {}'.format(message.as_json()))
        # pylint: disable=maybe-no-member
        self.factory.engine.handle_message(self, message)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
        # pylint: disable=maybe-no-member
        self.factory.engine.handle_socket_close(self)
        self.factory.broadcaster.unregister_client(self)

    # IChannel impl

    def send_message(self, message):
        self.sendMessage(message.as_bin())

    def send_prepared_message(self, message):
        self.sendPreparedMessage(message)

    def broadcast(self, message):
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.broadcast(message)


class ServerFactory(BlockchainFactory, WebSocketServerFactory):

    def __init__(self, url, engine, broadcaster):
        BlockchainFactory.__init__(self, engine, broadcaster)
        WebSocketServerFactory.__init__(self, url)

class ServerProtocol(BlockchainPrototocol, WebSocketServerProtocol):
    pass


class ClientFactory(BlockchainFactory, WebSocketClientFactory):

    def __init__(self, url, engine, broadcaster):
        BlockchainFactory.__init__(self, engine, broadcaster)
        WebSocketClientFactory.__init__(self, url=url)

class ClientProtocol(BlockchainPrototocol, WebSocketClientProtocol):
    pass

class Application:
    ''' The external interface of the p2p node. '''

    def __init__(self, blockchain):
        self.engine = Engine(blockchain)
        self.broadcaster = Broadcaster()

    def start_server(self, url):
        server_factory = ServerFactory(url, self.engine, self.broadcaster)
        server_factory.protocol = ServerProtocol
        listenWS(server_factory)

    def connect_to_peer(self, url):
        client_factory = ClientFactory(url, self.engine, self.broadcaster)
        client_factory.protocol = ClientProtocol
        connectWS(client_factory)

    def peers(self):
        return self.broadcaster.peers()

    def broadcast_blockchain(self, blockchain):
        self.broadcaster.broadcast(Message.response_chain_message(blockchain))

    def broadcast_latest(self, blockchain):
        self.broadcaster.broadcast(Message.response_latest_message(blockchain))
