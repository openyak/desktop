# Fix Records Index

> Agent: 遇到 bug 时先搜索这里。`grep -ri "keyword" docs/fixes/`

## By Category

### api
(empty)

### session
(empty)

### tool
(empty)

### provider
(empty)

### mcp
(empty)

### plugin
(empty)

### frontend
- [dev:all browser UI shows no models and API requests return 401](frontend/dev-all-web-ui-api-401.md)

### desktop
(empty)

### infra
(empty)

### general
(empty)

---

## Symptom Lookup Table

> 遇到问题先查这张表。每修一个 bug，花 10 秒加一行。

| Symptom | Check First | Quick Fix | Record |
|---------|------------|-----------|--------|
| Tool part stuck in "running" | `update_part_data()` missing in error path | Add error status persistence | (add record) |
| Click handler fires twice | `useState` guard vs `useRef` guard | Switch to `useRef` for sync guard | (add record) |
| Startup crash — one bad plugin | Missing try-catch in init loop | Wrap per-item in try-catch | (add record) |
| dev:all browser UI shows no models / API 401 | Web dev proxy missing session token | Run through `scripts/dev-all.mjs` dev token bridge | [record](frontend/dev-all-web-ui-api-401.md) |
