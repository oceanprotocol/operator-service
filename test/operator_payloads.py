from copy import deepcopy

VALID_COMPUTE_BODY = {
    "agreementId": "0x0",
    "owner": "0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
    "providerSignature": "sig",
    "workflow": {
        "stages": [
            {
                "algorithm": {
                    "container": {
                        "entrypoint": "node $ALGO",
                        "image": "node",
                        "tag": "10",
                    },
                    "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
                    "rawcode": "console.log('this is a test')",
                    "url": "https://raw.githubusercontent.com/oceanprotocol/test-algorithm/master/javascript/algo.js",
                },
                "compute": {"Instances": 1, "maxtime": 3600, "namespace": "withgpu"},
                "index": 0,
                "input": [
                    {
                        "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
                        "index": 0,
                        "url": [
                            "https://data.ok.gov/sites/default/files/unspsc%20codes_3.csv"
                        ],
                    },
                ],
                "output": {
                    "brizoAddress": "0x4aaab179035dc57b35e2ce066919048686f82972",
                    "brizoUri": "https://brizo.marketplace.dev-ocean.com",
                    "metadata": {"name": "Workflow output"},
                    "metadataUri": "https://aquarius.marketplace.dev-ocean.com",
                    "nodeUri": "https://nile.dev-ocean.com",
                    "owner": "0xC41808BBef371AD5CFc76466dDF9dEe228d2BdAA",
                    "publishAlgorithmLog": True,
                    "publishOutput": True,
                    "secretStoreUri": "https://secret-store.nile.dev-ocean.com",
                    "whitelist": [
                        "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                        "0xACBd138aBD70e2F00903268F3Db08f2D25677C9e",
                    ],
                },
            }
        ],
    },
}

NO_WORKFLOW_COMPUTE_BODY = deepcopy(VALID_COMPUTE_BODY)
NO_WORKFLOW_COMPUTE_BODY["workflow"] = {}

NO_STAGES_COMPUTE_BODY = deepcopy(VALID_COMPUTE_BODY)
NO_STAGES_COMPUTE_BODY["workflow"]["stages"] = []

INVALID_STAGE_COMPUTE_BODY = deepcopy(VALID_COMPUTE_BODY)
del INVALID_STAGE_COMPUTE_BODY["workflow"]["stages"][0]["algorithm"]

VALID_COMPUTE_BODY_WITH_NO_MAXTIME = deepcopy(VALID_COMPUTE_BODY)
del VALID_COMPUTE_BODY_WITH_NO_MAXTIME["workflow"]["stages"][0]["compute"]["maxtime"]
