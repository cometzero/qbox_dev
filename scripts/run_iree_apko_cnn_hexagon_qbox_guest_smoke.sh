#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

cat <<EOF
FAIL: generic APKO CNN smoke is blocked.
Reason: the Apollo Hexagon APKO executable/runtime ABI is not implemented yet,
so QBox can only run the preserved compat tiny-CNN lane.
Compat fallback: ${repo_root}/scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
EOF

exit 2
