# DueCare AI hub on Kubernetes

Real, minimal manifests for running the DueCare AI hub server (the public
website + central knowledge server, `apps/duecare-ai.com`) on a cluster.
They are grounded in `apps/duecare-ai.com/Dockerfile`: the container
listens on **port 10000** and serves its health check at **`/api/health`**.

| File | Kind | Purpose |
|---|---|---|
| `configmap.yaml` | ConfigMap | Non-secret `DUECARE_*` env (mirrors the Dockerfile / render.yaml). |
| `deployment.yaml` | Deployment | The hub container, readiness + liveness on `/api/health`, resource requests/limits, a data volume. |
| `service.yaml` | Service | ClusterIP; port 80 -> container port 10000. |
| `ingress.yaml` | Ingress | Public host + TLS (placeholders to fill in). |

## Placeholders to edit before applying

| Placeholder | In file | Replace with |
|---|---|---|
| `REGISTRY_PLACEHOLDER` | `deployment.yaml` | Your image registry/repo, e.g. `ghcr.io/yourorg`. |
| `HOST_PLACEHOLDER` | `ingress.yaml` | Your public hostname, e.g. `duecare-ai.com`. |
| `CLUSTER_ISSUER_PLACEHOLDER` | `ingress.yaml` | Your cert-manager ClusterIssuer name, e.g. `letsencrypt-prod`. |

The Ingress assumes an nginx ingress controller and cert-manager. Adapt
`ingressClassName` and the TLS annotation to whatever your cluster runs.

## 1. Build and push the image

```bash
# From the repo root. The Dockerfile lives in apps/duecare-ai.com.
docker build -t REGISTRY_PLACEHOLDER/duecare-ai-hub:latest apps/duecare-ai.com
docker push REGISTRY_PLACEHOLDER/duecare-ai-hub:latest
```

## 2. Apply

```bash
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/deployment.yaml
kubectl apply -f deployment/k8s/service.yaml
kubectl apply -f deployment/k8s/ingress.yaml
# or, all at once:
kubectl apply -f deployment/k8s/
```

## 3. Verify

```bash
kubectl rollout status deployment/duecare-ai-hub
kubectl get pods -l app.kubernetes.io/name=duecare-ai-hub

# Health check without the ingress:
kubectl port-forward deploy/duecare-ai-hub 10000:10000
curl -fsS http://127.0.0.1:10000/api/health
# -> {"status":"ok","service":"duecare-ai-hub","storage":"file", ...}
```

## Durable knowledge storage (recommended)

`deployment.yaml` ships with an `emptyDir` volume so it runs out of the
box, but that volume is wiped when the pod restarts. For a real hub that
keeps its knowledge submissions and vetted packs, replace the volume with
a PersistentVolumeClaim.

Create a PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: duecare-ai-hub-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

Then in `deployment.yaml`, swap the `volumes:` entry:

```yaml
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: duecare-ai-hub-data
```

The mount path (`/app/.duecare`, i.e. `DUECARE_DATA_DIR`) stays the same.

## Secrets

Non-secret config lives in `configmap.yaml`. If your hub needs an admin /
curator token (`DUECARE_ADMIN_TOKEN`), put it in a Secret and reference it
from the container, do NOT add it to the ConfigMap:

```bash
kubectl create secret generic duecare-ai-hub-secrets \
  --from-literal=DUECARE_ADMIN_TOKEN=REPLACE_ME
```

```yaml
          envFrom:
            - configMapRef:
                name: duecare-ai-hub-config
            - secretRef:
                name: duecare-ai-hub-secrets
```

## Notes

- Port `10000` and health path `/api/health` are taken directly from
  `apps/duecare-ai.com/Dockerfile`; do not change one without the other.
- These manifests were validated to parse (`yaml.safe_load`) but are a
  starting point, not a hardened production install. Review resource
  sizing, replicas, network policy, and PVC storage class for your
  cluster before going live.
- For managed hosting without a cluster, `render.yaml` at the repo root
  deploys the same image on Render. See `docs/DEPLOYMENT.md`.