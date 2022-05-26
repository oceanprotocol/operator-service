from datetime import datetime

from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from web3 import Web3

keys = KeyAPI(NativeECCBackend)


def sign(owner, wallet, job_id=None):
    nonce = datetime.utcnow().timestamp()

    # prepare consumer signature on did
    msg = f"{owner}{job_id}{nonce}" if job_id else f"{owner}{nonce}"
    signature = sign_message(msg, wallet)

    return nonce, signature


def sign_message(msg, wallet):
    keys_pk = keys.PrivateKey(wallet.key)
    hexable = Web3.toBytes(text=msg) if isinstance(msg, str) else msg

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
