import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();
const rootPkgPath = path.join(rootDir, "package.json");
const tauriConfPath = path.join(rootDir, "desktop-tauri", "src-tauri", "tauri.conf.json");
const cargoTomlPath = path.join(rootDir, "desktop-tauri", "src-tauri", "Cargo.toml");

const rootPkg = JSON.parse(fs.readFileSync(rootPkgPath, "utf8"));
const version = rootPkg.version;
const description = rootPkg.description;

const tauriConf = JSON.parse(fs.readFileSync(tauriConfPath, "utf8"));
tauriConf.version = version;
tauriConf.productName = "OpenYak";
tauriConf.app.windows = tauriConf.app.windows.map((window) => ({
  ...window,
  title: "OpenYak",
}));
fs.writeFileSync(tauriConfPath, `${JSON.stringify(tauriConf, null, 2)}\n`);

let cargoToml = fs.readFileSync(cargoTomlPath, "utf8");
cargoToml = cargoToml.replace(/^version = ".*"$/m, `version = "${version}"`);
cargoToml = cargoToml.replace(/^description = ".*"$/m, `description = "${description}"`);
fs.writeFileSync(cargoTomlPath, cargoToml);

console.log(`Synced desktop metadata to version ${version}`);
