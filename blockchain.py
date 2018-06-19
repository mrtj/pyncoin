# pychain/pychain.py

import hashlib
import json
from datetime import datetime, timezone
from bitstring import BitArray

''' Implements the business logic of the blockchain. '''

class Block:
    ''' Represents a block in the blockchain. A block can contain arbitrary data
    in the format of a unicode string. '''

    INT_SIZE = 8
    BYTE_ORDER = 'big'

    def __init__(self, index, previous_hash, timestamp, data, difficulty, nonce):
        '''Initializes the block.
        Params:
            - index (int): The height of the block in the blockchain
            - previous_hash (bytes): A reference to the hash of the previous block. 
                This value explicitly defines the previous block.
            - timestamp (datetime): A timestamp
            - data (str): Any data that is included in the block
            - difficulty (int): The difficulty of the Proof of Work algorithm
            - nonce (int): The nonce of the block
        '''
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.difficulty = difficulty
        self.nonce = nonce
        self.hash = Block.calculate_hash_for_block(self)

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return False

    @staticmethod
    def calculate_hash(index, previous_hash, timestamp, data, difficulty, nonce):
        hasher = hashlib.sha256()
        hasher.update(index.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        if previous_hash is not None:
            hasher.update(previous_hash)
        ts_int = int(timestamp.timestamp())
        hasher.update(ts_int.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        hasher.update(data.encode('utf-8'))
        hasher.update(difficulty.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        hasher.update(nonce.to_bytes(Block.INT_SIZE, byteorder=Block.BYTE_ORDER))
        return hasher.digest()

    @staticmethod
    def calculate_hash_for_block(block):
        return Block.calculate_hash(block.index, block.previous_hash, block.timestamp, 
                                    block.data, block.difficulty, block.nonce)

    @staticmethod
    def find(index, previous_hash, timestamp, data, difficulty):
        nonce = 0
        while True:
            hash = Block.calculate_hash(index, previous_hash, timestamp, data, difficulty, nonce)
            if Block.hash_matches_difficulty(hash, difficulty):
                return Block(index, previous_hash, timestamp, data, difficulty, nonce)
            nonce += 1

    @staticmethod
    def genesis_block():
        timestamp = datetime.fromtimestamp(1528359030, tz=timezone.utc)
        return Block(0, None, timestamp, 'The story begins here!', 0, 0)

    @staticmethod
    def hash_matches_difficulty(hash, difficulty):
        bits = BitArray(bytes=hash)
        required_prefix = '0' * difficulty
        return bits.bin.startswith(required_prefix)

    def hash_matches_block_content(self):
        return Block.calculate_hash_for_block(self) == self.hash

    def has_valid_hash(self):
        if not self.hash_matches_block_content():
            print('invalid hash')
            return False
        elif not Block.hash_matches_difficulty(self.hash, self.difficulty):
            print('block difficulty not satisfied. Expected: {}, got: {}'.format(self.difficulty, self.hash))
            return False
        return True

    @staticmethod
    def is_genesis(block):
        return block == Block.genesis_block()

    def is_valid_next(self, next_block):
        if not next_block.has_valid_structure():
            print('invalid structure')
            return False
        elif self.index + 1 != next_block.index:
            print('invalid index')
            return False
        elif self.hash != next_block.previous_hash:
            print('invalid previous hash')
            return False
        elif not Block.is_valid_timestamp(next_block, self):
            print('invalid timestamp')
            return False
        elif not next_block.has_valid_hash():
            return False
        return True

    def as_dict(self):
        return {
            'index': self.index,
            'previous_hash': self.previous_hash.hex() if self.previous_hash is not None else None,
            'timestamp': int(self.timestamp.timestamp()),
            'data': self.data,
            'difficulty': self.difficulty,
            'nonce': self.nonce,
            'hash': self.hash.hex()
        }

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_dict(json_obj):
        return Block(index=json_obj['index'], 
            previous_hash=bytes.fromhex(json_obj['previous_hash']) if json_obj['previous_hash'] is not None else None, 
            timestamp=datetime.fromtimestamp(json_obj['timestamp'], tz=timezone.utc),
            data=json_obj['data'],
            difficulty=json_obj['difficulty'],
            nonce=json_obj['nonce'])

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return Block.from_dict(json_obj)

    def has_valid_structure(self):
        return (isinstance(self.index, int) 
            and isinstance(self.hash, bytes) 
            and (isinstance(self.previous_hash, bytes) if self.previous_hash is not None else True)
            and isinstance(self.timestamp, datetime) 
            and isinstance(self.data, str)
            and isinstance(self.difficulty, int)
            and isinstance(self.nonce, int))

    @staticmethod
    def is_valid_timestamp(new_block, previous_block):
        return ((previous_block.timestamp - new_block.timestamp).total_seconds() < 60 
            and (new_block.timestamp - datetime.now(tz=timezone.utc)).total_seconds() < 60)

class Blockchain:

    BLOCK_GENERATION_INTERVAL = 10 # in seconds
    DIFFICULTY_ADJUSTMENT_INTERVAL = 10 # in blocks

    def __init__(self):
        self.blocks = [Block.genesis_block()]
        self.p2p_application = None

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
        previous_block = self.get_latest()
        next_index = previous_block.index + 1
        next_timestamp = datetime.now(tz=timezone.utc)
        difficulty = self.get_difficulty()
        print('Blockchain.generate_next: difficulty = {}'.format(difficulty))
        next_block = Block.find(next_index, previous_block.hash, next_timestamp, data, difficulty)
        self.add_block(next_block)
        self.broadcast_latest()
        return next_block

    def broadcast_latest(self):
        self.p2p_application.broadcast_latest(self)

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

    def get_difficulty(self):
        latest_block = self.get_latest()
        if latest_block.index % Blockchain.DIFFICULTY_ADJUSTMENT_INTERVAL == 0 and latest_block.index != 0:
            return self.get_adjusted_difficulty()
        else:
            return latest_block.difficulty

    def get_adjusted_difficulty(self):
        prev_adjusment_block = self.blocks[max(0, len(self.blocks) - Blockchain.DIFFICULTY_ADJUSTMENT_INTERVAL)]
        latest_block = self.get_latest()
        time_expected = Blockchain.BLOCK_GENERATION_INTERVAL * Blockchain.DIFFICULTY_ADJUSTMENT_INTERVAL
        time_taken = (latest_block.timestamp - prev_adjusment_block.timestamp).total_seconds()
        print('prev_adjusment_block.idx: {}, latest_block.idx: {}'.format(prev_adjusment_block.index, latest_block.index))
        print('time_taken: {}, time_expected: {}'.format(time_taken, time_expected))
        if time_taken < time_expected / 2:
            return prev_adjusment_block.difficulty + 1
        elif time_taken > time_expected * 2:
            return max(prev_adjusment_block.difficulty - 1, 0)
        else:
            return prev_adjusment_block.difficulty
