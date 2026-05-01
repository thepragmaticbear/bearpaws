---
name: cloud-run
description: Use when working on Google Cloud Run — gcloud run commands, service.yaml/cloudrun.yaml configuration, Dockerfiles in a GCP project context, or decisions about services vs. jobs, scaling, concurrency, secrets, identity, or auth
---

<skill>
  <purpose>
    Reference for Google Cloud Run mechanics. This is the *what* — services vs. jobs, the revision/traffic model, scaling and concurrency knobs, secrets, identity, auth. Pair with the workflow skill `deploying-to-cloud-run` for the *how-to-actually-deploy* checklist.
  </purpose>

  <triggers>
    <rule>Use when seeing `gcloud run deploy`, `gcloud run services`, `gcloud run jobs` in code or terminal context.</rule>
    <rule>Use when reading or writing `service.yaml`, `cloudrun.yaml`, or a `Dockerfile` in a GCP project.</rule>
    <rule>Use when deciding between services vs. jobs, allow-unauthenticated vs. IAM, min-instances=0 vs. >0.</rule>
  </triggers>

  <rules>
    <rule>Cloud Run *services* serve HTTP requests; *jobs* run to completion. Long-running batch work = job. Always-on API = service.</rule>
    <rule>Each `gcloud run deploy` creates a new immutable *revision*. Traffic routing is independent — 100% to latest by default, or split via `--no-traffic` + `gcloud run services update-traffic`.</rule>
    <rule>Default scaling is request-based; CPU is allocated only during requests. For background work, set `--no-cpu-throttling` (CPU stays on between requests). For faster cold-start CPU, add `--cpu-boost`.</rule>
    <rule>Concurrency default is 80 simultaneous requests per instance; tune down for memory-heavy or CPU-bound work.</rule>
    <rule>`--min-instances=0` is cheaper but cold-starts; `--min-instances=1+` removes cold-start at the cost of always-on billing.</rule>
    <rule>Runtime service account != deployer service account. Bind only the runtime SA to the resources the service actually accesses.</rule>
    <rule>`--allow-unauthenticated` makes the service publicly invokable. Without it, callers need `roles/run.invoker`. Default to authenticated; opt out only with explicit reason.</rule>
    <rule>Secrets from Secret Manager mount as env vars or files via `--set-secrets`. Don't bake secrets into images or env vars on the deploy command.</rule>
    <rule>VPC egress: use serverless VPC access connectors or Direct VPC egress for traffic that must reach private resources.</rule>
  </rules>

  <example type="good">
    A typical authenticated service deploy:

    ```bash
    gcloud run deploy api \
      --image=us-central1-docker.pkg.dev/$PROJECT/repo/api:$SHA \
      --region=us-central1 \
      --service-account=runtime-sa@$PROJECT.iam.gserviceaccount.com \
      --no-allow-unauthenticated \
      --set-secrets=DB_PASSWORD=db-password:latest \
      --concurrency=40 \
      --min-instances=1 \
      --max-instances=20
    ```
  </example>

  <example type="bad">
    `--allow-unauthenticated` on an internal-only service ("we'll fix permissions later"). Once public, attackers can hit the URL during the gap. Default to no, opt in with intent.
  </example>

  <antipattern>
    Using Cloud Run for hours-long batch processing as a service. The 60-minute request timeout will cut you off. Use a Cloud Run *job* instead.
  </antipattern>

  <see file="references/official-docs.md"/>
</skill>
