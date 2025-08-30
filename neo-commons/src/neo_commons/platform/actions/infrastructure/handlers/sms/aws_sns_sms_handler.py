"""AWS SNS SMS action handler implementation."""

import asyncio
import json
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote
import httpx

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class AWSSNSSMSHandler(ActionHandler):
    """
    AWS SNS SMS handler for sending SMS messages via AWS SNS.
    
    Configuration:
    - aws_access_key_id: AWS Access Key ID (required)
    - aws_secret_access_key: AWS Secret Access Key (required)
    - aws_region: AWS region (default: us-east-1)
    - sender_id: Sender ID for SMS (optional)
    - sms_type: SMS type (Promotional or Transactional, default: Transactional)
    - max_price: Maximum price per SMS (optional)
    - api_timeout: API request timeout in seconds (default: 30)
    """
    
    @property
    def handler_name(self) -> str:
        return "aws_sns_sms_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["sms", "text_message", "aws_sms", "sns_sms"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate AWS SNS SMS handler configuration."""
        required_fields = ["aws_access_key_id", "aws_secret_access_key"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required AWS config field: {field}")
        
        # Validate AWS credentials format (basic checks)
        access_key = config["aws_access_key_id"]
        if not access_key.startswith("AKIA") or len(access_key) != 20:
            raise ValueError("Invalid AWS Access Key ID format")
        
        secret_key = config["aws_secret_access_key"]
        if len(secret_key) != 40:
            raise ValueError("Invalid AWS Secret Access Key format")
        
        # Validate region
        region = config.get("aws_region", "us-east-1")
        valid_regions = [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1", "ap-southeast-1",
            "ap-southeast-2", "ap-northeast-1", "ap-northeast-2"
        ]
        if region not in valid_regions:
            raise ValueError(f"Invalid AWS region: {region}")
        
        # Validate SMS type
        sms_type = config.get("sms_type", "Transactional")
        if sms_type not in ["Promotional", "Transactional"]:
            raise ValueError("sms_type must be 'Promotional' or 'Transactional'")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute AWS SNS SMS sending.
        
        Expected input_data:
        - to_phone: Recipient phone number in E.164 format (required)
        - message: SMS message content (required)
        - subject: SMS subject (optional)
        """
        try:
            # Extract configuration
            access_key_id = config["aws_access_key_id"]
            secret_access_key = config["aws_secret_access_key"]
            region = config.get("aws_region", "us-east-1")
            sender_id = config.get("sender_id")
            sms_type = config.get("sms_type", "Transactional")
            max_price = config.get("max_price")
            api_timeout = config.get("api_timeout", 30)
            
            # Extract input data
            to_phone = input_data.get("to_phone")
            message = input_data.get("message")
            subject = input_data.get("subject")
            
            if not to_phone:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required field: to_phone"
                )
            
            if not message:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required field: message"
                )
            
            # Validate phone number format
            if not to_phone.startswith("+") or not to_phone[1:].isdigit():
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="to_phone must be in E.164 format (e.g., +1234567890)"
                )
            
            # Prepare AWS SNS API request
            service = "sns"
            endpoint = f"https://sns.{region}.amazonaws.com/"
            
            # Prepare parameters
            params = {
                "Action": "Publish",
                "PhoneNumber": to_phone,
                "Message": message,
                "Version": "2010-03-31"
            }
            
            if subject:
                params["Subject"] = subject
            
            # Add SMS attributes
            if sender_id:
                params["MessageAttributes.entry.1.Name"] = "AWS.SNS.SMS.SenderID"
                params["MessageAttributes.entry.1.Value.StringValue"] = sender_id
                params["MessageAttributes.entry.1.Value.DataType"] = "String"
            
            params["MessageAttributes.entry.2.Name"] = "AWS.SNS.SMS.SMSType"
            params["MessageAttributes.entry.2.Value.StringValue"] = sms_type
            params["MessageAttributes.entry.2.Value.DataType"] = "String"
            
            if max_price:
                params["MessageAttributes.entry.3.Name"] = "AWS.SNS.SMS.MaxPrice"
                params["MessageAttributes.entry.3.Value.StringValue"] = str(max_price)
                params["MessageAttributes.entry.3.Value.DataType"] = "Number"
            
            # Create AWS Signature Version 4
            signed_headers = await self._create_aws_signature(
                params, endpoint, access_key_id, secret_access_key, region, service
            )
            
            # Send request to AWS SNS
            form_data = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
            
            async with httpx.AsyncClient(timeout=api_timeout) as client:
                response = await client.post(
                    endpoint,
                    headers=signed_headers,
                    content=form_data
                )
                
                if response.status_code == 200:
                    # Success - parse XML response
                    response_text = response.text
                    
                    # Extract MessageId from XML response
                    import re
                    message_id_match = re.search(r'<MessageId>([^<]+)</MessageId>', response_text)
                    message_id = message_id_match.group(1) if message_id_match else None
                    
                    return ExecutionResult(
                        success=True,
                        output_data={
                            "message_id": message_id,
                            "to_phone": to_phone,
                            "message_status": "sent",
                            "sms_type": sms_type,
                            "sender_id": sender_id,
                            "region": region,
                            "service": "aws-sns",
                            "response_status": response.status_code
                        }
                    )
                
                else:
                    # Error response - parse XML error
                    error_text = response.text
                    
                    # Extract error details from XML
                    import re
                    error_code_match = re.search(r'<Code>([^<]+)</Code>', error_text)
                    error_message_match = re.search(r'<Message>([^<]+)</Message>', error_text)
                    
                    error_code = error_code_match.group(1) if error_code_match else "Unknown"
                    error_message = error_message_match.group(1) if error_message_match else error_text[:200]
                    
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"AWS SNS error: {error_message}",
                        error_details={
                            "status_code": response.status_code,
                            "error_code": error_code,
                            "aws_response": error_text[:500]
                        }
                    )
        
        except httpx.TimeoutException:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message="AWS SNS API timeout",
                error_details={
                    "timeout_seconds": api_timeout,
                    "error_type": "TimeoutException"
                }
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"AWS SNS SMS sending failed: {str(e)}",
                error_details={
                    "error_type": type(e).__name__,
                    "to_phone": input_data.get("to_phone")
                }
            )
    
    async def _create_aws_signature(
        self,
        params: Dict[str, str],
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        region: str,
        service: str
    ) -> Dict[str, str]:
        """Create AWS Signature Version 4."""
        from urllib.parse import urlparse
        
        # Current timestamp
        now = datetime.utcnow()
        amzdate = now.strftime('%Y%m%dT%H%M%SZ')
        datestamp = now.strftime('%Y%m%d')
        
        # Parse endpoint
        parsed_url = urlparse(endpoint)
        host = parsed_url.netloc
        canonical_uri = parsed_url.path if parsed_url.path else '/'
        
        # Create canonical query string
        sorted_params = sorted(params.items())
        canonical_querystring = '&'.join([f'{quote(k)}={quote(str(v))}' for k, v in sorted_params])
        
        # Create canonical headers
        canonical_headers = f'host:{host}\nx-amz-date:{amzdate}\n'
        signed_headers = 'host;x-amz-date'
        
        # Create payload hash
        payload = canonical_querystring
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # Create canonical request
        canonical_request = f'POST\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{datestamp}/{region}/{service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        
        # Create signing key
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        def getSignatureKey(key, dateStamp, regionName, serviceName):
            kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
            kRegion = sign(kDate, regionName)
            kService = sign(kRegion, serviceName)
            kSigning = sign(kService, 'aws4_request')
            return kSigning
        
        signing_key = getSignatureKey(secret_access_key, datestamp, region, service)
        
        # Create signature
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Create authorization header
        authorization_header = f'{algorithm} Credential={access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        return {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'X-Amz-Date': amzdate,
            'Authorization': authorization_header
        }
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for AWS SNS SMS sending."""
        return config.get("api_timeout", 30) + 10  # Add buffer
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing AWS SNS API connectivity."""
        try:
            access_key_id = config["aws_access_key_id"]
            secret_access_key = config["aws_secret_access_key"]
            region = config.get("aws_region", "us-east-1")
            
            # Test API connectivity by getting SMS attributes
            endpoint = f"https://sns.{region}.amazonaws.com/"
            params = {
                "Action": "GetSMSAttributes",
                "Version": "2010-03-31"
            }
            
            signed_headers = await self._create_aws_signature(
                params, endpoint, access_key_id, secret_access_key, region, "sns"
            )
            
            form_data = "&".join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    endpoint,
                    headers=signed_headers,
                    content=form_data
                )
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "status": "AWS SNS API accessible",
                        "details": {
                            "region": region,
                            "service": "sns",
                            "api_version": "2010-03-31"
                        }
                    }
                
                elif response.status_code == 403:
                    return {
                        "healthy": False,
                        "status": "AWS authentication failed",
                        "details": {
                            "status_code": response.status_code,
                            "error_type": "AuthenticationError"
                        }
                    }
                
                else:
                    return {
                        "healthy": False,
                        "status": f"AWS SNS API error: {response.status_code}",
                        "details": {
                            "status_code": response.status_code,
                            "error_type": "APIError",
                            "response": response.text[:200]
                        }
                    }
        
        except httpx.TimeoutException:
            return {
                "healthy": False,
                "status": "AWS SNS API timeout",
                "details": {
                    "error_type": "TimeoutException",
                    "timeout_seconds": 10
                }
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "status": f"AWS SNS health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for AWS SNS SMS handler."""
        return {
            "type": "object",
            "properties": {
                "aws_access_key_id": {
                    "type": "string",
                    "description": "AWS Access Key ID",
                    "pattern": "^AKIA[A-Z0-9]{16}$"
                },
                "aws_secret_access_key": {
                    "type": "string",
                    "description": "AWS Secret Access Key",
                    "minLength": 40,
                    "maxLength": 40
                },
                "aws_region": {
                    "type": "string",
                    "default": "us-east-1",
                    "enum": [
                        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
                        "eu-west-1", "eu-west-2", "eu-central-1", 
                        "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2"
                    ],
                    "description": "AWS region"
                },
                "sender_id": {
                    "type": "string",
                    "maxLength": 11,
                    "description": "Sender ID for SMS (max 11 alphanumeric characters)"
                },
                "sms_type": {
                    "type": "string",
                    "enum": ["Promotional", "Transactional"],
                    "default": "Transactional",
                    "description": "SMS type"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price per SMS in USD"
                },
                "api_timeout": {
                    "type": "number",
                    "default": 30,
                    "description": "API request timeout in seconds"
                }
            },
            "required": ["aws_access_key_id", "aws_secret_access_key"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for AWS SNS SMS handler."""
        return {
            "type": "object",
            "properties": {
                "to_phone": {
                    "type": "string",
                    "description": "Recipient phone number in E.164 format",
                    "pattern": "^\\+[1-9]\\d{1,14}$"
                },
                "message": {
                    "type": "string",
                    "maxLength": 1600,
                    "description": "SMS message content (max 1600 chars)"
                },
                "subject": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "SMS subject (optional)"
                }
            },
            "required": ["to_phone", "message"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for AWS SNS SMS handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "to_phone": {"type": "string"},
                "message_status": {"type": "string"},
                "sms_type": {"type": "string"},
                "sender_id": {"type": ["string", "null"]},
                "region": {"type": "string"},
                "service": {"type": "string"},
                "response_status": {"type": "integer"}
            },
            "required": ["success"]
        }