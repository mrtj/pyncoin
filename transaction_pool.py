# pyncoin/transaction_pool.py

from transaction import Transaction
from utils import RawSerializable, BadRequestError

class TransactionPool(RawSerializable):

    def __init__(self):
        self.transactions = []

    def add_transaction(self, transaction, unspent_tx_outs):
        if not transaction.validate(unspent_tx_outs) or not self.is_valid_transaction(transaction):
            return False
        print('adding to tx_pool: {}'.format(transaction))
        self.transactions.append(transaction)
        return True

    def ins(self):
        ''' Returns the transaction inputs in this pool. '''
        return [tx_in for tx in self.transactions for tx_in in tx.tx_ins]

    @staticmethod
    def has_tx_in(tx_in, unspent_tx_outs):
        return next((uTxO for uTxO in unspent_tx_outs if uTxO.matches_tx_in(tx_in)), None) is not None

    def is_valid_transaction(self, transaction):
        pool_ins = self.ins()
        for tx_in in transaction.tx_ins:
            if tx_in in pool_ins:
                print('tx_in already found in the tx_pool')
                return False
        return True

    def update(self, unspent_tx_outs):
        invalid_txs = []
        for tx in self.transactions:
            for tx_in in tx.tx_ins:
                if not TransactionPool.has_tx_in(tx_in, unspent_tx_outs):
                    invalid_txs.append(tx)
                    break
        if invalid_txs:
            print('removing the following transactions from tx_pool: {}'.format(invalid_txs))
            self.transactions = [tx for tx in self.transactions if tx not in invalid_txs]

    def to_raw(self):
        return Transaction.to_raw_list(self.transactions)

    def filtered_unspent_tx_outs(self, unspent_tx_outs):
        tx_ins = [tx_in for tx in self.transactions for tx_in in tx.tx_ins]
        removable = []
        for unspent_tx_out in unspent_tx_outs:
            tx_in = next((tx_in for tx_in in tx_ins if unspent_tx_out.matches_tx_in(tx_in)), None)
            if tx_in is not None:
                removable.append(unspent_tx_out)
        remaining = [uTxO for uTxO in unspent_tx_outs if uTxO not in removable]
        return remaining

    @classmethod
    def from_raw(cls, raw_obj):
        raise AssertionError('Transaction pool must not be created from raw values.')
