# pychain/p2p.py

import json

from blockchain import Block, Blockchain, get_blockchain

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory, listenWS
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS

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

    def as_bin(self):
        return self.as_json().encode('utf-8')

    @staticmethod
    def from_dict(json_obj):
        return Message(json_obj['type'], json_obj['data'])

    @staticmethod
    def from_json(json_str):
        return Message.from_dict(json.loads(json_str))

    @staticmethod
    def from_bin(json_bin):
        return Message.from_json(json_bin.decode('utf-8'))

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
        return Message(Message.RESPONSE_BLOCKCHAIN, [blockchain.get_latest().as_dict()])

# ----------------------------

class Engine:

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
        if not Block.is_valid_block_structure(latest_block_received):
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

    def __init__(self):
        self.remote_clients = []
        self.local_clients = []

    def remote_peers(self):
        return [client.peer for client in self.remote_clients]

    def local_peers(self):
        return [client.peer for client in self.local_clients]

    def register_remote_client(self, remote_client):
        if remote_client.peer not in self.remote_peers():
            print("registered remote client {}".format(remote_client.peer))
            self.remote_clients.append(remote_client)

    def unregister_remote_client(self, remote_client):
        if remote_client.peer in self.remote_peers():
            print("unregistered remote client {}".format(remote_client.peer))
            self.remote_clients.remove(remote_client)

    def register_local_client(self, local_client):
        if local_client.peer not in self.local_peers():
            print("registered local client {}".format(local_client.peer))
            self.local_clients.append(local_client)

    def unregister_local_client(self, local_client):
        if local_client.peer in self.local_peers():
            print("unregistered remote client {}".format(local_client.peer))
            self.local_clients.remove(local_client)

    def broadcast(self, protocol, message):
        print("broadcasting message '{}' ..".format(message.as_json()))
        preparedMsg = protocol.factory.prepareMessage(message.as_bin())
        for client in self.local_clients + self.remote_clients:
            client.send_prepared_message(preparedMsg)
            print("message sent to client {}".format(client.peer))

    def peers(self):
        return [client.peer for client in self.local_clients + self.remote_clients]

class IChannel:

    def send_message(self, message):
        raise AssertionError('IBlockchainTransport.sendMessage abstract method called.')

    def send_prepared_message(self, message):
        raise AssertionError('IBlockchainTransport.send_prepared_message abstract method called.')

    def broadcast(self, message):
        raise AssertionError('IBlockchainTransport.broadcast abstract method called.')

    def peer(self):
        raise AssertionError('IBlockchainTransport.broadcast abstract method called.')

# ---------

class ServerFactory(WebSocketServerFactory):

    def __init__(self, url, engine, broadcaster):
        WebSocketServerFactory.__init__(self, url)
        self.engine = engine
        self.broadcaster = broadcaster

class ServerProtocol(WebSocketServerProtocol, IChannel):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.register_remote_client(self)
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
        self.factory.broadcaster.unregister_remote_client(self)

    # IChannel impl

    def send_message(self, message):
        self.sendMessage(message.as_bin())

    def send_prepared_message(self, message):
        self.sendPreparedMessage(message)

    def broadcast(self, message):
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.broadcast(self, message)


class ClientFactory(WebSocketClientFactory):

    def __init__(self, url, engine, broadcaster, reactor):
        WebSocketClientFactory.__init__(self, url=url, reactor=reactor)
        self.engine = engine
        self.broadcaster = broadcaster

class ClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Client connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.register_local_client(self)
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
        self.factory.broadcaster.unregister_local_client(self)

    # IChannel impl

    def send_message(self, message):
        self.sendMessage(message.as_bin())

    def send_prepared_message(self, message):
        self.sendPreparedMessage(message)

    def broadcast(self, message):
        # pylint: disable=maybe-no-member
        self.factory.broadcaster.broadcast(self, message)


class Application:

    def __init__(self, reactor):
        self.blockchain = get_blockchain()
        self.engine = Engine(self.blockchain)
        self.broadcaster = Broadcaster()
        self.reactor = reactor

    def start_server(self, url):
        server_factory = ServerFactory(url, self.engine, self.broadcaster)
        server_factory.protocol = ServerProtocol
        listenWS(server_factory)

    def connect_to_peer(self, url):
        client_factory = ClientFactory(url, self.engine, self.broadcaster, self.reactor)
        client_factory.protocol = ClientProtocol
        connectWS(client_factory)

    def peers(self):
        return self.broadcaster.peers()

from twisted.internet import reactor

application = Application(reactor)

# class BlockchainServer(WebSocketServer):

#     def peers(self):
#         return ['{}:{}'.format(client.address[0], client.address[1]) for client in self.clients.values()]

#     def connect_to_peer(self, address):
#         print('Creating socket connection...')
#         sock = socket.create_connection(address)
#         print('handling new socket...')
#         self.handle(sock, address)

# server = BlockchainServer(
#     ('', 8001),
#     Resource(OrderedDict([('/', BlockchainApplication)]))
# )

