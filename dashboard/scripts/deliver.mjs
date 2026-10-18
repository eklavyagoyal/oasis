import { chromium } from "@playwright/test";
import { mkdir, rename, writeFile } from "node:fs/promises";
const out = "docs/screenshots";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
});
const page = await context.newPage(),
  errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
const url = process.env.MW_URL ?? "http://127.0.0.1:5173/";
await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(4500);
await page.screenshot({ path: `${out}/delta-dusk.png` });
await page.locator("#command-open").click();
await page.locator("#command-input").fill("jump 14:14:40");
await page.locator("#command-input").press("Enter");
await page.locator("#layer-shadow").check();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${out}/dead-zones.png` });
await page.locator('[data-tab="audit"]').click();
await page.waitForTimeout(200);
await page.screenshot({ path: `${out}/audit.png` });
await page.locator('[data-tab="feeds"]').click();
await page.locator("#layer-shadow").uncheck();
await page.setViewportSize({ width: 1280, height: 720 });
await page.waitForTimeout(400);
await page.screenshot({ path: "docs/ui-review/final-1280.png" });
await page.setViewportSize({ width: 1440, height: 900 });
await page.waitForTimeout(400);
await page.screenshot({ path: "docs/ui-review/final-1440.png" });
await context.close();
const videoContext = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  recordVideo: {
    dir: "dashboard/test-results/video",
    size: { width: 1440, height: 900 },
  },
});
const videoPage = await videoContext.newPage();
videoPage.on("pageerror", (e) => errors.push(e.message));
await videoPage.goto(url, { waitUntil: "load" });
await videoPage.waitForTimeout(3000);
await videoPage.locator("#present-start").click();
for (let beat = 0; beat < 5; beat++) {
  await videoPage.waitForTimeout(4000);
  if (beat < 4) await videoPage.locator("#present-next").click();
}
await videoContext.close();
await rename(await videoPage.video().path(), `${out}/present-full.webm`);
await browser.close();
await writeFile(
  "dashboard/test-results/delivery.json",
  JSON.stringify(
    {
      errors,
      views: ["1920×1080", "1440×900", "1280×720"],
      video: "five PRESENT beats",
    },
    null,
    2,
  ),
);
if (errors.length) throw new Error(JSON.stringify(errors));
console.log(
  "Saved three delivery screenshots, responsive captures and PRESENT recording; no browser errors.",
);
