---
name: "openclaw-plugin-native-rebuild"
description: "Install/update an OpenClaw plugin with native deps (better-sqlite3) — rebuild native binaries after install; fixes \"Cannot find module better-sqlite3\"."
---

# Rebuild native deps after installing an OpenClaw plugin

OpenClaw's plugin installer runs `npm install --ignore-scripts`, so native-module
dependencies (better-sqlite3, sqlite-vec, and similar) land without their compiled
binary. The plugin still installs and registers, but the gateway fails to load it
with `Cannot find module 'better-sqlite3'` or `Could not locate the bindings file`.

## Steps

1. Find the plugin directory: ClawHub installs go to `~/.openclaw/extensions/<id>/`;
   npm installs go to `~/.openclaw/npm/projects/<id>/`. Confirm with the Source column
   of `openclaw plugins list`.
2. Read the plugin's `package.json` and note its native dependencies
   (e.g. `better-sqlite3`, `sqlite-vec`).
3. From inside that directory, rebuild them:
   `npm rebuild better-sqlite3 sqlite-vec`
   — replace the list with the actual native deps found in step 2.
4. Verify the binary is present and loadable:
   `node -e "require('better-sqlite3')(':memory:')"` prints a row with no error, and
   `node_modules/better-sqlite3/build/Release/better_sqlite3.node` exists.
5. Re-run the rebuild after every `openclaw plugins update <id>`, because updates
   reinstall dependencies with `--ignore-scripts`.
