# PDF Manager — Agent Context

- Slug: `pdf-manager`
- Source: `/home/locdodoan/webapps/projects/pdf-manager`
- Service: `pdf-manager.service`
- Port: `3511`
- Runtime: Python
- Runtime paths: uploads, backups, logs
- Data class: restricted

## Rules

- Uploaded PDFs contain protected operational/customer material. Never commit, copy to worktree, or expose them in broad prompt context.
- Production checkout is deploy-only; worktrees only for code work.
- PDF/runtime migration needs dedicated approval, full manifest/checksum, rollback, and live retrieval verification.
- Verify rendered output and access path, not only HTTP 200, after approved change.

Registry: `/home/locdodoan/webapps/registry/projects.yaml`
