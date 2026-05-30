# Cloudflare Tunnel

## Use Case

Cloudflare Tunnel is the documented deployment path when the server or Kubernetes
cluster does not have a public IP address or cannot expose inbound ports.

## Shape

Run `cloudflared` as:

- a container next to Docker Compose, or
- a Kubernetes deployment inside the cluster.

It routes a Cloudflare hostname to the internal API service.

Secrets stay outside git.

## Justification

This allows HTTPS access through Cloudflare without opening inbound firewall ports
or requiring a public IPv4 address.

