# Grafana Loki Error Dashboard

**Date:** 2026-08-06
**Purpose:** Create a Grafana dashboard with one table tile each for LiteLLM, llama.cpp, and OpenClaw. Each tile shows one row per normalized error message and the total number of occurrences.

## Verified Environment

- Grafana: `12.3.1`
- Loki datasource name: `Loki`
- Loki datasource UID: `P8E80F9AEF21F6940`
- Grafana URL: `http://192.168.1.206:30300`
- Loki URL from Grafana: `http://loki:3100`
- Dashboard time window used: `now-6h` to `now`

Do not hardcode Grafana credentials in dashboard instructions. Use the existing authenticated browser session or the configured Grafana authentication mechanism.

## Root Cause Of Duplicate Rows

A Loki range query returns multiple samples for the same label set, one sample per time step. Applying `labelsToFields` and displaying those samples directly creates rows such as:

```text
Context size has been exceeded. | 2
Context size has been exceeded. | 2
Context size has been exceeded. | 4
Context size has been exceeded. | 6
```

The reliable solution has three parts:

1. Use `sum by (msg) (count_over_time(...))` so Loki aggregates all matching streams by the normalized message.
2. Set the Grafana target to an instant query with both `queryType: "instant"` and `instant: true`. This returns one sample per `msg` series instead of a time series of repeated samples.
3. Use `labelsToFields` followed only by `organize`. Do not add a second `groupBy` transformation; the aggregation already happened in LogQL.

For llama.cpp and OpenClaw, request/task IDs must be excluded from the captured `msg` field. Otherwise every request has a different message and cannot be grouped.

## Common Datasource And Panel Settings

Use the Loki datasource object at both panel and target level:

```json
{
  "type": "loki",
  "uid": "P8E80F9AEF21F6940"
}
```

Every table target must include:

```json
{
  "refId": "A",
  "queryType": "instant",
  "instant": true,
  "direction": "backward"
}
```

The table transformation list must be exactly:

```json
[
  {
    "id": "labelsToFields",
    "options": {}
  },
  {
    "id": "organize",
    "options": {
      "excludeByName": {
        "Time": true
      },
      "indexByName": {
        "msg": 0,
        "Value": 1
      },
      "renameByName": {
        "msg": "Error Message",
        "Value": "Occurrences"
      }
    }
  }
]
```

Do not use `maxLines` with the aggregated instant queries. `maxLines` is for raw log queries and is not needed here.

## Tile 1: LiteLLM Errors

**Container label:** `LiteLLM`

**LogQL expression:**

```logql
sum by (msg) (
  count_over_time(
    {container="LiteLLM"}
    |= "ERROR"
    | pattern "<_> - <_> <_>: <_> - <msg>"
    [6h]
  )
)
```

**Target JSON:**

```json
{
  "datasource": {
    "type": "loki",
    "uid": "P8E80F9AEF21F6940"
  },
  "expr": "sum by (msg) (count_over_time({container=\"LiteLLM\"} |= \"ERROR\" | pattern \"<_> - <_> <_>: <_> - <msg>\" [6h]))",
  "refId": "A",
  "queryType": "instant",
  "instant": true,
  "direction": "backward"
}
```

Expected log shape:

```text
2026-08-05T... - ERROR file.py:123 - function(): message
```

## Tile 2: llama.cpp Errors

**Container label:** `llama-cpp-server`

**LogQL expression:**

```logql
sum by (msg) (
  count_over_time(
    {container="llama-cpp-server"}
    |= "error"
    | pattern "<_> E <_> send_error: task id = <_>, error: <msg>"
    [6h]
  )
)
```

**Target JSON:**

```json
{
  "datasource": {
    "type": "loki",
    "uid": "P8E80F9AEF21F6940"
  },
  "expr": "sum by (msg) (count_over_time({container=\"llama-cpp-server\"} |= \"error\" | pattern \"<_> E <_> send_error: task id = <_>, error: <msg>\" [6h]))",
  "refId": "A",
  "queryType": "instant",
  "instant": true,
  "direction": "backward"
}
```

Expected log shape:

```text
2314.50.567.711 E srv    send_error: task id = 316563, error: Failed to initialize samplers: failed to parse grammar
```

The task ID is deliberately represented by `<_>` so it does not become part of `msg`. The important grouped message becomes:

```text
Failed to initialize samplers: failed to parse grammar
```

Some unrelated llama.cpp error lines may not match this pattern. If a catch-all row is undesirable, add a more specific line filter or a separate raw-log tile rather than weakening the normalized tile.

## Tile 3: OpenClaw Errors

**Container label:** `OpenClaw`

**LogQL expression:**

```logql
sum by (msg) (
  count_over_time(
    {container="OpenClaw"}
    |= "errorCode"
    | pattern "<_> errorCode=<_> errorMessage=<msg> conn=<_> id=<_>"
    [6h]
  )
)
```

**Target JSON:**

