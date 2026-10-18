import { cp, mkdir, access, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const publicDir = resolve("dashboard/public");
await mkdir(publicDir, { recursive: true });
try {
  await access(resolve(publicDir, "cesium/Cesium.js"));
} catch {
  await cp(
    resolve("node_modules/cesium/Build/Cesium"),
    resolve(publicDir, "cesium"),
    { recursive: true },
  );
}
try {
  await access(resolve(publicDir, "data.js"));
} catch {
  await writeFile(resolve(publicDir, "data.js"), "window.MW = null;\n");
  console.warn(
    "No scenario exported. Run npm run data:export or place data.js in dashboard/public/.",
  );
}
