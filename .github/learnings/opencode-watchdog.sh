#!/usr/bin/env bash
# opencode-watchdog.sh
# Detects stalled OpenCode sessions (hang or CPU-spin), kills them, and
# re-triggers the session to continue via tmux.
# Deploy to each host that runs an OpenCode container.
#
# Usage:
#   opencode-watchdog.sh --log <path-to-opencode.log> \
#       --tmux <session:pane> [--dry-run] [--container OpenCode]
#
#   --tmux  The tmux target (e.g. "Reflexia:0.0") whose pane runs the opencode
#           session. After killing a stuck process, the watchdog sends
#           "opencode --continue" to this pane so the session resumes work.
#
# Detection logic (from W:\.github\learnings\stalled-sessions.md):
#
#   IMPORTANT: We only kill on the SPECIFIC, PROVEN stall signatures. Generic
#   "log idle" is NOT sufficient — a session can be legitimately idle (waiting
#   for a model response, waiting for user input, between turns) or busy (running
#   tests at high CPU). Killing those would be a false positive.
#
#   Proven signatures (from the 2026-09-11 incidents):
#
#   SIG-1 (bash-tool descriptor hang, Amminox): the LAST log line is an
#     "evaluated permission=bash" for a command that backgrounds/detaches a
#     long-running process (contains "setsid", " &", "nohup", "disown"), AND
#     the process is idle (low CPU), AND the log has been idle for HANG_MINUTES.
#     This is the exact pattern that left a server holding the tool's descriptor.
#
#   SIG-2 (Worker-thread spin, Reflexia): the MAIN process is idle (low CPU)
#     but a WORKER thread is spinning at >= WORKER_SPIN_THRESHOLD% (default 90),
#     AND the log has been idle for HANG_MINUTES. This is the infinite-loop
#     signature (Worker thread at 99.9% while main process idle).
#
#   Anything else (busy session, idle-but-healthy session) is NOT killed.
#
# On detection, it kills the stuck opencode process (SIGTERM, then SIGKILL),
# waits for the shell prompt to return, then sends "opencode --continue" to the
# tmux pane so the session resumes.
#
# Example (Reflexia 149):
#   opencode-watchdog.sh --log /home/ethan/appdata/opencode/opencode-data/log/opencode.log \
#       --tmux Reflexia:0.0
# Example (Amminox 194):
#   opencode-watchdog.sh --log /mnt/user/appdata/opencode/opencode-data/log/opencode.log \
#       --tmux Amminox:0.0

set -euo pipefail

CONTAINER="${CONTAINER:-OpenCode}"
DRY_RUN="${DRY_RUN:-0}"
HANG_MINUTES="${HANG_MINUTES:-10}"
CPU_IDLE_THRESHOLD="${CPU_IDLE_THRESHOLD:-20}"      # below this = idle
WORKER_SPIN_THRESHOLD="${WORKER_SPIN_THRESHOLD:-90}" # worker thread above this = spin
LOG_DIR="${LOG_DIR:-/tmp/opencode-watchdog}"
LOGFILE=""
TMUX_TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log) LOGFILE="$2"; shift 2 ;;
    --tmux) TMUX_TARGET="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --container) CONTAINER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$LOG_DIR"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_DIR/watchdog.log"; }

# List all opencode session PIDs (opencode and opencode --continue).
find_session_pids() {
  docker exec "$CONTAINER" sh -c 'ps -eo pid,cmd | grep -E "opencode( --continue)?$" | grep -v grep' 2>/dev/null \
    | awk '{print $1}'
}

# Seconds since the last log line was written (0 if unknown).
log_idle_seconds() {
  local logfile="$1" last_line ts epoch now
  last_line=$(tail -1 "$logfile" 2>/dev/null || echo "")
  [ -z "$last_line" ] && { echo 0; return; }
  ts=$(echo "$last_line" | sed -n 's/.*timestamp=\([0-9T:.Z-]*\).*/\1/p')
  [ -z "$ts" ] && { echo 0; return; }
  epoch=$(date -u -d "$ts" +%s 2>/dev/null || echo 0)
  now=$(date -u +%s)
  echo $(( now - epoch ))
}

# The last log line (for signature detection).
last_log_line() {
  tail -1 "$1" 2>/dev/null || echo ""
}

# Get integer CPU% of a process.
proc_cpu() {
  local pid="$1" cpu
  cpu=$(docker exec "$CONTAINER" sh -c "ps -o pcpu= -p $pid 2>/dev/null | tr -d ' '" 2>/dev/null || echo 0)
  cpu=${cpu:-0}
  echo "${cpu%.*}"
}

