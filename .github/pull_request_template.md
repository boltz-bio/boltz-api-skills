## Checklist

- [ ] I edited source files under `core/` or `surfaces/`, not generated files under `plugins/boltz/` directly.
- [ ] If Claude Code plugin behavior changed, I ran `scripts/generate-surfaces.sh`.
- [ ] I ran `scripts/verify-generated.sh`.

## Notes

`plugins/boltz/` is generated from `surfaces/claude-code-cli/`. If a PR changes
only `plugins/boltz/`, move the change to the source surface or shared `core/`
files instead.