```json
{
  "datasource": {
    "type": "loki",
    "uid": "P8E80F9AEF21F6940"
  },
  "expr": "sum by (msg) (count_over_time({container=\"OpenClaw\"} |= \"errorCode\" | pattern \"<_> errorCode=<_> errorMessage=<msg> conn=<_> id=<_>\" [6h]))",
  "refId": "A",
  "queryType": "instant",
  "instant": true,
  "direction": "backward"
}
```

Expected log shape:

```text
2026-08-05T... [ws] ... errorCode=INVALID_REQUEST errorMessage=Error: Channel is required ... conn=abc... id=def...
```

The connection and request IDs are represented by `<_>` and excluded from `msg`. This groups messages such as:

```text
Error: Channel is required when multiple channels are configured: telegram, whatsapp. Pass --channel <channel> to choose one.
unknown method: question.list
unknown method: sessions.branches.list
unknown method: sessions.observer.visibility
```

## Dashboard Panel Layout

Use three table panels in one row:

```json
[
  {
    "id": 1,
    "title": "LiteLLM Errors",
    "type": "table",
    "gridPos": { "h": 12, "w": 8, "x": 0, "y": 0 }
  },
  {
    "id": 2,
    "title": "Llama.cpp Errors",
    "type": "table",
    "gridPos": { "h": 12, "w": 8, "x": 8, "y": 0 }
  },
  {
    "id": 3,
    "title": "OpenClaw Errors",
    "type": "table",
    "gridPos": { "h": 12, "w": 8, "x": 16, "y": 0 }
  }
]
```

Each panel needs:

- Its own container-specific target expression from the sections above.
- The Loki datasource object on the panel and target.
- `labelsToFields` followed by `organize`.
- `Time` hidden.
- `msg` renamed to `Error Message`.
- `Value` renamed to `Occurrences`.
- An integer panel ID. Never use `id: null` for saved panels.

## Save Through Grafana API

When using the authenticated browser session, fetch the current dashboard first, preserve its unrelated settings, replace only the intended panels, increment `dashboard.version`, and save with:

```javascript
const response = await fetch('/api/dashboards/db', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    dashboard,
    message: 'Create per-container Loki error tiles',
    overwrite: true
  })
});
```

A new dashboard can use this base shape:

```json
{
  "dashboard": {
    "title": "Error Monitoring",
    "uid": "err-mon",
    "schemaVersion": 39,
    "timezone": "browser",
    "refresh": "30s",
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "panels": []
  },
  "overwrite": false
}
```

## Browser Validation Checklist

Never validate this dashboard only through direct Loki HTTP requests. Validate through the Grafana browser UI and Grafana's datasource proxy:

1. Open the dashboard URL.
2. Wait for the refresh button to return from `Cancel` to `Refresh`.
3. Confirm all three tile titles are visible.
4. Confirm the LiteLLM tile contains one row for each distinct message.
5. Confirm `Context size has been exceeded.` appears once, not once per time bucket.
6. Confirm each row has a numeric `Occurrences` value.
7. Confirm the llama.cpp grammar errors are grouped despite different task IDs.
8. Confirm the OpenClaw channel error is grouped despite different `conn=` and `id=` values.
9. Use Grafana's browser-side `/api/ds/query` with `queryType: "instant"` as a secondary check. For each panel, assert that the maximum number of rows for any identical message is `1`.
10. Treat a blank canvas, a stuck `Loading` state, or a `No data` tile as a failed validation even if the Loki API works directly.

Example browser-side assertion:

```javascript
const target = {
  refId: 'A',
  datasource: { type: 'loki', uid: 'P8E80F9AEF21F6940' },
  expr,
  queryType: 'instant',
  instant: true,
  direction: 'backward'
};

const response = await fetch('/api/ds/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    queries: [target],
    from: 'now-6h',
    to: 'now'
  })
});

const data = await response.json();
const frames = data.results.A.frames;
// Extract each Value field's msg label and one value from each frame.
// Assert no msg occurs in more than one frame.
```

## Lessons From Failed Attempts

- A range query plus `labelsToFields` produces repeated rows for each time step.
- A second Grafana `groupBy` is not a substitute for Loki aggregation and can preserve duplicate samples.
- `sum by (msg)` is required to combine messages across Loki streams.
- `queryType: "instant"` and `instant: true` are both needed in the saved target configuration.
- `maxLines` is not the fix for aggregation and should be omitted from instant metric queries.
- Raw llama.cpp messages include unique task IDs; raw OpenClaw messages include unique connection/request IDs. Exclude those IDs in the `pattern` parser.
- The Grafana datasource UID must be an object with `type` and `uid`, not the display name string `"Loki"`.
- Saved panels require integer IDs. Null IDs caused dashboard rendering problems during earlier API edits.
- Grafana may request `/api/dashboards/uid/<uid>/public-dashboards` and receive a 404 when public dashboards are not configured. That request is unrelated to Loki data; inspect `/api/ds/query` and the actual panel contents instead.
