# Compute Service Endpoints

## Create new job or restart an existing stopped job

### POST /api/v1/compute


Start a new job

Parameters
```
{
    "agreementId":"111",
    "owner":"0x22",
    "signature":"9999",
    "workflow":{
        "stages": [
          {
            "index": 0,
            "input": [
              {
                "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
                "url": [
                  "https://data.ok.gov/sites/default/files/unspsc%20codes_3.csv"
                ],
                "index": 0
              },
              {
                "id": "did:op:1384941e6f0b46299b6e515723df3d8e8e5d1fb175554467a1cb7bc613f5c72e",
                "url": [
                  "https://data.ct.gov/api/views/2fi9-sgi3/rows.csv?accessType=DOWNLOAD"
                ],
                "index": 1
              }
            ],
            "compute": {
              "Instances": 1,
              "namespace": "withgpu",
              "maxtime": 3600
            },
            "algorithm": {
              "id": "did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf",
              "url": "https://raw.githubusercontent.com/oceanprotocol/test-algorithm/master/javascript/algo.js",
              "rawcode": "console.log('this is a test')",
              "container": {
                "image": "node",
                "tag": "10",
                "entrypoint": "node $ALGO"
              }
            },
            "output": {
              "nodeUri": "https://nile.dev-ocean.com",
              "brizoUri": "https://brizo.marketplace.dev-ocean.com",
              "brizoAddress": "0x4aaab179035dc57b35e2ce066919048686f82972",
              "metadata": {
                "name": "Workflow output"
              },
              "metadataUri": "https://aquarius.marketplace.dev-ocean.com",
              "secretStoreUri": "https://secret-store.nile.dev-ocean.com",
              "whitelist": [
                            "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                            "0xACBd138aBD70e2F00903268F3Db08f2D25677C9e"
              ],
              "owner":""https://gishubdata.nd.gov/sites/default/files/NDHUB.Roads_MileMarkers_1.csv"",
              "publishOutput":true,
              "publishAlgorithmLog":true
            }
          }
        ]
    }
}
```

Returns:
A string containing jobId




## Status and Result
  
  
### GET /api/v1/compute
   
   
Get all jobs and corresponding stats

Parameters
```
        signature: String object containg user signature (signed message)
        serviceAgreementId: String object containing agreementID (optional)
        jobId: String object containing workflowID (optional)
        
```

Returns

An Array of status objects, each object describing a workflow. If the array is empty, then the search yeld no results

### Status object
```
        owner:The owner of this compute job
        agreementId:
        jobId:
        dateCreated:Unix timestamp of job creation
        dateFinished:Unix timestamp when job finished
        status:  Int, see below for list
        statusText: String, see below
        configlogUrl: URL to get the configuration log (for admins only)
        publishlogUrl: URL to get the publish log (for admins only)
        algologUrl: URL to get the algo log (for user)
        outputsUrl: Array of URLs for algo outputs
        resultsDid: if we have a did
        stopreq: 0 - None, 1 - API Enpoint Stop called, 2 - Job exceeded allocated time
        removed: 0 - No, 1 - Removed from k8 cluster
```

### Status description:

| status   | Description        |
|----------|--------------------|
|  1       | Warming up        |
|  10       | Job started        |
|  20       | Configuring volumes|
|  30       | Provisioning success |
|  31       | Data provisioning failed |
|  32       | Algorithm provisioning failed |
|  40       | Running algorith   |
|  50       | Filtering results  |
|  60       | Publishing results |
|  70       | Job completed      |


Example:
```
GET /api/v1/compute?signature=0x00110011&serviceAgreementId=0x1111&jobId=012023
```

Output:
```
[
      {
        "owner":"0x1111",
        "agreementId":"0x2222",
        "jobId":"3333",
        "dateCreated":"2020-10-01T01:00:00Z",
        "dateFinished":"2020-10-01T01:00:00Z",
        "status":5,
        "statusText":"Job finished",
        "configlogUrl":"http://example.net/logs/config.log",
        "publishlogUrl":"http://example.net/logs/publish.log",
        "algologUrl":"http://example.net/logs/algo.log",
        "outputsUrl":[
            {
            "http://example.net/logs/output/0",
            "http://example.net/logs/output/1"
            }
         ],
         "resultsDid":"did:op:87bdaabb33354d2eb014af5091c604fb4b0f67dc6cca4d18a96547bffdc27bcf"
       },
       {
        "owner":"0x1111",
        "agreementId":"0x2222",
        "jobId":"3333",
        "dateCreated":"2020-10-01T01:00:00Z",
        "dateFinished":"2020-10-01T01:00:00Z",
        "status":5,
        "statusText":"Job finished",
        "configlogUrl":"http://example.net/logs2/config.log",
        "publishlogUrl":"http://example.net/logs2/cpublish.log",
        "algologUrl":"http://example.net/logs2/algo.log",
        "outputsUrl":[
            {
            "http://example.net/logs2/output/0",
            "http://example.net/logs2/output/1"
            }
         ],
         "resultsDid":""
       }
 ]
 ```
       
## Stop
  
  
### PUT /api/v1/compute
   
   
Stop a running compute job.

Parameters
```
        signature: String object containg user signature (signed message)
        serviceAgreementId: String object containing agreementID (optional)
        jobId: String object containing workflowID (optional)
        
        At least one parameter is required (can be any of them)
```

Returns

One or more status objects

Example:
```
PUT /api/v1/compute?signature=0x00110011&serviceAgreementId=0x1111&jobId=012023
```

## Delete

### DELETE /api/v1/compute

Delete a compute job and all resources associated with the job. If job is running it will be stopped first.

Parameters
```
        signature: String object containg user signature (signed message)
        serviceAgreementId: String object containing agreementID (optional)
        jobId: String object containing workflowID (optional)
        
```

Returns

One or more status objects

Example:
```
DELETE /api/v1/compute?signature=0x00110011&serviceAgreementId=0x1111&jobId=012023
```


## Get running jobs

### GET /api/v1/runningjobs

Gets all running jobs


Returns

One or more status objects

Example:
```
GET /api/v1/runningjobs
```
