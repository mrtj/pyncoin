# pyncoin/transaction.py

''' Implements a cryptocurrency transaction. '''

import functools
import hashlib
from decimal import Decimal

import ecdsa
from utils import RawSerializable, bytes_to_int, int_to_bytes, bytes_to_hex, hex_to_bytes
from utils import BadRequestError, UnauthorizedError

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

class TxOut(RawSerializable):
    ''' Transaction output. '''
    def __init__(self, address, amount):
        ''' Initializes the TxOut instance.
        Params:
            - address (bytes): The address of the receiver.
            - amount (Decimal): The amount to be transfered.
        '''
        self.address = address
        self.amount = amount

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.address == other.address
            and self.amount == other.amount)

    def to_raw(self):
        return {
            'address': bytes_to_hex(self.address),
            'amount': self.amount
        }

    @classmethod
    def from_raw(cls, raw_obj):
        address = hex_to_bytes(raw_obj['address'])
        amount = raw_obj['amount'] if isinstance(raw_obj['amount'], Decimal) else Decimal(raw_obj['amount'])
        return cls(address, amount)

    @staticmethod
    def is_valid_address(address):
        if len(address) != 48:
            print('invalid public key length')
            return False
        return True

    def has_valid_structure(self):
        return (isinstance(self.address, bytes)
            and TxOut.is_valid_address(self.address)
            and isinstance(self.amount, Decimal)
        )

class TxIn(RawSerializable):
    ''' Transaction input. '''
    def __init__(self, tx_out_id, tx_out_index, signature=None):
        ''' Initializes the TxIn instance.
        Params:
            - tx_out_id (bytes): The id of the output transaction providing the coins for this transaction.
            - tx_out_index (int): The index of the block containing the output transaction
            - signature (bytes): The signature of the TxIn, signed by the private key of the output transaction.
        '''
        self.tx_out_id = tx_out_id
        self.tx_out_index = tx_out_index
        self.signature = signature

    def __eq__(self, other):
        return (isinstance(self, other.__class__)
            and self.tx_out_id == other.tx_out_id
            and self.tx_out_index == other.tx_out_index)

    def to_raw(self):
        return {
            'txOutId': bytes_to_hex(self.tx_out_id),
            'txOutIndex': self.tx_out_index,
            'signature': bytes_to_hex(self.signature) if self.signature is not None else None
        }

    @classmethod
    def from_raw(cls, raw_obj):
        tx_out_id = hex_to_bytes(raw_obj['txOutId'])
        tx_out_index = raw_obj['txOutIndex']
        signature = hex_to_bytes(raw_obj['signature']) if raw_obj['signature'] is not None else None
        return cls(tx_out_id, tx_out_index, signature)

    def has_valid_structure(self):
        return (isinstance(self.signature, bytes)
            and isinstance(self.tx_out_id, bytes)
            and isinstance(self.tx_out_index, int)
        )

    def validate(self, transaction, unspent_tx_outs):
        condition = lambda uTxO: uTxO.tx_out_id == self.tx_out_id and uTxO.tx_out_index == self.tx_out_index
        referenced_uTxO = next((uTxO for uTxO in unspent_tx_outs if condition(uTxO)), None)
        if not referenced_uTxO:
            print('referenced tx_out not found: {}'.format(self.__dict__))
            return False
        address = referenced_uTxO.address
        vk = ecdsa.VerifyingKey.from_string(address)
        result = False
        print('validating tx_in signature: {}\naddress: {}\ndata: {}'
            .format(bytes_to_hex(self.signature), bytes_to_hex(address), bytes_to_hex(transaction.id)))
        try:
            if self.signature:
                result = vk.verify(self.signature, transaction.id)
        except ecdsa.BadSignatureError:
            print('bad signature for tx_in: {}'.format(self))
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

class UnspentTxOut(RawSerializable):
    ''' Unspent transaction outputs. '''
    def __init__(self, tx_out_id, tx_out_index, address, amount):
        self.tx_out_id = tx_out_id
        self.tx_out_index = tx_out_index
        self.address = address
        self.amount = amount

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.tx_out_id == other.tx_out_id
            and self.tx_out_index == other.tx_out_index
            and self.address == other.address
            and self.amount == other.amount)

    def matches_tx_in(self, tx_in):
        return self.tx_out_id == tx_in.tx_out_id and self.tx_out_index == tx_in.tx_out_index

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
        resulting_unspent_tx_outs.extend(new_unspent_tx_outs)
        return resulting_unspent_tx_outs

    def to_raw(self):
        return {
            'txOutId': bytes_to_hex(self.tx_out_id),
            'txOutIndex': self.tx_out_index,
            'address': bytes_to_hex(self.address),
            'amount': self.amount
        }

    @classmethod
    def from_raw(cls, raw_obj):
        tx_out_id = hex_to_bytes(raw_obj['txOutId'])
        tx_out_index = raw_obj['txOutIndex']
        address = hex_to_bytes(raw_obj['address'])
        amount = raw_obj['amount'] if isinstance(raw_obj['amount'], Decimal) else Decimal(raw_obj['amount'])
        return cls(tx_out_id, tx_out_index, address, amount)

