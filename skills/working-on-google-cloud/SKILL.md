---
name: working-on-google-cloud
description: Use when deploying to GCP, setting up infrastructure, configuring services, or debugging GCP deployment issues
---

<skill>

  <purpose>
    Workflow for common GCP operations: project setup, deploying services, configuring IAM, and debugging infrastructure.
  </purpose>

  <triggers>
    <rule>Use when setting up a new GCP project or deploying a service.</rule>
    <rule>Use when configuring IAM, networking, or infrastructure.</rule>
    <rule>Use when debugging deployment failures or permission issues.</rule>
  </triggers>

  <gate name="verify-project-context">
    Before any `gcloud` command: verify active project and auth. Run `gcloud config get-value project` and `gcloud auth list`. Wrong project = wrong deployment.
  </gate>

  <process>
    <step>**Verify context** — `gcloud config get-value project`, `gcloud config get-value account`. Confirm you're targeting the right project/env.</step>
    <step>**Check existing state** — `gcloud services list --enabled`, check what's already deployed, review IAM bindings.</step>
    <step>**Enable required APIs** — `gcloud services enable <api>.googleapis.com`. Common: run, cloudbuild, secretmanager, sqladmin, artifactregistry.</step>
    <step>**Configure service account** — Create dedicated SA, grant minimum roles, use for workload identity.</step>
    <step>**Deploy** — Use appropriate deploy command for service type. Verify with health check or smoke test.</step>
    <step>**Verify** — Check logs (`gcloud logging read`), test endpoint, confirm IAM works end-to-end.</step>
  </process>

  ## Common workflows

  **New service account:**
  ```bash
  gcloud iam service-accounts create {name} --display-name="{description}"
  gcloud projects add-iam-policy-binding {project} \
    --member="serviceAccount:{name}@{project}.iam.gserviceaccount.com" \
    --role="roles/{specific-role}"
  ```

  **Secret creation + access grant:**
  ```bash
  echo -n "value" | gcloud secrets create {name} --data-file=-
  gcloud secrets add-iam-policy-binding {name} \
    --member="serviceAccount:{sa}" --role="roles/secretmanager.secretAccessor"
  ```

  **Enable Artifact Registry + push:**
  ```bash
  gcloud services enable artifactregistry.googleapis.com
  gcloud artifacts repositories create {repo} --repository-format=docker --location={region}
  gcloud auth configure-docker {region}-docker.pkg.dev
  docker push {region}-docker.pkg.dev/{project}/{repo}/{image}:{tag}
  ```

  <rules>
    <rule>Always verify target project before destructive operations.</rule>
    <rule>Never use default compute service account for workloads — create dedicated SAs.</rule>
    <rule>Test IAM changes with `gcloud auth print-identity-token` or `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)"` before deploying dependents.</rule>
    <rule>Use `--quiet` flag in CI scripts to suppress interactive prompts.</rule>
  </rules>

  <antipattern>
    Granting `roles/editor` or `roles/owner` to a service account. Use the most specific predefined role (e.g., `roles/run.invoker`, `roles/secretmanager.secretAccessor`).
  </antipattern>

  <antipattern>
    Creating service account keys for CI/CD. Use Workload Identity Federation to authenticate from GitHub Actions, GitLab, or other CI providers without key files.
  </antipattern>

</skill>
