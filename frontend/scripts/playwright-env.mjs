#!/usr/bin/env node
import { spawn } from "node:child_process";

const env = { ...process.env };
delete env.NO_COLOR;

const args = process.argv.slice(2);
if (args[0] === "--headless") {
  env.OPENYAK_UI_HEADLESS = "true";
  args.shift();
}

const bin = process.platform === "win32" ? "playwright.cmd" : "playwright";
const child = spawn(bin, args, {
  env,
  shell: process.platform === "win32",
  stdio: "inherit",
});

child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
