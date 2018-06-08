# pychain/pychain.py

import hashlib
import json
from datetime import datetime, timezone

class Block:

    INT_SIZE = 8 # bytes
    BYTE_ORDER = 'big'

    def __init__(self, index, previous_hash, timestamp, data):
        '''Initializes the block.
        Params:
            - index (int): The height of the block in the blockchain
            - previous_hash (bytes): A reference to the hash of the previous block. 
                This value explicitly defines the previous block.
            - timestamp (datetime): A timestamp
            - data (str): Any data that is included in the block
        '''
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = Block.calculate_hash_for_block(self)

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return False

    @staticmethod
    def calculate_hash(index, previous_hash, timestamp, data):
        hasher = hashlib.sha256()
        hasher.update(index.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        if previous_hash is not None:
            hasher.update(previous_hash)
        ts_int = int(timestamp.timestamp())
        hasher.update(ts_int.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        hasher.update(data.encode('utf-8'))
        return hasher.digest()

    @staticmethod
    def calculate_hash_for_block(block):
        return Block.calculate_hash(block.index, block.previous_hash, block.timestamp, block.data)

    @staticmethod
    def genesis_block():
        timestamp = datetime.fromtimestamp(1528359030, tz=timezone.utc)
        return Block(0, None, timestamp, 'The story begins here!')

    @staticmethod
    def is_genesis(block):
        return block == Block.genesis_block()

    def generate_next(self, data):
        next_index = self.index + 1
        next_timestamp = datetime.utcnow()
        return Block(next_index, self.hash, next_timestamp, data)

    def is_valid_next(self, next_block):
        if self.index + 1 != next_block.index:
            print('invalid index')
            return False
        elif self.hash != next_block.previous_hash:
            print('invalid previous hash')
            return False
        elif Block.calculate_hash_for_block(next_block) != next_block.hash:
            print('invalid hash: {} {}'.format(Block.calculate_hash_for_block(next_block), next_block.hash))
            return False
        return True

    def as_dict(self):
        return {
            'index': self.index,
            'previous_hash': self.previous_hash.hex() if self.previous_hash is not None else None,
            'timestamp': int(self.timestamp.timestamp()),
            'data': self.data,
            'hash': self.hash.hex()
        }

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_dict(json_obj):
        return Block(index=json_obj['index'], 
            previous_hash=bytes.fromhex(json_obj['previous_hash']) if json_obj['previous_hash'] is not None else None, 
            timestamp=datetime.fromtimestamp(json_obj['timestamp'], tz=timezone.utc),
            data=json_obj['data'])

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return Block.from_dict(json_obj)

    @staticmethod
    def is_valid_block_structure(block):
        return (isinstance(block.index, int) 
            and isinstance(block.hash, bytes) 
            and (isinstance(block.previous_hash, bytes) if block.previous_hash is not None else True)
            and isinstance(block.timestamp, datetime) 
            and isinstance(block.data, str))

class Blockchain:

    def __init__(self):
        self.blocks = [Block.genesis_block()]

    def get_latest(self):
        return self.blocks[-1]

    @staticmethod
    def is_valid_chain(blocks):
        if not isinstance(blocks, list):
            print('blocks argument is not a list')
            return False
        elif not Block.is_genesis(blocks[0]):
            print('invalid genesis block')
            return False
        for i in range(1, len(blocks)):
            if not isinstance(blocks[i], Block) or not blocks[i - 1].is_valid_next(blocks[i]):
                print('block #{} is not valid'.format(i))
                return False
        return True

    def is_valid(self):
        return Blockchain.is_valid_chain(self.blocks)

    def add_block(self, block):
        if not isinstance(block, Block):
            raise ValueError('Invalid block.')
        if self.get_latest().is_valid_next(block):
            self.blocks.append(block)
            return True
        return False

    def generate_next(self, data):
        next_block = self.get_latest().generate_next(data)
        self.add_block(next_block)
        self.broadcast_latest()
        return next_block

    def broadcast_latest(self):
        pass

    def replace(self, new_blocks):
        if (isinstance(new_blocks, list) 
            and Blockchain.is_valid_chain(new_blocks) 
            and len(new_blocks) > len(self.blocks)):
            print('Received blockchain is valid. Replacing current blockchain with received blockchain.')
            self.blocks = new_blocks
            self.broadcast_latest()
            return True
        else:
            print('Received blockchain is invalid.')
            return False

    def as_json(self):
        return json.dumps(self.as_list())

    def as_list(self):
        return [block.as_dict() for block in self.blocks]

blockchain = Blockchain()

def get_blockchain():
    return blockchain
