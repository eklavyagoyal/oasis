import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
const browser = await chromium.launch({
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const messages = [];
page.on("pageerror", (e) => messages.push({ type: "error", message: e.stack }));
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning" || m.type() === "info")
    messages.push({ type: m.type(), message: m.text() });
});
await page.goto(process.env.MW_URL ?? "http://127.0.0.1:5173/", {
  waitUntil: "load",
});
await page.waitForTimeout(6000);
await mkdir("docs/ui-review", { recursive: true });
const pass = process.env.MW_PASS ?? "pass-1";
await page.screenshot({ path: `docs/ui-review/${pass}-1440.png` });
await page.setViewportSize({ width: 1920, height: 1080 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `docs/ui-review/${pass}-1920.png` });
console.log(
  JSON.stringify(
    { messages, body: (await page.locator("body").innerText()).slice(0, 2500) },
    null,
    2,
  ),
);
await writeFile(
  `docs/ui-review/${pass}-console.json`,
  JSON.stringify(messages, null, 2),
);
await browser.close();
