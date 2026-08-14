const { chromium } = require("playwright");
const fs = require("fs");

async function main() {
  const browserCandidates = [
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ];
  const executablePath = browserCandidates.find((candidate) => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto("http://localhost:5173", { waitUntil: "networkidle" });

  if (await page.locator("#loginForm").isVisible()) {
    await page.locator("#emailInput").fill("admin@example.com");
    await page.locator("#passwordInput").fill("ChangeMe123!");
    await page.locator("#loginForm button[type='submit']").click();
    await page.locator("#adminNav").waitFor({ state: "visible", timeout: 15_000 });
  }

  const targets = ["overview", "knowledge", "documents", "indexing", "agents", "users", "audit", "settings"];
  const navigationChecks = [];
  for (const target of targets) {
    await page.locator(`.nav-item[data-view-target='${target}']`).click();
    const check = await page.evaluate((view) => {
      const activeViews = [...document.querySelectorAll(".admin-view.active")].filter(
        (element) => getComputedStyle(element).display !== "none",
      );
      const expected = document.querySelector(`.admin-view[data-view='${view}']`);
      return {
        target: view,
        title: document.querySelector("#workspaceTitle")?.textContent,
        activeCount: activeViews.length,
        expectedVisible: Boolean(expected && getComputedStyle(expected).display !== "none"),
      };
    }, target);
    navigationChecks.push(check);
  }

  await page.locator(".nav-item[data-view-target='overview']").click();
  await page.screenshot({ path: "tmp/admin-overview-qa.png", fullPage: false });

  await page.locator(".nav-item[data-view-target='audit']").click();
  await page.locator("#auditLogsList").evaluate((list) => {
    list.innerHTML = Array.from({ length: 48 }, (_, index) => `
      <article class="governance-item">
        <div class="governance-item-head"><strong>测试审计记录 ${index + 1}</strong><span class="pill good">成功</span></div>
        <div class="job-meta">文档 · layout-test-${index + 1}</div>
        <div class="job-meta">07/19 20:${String(index % 60).padStart(2, "0")} · 操作人 admin</div>
      </article>
    `).join("");
  });

  const metrics = await page.evaluate(() => {
    const activeView = document.querySelector(".admin-view.active");
    const style = getComputedStyle(activeView);
    return {
      viewportHeight: window.innerHeight,
      pageClientHeight: document.documentElement.clientHeight,
      pageScrollHeight: document.documentElement.scrollHeight,
      bodyScrollHeight: document.body.scrollHeight,
      activeViewClientHeight: activeView.clientHeight,
      activeViewScrollHeight: activeView.scrollHeight,
      activeViewOverflowY: style.overflowY,
      sidebarClientHeight: document.querySelector(".sidebar").clientHeight,
      workspaceClientHeight: document.querySelector(".workspace").clientHeight,
    };
  });
  await page.screenshot({ path: "tmp/admin-audit-qa.png", fullPage: false });

  const failures = [];
  if (metrics.pageScrollHeight > metrics.pageClientHeight) failures.push("browser page scrolls vertically");
  if (metrics.bodyScrollHeight > metrics.viewportHeight) failures.push("body exceeds viewport height");
  if (metrics.activeViewScrollHeight <= metrics.activeViewClientHeight) failures.push("active admin view does not scroll internally");
  if (metrics.activeViewOverflowY !== "auto") failures.push("active admin view overflow is not auto");
  if (metrics.workspaceClientHeight !== metrics.viewportHeight) failures.push("workspace is not viewport-height");
  for (const check of navigationChecks) {
    if (check.activeCount !== 1 || !check.expectedVisible) failures.push(`navigation failed: ${check.target}`);
  }

  await browser.close();
  console.log(JSON.stringify({ status: failures.length ? "failed" : "passed", metrics, navigationChecks, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
