# Boltz

Predict structures, screen molecules and proteins, and design binders with
Boltz.

## Tools

- `boltz_check_setup` verifies access, sign-in, and output configuration.
- `boltz_install_cli` installs or updates the local Boltz components required to run workflows.
- `boltz_auth_login` starts Boltz sign-in through a Boltz-owned auth link.
- Workflow tools estimate and optionally start one Boltz job, then optionally download results.
- `boltz_download_results` resumes result downloads for existing jobs.
- `boltz_job_status` checks job progress, local result download state, or recent downloader activity.

## Privacy Policy

Boltz's privacy policy is available at https://boltz.bio/privacy.

This desktop extension stores local setup, sign-in, and result-download state
on the user's machine. Boltz workflow inputs, job metadata, and downloaded
result artifacts are sent to and retrieved from Boltz services when users run
workflow tools. The extension does not collect Claude conversations beyond the
tool inputs needed to run the requested Boltz workflow.

## Development

```sh
npm install
npm test
npm install --production
mcpb pack
```

Install the produced `.mcpb` with Settings -> Extensions -> Advanced settings
-> Install Extension.
