# WebhookEndpoint usage mismatches in service/adapter

## Summary
`WebhookDeliveryService` and `HttpWebhookAdapter` reference fields that don’t exist on `WebhookEndpoint`, and ignore existing ones.

## Evidence
- Entity field is `custom_headers`, no `headers` or `tenant_id`:
```27:66:neo-commons/src/neo_commons/features/events/entities/webhook_endpoint.py
custom_headers: Dict[str, str] = field(default_factory=dict)
...
verify_ssl: bool = True
...
created_by_user_id: UserId
```
- Service/adapter use `endpoint.headers` and `tenant_id`:
```429:436:neo-commons/src/neo_commons/features/events/services/webhook_delivery_service.py
return WebhookHeaderBuilder.build_delivery_headers(
    custom_headers=endpoint.headers,
    signature=signature,
    tenant_id=str(endpoint.tenant_id) if hasattr(endpoint, 'tenant_id') and endpoint.tenant_id else None,
    request_id=None
)
```
```197:204:neo-commons/src/neo_commons/features/events/adapters/http_webhook_adapter.py
request_headers = WebhookHeaderBuilder.build_delivery_headers(
    custom_headers=delivery.headers,
    signature=delivery.signature if hasattr(delivery, 'signature') else None,
    tenant_id=str(endpoint.tenant_id) if hasattr(endpoint, 'tenant_id') and endpoint.tenant_id else None
)
```

## Impact
- Attribute errors at runtime; headers not applied; multitenancy context header never set.

## Recommendations
- Replace all `endpoint.headers` with `endpoint.custom_headers`.
- If tenant scoping is required, add `tenant_id: Optional[UUID]` to `WebhookEndpoint` and persist it, or remove `tenant_id` usage.
- Ensure header builder callers pass the configured signature header name (see 005).

