#!/usr/bin/env bash
set -euo pipefail

old_compose=/home/azureuser/forestguard-releases/current/compose.yaml
new_compose=/home/azureuser/forestguard-releases/fg1-prepared-20261014-1520/compose.yaml
expected_secret_sha=7ca792200a290a64359b3bdcfc5961f0110b126f87a4cdcdb879984491533160

old_image=$(docker inspect forestguard-backend-1 --format '{{.Image}}')
mongo_id=$(docker inspect forestguard-mongo-1 --format '{{.Id}}')
switched=0

rollback() {
  echo 'Candidate verification failed; restoring previous Backend and Tunnel containers' >&2
  docker compose -f "$old_compose" up -d --no-deps --force-recreate backend || true
  docker compose -f "$old_compose" up -d --no-deps --force-recreate cloudflared || true
}
on_exit() {
  status=$?
  if [ "$status" -ne 0 ] && [ "$switched" -eq 1 ]; then rollback; fi
}
trap on_exit EXIT

docker compose -f "$new_compose" config --quiet
switched=1
docker compose -f "$new_compose" up -d --no-deps --force-recreate backend

healthy=0
for attempt in $(seq 1 15); do
  backend_ip=$(docker inspect forestguard-backend-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || true)
  if [ -n "$backend_ip" ] &&
     curl --max-time 4 -fsS "http://$backend_ip:4000/api/health" 2>/dev/null |
       python3 -c 'import json,sys; x=json.load(sys.stdin); sys.exit(0 if x.get("ok") is True and x.get("node_registration_configured") is True and x.get("radio_protocol") == "FG1" else 1)' 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 2
done
if [ "$healthy" -ne 1 ]; then
  echo 'Backend failed readiness check' >&2
  exit 1
fi

mounted_sha=$(docker exec forestguard-backend-1 sha256sum /run/secrets/node_credentials | cut -d ' ' -f 1)
if [ "$mounted_sha" != "$expected_secret_sha" ]; then
  echo 'Mounted node credential checksum does not match' >&2
  exit 1
fi

docker compose -f "$new_compose" up -d --no-deps --force-recreate cloudflared
public_ok=0
for attempt in $(seq 1 15); do
  if curl --max-time 5 -fsS https://wildfire.nattaphat.me/api/health 2>/dev/null |
       python3 -c 'import json,sys; x=json.load(sys.stdin); sys.exit(0 if x.get("ok") is True and x.get("node_registration_configured") is True and x.get("radio_protocol") == "FG1" else 1)' 2>/dev/null; then
    public_ok=1
    break
  fi
  sleep 2
done
if [ "$public_ok" -ne 1 ]; then
  echo 'Public health check failed' >&2
  exit 1
fi

new_image=$(docker inspect forestguard-backend-1 --format '{{.Image}}')
new_mongo_id=$(docker inspect forestguard-mongo-1 --format '{{.Id}}')
if [ "$new_image" = "$old_image" ] || [ "$new_mongo_id" != "$mongo_id" ]; then
  echo 'Backend image did not change or MongoDB container changed' >&2
  exit 1
fi

trap - EXIT
echo 'New Backend and Cloudflare Tunnel are healthy; MongoDB container unchanged; private credentials mounted and verified'
