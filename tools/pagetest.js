// 페이지가 **실제로 그려지는지** 진짜 브라우저로 본다.
//
// 왜 있나: Pages 가 200 을 줘도 화면이 그려지는 건 아니다. 스크립트 하나가 터지면
// 흰 화면이 뜨는데 배포는 "성공"으로 남는다 — 조용한 거짓 성공이다.
// 실제로 이 검사가 첫 구축 때 버그를 잡았다: 매출 뷰를 빼면서 userrow.js 도 같이 뺐는데
// realtime.js 가 window.UserRow 를 쓰고 있어서 실시간 탭이 통째로 죽어 있었다.
// 파일 목록만 봐서는 안 보이고, 탭을 눌러 봐야 보인다.
//
//   node tools/pagetest.js          (서버는 이 스크립트가 직접 띄우지 않는다)
//   python3 -m http.server -d docs 8099 &   를 먼저 띄워 둘 것
//
// playwright 는 ~/dev/chatgpt_art_auto_a 의 것을 빌려 쓴다(이 리포에 의존성을 안 만든다).
const PW = process.env.HOME + "/dev/chatgpt_art_auto_a/node_modules/playwright";
const URL = process.env.URL || "http://127.0.0.1:8099/";
const { chromium } = require(PW);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 420, height: 900 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  await p.goto(URL, { waitUntil: "networkidle" });
  await p.waitForTimeout(600);

  const fails = [];
  const tabs = await p.$$eval(".vtab", bs => bs.map(b => b.dataset.view));
  if (!tabs.length) fails.push("탭이 하나도 없다");

  // 모든 탭을 **눌러 본다.** 렌더는 탭을 눌러야 돌므로, 안 누르면 죽은 뷰를 못 잡는다.
  for (const v of tabs) {
    await p.click(`.vtab[data-view="${v}"]`);
    await p.waitForTimeout(400);
    const shown = await p.$eval(`#view-${v}`, el => !el.hidden).catch(() => null);
    if (shown === null) fails.push(`${v}: #view-${v} 가 없다`);
    else if (!shown) fails.push(`${v}: 탭을 눌러도 안 보인다`);
  }
  if (errs.length) fails.push("JS 예외: " + errs.join(" / "));

  console.log(`탭 ${tabs.length}개: ${tabs.join(", ")}`);
  if (fails.length) { console.log("❌ FAIL\n  - " + fails.join("\n  - ")); await b.close(); process.exit(1); }
  console.log("✅ PASS — 모든 탭이 예외 없이 그려진다");
  await b.close();
})();
