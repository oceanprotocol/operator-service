#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import pickle
import time
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from ocean_lib.example_config import ExampleConfig
from ocean_lib.models.compute_input import ComputeInput
from ocean_lib.ocean.mint_fake_ocean import mint_fake_OCEAN
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.services.service import Service
from ocean_lib.structures.file_objects import UrlFile
from ocean_lib.web3_internal.constants import ZERO_ADDRESS
from ocean_lib.web3_internal.wallet import Wallet

from operator_service.constants import BaseURLs

config = ExampleConfig.get_config()
ocean = Ocean(config)

# Create Alice's wallet
alice_private_key = os.getenv("TEST_PRIVATE_KEY1")
alice_wallet = Wallet(
    ocean.web3,
    alice_private_key,
    config.block_confirmations,
    config.transaction_timeout,
)
assert alice_wallet.address

# Mint OCEAN
mint_fake_OCEAN(config)
assert alice_wallet.web3.eth.get_balance(alice_wallet.address) > 0, "need ETH"

# Publish the data NFT token
erc721_nft = ocean.create_erc721_nft("NFTToken1", "NFT1", alice_wallet)
assert erc721_nft.address
assert erc721_nft.token_name()
assert erc721_nft.symbol()

# Publish the datatoken
DATA_datatoken = erc721_nft.create_datatoken(
    template_index=1,
    name="Datatoken 1",
    symbol="DT1",
    minter=alice_wallet.address,
    fee_manager=alice_wallet.address,
    publish_market_order_fee_address=ZERO_ADDRESS,
    publish_market_order_fee_token=ocean.OCEAN_address,
    publish_market_order_fee_amount=0,
    bytess=[b""],
    from_wallet=alice_wallet,
)
assert DATA_datatoken.address

# Specify metadata and services, using the Branin test dataset
DATA_date_created = "2021-12-28T10:55:11Z"

DATA_metadata = {
    "created": DATA_date_created,
    "updated": DATA_date_created,
    "description": "Branin dataset",
    "name": "Branin dataset",
    "type": "dataset",
    "author": "Trent",
    "license": "CC0: PublicDomain",
}


DATA_url_file = UrlFile(
    url="https://raw.githubusercontent.com/oceanprotocol/c2d-examples/main/branin_and_gpr/branin.arff"
)

# Encrypt file(s) using provider
DATA_encrypted_files = ocean.assets.encrypt_files([DATA_url_file])

# Set the compute values for compute service
DATA_compute_values = {
    "allowRawAlgorithm": False,
    "allowNetworkAccess": True,
    "publisherTrustedAlgorithms": [],
    "publisherTrustedAlgorithmPublishers": [],
}

# Create the Service
DATA_compute_service = Service(
    service_id="2",
    service_type="compute",
    service_endpoint=ocean.config.provider_url,
    datatoken=DATA_datatoken.address,
    files=DATA_encrypted_files,
    timeout=3600,
    compute_values=DATA_compute_values,
)

# Publish asset with compute service on-chain.
DATA_asset = ocean.assets.create(
    metadata=DATA_metadata,
    publisher_wallet=alice_wallet,
    encrypted_files=DATA_encrypted_files,
    services=[DATA_compute_service],
    erc721_address=erc721_nft.address,
    deployed_erc20_tokens=[DATA_datatoken],
)

assert DATA_asset.did, "create dataset with compute service unsuccessful"

# 3. Alice publishes algorithm

# Publish the algorithm NFT token
ALGO_nft_token = ocean.create_erc721_nft("NFTToken1", "NFT1", alice_wallet)
assert ALGO_nft_token.address

# Publish the datatoken
ALGO_datatoken = ALGO_nft_token.create_datatoken(
    template_index=1,
    name="Datatoken 1",
    symbol="DT1",
    minter=alice_wallet.address,
    fee_manager=alice_wallet.address,
    publish_market_order_fee_address=ZERO_ADDRESS,
    publish_market_order_fee_token=ocean.OCEAN_address,
    publish_market_order_fee_amount=0,
    bytess=[b""],
    from_wallet=alice_wallet,
)
assert ALGO_datatoken.address

# Specify metadata and services, using the Branin test dataset
ALGO_date_created = "2021-12-28T10:55:11Z"

