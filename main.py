# pchain/main.py

import threading
from gevent import monkey

from webserver import server as web_server
from p2p import server as p2p_server

if __name__ == '__main__':
    monkey.patch_thread()
    t = threading.Thread(target=p2p_server.serve_forever)
    t.setDaemon(True)
    t.start()
    web_server.serve_forever()