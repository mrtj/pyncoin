# pynaive

This project is a python port of [Naivecoin](https://github.com/lhartikk/naivecoin), an excellent tutorial that lets you implement a fully functioning blockchain in TypeScript of educational purposes.

## Description

In this repo you find the implementation of a full node for the pynaive blockchain. Only the features strictly necessary to make the node work are implemented. 

As a user interface the node starts a simple web server that provides the following REST services:

 - `GET /blocks`: Returns the blockchain known to this node
 - `POST /mineBlock`: Mines a new block. Include the data you wish to put in the block as a string in the `data` parameter.
 - `GET /peers`: Returns the list of the peers known to this node
 - `POST /addPeer`: Adds a new peer to the node. The node does not discover other nodes, you should add them manually calling this service and passing the address of the peer node in `ws://127.0.0.1:6000` format in the `peer` parameter.

The blockchain is not persisted by the node, it is kept only in the memory.

pynaive also manages a WebSocket interface to communcicate with peer nodes.

## Getting Started

### Dependencies

pynaive depends on the following python libraries:

 - [twisted](https://github.com/twisted/twisted)
 - [autobahn](https://github.com/crossbario/autobahn-python)
 - [flask](https://github.com/pallets/flask)
 - [bitstring](https://github.com/scott-griffiths/bitstring)

pynaive is developed and tested on python 3.

### Installing

Install the dependent libraries above and check out the contents of this repository into a separate folder.

### Executing program

Start the node by passing the port number of the web server and the p2p server to `main.py`:

```
python main.py 5000 6000
```

This command starts a web server at `127.0.0.1:5000` and a p2p node at `127.0.0.1:6000`. You can communicate with the web server with the simple API described in the introduction of the readme, for example:

```
curl -d "data=Hello+World%21" -X POST http://127.0.0.1:5000/mineBlock
curl http://127.0.0.1:5000/blocks
```

If you want, you can also start a second node on the same machine with different ports:

```
python main.py 5001 6001
```

And connect the two nodes:

```
curl -d "peer=ws%3A%2F%2F127.0.0.1%3A6000" -X POST http://127.0.0.1:5000/addPeer
curl http://127.0.0.1:5000/peers
```

## Authors

[@jtolgyesi](http://twitter.com/jtolgyesi)

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments

Many thanks to Lauri Hartikka for his original [tutorial](https://lhartikk.github.io) of Naivecoin
