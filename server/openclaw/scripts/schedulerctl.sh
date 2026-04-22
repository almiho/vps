#!/bin/sh
set -eu

WORKSPACE="/home/node/.openclaw/workspace"
PIDFILE="$WORKSPACE/logs/scheduler.pid"
LOGFILE="$WORKSPACE/logs/scheduler-service.log"
SCHEDULER="$WORKSPACE/scripts/scheduler.py"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

mkdir -p "$WORKSPACE/logs"

proc_ok() {
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start_service() {
  if proc_ok; then
    echo "workspace-scheduler already running (pid $(cat "$PIDFILE"))"
    return 0
  fi

  /usr/sbin/start-stop-daemon \
    --start \
    --background \
    --make-pidfile \
    --pidfile "$PIDFILE" \
    --chdir "$WORKSPACE" \
    --startas /bin/sh \
    -- -lc "exec '$PYTHON_BIN' '$SCHEDULER' >>'$LOGFILE' 2>&1"

  sleep 2
  if proc_ok; then
    echo "workspace-scheduler started"
    return 0
  fi

  echo "workspace-scheduler failed to start, see $LOGFILE" >&2
  return 1
}

stop_service() {
  if [ -f "$PIDFILE" ]; then
    /usr/sbin/start-stop-daemon --stop --retry=TERM/10/KILL/5 --pidfile "$PIDFILE" || true
    rm -f "$PIDFILE"
  else
    pkill -f "$SCHEDULER" >/dev/null 2>&1 || true
  fi
  echo "workspace-scheduler stopped"
}

status_service() {
  if proc_ok; then
    echo "workspace-scheduler is up (pid $(cat "$PIDFILE"))"
    return 0
  fi
  echo "workspace-scheduler is down"
  return 1
}

foreground_service() {
  cd "$WORKSPACE"
  exec "$PYTHON_BIN" "$SCHEDULER"
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