class Transaction(RawSerializable):
    ''' A transaction.'''

    COINBASE_AMOUNT =  Decimal(50)

    def __init__(self, tx_ins, tx_outs, identifier=None):
        ''' Initializes the Transaction instance.
        Params:
            - tx_ins (list<TxIn>): The list of transaction inputs.
            - tx_outs (list<TxOut>): The list of transaction outputs.
        '''
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs
        self.id = identifier if identifier is not None else self.get_id()

    def __eq__(self, other):
        return (isinstance(other, self.__class__) 
            and self.tx_ins == other.tx_ins
            and self.tx_outs == other.tx_outs)

    def to_raw(self):
        return {
            'txIns': TxIn.to_raw_list(self.tx_ins),
            'txOuts': TxOut.to_raw_list(self.tx_outs),
            'id': bytes_to_hex(self.id)
        }

    @classmethod
    def from_raw(cls, raw_obj):
        tx_ins = TxIn.from_raw_list(raw_obj['txIns'])
        tx_outs = TxOut.from_raw_list(raw_obj['txOuts'])
        identifier = hex_to_bytes(raw_obj['id'])
        return cls(tx_ins, tx_outs, identifier)

    def get_id(self):
        hasher = hashlib.sha256()
        for tx_in in self.tx_ins:
            hasher.update(tx_in.tx_out_id)
            hasher.update(int_to_bytes(tx_in.tx_out_index))
        for tx_out in self.tx_outs:
            hasher.update(tx_out.address)
            (amount_num, amount_denom) = tx_out.amount.as_integer_ratio()
            hasher.update(int_to_bytes(amount_num))
            hasher.update(int_to_bytes(amount_denom))
        return hasher.digest()

    def sign_input(self, tx_in_index, private_key, unspent_tx_outs):
        tx_in = self.tx_ins[tx_in_index]
        data_to_sign = self.id
        referenced_unspent_tx_out = UnspentTxOut.find(tx_in.tx_out_id, tx_in.tx_out_index, unspent_tx_outs)
        if not referenced_unspent_tx_out:
            print('could not find referenced txOut')
            raise BadRequestError('could not find referenced txOut')
        referenced_address = referenced_unspent_tx_out.address
        if get_public_key(private_key) != referenced_address:
            print('trying to sign an input with private ' +
                  ' key that does not match the address that is referenced in txIn')
            raise UnauthorizedError('invalid private key')
        print('signing data: {}\nfor address: {}'
            .format(bytes_to_hex(data_to_sign), bytes_to_hex(get_public_key(private_key))))
        sk = ecdsa.SigningKey.from_string(private_key)
        signature = sk.sign(data_to_sign)
        print('signature: {}'.format(bytes_to_hex(signature)))
        return signature

    def has_valid_structure(self):
        return (isinstance(self.id, bytes)
            and isinstance(self.tx_outs, list)
            and isinstance(self.tx_ins, list)
            and all([tx_in.has_valid_structure() for tx_in in self.tx_ins])
            and all([tx_out.has_valid_structure() for tx_out in self.tx_outs])
        )

    def validate(self, unspent_tx_outs):
        if self.id != self.get_id():
            print('invalid tx id: {}'.format(self))
            return False
        has_valid_tx_ins = all([tx_in.validate(self, unspent_tx_outs) for tx_in in self.tx_ins])
        if not has_valid_tx_ins:
            print('some of tx_ins are invalid in tx: {}'.format(self))
            return False
        total_tx_in_values = sum([tx_in.get_amount(unspent_tx_outs) for tx_in in self.tx_ins])
        total_tx_out_values = sum([tx_out.amount for tx_out in self.tx_outs])
        if total_tx_in_values != total_tx_out_values:
            print('total_tx_in_values != total_tx_out_values in tx: {}'.format(self))
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
