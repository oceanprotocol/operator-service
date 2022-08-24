from datetime import datetime

from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from web3 import Web3

from . import operator_payloads as payloads

keys = KeyAPI(NativeECCBackend)


def sign_message(message, wallet):
    """
    Signs the message with the private key of the given Wallet
    :param message: str
    :param wallet: Wallet instance
    :return: signature
    """
    keys_pk = keys.PrivateKey(wallet.key)
    hexable = Web3.toBytes(text=message) if isinstance(message, str) else message

    message_hash = Web3.solidityKeccak(
        ["bytes"],
        [Web3.toHex(hexable)],
    )
    prefix = "\x19Ethereum Signed Message:\n32"
    signable_hash = Web3.solidityKeccak(
        ["bytes", "bytes"], [Web3.toBytes(text=prefix), Web3.toBytes(message_hash)]
    )
    signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=keys_pk)

    v = str(Web3.toHex(Web3.toBytes(signed.v)))
    r = str(Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")))
    s = str(Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")))

    signature = "0x" + r[2:] + s[2:] + v[2:]

    return signature


def decorate_nonce(payload):
    nonce = str(datetime.utcnow().timestamp())
    try:
        did = payload["workflow"]["stages"][0]["input"][0]["id"]
    except (KeyError, IndexError):
        did = ""

    if "jobId" in payload:
        did = payload["jobId"]

    wallet = payloads.VALID_WALLET

    msg = f"{wallet.address}{did}{nonce}"
    signature = sign_message(msg, wallet)

    payload["nonce"] = nonce
    payload["providerSignature"] = signature

    return payload
