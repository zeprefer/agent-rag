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
  await page.goto("http://localhost:5174", { waitUntil: "networkidle" });
  await page.locator("#sessionList").evaluate((sessionList) => {
    sessionList.innerHTML = `
      <div class="session-item active">
        <button class="session-select" type="button">
          <strong>Knowledge chat</strong>
          <span class="session-meta">默认助手 / 07/19 17:35</span>
        </button>
        <button class="session-delete" type="button">删除</button>
      </div>
      <div class="session-item">
        <button class="session-select" type="button">
          <strong>你是谁</strong>
          <span class="session-meta">默认助手 / 07/19 17:31</span>
        </button>
        <button class="session-delete" type="button">删除</button>
      </div>
    `;
  });
  await page.locator("#messages").evaluate((messages) => {
    const longAnswer = "这是一段用于验证固定回答窗口的测试内容。".repeat(600);
    messages.innerHTML = `
      <article class="message assistant">
        <span class="message-role">知识助手</span>
        <div class="bubble">${longAnswer}</div>
      </article>
    `;
  });

  const metrics = await page.evaluate(() => {
    const messages = document.querySelector("#messages");
    const composer = document.querySelector("#messageForm");
    const messageStyle = getComputedStyle(messages);
    const composerRect = composer.getBoundingClientRect();
    return {
      viewportHeight: window.innerHeight,
      pageClientHeight: document.documentElement.clientHeight,
      pageScrollHeight: document.documentElement.scrollHeight,
      bodyScrollHeight: document.body.scrollHeight,
      messagesClientHeight: messages.clientHeight,
      messagesScrollHeight: messages.scrollHeight,
      messagesOverflowY: messageStyle.overflowY,
      composerTop: Math.round(composerRect.top),
      composerBottom: Math.round(composerRect.bottom),
      deleteButtonVisible: Boolean(document.querySelector(".session-delete")?.offsetParent),
    };
  });

  const failures = [];
  if (metrics.pageScrollHeight > metrics.pageClientHeight) failures.push("page scrolls vertically");
  if (metrics.messagesScrollHeight <= metrics.messagesClientHeight) failures.push("message area does not scroll internally");
  if (metrics.messagesOverflowY !== "auto") failures.push("message overflow is not auto");
  if (metrics.composerBottom > metrics.viewportHeight) failures.push("composer is outside the viewport");
  if (!metrics.deleteButtonVisible) failures.push("session delete button is not visible");

  await page.screenshot({ path: "tmp/user-layout-qa.png", fullPage: false });
  await browser.close();
  console.log(JSON.stringify({ status: failures.length ? "failed" : "passed", metrics, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
