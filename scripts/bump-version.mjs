#!/usr/bin/env node

/**
 * Bump the project version across all packages.
 *
 * Usage:
 *   node scripts/bump-version.mjs <version>
 *   node scripts/bump-version.mjs patch|minor|major
 *
 * Single source of truth: root package.json
 * Syncs to: frontend/package.json, backend/pyproject.toml,
 *           desktop-tauri (via sync-desktop-meta.mjs), lock files.
 */

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const rootDir = process.cwd();

// --- Resolve target version ---------------------------------------------------

const arg = process.argv[2];
if (!arg) {
  console.error("Usage: node scripts/bump-version.mjs <version|patch|minor|major>");
  process.exit(1);
}

const rootPkgPath = path.join(rootDir, "package.json");
const rootPkg = JSON.parse(fs.readFileSync(rootPkgPath, "utf8"));
const current = rootPkg.version;

function bump(version, level) {
  const parts = version.split(".").map(Number);
  if (level === "major") return `${parts[0] + 1}.0.0`;
  if (level === "minor") return `${parts[0]}.${parts[1] + 1}.0`;
  if (level === "patch") return `${parts[0]}.${parts[1]}.${parts[2] + 1}`;
  throw new Error(`Unknown bump level: ${level}`);
}

const version = ["patch", "minor", "major"].includes(arg) ? bump(current, arg) : arg;

if (!/^\d+\.\d+\.\d+$/.test(version)) {
  console.error(`Invalid version: "${version}". Expected format: X.Y.Z`);
  process.exit(1);
}

console.log(`Bumping version: ${current} → ${version}\n`);

// --- 1. Root package.json ----------------------------------------------------

rootPkg.version = version;
fs.writeFileSync(rootPkgPath, `${JSON.stringify(rootPkg, null, 2)}\n`);
console.log(`  ✓ package.json`);

// --- 2. Frontend package.json ------------------------------------------------

const frontendPkgPath = path.join(rootDir, "frontend", "package.json");
const frontendPkg = JSON.parse(fs.readFileSync(frontendPkgPath, "utf8"));
frontendPkg.version = version;
fs.writeFileSync(frontendPkgPath, `${JSON.stringify(frontendPkg, null, 2)}\n`);
console.log(`  ✓ frontend/package.json`);

// --- 3. Backend pyproject.toml -----------------------------------------------

const pyprojectPath = path.join(rootDir, "backend", "pyproject.toml");
let pyproject = fs.readFileSync(pyprojectPath, "utf8");
pyproject = pyproject.replace(/^version = ".*"$/m, `version = "${version}"`);
fs.writeFileSync(pyprojectPath, pyproject);
console.log(`  ✓ backend/pyproject.toml`);

// --- 4. Desktop (Tauri conf + Cargo.toml) via existing sync script -----------

execSync("node scripts/sync-desktop-meta.mjs", { cwd: rootDir, stdio: "pipe" });
console.log(`  ✓ desktop-tauri (tauri.conf.json + Cargo.toml)`);

// --- 5. Lock files -----------------------------------------------------------

execSync("npm install --package-lock-only", { cwd: rootDir, stdio: "pipe" });
console.log(`  ✓ package-lock.json`);

execSync("npm install --package-lock-only --legacy-peer-deps", {
  cwd: path.join(rootDir, "frontend"),
  stdio: "pipe",
});
console.log(`  ✓ frontend/package-lock.json`);

console.log(`\nDone! All files updated to ${version}.`);
console.log(`Next steps:`);
console.log(`  git add -A && git commit -m "chore: bump version to ${version}"`);
console.log(`  git tag v${version}`);
