#!/usr/bin/env bash

radvd --logmethod=stderr_syslog --pidfile=/run/radvd.pid

# mdns announcement
announce_mdns.py &

# serve static pages and proxy HTTP services
nginx

# enable SSH over ethernet
inetd -e /etc/inetd.conf

# If user boot script exists, run it
mkdir -p /data/boot.d
run-parts /data/boot.d

export ENABLE_NETWORKING_ENDPOINTS=true
echo "Starting 5001 Test-Fixture Script..."
python -m opentrons.tools.pcb_fixture_5001
echo "Script exited unexpectedly. Please power-cycle the test-fixture."
while true; do sleep 1; done
