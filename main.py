# pyncoin/main.py

''' Implements the CLI of the blockchain node '''

import argparse
import sys

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

from webserver import app as web_app
from p2p import Application as P2PApplication
from blockchain import Blockchain

from twisted.internet.defer import setDebugging
from twisted.logger import globalLogPublisher, textFileLogObserver

log_output = textFileLogObserver(sys.stdout)
globalLogPublisher.addObserver(log_output)

if __name__ == '__main__':

    setDebugging(True)

    parser = argparse.ArgumentParser()
    parser.add_argument('webport', help='web server port', default=5000, type=int)
    parser.add_argument('p2pport', help='p2p server port', default=6000, type=int)
    args = parser.parse_args()

    blockchain = Blockchain()
    p2p_application = P2PApplication(blockchain)
    blockchain.p2p_application =p2p_application
    web_app.blockchain = blockchain
    web_app.p2p_application = p2p_application

    server_url = 'ws://127.0.0.1:{}'.format(args.p2pport)
    print('Starting p2p server at {}'.format(server_url))
    p2p_application.start_server(server_url)
    
    # pylint: disable=maybe-no-member
    resource = WSGIResource(reactor, reactor.getThreadPool(), web_app)
    site = Site(resource)
    print('Starting web server at http://127.0.0.1:{}'.format(args.webport))
    reactor.listenTCP(args.webport, site)
    reactor.run()
