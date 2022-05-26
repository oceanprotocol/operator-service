import os

from eth_account import Account


def consumer_wallet():
    return Account.from_key(os.getenv("TEST_PRIVATE_KEY2"))
