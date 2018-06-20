# pyncoin/wallet.py
''' Implements the pyncoin wallet, a high-level user interface for pyncoin transactions. '''

import os

import ecdsa
from transaction import Transaction, TxIn, TxOut

class Wallet:

    def __init__(self, private_key_location):
        ''' Initializes the wallet.

        Params: 
            - private_key_location (str): The location of the private key PEM file. If the 
                private key file is not found in the given location, a new key will be 
                generated and saved to the same location.
        '''
        self.private_key = None
        try:
            with open(private_key_location, 'rb') as pk_file:
                pk_bin = pk_file.read()
                self.private_key = ecdsa.SigningKey.from_pem(pk_bin)
        except FileNotFoundError:
            print('private key file not found')
        if not self.private_key:
            print('generating private key...')
            self.private_key = ecdsa.SigningKey.generate()
            pk_bin = self.private_key.to_pem()
            print('saving private key...')
            dir_name = os.path.dirname(private_key_location)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with open(private_key_location, 'wb') as pk_file:
                pk_file.write(pk_bin)

    def get_public_key(self):
        ''' Returns the public key of this wallet.

        Returns (bytes): The raw public key of this wallet.
        '''
        public_key = self.private_key.get_verifying_key()
        return public_key.to_string()

    def get_private_key(self):
        return self.private_key.to_string()

    @staticmethod
    def get_balance(address, unspent_tx_outs):
        ''' Gets the balance of a given address.

        Params:
            - address (bytes): The address of the wallet
            - unspent_tx_outs (list<transaction.UnspentTxOut>): The current unspent 
                transaction outputs of the blockchain
        
        Returns (Decimal): The balance of the given address
        '''
        return sum([uTxO.amount for uTxO in unspent_tx_outs if uTxO.address == address])

    @staticmethod
    def find_tx_outs_for_amount(amount, my_unspent_tx_outs):
        current_amount = 0
        included_unspent_tx_outs = []
        for my_unspent_tx_out in my_unspent_tx_outs:
            included_unspent_tx_outs.append(my_unspent_tx_out)
            current_amount += my_unspent_tx_out.amount
            if current_amount > amount:
                left_over_amount = current_amount - amount
                return (included_unspent_tx_outs, left_over_amount)
        raise AssertionError('not enough coins to send transaction')

    def create_tx_outs(self, receiver_address, amount, left_over_amount):
        tx_out_1 = TxOut(receiver_address, amount)
        tx_outs = [tx_out_1]
        if left_over_amount > 0:
            my_address = self.get_public_key()
            left_over_tx_out = TxOut(my_address, left_over_amount)
            tx_outs.append(left_over_tx_out)
        return tx_outs

    def create_transaction(self, receiver_address, amount, unspent_tx_outs):
        my_address = self.get_public_key()
        private_key = self.get_private_key()
        my_unspent_tx_outs = [uTxO for uTxO in unspent_tx_outs if uTxO.address == my_address]
        (included_unspent_tx_outs, left_over_amount) = \
            Wallet.find_tx_outs_for_amount(amount, my_unspent_tx_outs)
        unsigned_tx_ins = [TxIn(uTxO.tx_out_id, uTxO.tx_out_index) for uTxO in included_unspent_tx_outs]
        tx_outs = self.create_tx_outs(receiver_address, amount, left_over_amount)
        tx = Transaction(unsigned_tx_ins, tx_outs)
        for index, tx_in in enumerate(tx.tx_ins):
            tx_in.signature = tx.sign_input(index, private_key, unspent_tx_outs)
        return tx
