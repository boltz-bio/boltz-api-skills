.PHONY: generate-surfaces verify-generated validate-claude-plugin validate-json

generate-surfaces:
	scripts/generate-surfaces.sh

verify-generated:
	scripts/verify-generated.sh

validate-json:
	jq empty surfaces/codex-cli/.codex-plugin/plugin.json
	jq empty plugins/boltz-api-cli/.codex-plugin/plugin.json

validate-claude-plugin:
	claude plugin validate .
	claude plugin validate plugins/boltz
