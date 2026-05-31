# Cloudflare Tunnel

## Use Case

Cloudflare Tunnel is the documented deployment path when the server or Kubernetes
cluster does not have a public IP address or cannot expose inbound ports.

## Shape

Run `cloudflared` as:

- a container next to Docker Compose, or
- a Kubernetes deployment inside the cluster.

It routes a Cloudflare hostname to the internal API service. Secrets stay outside
git.

## Kubernetes Example

The example manifest is:

```text
deploy/k8s/cloudflared-deployment.example.yaml
```

Create the tunnel token secret outside git:

```bash
kubectl -n project-management create secret generic cloudflared-secret \
  --from-literal=tunnel-token='<cloudflare-tunnel-token>'
```

In Cloudflare Zero Trust, configure the tunnel public hostname to route to:

```text
http://project-management-api.project-management.svc.cluster.local:8000
```

Then apply the deployment:

```bash
kubectl apply -f deploy/k8s/cloudflared-deployment.example.yaml
```

## Django Settings

Keep these values aligned with the Cloudflare hostname:

```text
DJANGO_ALLOWED_HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS
DJANGO_CORS_ALLOWED_ORIGINS
```

For the public `radekkriz.space` and `www.radekkriz.space` hostnames, use:

```text
DJANGO_ALLOWED_HOSTS=radekkriz.space,www.radekkriz.space,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://radekkriz.space,https://www.radekkriz.space
```

Cloudflare terminates public HTTPS and forwards traffic into the cluster. Django
should still be configured as if it is behind an HTTPS reverse proxy.

## Justification

This allows HTTPS access through Cloudflare without opening inbound firewall ports
or requiring a public IPv4 address.

## Operational Notes

For production, run at least two `cloudflared` replicas when the account plan and
tunnel configuration support it. The example keeps one replica to stay minimal for
home-lab and assignment deployments.
