# boltz-mcpb

Claude Desktop MCPB distribution for Boltz workflows. This bundle runs a local
Node.js MCP server and shells out to the `boltz-api` CLI with the same
estimate/start/download shape used by the Claude Code and Codex skill plugins.

## Tools

- `boltz_check_setup` verifies `boltz-api`, auth, and output configuration.
- `boltz_install_cli` explicitly installs or updates `boltz-api` with the official installer.
- `boltz_auth_login` starts `boltz-api auth login --device-code`.
- Workflow tools estimate and optionally start one Boltz job, then optionally launch `download-results`.
- `boltz_download_results` resumes result downloads for existing jobs.
- `boltz_job_status` checks local download status, remote retrieve status, or downloader tails.

## Development

```sh
npm install
npm test
npm install --production
mcpb pack
```

Install the produced `.mcpb` in Claude Desktop with Settings -> Extensions ->
Advanced settings -> Install Extension.
