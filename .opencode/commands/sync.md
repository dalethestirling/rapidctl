---
description: Sync versions across all 3 rapidctl repos
agent: cross-repo
---

Coordinate version alignment across rapidctl, rapidctl-container, and rapidctl-examplectl.

## Check Current Versions
```bash
# rapidctl (hatch-vcs)
cd rapidctl && git describe --tags

# rapidctl-container (GHCR tags)
# Check https://github.com/dalethestirling/rapidctl-container/pkgs/container/rapidctl-container

# examplectl baseline
cd rapidctl-examplectl && grep baseline_version examplectl
```

## Sync Workflow
1. **Container publishes**: Push to rapidctl-container main → auto-creates timestamp tag
2. **Update examplectl**: Set `baseline_version = "<new-timestamp>"` in examplectl script
3. **Library release** (if needed): Tag `v*` in rapidctl → PyPI publish

## Breaking Changes Requiring Full Sync
- commands.json schema changes
- Command path changes (/opt/rapidctl/cmd/)
- Container contract changes
- CLI argument parsing changes