# Backup & Restore Procedures

## What to back up

| Path | Contents | Criticality |
|---|---|---|
| `data/` (project root, sibling of `smartgrid_simulation/`) | Blockchain ledger, meter readings, all generated datasets | **Critical** — the tamper-evidence of the PoA ledger depends on continuity |
| `smartgrid_simulation/outputs/early_stopping_final/`, `outputs/test_run_now/` | Trained model weights + preprocessing artifacts + threshold | **Critical** — losing these means re-running training (out of Phase 6 scope) |
| `smartgrid_simulation/production/security/users.json` | User accounts (hashes only) | Important — regenerable, but disruptive to lose |
| `smartgrid_simulation/.env` | Configuration + secrets | **Critical**, and must be backed up **separately/more securely** than the rest (it's the secret material) |
| `smartgrid_simulation/logs/` | Audit trail (predictions/attacks/blockchain/system) | Important for incident investigation, not for restart |

## What NOT to back up in the same place as the rest

`.env` contains `SGRID_JWT_SECRET_KEY` — back it up to a secrets manager or
encrypted store, not alongside plain data snapshots, and never commit it to
version control (`.gitignore` already excludes it — verified in
`security_report.md`).

## Backup command (simple, filesystem-level)

```powershell
# From the project root (parent of smartgrid_simulation/):
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force "backups\$stamp" | Out-Null
Copy-Item -Recurse "data" "backups\$stamp\data"
Copy-Item -Recurse "smartgrid_simulation\outputs\early_stopping_final" "backups\$stamp\model_v3"
Copy-Item -Recurse "smartgrid_simulation\outputs\test_run_now" "backups\$stamp\model_v2"
Copy-Item "smartgrid_simulation\production\security\users.json" "backups\$stamp\users.json"
```

For the 3-container Docker topology, the equivalent is backing up the
`../../../data` bind-mounted host directory and the `backend_logs` named
volume (`docker volume inspect` for its host path, or `docker run --rm -v
backend_logs:/l -v $(pwd):/backup alpine tar czf /backup/logs.tgz /l`).

## Restore

1. Stop the service.
2. Restore `data/` and the two `outputs/` model directories from the backup.
3. Restore `production/security/users.json` if user accounts changed since
   the backup (otherwise the current one is fine to keep).
4. Restart. Verify with `/health/ready` and
   `/api/blockchain/status` (`"valid": true`) before considering the
   restore complete.

## Blockchain-specific note

The PoA ledger's integrity check (`/api/blockchain/status`) will report
`"valid": false` if a restored ledger file doesn't match its own recorded
hashes (e.g. a partial/corrupted copy) — **do not** resume writing to a
ledger that fails validation; that would fork the chain of custody. Restore
from an earlier, valid backup instead.

## Disaster recovery — what "worst case" looks like

If both `data/` and the model `outputs/` are lost with no backup: the
blockchain audit trail is unrecoverable (by design — that's what makes it
tamper-evident), but the **model itself is not lost forever** — it can be
regenerated from the frozen scientific pipeline (Phases 0-5) using the
training scripts documented there, since those results are versioned
independently of the production runtime. This is why the model artifacts
and the operational data have different recovery paths.
