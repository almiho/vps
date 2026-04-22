#!/bin/sh
set -eu

WORKSPACE="/home/node/.openclaw/workspace"
PIDFILE="$WORKSPACE/logs/dashboard-web.pid"
LOGFILE="$WORKSPACE/logs/dashboard-web.log"
SERVER="$WORKSPACE/dashboard/server.py"
PORT="${DASHBOARD_PORT:-8080}"
BIND_ADDRS="${DASHBOARD_BIND_ADDRS:-127.0.0.1,100.67.100.125}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

mkdir -p "$WORKSPACE/logs"

http_ok() {
  DASHBOARD_PORT="$PORT" "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import os, urllib.request
port = int(os.environ.get("DASHBOARD_PORT", "8080"))
for url in [f"http://127.0.0.1:{port}/__healthz", f"http://127.0.0.1:{port}/"]:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            raise SystemExit(0 if r.status == 200 else 1)
    except Exception:
        pass
raise SystemExit(1)
PY
}

start_service() {
  if http_ok; then
    echo "dashboard-web already responding on 127.0.0.1:$PORT"
    return 0
  fi

  export DASHBOARD_PORT="$PORT"
  export DASHBOARD_BIND_ADDRS="$BIND_ADDRS"

  /usr/sbin/start-stop-daemon \
    --start \
    --background \
    --make-pidfile \
    --pidfile "$PIDFILE" \
    --chdir "$WORKSPACE/dashboard" \
    --startas /bin/sh \
    -- -lc "exec env DASHBOARD_PORT='$PORT' DASHBOARD_BIND_ADDRS='$BIND_ADDRS' '$PYTHON_BIN' '$SERVER' >>'$LOGFILE' 2>&1"

  sleep 2
  if http_ok; then
    echo "dashboard-web started"
    return 0
  fi

  echo "dashboard-web failed to start, see $LOGFILE" >&2
  return 1
}

stop_service() {
  if [ -f "$PIDFILE" ]; then
    /usr/sbin/start-stop-daemon --stop --retry=TERM/10/KILL/5 --pidfile "$PIDFILE" || true
    rm -f "$PIDFILE"
  else
    pkill -f "$SERVER" >/dev/null 2>&1 || true
  fi

  if http_ok; then
    echo "dashboard-web still responding after stop attempt" >&2
    return 1
  fi

  echo "dashboard-web stopped"
}

status_service() {
  if http_ok; then
    if [ -f "$PIDFILE" ]; then
      echo "dashboard-web is up (pidfile $(cat "$PIDFILE" 2>/dev/null || true))"
    else
      echo "dashboard-web is up"
    fi
    return 0
  fi

  if [ -f "$PIDFILE" ]; then
    echo "dashboard-web pidfile exists but HTTP check failed"
  else
    echo "dashboard-web is down"
  fi
  return 1
}

foreground_service() {
  export DASHBOARD_PORT="$PORT"
  export DASHBOARD_BIND_ADDRS="$BIND_ADDRS"
  cd "$WORKSPACE/dashboard"
  exec "$PYTHON_BIN" "$SERVER"
}

case "${1:-}" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  restart)
    stop_service || true
    start_service
    ;;
  status)
    status_service
    ;;
  foreground)
    foreground_service
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|foreground}" >&2
    exit 2
    ;;
esac