# Get the highest CPU% among the process's threads (for spin detection).
proc_max_thread_cpu() {
  local pid="$1" maxcpu
  maxcpu=$(docker exec "$CONTAINER" sh -c "top -b -n 1 -H -p $pid 2>/dev/null" 2>/dev/null \
    | awk 'NR>7 {gsub(/%/,"",$9); if ($9+0 > m) m=$9+0} END {print int(m)}')
  echo "${maxcpu:-0}"
}

# SIG-1: last log line is a bash permission eval that backgrounds/detaches a process.
is_bash_tool_hang_signature() {
  local line="$1"
  echo "$line" | grep -q "evaluated permission=bash" \
    && echo "$line" | grep -qE 'setsid|nohup|disown| &|&>|>/dev/null 2>&1 &'
}

# Kill a stuck process (SIGTERM then SIGKILL).
kill_session() {
  local pid="$1"
  if [ "$DRY_RUN" = "1" ]; then
    log "DRY-RUN: would kill opencode pid $pid"
    return
  fi
  log "Killing opencode pid $pid (SIGTERM)"
  docker exec "$CONTAINER" sh -c "kill $pid 2>/dev/null" || true
  sleep 5
  if docker exec "$CONTAINER" sh -c "kill -0 $pid 2>/dev/null"; then
    log "pid $pid still alive, sending SIGKILL"
    docker exec "$CONTAINER" sh -c "kill -9 $pid 2>/dev/null" || true
  fi
}

# Re-trigger the session to continue by sending "opencode --continue" to the
# tmux pane. Waits for the shell prompt to return first.
resume_session() {
  if [ -z "$TMUX_TARGET" ]; then
    log "WARN: no --tmux target given; session killed but NOT resumed. Resume manually with 'opencode --continue'."
    return
  fi
  if [ "$DRY_RUN" = "1" ]; then
    log "DRY-RUN: would send 'opencode --continue' to tmux $TMUX_TARGET"
    return
  fi
  log "Waiting for shell prompt in tmux $TMUX_TARGET..."
  local waited=0
  while [ "$waited" -lt 30 ]; do
    if tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | grep -qE '\$ $|➜ .*\$'; then
      break
    fi
    sleep 2
    waited=$(( waited + 2 ))
  done
  log "Sending 'opencode --continue' to tmux $TMUX_TARGET"
  tmux send-keys -t "$TMUX_TARGET" 'opencode --continue' Enter
}

main() {
  if [ -z "$LOGFILE" ] || [ ! -f "$LOGFILE" ]; then
    log "WARN: log file not found: ${LOGFILE:-<none>}. Pass --log <path>"
    return 0
  fi

  local pids idle cpu pid killed=0 lastline maxthread
  pids=$(find_session_pids)
  if [ -z "$pids" ]; then
    log "INFO: no active opencode session"
    return 0
  fi

  idle=$(log_idle_seconds "$LOGFILE")
  lastline=$(last_log_line "$LOGFILE")

  for pid in $pids; do
    cpu=$(proc_cpu "$pid")

    # Only consider a stall if the log has been idle long enough.
    if [ "$idle" -lt $(( HANG_MINUTES * 60 )) ]; then
      log "OK: pid $pid healthy (idle=${idle}s, cpu=${cpu}%)"
      continue
    fi

    # SIG-1: bash-tool descriptor hang (proven Amminox signature).
    if is_bash_tool_hang_signature "$lastline"; then
      log "SIG-1 (bash-tool hang): pid $pid idle ${idle}s, last line is a backgrounded bash eval. Killing"
      kill_session "$pid"
      killed=1
      continue
    fi

    # SIG-2: Worker-thread spin (proven Reflexia signature).
    maxthread=$(proc_max_thread_cpu "$pid")
    if [ "$cpu" -lt "$CPU_IDLE_THRESHOLD" ] && [ "$maxthread" -ge "$WORKER_SPIN_THRESHOLD" ]; then
      log "SIG-2 (worker spin): pid $pid main at ${cpu}% but worker thread at ${maxthread}% with idle log ${idle}s. Killing"
      kill_session "$pid"
      killed=1
      continue
    fi

    # No proven signature matched. Do NOT kill — could be idle-but-healthy or busy.
    log "OK: pid $pid no stall signature (idle=${idle}s, cpu=${cpu}%, maxthread=${maxthread}%) — not killing"
  done

  if [ "$killed" = "1" ]; then
    resume_session
  fi
}

main "$@"\n