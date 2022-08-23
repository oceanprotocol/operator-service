import logging

from flask import request as flask_request
from flask_sieve import JsonRequest, ValidationException
from flask_sieve.rules_processor import RulesProcessor
from flask_sieve.validator import Validator
from kubernetes.client.rest import ApiException

from operator_service.data_store import check_environment_exists, get_sql_running_jobs
from operator_service.utils import process_provider_signature_validation

logger = logging.getLogger(__name__)


class CustomJsonRequest(JsonRequest):
    """
    Extension of JsonRequest from Flask Sieve, allows us to set
    a custom Validator with specific rules
    """

    def __init__(self, request=None):
        request = request or flask_request
        headers = request.headers
        request = request.args if request.args else request.json
        self._validators = [
            CustomValidator(
                rules=self.rules(),
                messages={
                    "agreementId.not_in_use": "`agreementId` already in use for other job.",
                    "environment.environment_exists": "Environment invalid or does not exist",
                    "workflow.stages.stage_length": "Multiple stages are not supported yet",
                    "workflow.stages.stage_format": "Missing attributes algorithm, compute, input or ouput in first stage",
                    "providerSignature.signature": "Invalid providerSignature.",
                },
                request=request,
                headers=headers,
            )
        ]

    def validate(self):
        for validator in self._validators:
            if validator.fails():
                raise ValidationException(validator.messages())
        return True


class CustomValidator(Validator):
    """
    Extension of Validator from Flask Sieve, allows us to set
    custom validation rules. Implemented like this because handlers in
    Flask Sieve do not allow access to other parameters, just the value and
    attributes
    """

    def __init__(
        self,
        rules=None,
        request=None,
        custom_handlers=None,
        messages=None,
        headers=None,
        **kwargs,
    ):
        super(CustomValidator, self).__init__(
            rules, request, custom_handlers, messages, **kwargs
        )
        self._processor = CustomRulesProcessor()
        self._processor.headers = headers


class CustomRulesProcessor(RulesProcessor):
    def validate_not_in_use(self, value, **kwargs):
        try:
            active_jobs = get_sql_running_jobs()
            logger.info(f"active_jobs: {active_jobs}")
        except Exception as ex:
            prefix = (
                "Error getting the active jobs for initializing a compute job: "
                if isinstance(ex, ApiException)
                else ""
            )
            msg = prefix + f"{ex}"
            logger.error(msg)
            return False

        return value not in [job["agreementId"] for job in active_jobs]

    def validate_environment_exists(self, value, params, **kwargs):
        if not check_environment_exists(value, params[0]):
            logger.error(f"Environment invalid or does not exist")
            return False

        return True

    def validate_stage_length(self, value, **kwargs):
        if value and len(value) > 1:
            logger.error(f"Multiple stages are not supported yet")
            return False

        return True

    def validate_stage_format(self, value, **kwargs):
        if not value:
            return False

        for _attr in ("algorithm", "compute", "input", "output"):
            if _attr not in value[0]:
                logger.error(f"Missing {_attr} in stage 0")
                return False

            return True

    def validate_signature(self, value, params, **kwargs):
        owner = params[0]
        nonce = params[1]

        msg, _, _ = process_provider_signature_validation(value, f"{owner}", nonce)

        return not msg


class StartRequest(CustomJsonRequest):
    def rules(self):
        return {
            "workflow": ["required"],
            "workflow.stages": ["required", "stage_length", "stage_format"],
            "chainId": ["required"],
            "agreementId": ["bail", "required", "not_in_use"],
            "owner": ["bail", "required"],
            "environment": ["required", "environment_exists:chainId"],
            "providerSignature": ["bail", "required", "signature:owner,nonce"],
            "nonce": ["required"],
        }
