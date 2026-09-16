#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'run with sudo'; exit 1; fi
SOURCE="${1:-$PWD}"
id edgeppe >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/edgeppe --shell /usr/sbin/nologin edgeppe
mkdir -p /opt/edge-ppe-lab /etc/edge-ppe
rsync -a --delete --exclude '.git' --exclude '.venv' "$SOURCE/" /opt/edge-ppe-lab/
python3 -m venv /opt/edge-ppe-lab/.venv
/opt/edge-ppe-lab/.venv/bin/pip install -r /opt/edge-ppe-lab/requirements.txt
install -m 0644 /opt/edge-ppe-lab/deploy/systemd/edge-ppe.service /etc/systemd/system/edge-ppe.service
if [[ ! -f /etc/edge-ppe/edge-ppe.env ]]; then
  install -m 0640 /opt/edge-ppe-lab/deploy/systemd/edge-ppe.env.example /etc/edge-ppe/edge-ppe.env
fi
chown root:edgeppe /etc/edge-ppe/edge-ppe.env
chmod 0640 /etc/edge-ppe/edge-ppe.env
chown -R edgeppe:edgeppe /opt/edge-ppe-lab
systemctl daemon-reload
echo 'Edit /etc/edge-ppe/edge-ppe.env, then: sudo systemctl enable --now edge-ppe'
