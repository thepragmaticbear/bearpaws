---
name: google-cloud
description: Use when working on Google Cloud Platform projects, choosing GCP services, configuring IAM, or debugging GCP-related issues
---

<skill>

  <purpose>
    Reference knowledge for Google Cloud Platform: service selection, IAM model, networking, and common patterns across GCP services.
  </purpose>

  <triggers>
    <rule>Use when working in a GCP project or choosing between GCP services.</rule>
    <rule>Use when configuring IAM, service accounts, or permissions.</rule>
    <rule>Use when debugging GCP deployment, networking, or auth issues.</rule>
  </triggers>

  <rules>
    <rule>**Principle of least privilege** — service accounts get only the roles they need. Never use Editor/Owner for workloads. Prefer predefined roles over primitive roles.</rule>
    <rule>**Service accounts for workloads** — every workload (Cloud Run, GCE, Cloud Functions) runs as a dedicated service account, not the default compute SA.</rule>
    <rule>**Project structure** — separate projects for prod/staging/dev. Use folders for organizational grouping. Billing alerts on every project.</rule>
    <rule>**Region selection** — co-locate services in the same region to minimize latency and egress costs. Multi-region only when HA requirements demand it.</rule>
    <rule>**Secret Manager over env vars** — sensitive values go in Secret Manager, mounted at runtime. Never commit secrets, never pass via plain env vars in config files.</rule>
    <rule>**Cloud Logging structured** — emit JSON logs with severity, trace context, and labels. Use log-based metrics for alerting. Exclusion filters to control cost.</rule>
    <rule>**VPC and networking** — Serverless VPC Access connector for Cloud Run/Functions to reach VPC resources. Private Google Access for VMs without external IPs.</rule>
    <rule>**gcloud auth** — `gcloud auth login` for user auth, `gcloud auth application-default login` for local dev ADC. In CI, use workload identity federation over service account keys.</rule>
  </rules>

  ## Service selection

  | Need | Service | When NOT to use |
  |---|---|---|
  | HTTP APIs / web apps | Cloud Run | Long-running (>60min), GPU, websocket-heavy |
  | Event-driven functions | Cloud Functions (2nd gen) | Complex apps (use Cloud Run instead) |
  | Background jobs / batch | Cloud Run Jobs | Real-time requirements |
  | Managed containers | GKE | Simple apps (overkill — use Cloud Run) |
  | Static sites | Cloud Storage + CDN | Dynamic content |
  | Relational DB | Cloud SQL | Global scale (use Spanner) |
  | Document DB | Firestore | Analytics workloads (use BigQuery) |
  | Cache | Memorystore (Redis) | Persistent storage |
  | Queues | Pub/Sub | Strict ordering (use Pub/Sub + ordering key, or Cloud Tasks) |
  | Scheduling | Cloud Scheduler | Sub-minute intervals (use Cloud Tasks) |
  | CI/CD | Cloud Build | Complex pipelines (consider GitHub Actions) |

  ## IAM model

  - **Members** (who): user, serviceAccount, group, domain
  - **Roles** (what): collection of permissions. Use predefined (`roles/run.invoker`) over custom when possible.
  - **Bindings** (where): member + role + resource. Applied at project, folder, or resource level. Inheritance flows down.
  - **Conditions**: IAM conditions for time-based or attribute-based access.

  ## Common debugging

  | Problem | Check |
  |---|---|
  | Permission denied | `gcloud projects get-iam-policy` — verify SA has role; check resource-level bindings |
  | Can't reach VPC resource from serverless | VPC connector configured? In same region? Firewall rules allow ingress from connector range? |
  | Cloud SQL connection refused | Using Cloud SQL Auth Proxy or Cloud SQL connector? Private IP requires VPC connector. |
  | Deployment fails | Check Cloud Build logs: `gcloud builds list --limit=5` |
  | High latency between services | Services in different regions? Check network topology. |
  | Billing spike | `gcloud billing budgets list`; check resource labels; look for idle resources |

</skill>
