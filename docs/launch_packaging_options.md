# Launch packaging options beyond Docker

DueCare already has validated local CLI and container paths. The next launch improvements should reduce setup friction while keeping privacy claims honest and aligned with the website's five-lane story.

## Current validated baseline

| Path | Status | Best for |
|---|---|---|
| `pip install duecare-llm-cli` → `duecare init` → `duecare demo-stage` → `duecare serve --port 8080` | Smoke-tested from local wheels | Developers, judges, local demos |
| `docker-compose.enterprise.yml` with `.env.enterprise.example` | Compose config validated | Private/local organization stack |
| `duecare-llm` workflow CLI | Validated for `duecare run rapid_probe` against a local OpenAI-compatible backend | Model/backend workflow evaluation |

## Recommended next packaging tracks

| Track | What it gives users | Implementation shape | Claim only after |
|---|---|---|---|
| `pipx` installer | One command, isolated CLI on Windows/macOS/Linux | Publish `duecare-llm-cli`; document `pipx install duecare-llm-cli` | Fresh-machine smoke test |
| Offline wheelhouse | No internet after download; useful for NGOs | `duecare-offline-wheelhouse-<version>.zip` with DueCare + third-party wheels | No-index install succeeds in clean `virtualenv` |
| Desktop launcher bundle | Double-click local app | Extend `scripts/setup_consumer.py` to create OS launchers | Windows/macOS/Linux launcher smoke tests |
| AWS EC2 AMI | Prebuilt VM with ports, service, Nginx, and optional model cache | Packer or EC2 Image Builder AMI with systemd `duecare`, Nginx, CloudWatch/SSM, security group docs | Boot test from AMI, health check, vulnerability scan |
| AWS Marketplace AMI | Click-to-launch for organizations already on AWS | Marketplace listing around the tested AMI, license/EULA, support metadata | AWS review + private preview install |
| Lightsail snapshot/blueprint | Simpler AWS path than EKS | Lightsail instance snapshot from the AMI recipe or scripted bootstrap | Fresh Lightsail launch + `/healthz` check |
| CloudFormation/CDK quick launch | Reproducible AWS install without containers | VPC/security group/EC2/EBS/Route53/ACM template | Stack create/delete test |
| Azure/GCP VM image | Marketplace-like install outside AWS | Azure Compute Gallery / GCP machine image | Fresh VM boot + health check |
| DigitalOcean 1-Click App | Small NGO/developer VPS path | Droplet image or one-click app spec | Marketplace app validation |

## AWS AMI shape

An AMI is a strong fit for NGO offices and platform pilots that want a preconfigured server but do not want to operate Kubernetes.

Suggested AMI contents:

- Ubuntu LTS base image.
- Python 3.11/3.12 environment with DueCare wheels installed.
- `duecare` system user.
- systemd unit running `duecare serve --host 127.0.0.1 --port 8080`.
- Nginx listening on ports 80/443 and proxying to `127.0.0.1:8080`.
- `/healthz` exposed for load balancer checks.
- Optional EBS mount at `/var/lib/duecare` for local data/model cache.
- Optional Ollama install, but model pulls should be explicit and documented because of disk/VRAM size.
- CloudWatch agent and AWS Systems Manager Session Manager enabled for operator access without opening SSH by default.
- Security group template: 80/443 public, 22 closed by default, 8080 private only.

Do not publish an AMI or Marketplace listing until the image is boot-tested from scratch, scanned, and documented with exact costs and teardown steps.

## Privacy language to preserve

Raw worker chats, IDs, contact details, and private documents stay on the local machine, AMI volume, or private tenant deployment unless an authorized user explicitly creates a sanitized export. A marketplace listing should repeat this concrete data-flow language rather than using vague privacy slogans.

Launch packages should also expose the submission labeling controls from [submission_labeling_policy.md](submission_labeling_policy.md): deployments can default to anonymous, pseudonymous tenant, organization-tagged, or verified-organization submissions; local Gemma 4 can suggest region/corridor/sector labels, but the user or tenant policy must approve what is shared with the hub.

## Best next step

Build the offline wheelhouse first. It helps every other path: `pipx`, desktop launchers, AMIs, and air-gapped NGO installs all need the same clean install artifact.