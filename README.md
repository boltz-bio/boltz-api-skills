# Boltz Compute Skills

A collection of agent skills for running Boltz protein structure predictions through AI coding assistants.

## Contents

| Folder | Description |
|--------|-------------|
| `skills-python/` | Claude Code skills |
| `codex-plugin-python/` | OpenAI Codex plugin |

---

## Claude Code Skills (`skills-python/`)

### Installation

1. Clone the repo
2. Tell Claude Code to install the skills at the local path — it will add them to `.claude.json`
3. Start a fresh session and start querying Claude

---

## Codex Plugin (`codex-plugin-python/`)

### Installation

1. Clone the repo
2. Tell Codex to add this plugin from the local path
3. Start a fresh session — you should see the plugin listed under `/plugins`

---

## Differences

The two implementations are mostly identical, with a few exceptions:

- The Codex plugin includes extra plugin metadata (`plugin.json`) — this should be edited before use
- Codex recommended trimming `skill.md` and moving extra information into a separate `api.md` (suggested by the skill-creator skill in Codex)

---

## Expected Behavior

When you ask your agent to perform a Boltz-relevant task (e.g. *"fold a protein"*), it will:

1. Read the appropriate `skill.md`
2. Estimate the compute cost (enforced via `skill.md`)
3. Ask for confirmation before proceeding
4. Run the job, poll for completion, and download the output structure and metadata

> Note: It would be nice to surface the confirmation step in the native Claude Code / Codex permissions UI, but there's no known way to do this currently.
