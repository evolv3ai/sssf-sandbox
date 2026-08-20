# Namespaced host-only sandbox controls: `just sbx <recipe>`.
# These recipes are intentionally thin; sandbox/host/sbx.py owns lifecycle state.
set dotenv-load

runner := "../host/sbx.py"

default:
    @just --list

# Local, non-billable prerequisite and layout check.
doctor *ARGS:
    python3 {{runner}} doctor {{ARGS}}

# Billable: create a VM and capped key, clone this repo, provision it, then observe. Never tears down.
mount RUN_ID *ARGS:
    python3 {{runner}} mount {{RUN_ID}} {{ARGS}}

# Start SSSF SDLC detached inside an already-mounted VM.
execute RUN_ID PROMPT:
    python3 {{runner}} execute {{RUN_ID}} {{PROMPT}}

# Print a status/log snapshot for a sandbox.
observe RUN_ID:
    python3 {{runner}} observe {{RUN_ID}}

# Print the latest 80 VM workflow log lines.
logs RUN_ID:
    python3 {{runner}} logs {{RUN_ID}}

# Import run commits into refs/sandbox/<run-id>; does not mutate a branch.
harvest RUN_ID:
    python3 {{runner}} harvest {{RUN_ID}}

# Explicit destructive cleanup. Harvests first unless --no-harvest is supplied.
teardown RUN_ID *ARGS:
    python3 {{runner}} teardown {{RUN_ID}} {{ARGS}}
