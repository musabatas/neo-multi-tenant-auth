# Signature header alignment mismatch

## Summary
`WebhookHeaderBuilder` hardcodes `X-Neo-Signature` for delivery, while `WebhookEndpoint` exposes `signature_header` (default `X-Webhook-Signature`).

## Evidence
- Endpoint exposes configurable signature header:
```36:41:neo-commons/src/neo_commons/features/events/entities/webhook_endpoint.py
secret_token: str
signature_header: str = "X-Webhook-Signature"
```
- Header builder unconditionally uses `X-Neo-Signature`:
```92:99:neo-commons/src/neo_commons/features/events/utils/header_builder.py
if signature and context == HeaderContext.DELIVERY:
    headers["X-Neo-Signature"] = signature
```

## Impact
- Receivers expecting `signature_header` won’t see the signature. Breaks verification.

## Recommendations
- Change header builder API to accept a `signature_header_name` and use it when provided.
- Update callers (`WebhookDeliveryService`, adapter) to pass `endpoint.signature_header`.
- Keep `X-Neo-Signature` as fallback only when no name is provided.

