"""Twilio SMS action handler implementation."""

import asyncio
import httpx
import base64
from typing import Dict, Any, Optional
from datetime import datetime

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class TwilioSMSHandler(ActionHandler):
    """
    Twilio SMS handler for sending SMS messages via Twilio API.
    
    Configuration:
    - account_sid: Twilio Account SID (required)
    - auth_token: Twilio Auth Token (required)  
    - from_phone: From phone number in E.164 format (required)
    - api_timeout: API request timeout in seconds (default: 30)
    - webhook_url: Optional webhook URL for delivery status
    - max_price: Maximum price per SMS (optional)
    - validity_period: Message validity period in seconds (optional)
    """
    
    @property
    def handler_name(self) -> str:
        return "twilio_sms_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["sms", "text_message", "twilio_sms"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Twilio SMS handler configuration."""
        required_fields = ["account_sid", "auth_token", "from_phone"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required Twilio config field: {field}")
        
        # Validate account SID format
        account_sid = config["account_sid"]
        if not account_sid.startswith("AC") or len(account_sid) != 34:
            raise ValueError("Invalid Twilio Account SID format")
        
        # Validate auth token format
        auth_token = config["auth_token"]
        if len(auth_token) != 32:
            raise ValueError("Invalid Twilio Auth Token format")
        
        # Validate phone number format (basic E.164 check)
        from_phone = config["from_phone"]
        if not from_phone.startswith("+") or not from_phone[1:].isdigit():
            raise ValueError("from_phone must be in E.164 format (e.g., +1234567890)")
        
        # Validate timeout
        timeout = config.get("api_timeout", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("api_timeout must be a positive number")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute Twilio SMS sending.
        
        Expected input_data:
        - to_phone: Recipient phone number in E.164 format (required)
        - message: SMS message content (required)
        - media_url: MMS media URL (optional)
        - attempt_phone_number_lookup: Validate phone number (optional, default: false)
        """
        try:
            # Extract configuration
            account_sid = config["account_sid"]
            auth_token = config["auth_token"]
            from_phone = config["from_phone"]
            api_timeout = config.get("api_timeout", 30)
            webhook_url = config.get("webhook_url")
            max_price = config.get("max_price")
            validity_period = config.get("validity_period")
            
            # Extract input data
            to_phone = input_data.get("to_phone")
            message = input_data.get("message")
            media_url = input_data.get("media_url")
            attempt_lookup = input_data.get("attempt_phone_number_lookup", False)
            
            if not to_phone:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required field: to_phone"
                )
            
            if not message and not media_url:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Either message or media_url is required"
                )
            
            # Validate phone number format
            if not to_phone.startswith("+") or not to_phone[1:].isdigit():
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="to_phone must be in E.164 format (e.g., +1234567890)"
                )
            
            # Prepare Twilio API request
            api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            
            # Prepare authentication
            auth_string = f"{account_sid}:{auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Prepare form data
            form_data = {
                "From": from_phone,
                "To": to_phone
            }
            
            if message:
                form_data["Body"] = message
            
            if media_url:
                form_data["MediaUrl"] = media_url
            
            if webhook_url:
                form_data["StatusCallback"] = webhook_url
            
            if max_price:
                form_data["MaxPrice"] = str(max_price)
            
            if validity_period:
                form_data["ValidityPeriod"] = str(validity_period)
            
            if attempt_lookup:
                form_data["AttemptPhoneNumberLookup"] = "true"
            
            # Send SMS via Twilio API
            async with httpx.AsyncClient(timeout=api_timeout) as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    data=form_data
                )
                
                if response.status_code == 201:
                    # Success
                    response_data = response.json()
                    
                    return ExecutionResult(
                        success=True,
                        output_data={
                            "message_sid": response_data.get("sid"),
                            "from_phone": from_phone,
                            "to_phone": to_phone,
                            "message_status": response_data.get("status"),
                            "message_direction": response_data.get("direction"),
                            "price": response_data.get("price"),
                            "price_unit": response_data.get("price_unit"),
                            "num_segments": response_data.get("num_segments"),
                            "date_created": response_data.get("date_created"),
                            "date_sent": response_data.get("date_sent"),
                            "api_version": response_data.get("api_version"),
                            "account_sid": response_data.get("account_sid")
                        }
                    )
                
                else:
                    # Error response
                    try:
                        error_data = response.json()
                        error_message = error_data.get("message", f"HTTP {response.status_code}")
                        error_code = error_data.get("code")
                    except:
                        error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                        error_code = None
                    
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"Twilio API error: {error_message}",
                        error_details={
                            "status_code": response.status_code,
                            "error_code": error_code,
                            "twilio_response": error_data if 'error_data' in locals() else None
                        }
                    )
        
        except httpx.TimeoutException:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message="Twilio API timeout",
                error_details={
                    "timeout_seconds": api_timeout,
                    "error_type": "TimeoutException"
                }
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Twilio SMS sending failed: {str(e)}",
                error_details={
                    "error_type": type(e).__name__,
                    "to_phone": input_data.get("to_phone")
                }
            )
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for Twilio SMS sending."""
        return config.get("api_timeout", 30) + 10  # Add buffer
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing Twilio API connectivity."""
        try:
            account_sid = config["account_sid"]
            auth_token = config["auth_token"]
            api_timeout = config.get("api_timeout", 30)
            
            # Test API connectivity by fetching account info
            api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
            
            auth_string = f"{account_sid}:{auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}"
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    account_data = response.json()
                    
                    return {
                        "healthy": True,
                        "status": "Twilio API accessible",
                        "details": {
                            "account_sid": account_data.get("sid"),
                            "account_status": account_data.get("status"),
                            "account_type": account_data.get("type"),
                            "api_version": "2010-04-01"
                        }
                    }
                
                elif response.status_code == 401:
                    return {
                        "healthy": False,
                        "status": "Twilio authentication failed",
                        "details": {
                            "status_code": response.status_code,
                            "error_type": "AuthenticationError"
                        }
                    }
                
                else:
                    return {
                        "healthy": False,
                        "status": f"Twilio API error: {response.status_code}",
                        "details": {
                            "status_code": response.status_code,
                            "error_type": "APIError"
                        }
                    }
        
        except httpx.TimeoutException:
            return {
                "healthy": False,
                "status": "Twilio API timeout",
                "details": {
                    "error_type": "TimeoutException",
                    "timeout_seconds": 10
                }
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Twilio health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for Twilio SMS handler."""
        return {
            "type": "object",
            "properties": {
                "account_sid": {
                    "type": "string",
                    "description": "Twilio Account SID",
                    "pattern": "^AC[a-zA-Z0-9]{32}$"
                },
                "auth_token": {
                    "type": "string",
                    "description": "Twilio Auth Token",
                    "minLength": 32,
                    "maxLength": 32
                },
                "from_phone": {
                    "type": "string",
                    "description": "From phone number in E.164 format",
                    "pattern": "^\\+[1-9]\\d{1,14}$"
                },
                "api_timeout": {
                    "type": "number",
                    "default": 30,
                    "description": "API request timeout in seconds"
                },
                "webhook_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Webhook URL for delivery status"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price per SMS in USD"
                },
                "validity_period": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 14400,
                    "description": "Message validity period in seconds (max 4 hours)"
                }
            },
            "required": ["account_sid", "auth_token", "from_phone"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for Twilio SMS handler."""
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
                "media_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "MMS media URL (for multimedia messages)"
                },
                "attempt_phone_number_lookup": {
                    "type": "boolean",
                    "default": False,
                    "description": "Validate phone number before sending"
                }
            },
            "required": ["to_phone"],
            "anyOf": [
                {"required": ["message"]},
                {"required": ["media_url"]}
            ]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for Twilio SMS handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_sid": {"type": "string"},
                "from_phone": {"type": "string"},
                "to_phone": {"type": "string"},
                "message_status": {"type": "string"},
                "message_direction": {"type": "string"},
                "price": {"type": ["string", "null"]},
                "price_unit": {"type": "string"},
                "num_segments": {"type": "integer"},
                "date_created": {"type": "string"},
                "date_sent": {"type": ["string", "null"]},
                "api_version": {"type": "string"},
                "account_sid": {"type": "string"}
            },
            "required": ["success"]
        }