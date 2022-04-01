[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Operator-Service

> Compute to the Data Infrastructure Operator Micro-service


Table of Contents
=================

   * [Operator-Service](#operator-service)
      * [About](#about)
      * [Getting Started](#getting-started)
         * [Local Environment](#local-environment)
            * [Installing AWS &amp; K8s tools](#installing-aws--k8s-tools)
            * [Running the Service](#running-the-service)
         * [Testing](#testing)
         * [New Version](#new-version)
      * [License](#license)



## About

The Operator Service is a micro-service implementing part of the Ocean Protocol
[Compute to the Data OEP-12](https://github.com/oceanprotocol/OEPs/tree/master/12#infrastructure-orchestration),
in charge of managing the workflow executing requests.
Typically the Operator Service is integrated from the [Brizo proxy](https://github.com/oceanprotocol/brizo),
but can be called independently if it.

The Operator Service is in charge of stablishing the communication with the K8s cluster, allowing to:

* Register workflows as K8s objects
* List the workflows registered in K8s
* Stop a running workflow execution
* Get information about the state of execution of a workflow

The Operator Service doesn't provide any storage capability, all the state is stored directly in the K8s cluster.

## Getting Started

### Local Environment

The operator service is in charge of receiving the requests for running compute workflows and the
setup of those in the K8s infrastructure.
To do that, in a local environment the operator service needs connectivity to you K8s environment.

There are multiple configurations and deployments of K8s possible, but here we are going to show
how to connect to an existing K8s cluster running in Amazon Web Services (AWS).

#### Installing AWS & K8s tools

First is necessary to install the AWS CLI:

```
$ sudo pip3 install awscli --upgrade

$ aws --version
aws-cli/1.16.225 Python/3.7.3 Linux/5.0.0-25-generic botocore/1.12.215

```

You need to install the `aws-iam-authenticator`

```
$ curl -o aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.13.7/2019-06-11/bin/linux/amd64/aws-iam-authenticator
chmod +x ./aws-iam-authenticator
```
And later the Kubectl tool:

```
$ curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
$ chmod +x ./kubectl
$ sudo mv ./kubectl /usr/local/bin/kubectl
$ kubectl version
Client Version: version.Info{Major:"1", Minor:"15", GitVersion:"v1.15.3", GitCommit:"2d3c76f9091b6bec110a5e63777c332469e0cba2", GitTreeState:"clean", BuildDate:"2019-08-19T11:13:54Z", GoVersion:"go1.12.9", Compiler:"gc", Platform:"linux/amd64"}
```

To connect to your specific Kubernetes cluster you need to setup the `~/.kube/config` file with your environment setup.

You can find the complete tutorials here:

* https://aws.amazon.com/cli/
* https://kubernetes.io/docs/tasks/tools/install-kubectl/
* https://docs.aws.amazon.com/eks/latest/userguide/install-aws-iam-authenticator.html


#### Running the Service

Once you have Kubectl able to connect you your K8s cluster, run the service is as simple as running the following commands:


`export FLASK_APP=operator_service/run.py`

`flask run --host=0.0.0.0 --port 8050`

Having the server running you can find the complete Swagger API documentation here:

```
http://0.0.0.0:8050/api/v1/docs/
```

And check some of the API functions like the create or the list of the existing workflow executions:

```
$ curl -X GET "http://localhost:8050/api/v1/operator/list" -H "accept: application/json"
["9f9178dcffd34130a3158ce9ca3d15ff"]
```


### ENV Vars

     ALGO_POD_TIMEOUT  = the maximum amount of time in seconds that an algorithm can use before it is killed
     STORAGE_EXPIRY = the maximum amount of time in seconds to store the job files outputs
     POSTGRES_DB = Postgres database
     POSTGRES_USER = Postgresql user
     POSTGRES_PASSWORD = Postgresql password
     POSTGRES_HOST = Postgresql host
     POSTGRES_PORT = Postgresql port
     SIGNATURE_REQUIRED = 0 -> no signature required, 1 -> request brizo signature
     ALLOWED_PROVIDERS = Json array with allowed providers that can access the endpoints
     OPERATOR_ADDRESS = Address used by Compute environment (IMPORTANT: Corresponding private key must be set in operator-engine env)
     DEFAULT_NAMESPACE = namespace which will run the jobs
     X-API-KEY = if defined, when downloading a compute output, will add X-API-KEY header (used for IPFS auth)
     CLIENT-ID = if defined, when downloading a compute output, will add CLIENT-ID header (used for IPFS auth)
     LOG_CFG and LOG_LEVEL = define the location of the log file and logging level, respectively

### Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

### New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

## License

Copyright 2022 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
