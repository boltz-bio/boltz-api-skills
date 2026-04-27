.PHONY: generate-surfaces verify-generated validate-claude-plugin

generate-surfaces:
	scripts/generate-surfaces.sh

verify-generated:
	scripts/verify-generated.sh

validate-claude-plugin:
	claude plugin validate .
	claude plugin validate plugins/boltz