ALGO_metadata = {
    "created": ALGO_date_created,
    "updated": ALGO_date_created,
    "description": "gpr",
    "name": "gpr",
    "type": "algorithm",
    "author": "Trent",
    "license": "CC0: PublicDomain",
    "algorithm": {
        "language": "python",
        "format": "docker-image",
        "version": "0.1",
        "container": {
            "entrypoint": "python $ALGO",
            "image": "oceanprotocol/algo_dockers",
            "tag": "python-branin",
            "checksum": "44e10daa6637893f4276bb8d7301eb35306ece50f61ca34dcab550",
        },
    }
}

ALGO_url_file = UrlFile(
    url="https://raw.githubusercontent.com/oceanprotocol/c2d-examples/main/branin_and_gpr/gpr.py"
)

# Encrypt file(s) using provider
ALGO_encrypted_files = ocean.assets.encrypt_files([ALGO_url_file])

# Publish asset with compute service on-chain.
# The download (access service) is automatically created, but you can explore other options as well
ALGO_asset = ocean.assets.create(
    metadata=ALGO_metadata,
    publisher_wallet=alice_wallet,
    encrypted_files=ALGO_encrypted_files,
    erc721_address=ALGO_nft_token.address,
    deployed_erc20_tokens=[ALGO_datatoken],
)

assert ALGO_asset.did, "create algorithm unsuccessful"

# 4. Alice allows the algorithm for C2D for that data asset
compute_service = DATA_asset.services[0]
compute_service.add_publisher_trusted_algorithm(ALGO_asset)
DATA_asset = ocean.assets.update(DATA_asset, alice_wallet)

# 5. Bob acquires datatokens for data and algorithm
bob_wallet = Wallet(
    ocean.web3,
    os.getenv("TEST_PRIVATE_KEY2"),
    config.block_confirmations,
    config.transaction_timeout,
)
assert bob_wallet.address

# Alice mints DATA datatokens and ALGO datatokens to Bob.
# Alternatively, Bob might have bought these in a market.
DATA_datatoken.mint(bob_wallet.address, ocean.to_wei(5), alice_wallet)
ALGO_datatoken.mint(bob_wallet.address, ocean.to_wei(5), alice_wallet)

# 6. Bob starts a compute job

# Convenience variables
DATA_did = DATA_asset.did
ALGO_did = ALGO_asset.did

# Operate on updated and indexed assets
DATA_asset = ocean.assets.resolve(DATA_did)
ALGO_asset = ocean.assets.resolve(ALGO_did)

compute_service = DATA_asset.services[0]
algo_service = ALGO_asset.services[0]

environments = ocean.compute.get_c2d_environments(compute_service.service_endpoint)

DATA_compute_input = ComputeInput(DATA_asset, compute_service)
ALGO_compute_input = ComputeInput(ALGO_asset, algo_service)

# Pay for dataset and algo
datasets, algorithm = ocean.assets.pay_for_compute_service(
    datasets=[DATA_compute_input],
    algorithm_data=ALGO_compute_input,
    consume_market_order_fee_address=bob_wallet.address,
    wallet=bob_wallet,
    compute_environment=environments[0]["id"],
    valid_until=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
    consumer_address=environments[0]["consumerAddress"],
)
assert datasets, "pay for dataset unsuccessful"
assert algorithm, "pay for algorithm unsuccessful"

# Start compute job
job_id = ocean.compute.start(
    consumer_wallet=bob_wallet,
    dataset=datasets[0],
    compute_environment=environments[0]["id"],
    algorithm=algorithm,
)
assert job_id, "start compute unsuccessful"

# Wait until job is done
succeeded = False
for _ in range(0, 200):
    status = ocean.compute.status(DATA_asset, compute_service, job_id, bob_wallet)
    if status.get("dateFinished") and Decimal(status["dateFinished"]) > 0:
        print(f"Status = '{status}'")
        succeeded = True
        break
    time.sleep(5)
assert succeeded, "compute job unsuccessful"

# Retrieve algorithm output and log files
output = ocean.compute.compute_job_result_logs(
    DATA_asset, compute_service, job_id, bob_wallet
)[0]
assert output, "algorithm output not found"

model = pickle.loads(output)  # the gaussian model result
assert len(model) > 0, "unpickle result unsuccessful"

# Get running jobs
api_url = "http://172.15.0.13:31000/api/v1"
get_environments_response = requests.get(f"{api_url}/runningjobs")
assert get_environments_response.status_code == 200


