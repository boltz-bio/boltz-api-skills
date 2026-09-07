## Checklist

- [ ] I edited canonical `skills/` or `surfaces/` source and regenerated `plugins/` where needed.
- [ ] I ran `npm test` for skill or distribution changes.
- [ ] I ran `scripts/verify-generated.sh`.
- [ ] I ran the relevant MCP or protein-design helper tests for runtime changes.

## Notes

Public skills are installed directly from `skills/` with Vercel Skills.
Marketplace and MCPB copies under `plugins/` are generated distribution packages.
