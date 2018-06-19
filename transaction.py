# pychain/transaction.py

import functools
import hashlib
import binascii
import json

import ecdsa

def bytes_to_int(data):
    ''' Converts a binary data to an integer.
        Params:
            - data (bytes): The binary data
        Returns (int): The integer
    '''
    return int(binascii.hexlify(data), 16)

def bytes_to_hex(data):
    ''' Converts a binary data to a hexadecimal string.
        Params:
            - data (bytes): The binary data
        Returns (str): The hexadecimal string
    '''
    return binascii.hexlify(data)

def int_to_bytes(number):
    ''' Converts an integer into binary data.
        Params:
            - number (int): The integer
        Returns (bytes): The binary data
    '''
    return binascii.unhexlify(format(number, 'x'))

def hex_to_bytes(hexstr):
    ''' Converts a hexadecimal string into binary data.
        Params:
            - hexstr (str): The hexadecimal string
        Returns (bytes): The binary data
    '''
    return binascii.unhexlify(hexstr)

def get_public_key(private_key):
    ''' Gets the public key from the private key.
        Params:
            - private_key (bytes): The private key
        Returns (bytes): The public key corrisponding the private key.
    '''
    secexp = bytes_to_int(private_key)
    sk = ecdsa.SigningKey.from_secret_exponent(secexp)
    vk = sk.get_verifying_key()
    return vk.to_string()

class TxOut:
    ''' Transaction output. '''
    def __init__(self, address, amount):
        ''' Initializes the TxOut instance.
        Params:
            - address (bytes): The address of the receiver.
            - amount (int): The amount to be transfered.
        '''
        self.address = address
        self.amount = amount

    def as_dict(self):
        return {
            'address': bytes_to_hex(self.address),
            'amount': self.amount
        }

    @staticmethod
    def from_dict(json_obj):
        address = hex_to_bytes(json_obj['address'])
        amount = json_obj['amount']
        return TxOut(address, amount)

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return TxOut.from_dict(json_obj)

    @staticmethod
    def is_valid_address(address):
        if len(address) != 48:
            print('invalid public key length')
            return False
        return True

    def has_valid_structure(self):
        return (isinstance(self.address, bytes)
            and TxOut.is_valid_address(self.address)
            and isinstance(self.amount, int)
        )

class TxIn:
    ''' Transaction input. '''
    def __init__(self, tx_out_id, tx_out_index, signature):
        ''' Initializes the TxIn instance.
        Params:
            - tx_out_id (bytes): The id of the output transaction providing the coins for this transaction.
            - tx_out_index (int): The index of the block containing the output transaction
            - signature (bytes): The signature of the TxIn, signed by the private key of the output transaction.
        '''
        self.tx_out_id = tx_out_id
        self.tx_out_index = tx_out_index
        self.signature = signature

    def as_dict(self):
        return {
            'tx_out_id': bytes_to_hex(self.tx_out_id),
            'tx_out_index': self.tx_out_index,
            'signature': bytes_to_hex(self.signature)
        }

    @staticmethod
    def from_dict(json_obj):
        tx_out_id = hex_to_bytes(json_obj['tx_out_id'])
        tx_out_index = json_obj['tx_out_index']
        signature = hex_to_bytes(json_obj['signature'])
        return TxIn(tx_out_id, tx_out_index, signature)

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return TxIn.from_dict(json_obj)

    def has_valid_structure(self):
        return (isinstance(self.signature, bytes)
            and isinstance(self.tx_out_id, bytes)
            and isinstance(self.tx_out_index, int)
        )

    def validate(self, transaction, unspent_tx_outs):
        condition = lambda uTxO: uTxO.tx_out_id == self.tx_out_id and uTxO.tx_out_id == self.tx_out_id
        referenced_uTxO = next([uTxO for uTxO in unspent_tx_outs if condition(uTxO)], None)
        if not referenced_uTxO:
            print('referenced tx_out not found: {}'.format(self.__dict__))
            return False
        address = referenced_uTxO.address
        vk = ecdsa.VerifyingKey.from_string(address)
        result = False
        try:
            result = vk.verify(self.signature, transaction.id)
        except ecdsa.BadSignatureError:
            pass
        return result
    
    def get_amount(self, unspent_tx_outs):
        return UnspentTxOut.find(self.tx_out_id, self.tx_out_index, unspent_tx_outs).amount

    @staticmethod
    def has_duplicates(tx_ins):
        key = lambda tx_in: tx_in.tx_out_id + int_to_bytes(tx_in.tx_out_index)
        groups = set()
        for tx_in in tx_ins:
            tx_key = key(tx_in)
            if tx_key in groups:
                print('duplicate tx_in: {}'.format(key))
                return True
            else:
                groups.add(tx_key)
        return False

