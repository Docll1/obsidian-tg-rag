# TLS and HTTP

## Ports
HTTP is 80. HTTPS is 443. The TLS handshake negotiates certificates and ciphers before HTTP starts.

## Certificates
A certificate binds a public key to a name. Let's Encrypt issues short-lived public certs. CAA DNS records limit which CAs may issue for a domain.

## Status codes
2xx success, 3xx redirect, 4xx client error, 5xx server error. 401 is unauthenticated, 403 is authenticated but forbidden.
