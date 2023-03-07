import os
import time
from decimal import Decimal

from brownie import accounts
from datetime import datetime, timedelta

from ocean_lib.example_config import get_config_dict
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.ocean.util import to_wei
from ocean_lib.web3_internal.utils import connect_to_network

from ocean_lib.models.compute_input import ComputeInput


def test_integration_using_ocean_lib():
    connect_to_network("development")

    config = get_config_dict("development")
    ocean = Ocean(config)

    alice = accounts.add(os.environ["TEST_PRIVATE_KEY1"])
    bob = accounts.add(os.environ["TEST_PRIVATE_KEY2"])

    from ocean_lib.structures.file_objects import UrlFile

    DATA_url_file = UrlFile(
        url="https://raw.githubusercontent.com/oceanprotocol/c2d-examples/main/branin_and_gpr/branin.arff"
    )

    name = "Branin dataset"
    (DATA_data_nft, DATA_datatoken, DATA_ddo) = ocean.assets.create_url_asset(
        name, DATA_url_file.url, {"from": alice}, wait_for_aqua=True
    )
    print(f"DATA_data_nft address = '{DATA_data_nft.address}'")
    print(f"DATA_datatoken address = '{DATA_datatoken.address}'")

    # Create and attach the Service
    DATA_files = [DATA_url_file]

    # Add service and update asset
    DATA_ddo.create_compute_service(
        service_id="2",
        service_endpoint=ocean.config_dict["PROVIDER_URL"],
        datatoken_address=DATA_datatoken.address,
        files=DATA_files,
    )

    # Update the asset
    DATA_ddo = ocean.assets.update(DATA_ddo, {"from": alice})

    print(f"DATA_ddo did = '{DATA_ddo.did}'")

    ALGO_url = "https://raw.githubusercontent.com/oceanprotocol/c2d-examples/main/branin_and_gpr/gpr.py"

    name = "grp"
    (ALGO_data_nft, ALGO_datatoken, ALGO_ddo) = ocean.assets.create_algo_asset(
        name, ALGO_url, {"from": alice}, wait_for_aqua=True
    )

    print(f"ALGO_data_nft address = '{ALGO_data_nft.address}'")
    print(f"ALGO_datatoken address = '{ALGO_datatoken.address}'")
    print(f"ALGO_ddo did = '{ALGO_ddo.did}'")

    compute_service = DATA_ddo.services[1]
    compute_service.add_publisher_trusted_algorithm(ALGO_ddo)
    DATA_ddo = ocean.assets.update(DATA_ddo, {"from": alice})

    DATA_datatoken.mint(bob, to_wei(5), {"from": alice})
    ALGO_datatoken.mint(bob, to_wei(5), {"from": alice})

    DATA_did = DATA_ddo.did
    ALGO_did = ALGO_ddo.did

    # Operate on updated and indexed assets
    DATA_ddo = ocean.assets.resolve(DATA_did)
    ALGO_ddo = ocean.assets.resolve(ALGO_did)

    compute_service = DATA_ddo.services[1]
    algo_service = ALGO_ddo.services[0]
    free_c2d_env = ocean.compute.get_free_c2d_environment(
        compute_service.service_endpoint
    )

    DATA_compute_input = ComputeInput(DATA_ddo, compute_service)
    ALGO_compute_input = ComputeInput(ALGO_ddo, algo_service)

    # Pay for dataset and algo for 1 day
    datasets, algorithm = ocean.assets.pay_for_compute_service(
        datasets=[DATA_compute_input],
        algorithm_data=ALGO_compute_input,
        consume_market_order_fee_address=bob.address,
        tx_dict={"from": bob},
        compute_environment=free_c2d_env["id"],
        valid_until=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
        consumer_address=free_c2d_env["consumerAddress"],
    )
    assert datasets, "pay for dataset unsuccessful"
    assert algorithm, "pay for algorithm unsuccessful"

    # Start compute job
    job_id = ocean.compute.start(
        consumer_wallet=bob,
        dataset=datasets[0],
        compute_environment=free_c2d_env["id"],
        algorithm=algorithm,
    )
    print(f"Started compute job with id: {job_id}")

    succeeded = False
    for _ in range(0, 200):
        status = ocean.compute.status(DATA_ddo, compute_service, job_id, bob)
        if status.get("dateFinished") and Decimal(status["dateFinished"]) > 0:
            succeeded = True
            break
        time.sleep(5)

    assert succeeded, "Status for this algorithm is not successful."
