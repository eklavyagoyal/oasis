import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve, extname } from "node:path";

// Serve the production build under a nested path to catch absolute-URL regressions.
const root = resolve("dist"),
  prefix = "/nested/console/";
const mime = {
  ".js": "text/javascript",
  ".css": "text/css",
  ".html": "text/html",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".wasm": "application/wasm",
  ".jpg": "image/jpeg",
};
const server = createServer(async (req, res) => {
  let file;
  try {
    const url = new URL(req.url, "http://localhost");
    if (!url.pathname.startsWith(prefix)) {
      res.writeHead(404).end();
      return;
    }
    file = resolve(
      root,
      decodeURIComponent(url.pathname.slice(prefix.length)) || "index.html",
    );
    if (!file.startsWith(root + "/")) {
      res.writeHead(403).end();
      return;
    }
    const body = await readFile(file);
    res.writeHead(200, {
      "Content-Type": mime[extname(file)] ?? "application/octet-stream",
    });
    res.end(body);
  } catch (error) {
    res
      .writeHead(error.code === "ENOENT" ? 404 : 500)
      .end("Static resource unavailable");
  }
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const url = `http://127.0.0.1:${server.address().port}${prefix}`;
const browser = await chromium.launch({
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
await context.addInitScript(() => {
  const NativeAudioContext = window.AudioContext;
  window.AudioContext = class extends NativeAudioContext {
    createBufferSource() {
      const source = super.createBufferSource();
      window.__testAudioSource = source;
      return source;
    }
  };
});
const page = await context.newPage(),
  errors = [],
  consoleErrors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => {
  if (m.type() === "error") consoleErrors.push(m.text());
});
const checks = [];
const check = (message) => {
  checks.push(message);
  console.log(`PASS ${message}`);
};
try {
  await page.goto(url, { waitUntil: "load" });
  await expect(page.locator("#opening")).toBeHidden({ timeout: 15000 });
  await expect(page.locator(".brand")).toHaveText("OASIS");
  await expect(page.locator("#exaggeration-value")).toHaveText("RELIEF ×2.5");
  await expect(page.locator("#system-state")).toContainText("WORLD LOADED");
  await expect(page.locator("#clock")).toContainText("14:02:07");
  await expect(page.locator("#feed-image")).toBeVisible();
  await page.waitForFunction(
    () => document.querySelector("#feed-image").naturalWidth > 0,
  );
  await expect(page.locator("#globe-error")).toBeHidden();
  check("production build, Cesium workers and media load under a nested URL");
  await page.locator('[data-mode="operator"]').click();
  await expect(page.locator("#selection-reticle")).toBeHidden();
  await expect(page.locator("#inspector")).not.toContainText("MAVIC_1");
  await expect(page.locator("#moments")).not.toContainText("mavic_1");
  await expect(page.locator("#density-scope")).toHaveText(
    "DENSITY / ALL SIGNALS",
  );
  await expect(page.locator("#layer-truth")).toBeDisabled();
  await page.evaluate(() => {
    window.__originalPick = Cesium.Scene.prototype.pick;
    Cesium.Scene.prototype.pick = () => ({
      id: { type: "fix", index: 0 },
      primitive: {},
    });
  });
  await page.locator("#globe canvas").click({ position: { x: 500, y: 300 } });
  await page.evaluate(() => {
    Cesium.Scene.prototype.pick = window.__originalPick;
  });
  await expect(page.locator("#inspector-panel")).toBeVisible();
  await expect(page.locator("#inspector")).toContainText("POSITION FIX / 1");
  await expect(page.locator("#inspector")).not.toContainText("MAVIC_1");
  await page.locator('[data-feed="camera"]').click();
  await page.locator('[data-mode="god"]').click();
  await expect(page.locator("#feed-state")).toContainText("NO SIGNAL");
  await expect(page.locator("#event-ticker")).toContainText(
    "hidden in God mode",
  );
  await expect(page.locator("#density-scope")).toHaveText(
    "TRUTH MODE / RF HIDDEN",
  );
  await page.locator('[data-mode="delta"]').click();
  check("Operator hides answer-key truth; God mode hides sensor observations");
  for (const [time, value] of [
    ["09:00:00", "—"],
    ["14:02:07", "120m"],
  ]) {
    await page.locator("#command-open").click();
    await page.locator("#command-input").fill(`jump ${time}`);
    await page.locator("#command-input").press("Enter");
    await expect(page.locator("#stat-agl")).toHaveText(value);
  }
  check(
    "fix picking opens the inspector; telemetry recovers after an inactive interval",
  );
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill("jump 14:14:40");
  await page.locator("#command-input").press("Enter");
  await expect(page.locator("#clock")).toContainText("14:14:40");
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill("dead zones RF2 40 m");
  await page.locator("#command-input").press("Enter");
  await expect(page.locator("#layer-shadow")).toBeChecked();
  await expect(page.locator("#shadow-value")).toHaveText("40 m AGL");
  await page.waitForTimeout(1200);
  await expect(page.locator("#receiver-status")).toContainText(
    "RF2 TERRAIN NLOS",
  );
  check("UTC command seeking, shadow command and receiver visibility");
  await page.locator("#play").focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#clock")).toContainText("14:14:50");
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator("#clock")).toContainText("14:14:40");
  await page.keyboard.press("]");
  await expect(page.locator('[data-speed="60"]')).toHaveClass("active");
  await page.keyboard.press("[");
  await expect(page.locator('[data-speed="20"]')).toHaveClass("active");
  await page.keyboard.press("Space");
  await expect(page.locator("#play")).toHaveAttribute(
    "aria-label",
    "Pause scenario",
  );
  await page.waitForTimeout(400);
  await page.keyboard.press("Space");
  await expect(page.locator("#play")).toHaveAttribute(
    "aria-label",
    "Play scenario",
  );
  check("keyboard seek, playback and speed controls");
  await page.keyboard.press("h");
  await expect(page.locator("#cinema-exit")).toBeVisible();
  await expect(page.locator(".topbar")).toBeHidden();
  await page.keyboard.press("h");
  await expect(page.locator(".topbar")).toBeVisible();
  await page.locator("#layers-toggle").click();
  await expect(page.locator("#layers-card")).toBeVisible();
  await page.locator("#layers-close").click();
  await page.locator("#tab-inspector").click();
  await expect(page.locator("#inspector-panel")).toBeVisible();
  await page.locator('[data-feed="iq"]').click();
  check("Cinema shortcut, collapsible layers and six-tab observation deck");
  await page.locator('[data-feed="satellite"]').click();
  await expect(page.locator("#satellite-inset")).toBeVisible();
  await page.waitForFunction(
    () => document.querySelector("#satellite-zoom").naturalWidth > 0,
  );
  await expect(page.locator("#satellite-zoom")).toHaveAttribute(
    "src",
    /_zoom\./,
  );
  await page.locator('[data-mode="god"]').click();
  await expect(page.locator("#satellite-inset")).toBeHidden();
  await page.locator('[data-mode="delta"]').click();
  check(
    "recorded satellite detail loads with its chip and is hidden in God mode",
  );
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill("opening");
  await page.locator("#command-input").press("Enter");
  await expect(page.locator("#opening")).toBeVisible();
  await expect(page.locator(".opening-title")).toHaveCSS("opacity", "1", {
    timeout: 8000,
  });
  await expect(page.locator("#opening")).toBeHidden({ timeout: 8000 });
  await expect(page.locator(".topbar")).toBeVisible();
  assert.notEqual(
    await page.evaluate(() => document.activeElement?.id),
    "layers-toggle",
  );
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill("opening");
  await page.locator("#command-input").press("Enter");
  await page.keyboard.press("Escape");
  await expect(page.locator("#opening")).toBeHidden();
  await expect(page.locator("#layers-toggle")).toBeFocused();
  check(
    "opening reaches its title, completes without stealing focus and can be skipped",
  );
  await page.locator("#present-start").click();
  await expect(page.locator("#presentation")).toBeVisible();
  for (let i = 1; i <= 10; i++) {
    await expect(page.locator("#beat-number")).toHaveText(
      `${String(i).padStart(2, "0")}/ 10 CHAPTERS`,
    );
    if (i < 10) await page.locator("#present-next").click();
  }
  await expect(page.locator("#audit-panel")).toBeVisible();
  const deployed = JSON.parse(
    (await readFile("dashboard/public/data.js", "utf8"))
      .trim()
      .replace(/^window.MW\s*=\s*/, "")
      .replace(/;$/, ""),
  );
  await expect(page.locator("#audit-panel")).toContainText(
    deployed.audit
      ? deployed.audit.checks[0].name.replaceAll("_", " ")
      : "AUDIT NOT SUPPLIED",
  );
  await expect(page.locator("#beat-stat")).toContainText(
    deployed.audit ? `${deployed.audit.summary.pass}/` : "NOT SUPPLIED",
  );
  await page.keyboard.press("Escape");
  await expect(page.locator("#presentation")).toBeHidden();
  check(
    "all ten PRESENT beats, truthful missing-data captions, exit restores replay",
  );
  await page.locator('[data-feed="microphone"]').click();
  await expect(page.locator("#feed-empty-message")).toHaveText(
    "No capture in this dataset",
  );
  await page.locator('[data-feed="iq"]').click();
  await page.locator("#feed-zoom").click();
  await expect(page.locator("#image-dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.locator("#file-input").setInputFiles({
    name: "malicious.js",
    mimeType: "text/javascript",
    buffer: Buffer.from("window.MW = {}; window.COMPROMISED = true;"),
  });
  await expect(page.locator("#toast")).toContainText(
    "Executable JavaScript is not accepted",
  );
  assert.equal(await page.evaluate(() => window.COMPROMISED), undefined);
  await expect(page.locator("#scenario-name")).toHaveText("ROS VALLEY");
  check(
    "missing feeds, media zoom, executable imports rejected without losing the world",
  );
  // Valid imported data exercises full teardown/rebuild; audit fixture is clearly labelled.
  const source = await readFile("dashboard/public/data.js", "utf8");
  const imported = JSON.parse(
    source
      .trim()
      .replace(/^window.MW\s*=\s*/, "")
      .replace(/;$/, ""),
  );
  imported.scenario.name = "browser-test-fixture";
  const samples = 8000 * 90,
    wav = Buffer.alloc(44 + samples * 2);
  wav.write("RIFF", 0);
  wav.writeUInt32LE(wav.length - 8, 4);
  wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(8000, 24);
  wav.writeUInt32LE(16000, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write("data", 36);
  wav.writeUInt32LE(samples * 2, 40);
  await page.route("**/sensors/MIC1/browser-fixture.wav", (route) =>
    route.fulfill({ contentType: "audio/wav", body: wav }),
  );
  await page.route("**/sensors/EO1/missing.png", (route) =>
    route.fulfill({
      contentType: "image/png",
      body: Buffer.from("not an image"),
    }),
  );
  imported.media.push({
    sensor: "MIC1",
    kind: "audio",
    t: 18400,
    src: "./sensors/MIC1/browser-fixture.wav",
  });
  imported.media = imported.media.filter((m) => m.sensor !== "EO1");
  imported.media.push({
    sensor: "EO1",
    kind: "image",
    t: 18400,
    src: "./sensors/EO1/missing.png",
  });
  imported.audit = {
    scenario: "browser-test-fixture",
    summary: { pass: 1, fail: 1, skip: 1 },
    checks: [
      {
        id: "pass",
        name: "Fixture PASS",
        status: "PASS",
        value: 1,
        threshold: 2,
        detail: "Test-only fixture.",
      },
      {
        id: "fail",
        name: "Fixture FAIL",
        status: "FAIL",
        value: 3,
        threshold: 2,
        detail: "Test-only fixture.",
      },
      {
        id: "skip",
        name: "Fixture SKIP",
        status: "SKIP",
        value: null,
        threshold: null,
        detail: "Test-only fixture.",
      },
    ],
    baseline: {
      summary: { pass: 0, fail: 1, skip: 0 },
      checks: [
        {
          id: "baseline",
          name: "Fixture baseline",
          status: "FAIL",
          value: 3,
          threshold: 1,
          detail: "Test-only fixture.",
        },
      ],
    },
  };
  await page.locator("#file-input").setInputFiles({
    name: "data.js",
    mimeType: "text/javascript",
    buffer: Buffer.from(`window.MW = ${JSON.stringify(imported)};`),
  });
  await expect(page.locator("#scenario-name")).toHaveText(
    "BROWSER TEST FIXTURE",
  );
  await page.locator('[data-tab="audit"]').click();
  await expect(page.locator("#audit-count")).toHaveText("1/3");
  await page.locator(".audit-check").first().locator("summary").click();
  await expect(page.locator(".audit-check").first()).toContainText(
    "Test-only fixture.",
  );
  check("valid scenario replacement and audit PASS/FAIL/SKIP/baseline details");
  await page.locator('[data-feed="camera"]').click();
  await expect(page.locator("#feed-state")).toHaveText("MISSING MEDIA");
  await expect(page.locator("#feed-empty-message")).toHaveText(
    "Referenced capture could not be loaded",
  );
  await page.locator('[data-feed="microphone"]').click();
  await page.locator("#audio-play").click();
  await page.locator('[data-speed="5"]').click();
  await page.locator("#play").click();
  await expect(page.locator("#feed-state")).toHaveText("PLAYING / 5×");
  assert.equal(
    await page.evaluate(() => window.__testAudioSource.playbackRate.value),
    5,
  );
  await page.locator("#play").click();
  await expect(page.locator("#feed-state")).toHaveText("PAUSED");
  check(
    "broken image degrades visibly; WebAudio decodes, follows replay speed and pauses",
  );
  for (const [width, height] of [
    [1280, 720],
    [1440, 900],
    [1920, 1080],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(100);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    );
    assert.equal(overflow, false, `${width} horizontal overflow`);
    await expect(page.locator("#play")).toBeInViewport();
    await expect(page.locator("#present-start")).toBeInViewport();
  }
  check("1280×720, 1440×900, 1920×1080 and narrow-screen layout");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.locator('[data-feed="iq"]').click();
  await page.locator("#play").click();
  const cursor = await page
    .locator("#iq-cursor")
    .evaluate((el) => el.style.left);
  await page.waitForTimeout(350);
  assert.equal(
    await page.locator("#iq-cursor").evaluate((el) => el.style.left),
    cursor,
  );
  assert.equal(
    await page
      .locator("#feed-empty")
      .evaluate((el) => getComputedStyle(el, "::before").animationName),
    "none",
  );
  await page.locator("#play").click();
  await page.locator("#command-open").click();
  await page.locator("#command-input").fill("opening");
  await page.locator("#command-input").press("Enter");
  await expect(page.locator("#opening")).toBeHidden();
  check(
    "reduced-motion preference stops decorative CSS animation and IQ cursor motion",
  );
  assert.deepEqual(errors, [], "Uncaught browser exceptions");
  assert.deepEqual(consoleErrors, [], "Browser console errors");
  check("no browser runtime or console errors");
  await mkdir("dashboard/test-results", { recursive: true });
  await writeFile(
    "dashboard/test-results/browser-report.json",
    JSON.stringify({ url, checks, errors, consoleErrors }, null, 2),
  );
  console.log(`\n${checks.length} browser checks passed.`);
} finally {
  await browser.close();
  await new Promise((r) => server.close(r));
}
