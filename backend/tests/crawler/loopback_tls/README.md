# A throwaway TLS pair for a listener on 127.0.0.1

`cert.pem` and `key.pem` are a self-signed certificate and its private key,
generated once for `tests/crawler/test_transport_over_loopback.py`. **They secure
nothing, they are not a secret, and nothing outside these tests trusts them** -
the tests build their own `SSLContext` with this certificate as its own CA.

The certificate names **`alphaplumbing.example` and nothing else**. That absence
is load-bearing twice over:

* there is no `IP:127.0.0.1` in the SAN, so a request that reaches the listener
  WITHOUT the `sni_hostname` extension verifies the IP literal against a
  certificate that names no address, and fails - which is what makes the
  extension provably load-bearing rather than argued about;
* it names one host, so a second host name pinned to the same address is refused
  unless it gets its own handshake - which is what measures connection reuse.

Regenerated, if it ever needs to be, with:

```
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
  -keyout key.pem -out cert.pem -days 36500 \
  -subj "/CN=alphaplumbing.example" \
  -addext "subjectAltName=DNS:alphaplumbing.example" \
  -addext "basicConstraints=critical,CA:TRUE"
```

It is valid until 2126, so this is not a maintenance task anybody should meet.
