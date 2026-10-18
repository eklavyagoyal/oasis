import { chromium, expect } from "@playwright/test";
import { mkdir, rename, writeFile } from "node:fs/promises";
const out = "docs/screenshots";
await mkdir(out, { recursive: true });
await mkdir("dashboard/test-results", { recursive: true });
const browser = await chromium.launch({
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const errors = [];
const observe = (page) => {
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
};
const url = process.env.MW_URL ?? "http://127.0.0.1:4173/";
async function command(page, value) {
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill(value);
  await page.locator("#command-input").press("Enter");
}
try {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  observe(page);
  await page.goto(url, { waitUntil: "load" });
  await expect(page.locator("#opening")).toBeHidden({ timeout: 15000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${out}/delta-dusk.png` });
  await command(page, "jump 14:14:40");
  await command(page, "dead zones RF2 40 m");
  await page.waitForTimeout(1500);
  const callout = await page.locator(".reticle-callout").boundingBox();
  const deck = await page.locator(".right-rail").boundingBox();
  if (!callout || callout.x + callout.width > deck.x)
    throw new Error("Selected-track callout overlaps the observation deck");
  await page.screenshot({ path: `${out}/dead-zones.png` });
  await page.locator("#layers-toggle").click();
  await page.locator("#layer-shadow").uncheck();
  await page.locator("#layers-close").click();
  await page.locator('[data-tab="audit"]').click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${out}/audit.png` });
  await page.locator('[data-feed="camera"]').click();
  await command(page, "jump 14:02:07");
  await command(page, "opening");
  await expect(page.locator(".opening-title")).toHaveCSS("opacity", "1", {
    timeout: 8000,
  });
  await page.screenshot({ path: `${out}/opening.png` });
  await expect(page.locator("#opening")).toBeHidden({ timeout: 8000 });
  for (const [width, height] of [
    [1280, 720],
    [1440, 900],
  ]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `docs/ui-review/final-${width}.png` });
  }
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
  observe(videoPage);
  await videoPage.goto(url, { waitUntil: "load" });
  await expect(videoPage.locator("#opening")).toBeHidden({ timeout: 15000 });
  await videoPage.locator("#present-start").click();
  for (let beat = 0; beat < 5; beat++) {
    await videoPage.waitForTimeout(4000);
    if (beat === 0) await videoPage.screenshot({ path: `${out}/present.png` });
    if (beat < 4) await videoPage.locator("#present-next").click();
  }
  await videoContext.close();
  await rename(
    await videoPage.video().path(),
    "dashboard/test-results/present-full.webm",
  );
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
    "Saved DELTA, dead zones, audit, opening, PRESENT and responsive captures; no browser errors.",
  );
} finally {
  await browser.close();
}
