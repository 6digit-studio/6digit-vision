#!/usr/bin/env node
/**
 * cdp_shot.js — exact-viewport screenshot via Chrome DevTools Protocol.
 *
 * Why: on macOS, `chrome --headless --screenshot --window-size=W,H` captures
 * W×H pixels but lays the page out in a viewport of max(500,W) × (H-87)
 * (window chrome + minimum window width). CSS `vw`/`vh`/`right`/`bottom`
 * then resolve against the wrong box and content lands off-canvas.
 *
 * This script sets the layout viewport explicitly with
 * Emulation.setDeviceMetricsOverride, so the page sees exactly W×H.
 *
 * Usage: node cdp_shot.js <file-or-url> <out.png> <width> <height>
 */
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const CHROME = process.env.CHROME_BIN ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const [, , target, out, wArg, hArg] = process.argv;
if (!target || !out || !wArg || !hArg) {
  console.error("usage: node cdp_shot.js <file-or-url> <out.png> <width> <height>");
  process.exit(2);
}
const W = parseInt(wArg, 10);
const H = parseInt(hArg, 10);
const url = /^[a-z]+:/i.test(target) ? target : "file://" + path.resolve(target);

const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-shot-"));
const chrome = spawn(CHROME, [
  "--headless=new",
  "--remote-debugging-port=0",
  `--user-data-dir=${profile}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-gpu",
  "--hide-scrollbars",
  "--allow-file-access-from-files",
  "about:blank",
], { stdio: ["ignore", "ignore", "pipe"] });

const cleanup = () => { try { chrome.kill("SIGKILL"); } catch {} };
process.on("exit", cleanup);
setTimeout(() => { console.error("timeout"); cleanup(); process.exit(1); }, 30000);

function browserWs() {
  return new Promise((resolve, reject) => {
    let buf = "";
    chrome.stderr.on("data", (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) resolve(m[1]);
    });
    setTimeout(() => reject(new Error("no DevTools endpoint")), 10000);
  });
}

(async () => {
  const ws = new WebSocket(await browserWs());
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });

  let nextId = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  };
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });

  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Page.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", {
    width: W, height: H, deviceScaleFactor: 1, mobile: false,
  }, sessionId);
  await send("Page.navigate", { url }, sessionId);

  // wait for load + fonts + two RAFs
  for (let i = 0; i < 100; i++) {
    const r = await send("Runtime.evaluate", {
      expression: "document.readyState",
      returnByValue: true,
    }, sessionId);
    if (r.result && r.result.value === "complete") break;
    await new Promise((r2) => setTimeout(r2, 50));
  }
  await send("Runtime.evaluate", {
    expression: `(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      return [innerWidth, innerHeight];
    })()`,
    awaitPromise: true,
    returnByValue: true,
  }, sessionId);

  const shot = await send("Page.captureScreenshot", {
    format: "png", fromSurface: true, captureBeyondViewport: false,
  }, sessionId);
  fs.writeFileSync(out, Buffer.from(shot.data, "base64"));

  const dims = await send("Runtime.evaluate", {
    expression: "innerWidth + 'x' + innerHeight",
    returnByValue: true,
  }, sessionId);
  console.log(`wrote ${out} (${W}x${H}); page viewport ${dims.result.value}`);

  ws.close();
  cleanup();
  process.exit(0);
})().catch((e) => { console.error(e); cleanup(); process.exit(1); });
