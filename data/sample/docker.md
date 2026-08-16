# Docker Compose vs Kubernetes

## Compose
Docker Compose is the right default for a single VPS: one YAML file, restart policies, env files, named volumes.

## Kubernetes
Use Kubernetes when you need rolling deploys, many services, and a team operating the cluster. kind/k3s is enough to learn. A one-node toy cluster is not production HA.

## Secrets
Never commit `.env`. Mount secrets at runtime. Scan images in CI (for example Trivy) before you add a cluster.