class UnspentTxOut:
    ''' Unspent transaction outputs. '''
    def __init__(self, tx_out_id, tx_out_index, address, amount):
        self.tx_out_id = tx_out_id
        self.tx_out_index = tx_out_index
        self.address = address
        self.amount = amount

    @staticmethod
    def find(transaction_id, index, unspent_tx_outs):
        condition = lambda uTxO: uTxO.tx_out_id == transaction_id and uTxO.tx_out_index == index
        return next((uTxO for uTxO in unspent_tx_outs if condition(uTxO)), None)

    @staticmethod
    def update_unspent_tx_outs(new_transactions, current_unspent_tx_outs):
        new_unspent_tx_outs = [
            UnspentTxOut(tx.id, index, tx_out.address, tx_out.amount)
                for tx in new_transactions for index, tx_out in enumerate(tx.tx_outs)
            ]
        consumed_tx_outs = [
            UnspentTxOut(tx_in.tx_out_id, tx_in.tx_out_index, '', 0) 
                for tx in new_transactions for tx_in in tx.tx_ins
            ]
        consumed = lambda uTxO: UnspentTxOut.find(uTxO.tx_out_id, uTxO.tx_out_index, consumed_tx_outs)
        resulting_unspent_tx_outs = [uTxO for uTxO in current_unspent_tx_outs if not consumed(uTxO)]
        resulting_unspent_tx_outs.append(new_unspent_tx_outs)
        return resulting_unspent_tx_outs

