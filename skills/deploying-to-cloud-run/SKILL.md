---
name: deploying-to-cloud-run
description: Use when about to deploy a Cloud Run service or job — running gcloud run deploy, walking the pre-deploy checklist, post-deploy verification
---

<skill>
  <purpose>
    Pre-deploy checklist + the `gcloud run deploy` invocation + post-deploy verification. Hands off to `cloud-run` for *what* the flags mean.
  </purpose>

  <triggers>
    <rule>Use when about to run `gcloud run deploy` or its CI equivalent.</rule>
    <rule>Use when promoting a Cloud Run revision to production traffic.</rule>
  </triggers>

  <warning level="hard">
    Don't run `gcloud run deploy` until the checklist gate below is satisfied. Deploys are visible to your users immediately; "I'll fix it after" is a real outage in the gap.
  </warning>

  <gate name="checklist-complete">
    Before deploy, confirm out loud (in chat or commit message):

    - [ ] Region chosen (and matches the rest of the project's resources).
    - [ ] Image source decided: pre-built artifact registry image, or `--source` build-from-source?
    - [ ] Runtime service account named and bound to required resources only.
    - [ ] Secrets bound via `--set-secrets`, not baked in or set via `--set-env-vars`.
    - [ ] Min-instance decision: 0 (accept cold start) or >0 (always-on, pay always).
    - [ ] Concurrency value (default 80; tune down for memory or CPU heavy services).
    - [ ] Ingress mode (`all`, `internal`, `internal-and-cloud-load-balancing`).
    - [ ] Auth: `--no-allow-unauthenticated` unless deliberately public.

    If any item is unclear, invoke the `cloud-run` reference skill before continuing.
  </gate>

  <process>
    <step>Walk the gate checklist above. State each decision aloud (commit message or chat) before the deploy command runs.</step>
    <step>Run the deploy command. Example shape:

    ```bash
    gcloud run deploy $SERVICE \
      --image=$IMAGE --region=$REGION \
      --service-account=$RUNTIME_SA \
      --no-allow-unauthenticated \
      --set-secrets=$KEY=$SECRET_NAME:latest \
      --concurrency=$CONCURRENCY --min-instances=$MIN --max-instances=$MAX
    ```
    </step>
    <step>Capture the URL from the deploy output. Hit it (or the IAM-protected equivalent) and confirm a known-good response.</step>
    <step>Tail logs for ~60s: `gcloud run services logs tail $SERVICE --region=$REGION`. Watch for crash loops, missing-secret errors, permission errors.</step>
    <step>Check error rate in Cloud Run metrics for the new revision (Cloud Console or `gcloud monitoring`). If error rate spikes, roll back: `gcloud run services update-traffic $SERVICE --to-revisions=$PREV_REV=100`.</step>
  </process>

  <example type="bad">
    Skipping the gate: "I'll just push it, the test deploy was fine." The test deploy didn't have the production secrets bound. Service comes up, hits production with placeholders, error rate spikes, on-call gets paged.
  </example>

  <see file="../cloud-run/SKILL.md"/>
</skill>