class Transaction:
    ''' A transaction.'''

    COINBASE_AMOUNT = 50

    def __init__(self, tx_ins, tx_outs, identifier=None):
        ''' Initializes the Transaction instance.
        Params:
            - tx_ins (list<TxIn>): The list of transaction inputs.
            - tx_outs (list<TxOut>): The list of transaction outputs.
        '''
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs
        self.id = identifier if identifier is not None else self.get_id()

    def as_dict(self):
        return {
            'tx_ins': [tx_in.as_dict() for tx_in in self.tx_ins],
            'tx_outs': [tx_out.as_dict() for tx_out in self.tx_outs],
            'id': bytes_to_hex(self.id)
        }

    @staticmethod
    def from_dict(json_obj):
        tx_ins = [TxIn.from_dict(tx_in_dict) for tx_in_dict in json_obj['tx_ins']]
        tx_outs = [TxOut.from_dict(tx_out_dict) for tx_out_dict in json_obj['tx_outs']]
        identifier = hex_to_bytes(json_obj['id'])
        return Transaction(tx_ins, tx_outs, identifier)

    def as_json(self):
        return json.dumps(self.as_dict())

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return Transaction.from_dict(json_obj)

    def get_id(self):
        hasher = hashlib.sha256()
        for tx_in in self.tx_ins:
            hasher.update(tx_in.tx_out_id)
            hasher.update(int_to_bytes(tx_in.tx_out_index))
        for tx_out in self.tx_outs:
            hasher.update(tx_out.address)
            hasher.update(int_to_bytes(tx_out.amount))
        return hasher.digest()

    def sign_inputs(self, tx_in_index, private_key, unspent_tx_outs):
        tx_in = self.tx_ins[tx_in_index]
        data_to_sign = self.id
        referenced_unspent_tx_out = UnspentTxOut.find(tx_in.tx_out_id, tx_in.tx_out_index, unspent_tx_outs)
        if not referenced_unspent_tx_out:
            print('could not find referenced txOut')
            raise AssertionError('could not find referenced txOut')
        referenced_address = referenced_unspent_tx_out.address
        if get_public_key(private_key) != referenced_address:
            print('trying to sign an input with private ' +
                  ' key that does not match the address that is referenced in txIn')
            raise AssertionError('invalid private key')
        secexp = bytes_to_int(private_key)
        sk = ecdsa.SigningKey.from_secret_exponent(secexp)
        return sk.sign(data_to_sign)

    def has_valid_structure(self):
        return (isinstance(self.id, bytes)
            and isinstance(self.tx_outs, list)
            and isinstance(self.tx_ins, list)
            and all([tx_in.has_valid_structure() for tx_in in self.tx_ins])
            and all([tx_out.has_valid_structure() for tx_out in self.tx_outs])
        )

    def validate(self, unspent_tx_outs):
        if self.id != self.get_id():
            print('invalid tx id: {}'.format(self.id))
            return False
        has_valid_tx_ins = all([tx_in.validate(self, unspent_tx_outs) for tx_in in self.tx_ins])
        if not has_valid_tx_ins:
            print('some of tx_ins are invalid in tx: {}'.format(self.id))
            return False
        total_tx_in_values = sum([tx_in.get_amount() for tx_in in self.tx_ins])
        total_tx_out_values = sum([tx_out.amount for tx_out in self.tx_outs])
        if total_tx_in_values != total_tx_out_values:
            print('total_tx_in_values != total_tx_out_values in tx: {}'.format(self.id))
            return False
        return True

    def validate_coinbase(self, block_index):
        if self.id != self.get_id():
            print('invalid tx id: {}'.format(self.id))
            return False
        if len(self.tx_ins) != 1:
            print('one tx_in must be specified in the coinbase transaction')
            return False
        if self.tx_ins[0].tx_out_index != block_index:
            print('the tx_in index in coinbase tx must be the block height')
            return False
        if len(self.tx_outs) != 1:
            print('invalid number of tx_outs in coinbase transaction')
            return False
        if self.tx_outs[0].amount != Transaction.COINBASE_AMOUNT:
            print('invalid coinbase amount in coinbase transaction')
            return False
        return True

    @staticmethod
    def validate_block_transactions(transactions, unspent_tx_outs, block_index):
        if len(transactions) == 0:
            return True
        coinbase_tx = transactions[0]
        if not coinbase_tx.validate_coinbase(block_index):
            print('invalid coinbase tx: {}'.format(coinbase_tx.__dict__))
            return False
        tx_ins = [tx_in for tx in transactions for tx_in in tx.tx_ins]
        if TxIn.has_duplicates(tx_ins):
            return False
        normal_transactions = transactions[1:]
        return all([tx.validate(unspent_tx_outs) for tx in normal_transactions])

    @staticmethod
    def process_transactions(transactions, unspent_tx_outs, block_index):
        if not all([tx.has_valid_structure() for tx in transactions]):
            print('some of the transactions has invalid structure')
            return None
        if not Transaction.validate_block_transactions(transactions, unspent_tx_outs, block_index):
            print('invalid block transactions')
            return None
        return UnspentTxOut.update_unspent_tx_outs(transactions, unspent_tx_outs)

    @staticmethod
    def coinbase(address, block_index):
        tx_in = TxIn(bytes(), block_index, bytes())
        tx_out = TxOut(address, Transaction.COINBASE_AMOUNT)
        return Transaction([tx_in], [tx_out])
