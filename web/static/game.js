// game.js — 화면과 애니메이션 담당. 정답 판정·표류자 결과는 Python 서버(/api/...)에 물어본다.
// (흐름은 tkinter 버전 island_system.py와 같다)

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));   // ms만큼 기다리기

// 서버에 요청 보내기: body가 있으면 POST(데이터 보내기), 없으면 GET(데이터 받기)
// GitHub Pages처럼 Python 서버가 없는 곳(STATIC_MODE)에서는 localApi가 대신 대답한다
async function api(url, body) {
  if (window.STATIC_MODE) return localApi(url, body);
  const opt = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined;
  const res = await fetch(url, opt);
  return res.json();
}

// ── 정적 배포(GitHub Pages)용: Python의 build_static.py가 만든 data.json으로 판정 ──
// 정답은 SHA-256 해시로만 들어 있어서, 입력한 답을 같은 방식으로 해시해 비교한다
// (표류자 정체는 인코딩만 되어 있어 완전한 비밀은 아니다 — 서버가 있는 Flask 버전이 더 안전)
let LOCAL = null;
const norm = (t) => String(t).trim().replaceAll(" ", "").toLowerCase();   // Python normalize와 같음
const decode = (b64) => JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))));
const pick = (list) => list[Math.floor(Math.random() * list.length)];

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function localApi(url, body) {
  if (!LOCAL) LOCAL = await (await fetch("data.json")).json();
  const R = LOCAL.rules;
  if (url === "/api/setup") {
    return {
      rules: R,
      quests: LOCAL.quests.map(({ id, title, question, hint }) => ({ id, title, question, hint })),
      castaways: LOCAL.castaways.map(({ id, name, story, clues, image }) => ({ id, name, story, clues, image })),
    };
  }
  if (url === "/api/supply") return { item: pick(R.supplies) };
  if (url === "/api/check") {
    const q = LOCAL.quests.find((x) => x.id === body.quest_id);
    const correct = q.answer_hashes.includes(await sha256(norm(body.answer)));
    if (correct) return { correct, exp: body.tries === 0 ? R.exp_first_try : R.exp_with_hint };
    return body.tries + 1 >= R.max_tries ? { correct, reveal: decode(q.reveal) } : { correct };
  }
  if (url === "/api/rescue") return resolveLocal(body);
}

function resolveLocal({ castaway_id, choice, inventory, exp }) {   // game_data.resolve_choice와 같은 규칙
  const c = LOCAL.castaways.find((x) => x.id === castaway_id);
  const sec = decode(c.secret);
  const inv = [...inventory], name = c.name, items = sec.reward_items || [];
  let text = "", delta = 0;
  if (sec.truth === "ally") {
    if (choice === "trust") { inv.push(...items); text = `${name}이(가) 고마워하며 [${items.join(", ")}]을(를) 나눠 주었다!`; delta = 60; }
    else if (choice === "guard") { inv.push(items[0]); text = `조심스럽게 대하자 ${name}도(는) 거리를 두었다. 작은 도움 [${items[0]}]만 받았다.`; delta = 20; }
    else text = `${name}은(는) 혼자 섬 반대편으로 걸어가 버렸다. 좋은 동료를 놓쳤다.`;
  } else if (sec.truth === "thief") {
    if (choice === "trust") {
      if (inv.length) { const s = pick(inv); inv.splice(inv.indexOf(s), 1); text = `밤사이 [${s}]이(가) 사라졌다! ${name}도(는) 함께 사라졌다.`; }
      else { delta = -Math.min(exp, 30); text = `훔칠 물건이 없자 ${name}은(는) 식량을 몰래 먹어 치웠다. (EXP ${delta})`; }
    } else if (choice === "guard") { text = `가방을 몸에 지닌 채 구조했다. ${name}은(는) 다음 날 조용히 떠났다. 피해 없음! (판단력 보너스)`; delta = 40; }
    else { text = `멀리서 지켜보는 사이 ${name}은(는) 배를 고쳐 떠났다. 피해는 없었다.`; delta = 10; }
  } else {
    if (choice === "trust") {
      const food = inv.find((f) => LOCAL.rules.foods.includes(f));
      if (food) { inv.splice(inv.indexOf(food), 1); text = `${name}이(가) 응급처치법을 가르쳐 주었다. 대신 [${food}]을(를) 나눠 먹었다.`; }
      else text = `${name}이(가) 응급처치법을 가르쳐 주었다. 나눠 먹을 식량이 없어 함께 굶었다.`;
      delta = 20;
    } else if (choice === "guard") { text = `거리를 두고 지켜보니 ${name}은(는) 섬 지도를 그려 두고 떠났다.`; delta = 30; }
    else { text = `${name}은(는) 며칠 뒤 다른 해안으로 떠났다. 아무 일도 없었다.`; delta = 10; }
  }
  return { text, exp_delta: delta, inventory: inv, correct: choice === sec.best, truth_name: sec.truth_name, explain: sec.explain };
}

// ── 진행 상태 (Python 버전의 전역 변수들과 같은 역할) ──
const S = {
  rules: null, quests: [], order: [], current: 0, tries: 0,
  inRetry: false, retry: [], weak: [], finished: false, judged: false, checking: false,
  level: 1, exp: 0, clear: 0, inventory: [],
  castawaysLeft: [], pending: [], busy: false, eventsSeen: 0, judgeLog: [],
};

function shuffle(list) {           // 순서 무작위로 섞기
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

// ── 상태창 ──
function updateStatus() {
  const per = S.rules.exp_per_level;
  $("lv").textContent = `Lv.${S.level}`;
  $("expFill").style.width = `${(S.exp / per) * 100}%`;
  $("expText").textContent = `${S.exp} / ${per}`;
  const good = S.judgeLog.filter((j) => j.ok).length;
  $("meta").textContent = `재도전 ${S.retry.length} · 판단 ${good}/${S.judgeLog.length}`;
  $("bag").innerHTML = S.inventory.length
    ? "가방 " + S.inventory.map((it) => `<span class="chip">${it}</span>`).join("")
    : "가방 · 비어 있음";
  const flares = S.inventory.filter((it) => it === "신호탄").length;
  $("flare").textContent = `신호탄 쏘기 ×${flares}`;
  $("flare").disabled = !(flares > 0 && !S.judged && !S.finished && !S.busy && S.tries === 0);
}

function notice(text, cls) {
  const n = $("notice");
  n.textContent = text;
  n.className = `notice ${cls}`;
  setTimeout(() => { if (n.textContent === text) n.textContent = ""; }, 3000);
}

function setFuture(text) {         // 미래의 나 말풍선
  $("future").hidden = !text;
  $("hint").textContent = text || "";
}

function gainExp(amount) {         // EXP 얻기 → 레벨업 했으면 true
  S.exp += amount;
  let leveled = false;
  while (S.exp >= S.rules.exp_per_level) {
    S.exp -= S.rules.exp_per_level;
    S.level += 1;
    leveled = true;
  }
  updateStatus();
  return leveled;
}

function lockInput(locked) {
  $("answer").disabled = locked;
  $("submit").disabled = locked;
  if (locked) $("flare").disabled = true;
}

// ── 퀘스트 진행 ──
function showQuest() {
  S.judged = false;
  const q = S.order[S.current];
  $("progress").textContent = `${S.inRetry ? "재도전" : "QUEST"} ${S.current + 1} / ${S.order.length}`;
  $("qTitle").textContent = `【 ${q.title} 】`;
  $("qText").textContent = q.question;
  $("result").textContent = "";
  setFuture("");
  $("answer").value = "";
  lockInput(false);
  updateStatus();
  $("answer").focus();
}

function nextQuest() {
  S.current += 1;
  S.tries = 0;
  if (S.current < S.order.length) {
    showQuest();
  } else if (!S.inRetry && S.retry.length > 0) {
    S.order = S.retry;
    S.retry = [];
    S.current = 0;
    S.inRetry = true;
    notice("[알림] 재도전 퀘스트가 발동되었습니다.", "warn");
    showQuest();
  } else {
    showSummary();
  }
}

function showSummary() {
  S.finished = true;
  const good = S.judgeLog.filter((j) => j.ok).length;
  $("progress").textContent = "DAY 1 COMPLETE";
  $("qTitle").textContent = "【 오늘의 일일 퀘스트 종료 】";
  $("qText").textContent = `클리어 ${S.clear} / ${S.quests.length}   ·   최종 Lv.${S.level}\n표류자 판단 ${good} / ${S.judgeLog.length}`;
  $("result").textContent = "";
  if (S.weak.length === 0) {
    setFuture("잘했어. 지식도, 사람을 보는 눈도 섬에서는 생존 기술이야.");
  } else {
    const names = S.weak.map((q) => q.title.split(" ").pop()).join(", ");
    setFuture(`내일은 '${names}' 부분을 다시 공부하자.`);
  }
  lockInput(true);
  updateStatus();
}

async function onSubmit(e) {
  e.preventDefault();               // form 제출 시 페이지가 새로고침되는 기본 동작 막기
  if (S.busy || S.judged || S.finished || S.checking) return;
  const text = $("answer").value;
  if (text.trim() === "") {
    $("result").innerHTML = `<span class="warn">[경고] 답을 입력하십시오.</span>`;
    return;
  }
  const q = S.order[S.current];
  S.checking = true;
  const res = await api("/api/check", { quest_id: q.id, answer: text, tries: S.tries });
  S.checking = false;

  if (res.correct) {
    S.clear += 1;
    S.judged = true;
    $("result").innerHTML = `<span class="ok">▶ QUEST CLEAR &nbsp; EXP +${res.exp}</span>`;
    setFuture("");
    lockInput(true);
    const leveled = gainExp(res.exp);
    if (leveled) notice(`[알림] 레벨이 올랐습니다!  Lv.${S.level}`, "warn");
    finishQuest(leveled, leveled ? 900 : 1200);
  } else {
    S.tries += 1;
    if (S.tries < S.rules.max_tries) {
      $("result").innerHTML = `<span class="bad">✘ 오답 (남은 기회 ${S.rules.max_tries - S.tries})</span>`;
      setFuture(q.hint);
      $("answer").value = "";
      updateStatus();
    } else {
      $("result").innerHTML = `<span class="bad">▶ QUEST FAILED &nbsp; 정답: ${res.reveal}</span>`;
      (S.inRetry ? S.weak : S.retry).push(q);
      S.judged = true;
      lockInput(true);
      updateStatus();
      finishQuest(false, 2000);
    }
  }
}

function useFlare() {              // 신호탄: 힌트를 미리 보기 (EXP 절반)
  const i = S.inventory.indexOf("신호탄");
  if (i < 0) return;
  S.inventory.splice(i, 1);
  S.tries = 1;
  setFuture(`신호탄 확인! ${S.order[S.current].hint}`);
  $("result").innerHTML = `<span class="warn">신호탄 사용 (남은 기회 ${S.rules.max_tries - S.tries})</span>`;
  updateStatus();
  $("answer").focus();
}

// 퀘스트가 끝난 뒤: (무작위 돌발 미션 예약) → (레벨업 연출) → (돌발 미션들) → 다음 퀘스트
function finishQuest(leveled, delay) {
  const roll = Math.random() < S.rules.event_chance;
  const must = S.eventsSeen === 0 && !S.inRetry && S.current === 2;   // 시연용: 3번째까지 한 번은 보장
  if ((roll || must) && !S.inRetry && S.castawaysLeft.length) {
    S.pending.push(S.castawaysLeft.shift());
  }
  const go = async () => {
    if (S.busy) return setTimeout(go, 300);    // F2로 띄운 창이 떠 있으면 잠시 뒤 다시
    if (leveled) await playSupplyDrop();
    await runEvents();
    nextQuest();
  };
  setTimeout(go, delay);
}

// ★ 돌발 상황 해결의 핵심: 대기열의 미션을 하나씩 끝까지 처리한 다음에 원래 흐름으로 돌아간다
async function runEvents() {
  while (S.pending.length) {
    await startEvent(S.pending.shift());
  }
}

// ── 레벨업 보급 연출 ──
async function playSupplyDrop() {
  S.busy = true;
  lockInput(true);
  const { item } = await api("/api/supply");
  S.inventory.push(item);

  const ov = $("levelup"), heli = $("heli"), crate = $("crate"), reward = $("luReward");
  $("luSub").textContent = `Lv.${S.level} 달성 · 미래의 나가 구조 헬기를 보냈다`;
  reward.style.opacity = 0;
  reward.textContent = `보급 상자 획득!  [ ${item} ]`;
  crate.querySelector(".chute").style.opacity = 1;
  crate.querySelector(".lines").style.opacity = 1;
  ov.hidden = false;

  // element.animate(장면 목록, 옵션) = 위치를 시간에 따라 바꾸는 애니메이션 (Web Animations API)
  heli.animate(
    [{ left: "110%" }, { left: "42%", offset: 0.35 }, { left: "42%", offset: 0.55 }, { left: "-30%" }],
    { duration: 4200, easing: "ease-in-out", fill: "forwards" }
  );
  await sleep(1650);
  const fall = crate.animate(
    [{ top: "44%", opacity: 1 }, { top: "66%", opacity: 1 }],
    { duration: 1500, easing: "ease-in", fill: "forwards" }
  );
  await fall.finished;
  crate.querySelector(".chute").style.opacity = 0;   // 착지 → 낙하산 접기
  crate.querySelector(".lines").style.opacity = 0;
  reward.style.opacity = 1;
  updateStatus();
  await sleep(2200);
  ov.hidden = true;
  crate.getAnimations().forEach((a) => a.cancel());
  heli.getAnimations().forEach((a) => a.cancel());
  S.busy = false;
}

// ── 돌발 미션: 표류자 ──
function startEvent(c) {
  // Promise = '나중에 끝나는 일'. resolve()를 부르는 순간 await하던 쪽이 다음으로 진행한다
  return new Promise(async (resolve) => {
    S.busy = true;
    S.eventsSeen += 1;
    lockInput(true);

    const ov = $("event"), drifter = $("drifter");
    $("evBody").hidden = true;
    $("evTip").hidden = true;
    $("choices").hidden = true;
    $("evResult").hidden = true;
    $("evBanner").classList.remove("show");
    $("drifterImg").src = `static/img/${c.image}`;
    ov.hidden = false;

    // 1) 파도를 타고 오른쪽 바다에서 해안가로 떠밀려 온다
    drifter.classList.add("bobbing");
    const drift = drifter.animate(
      [
        { left: "105%", top: "52%", transform: "scale(0.55) rotate(-14deg)" },
        { left: "70%", top: "58%", transform: "scale(0.7) rotate(6deg)", offset: 0.5 },
        { left: "30%", top: "50%", transform: "scale(0.9) rotate(-3deg)" },
      ],
      { duration: 2800, easing: "ease-out", fill: "forwards" }
    );
    await drift.finished;
    drifter.classList.remove("bobbing");
    $("evBanner").classList.add("show");
    await sleep(700);

    // 2) 이야기와 단서 (③은 숨김)
    $("portrait").src = `static/img/${c.image}`;
    $("evName").textContent = c.name;
    $("evStory").textContent = c.story;
    $("clues").innerHTML =
      `<li>단서 ① ${c.clues[0]}</li><li>단서 ② ${c.clues[1]}</li>` +
      `<li class="hidden-clue" id="clue3">단서 ③ ???  (더 살펴보면 알 수 있다)</li>`;
    const look = $("lookCloser");
    look.disabled = false;
    look.textContent = "◎ 더 살펴보기";
    look.onclick = () => {
      const li = $("clue3");
      li.textContent = `단서 ③ ${c.clues[2]}`;
      li.className = "revealed";
      look.disabled = true;
      look.textContent = "모두 살펴봤다";
    };
    $("evBody").hidden = false;
    $("evTip").hidden = false;
    $("choices").hidden = false;
    document.querySelectorAll(".choice").forEach((b) => {
      b.disabled = false;
      b.onclick = () => choose(b.dataset.choice);
    });

    // 3) 선택 → 서버가 결과 계산 → 정체 공개 + 미래의 나 해설
    async function choose(choice) {
      document.querySelectorAll(".choice").forEach((b) => (b.disabled = true));
      look.disabled = true;
      const res = await api("/api/rescue", {
        castaway_id: c.id, choice, inventory: S.inventory, exp: S.exp,
      });
      S.inventory = res.inventory;
      S.judgeLog.push({ name: c.name, ok: res.correct });
      let leveled = false;
      if (res.exp_delta > 0) leveled = gainExp(res.exp_delta);
      else { S.exp += res.exp_delta; updateStatus(); }

      $("choices").hidden = true;
      $("evTip").hidden = true;
      const sign = res.exp_delta >= 0 ? "+" : "";
      const box = $("evResult");
      box.innerHTML = `
        <div class="verdict ${res.correct ? "ok" : "bad"}">${res.correct ? "✔ 좋은 판단" : "✘ 아쉬운 판단"} &nbsp; EXP ${sign}${res.exp_delta}</div>
        <p class="what">${res.text}</p>
        <div class="truth">정체: ${res.truth_name}</div>
        <div class="future"><img src="static/img/future_me.jpg" alt=""><p><b>미래의 나</b>${res.explain}</p></div>
        <button class="btn primary" id="evContinue" type="button">계속 ▶</button>`;
      box.hidden = false;
      $("evContinue").focus();
      $("evContinue").onclick = async () => {
        ov.hidden = true;
        drifter.getAnimations().forEach((a) => a.cancel());
        S.busy = false;
        if (leveled) await playSupplyDrop();   // 돌발 미션으로 레벨업했으면 보급 헬기도
        resolve();
      };
    }
  });
}

// F2 = 시연용 돌발 미션 즉시 발생. 진행 중인 퀘스트는 그대로 두고 끝나면 이어서 푼다
async function forceEvent() {
  const c = S.castawaysLeft.shift();
  if (!c) return notice("[알림] 더 이상 떠밀려 올 사람이 없습니다.", "warn");
  S.pending.push(c);
  if (S.busy) return;               // 다른 창이 떠 있으면 대기열에서 기다린다
  await runEvents();
  if (!S.finished && !S.judged) {   // 풀던 퀘스트로 복귀 (입력하던 글자도 그대로)
    lockInput(false);
    updateStatus();
    $("answer").focus();
  }
}

// ── 시작 화면: 미래의 나의 메시지를 한 글자씩 ──
async function intro() {
  const line = "[알림] 미래의 당신이 설계한 생존 교육 시스템이 활성화되었습니다.\n\n" +
    "나는 10년 뒤의 너다. 이 섬에서 살아남는 법을 퀘스트로 남겨 둔다.\n" +
    "그리고 기억해. 이 섬에는 예상하지 못한 손님이 찾아온다.";
  const el = $("introLine");
  for (const ch of line) {
    el.textContent += ch;
    await sleep(ch === "\n" ? 120 : 22);
  }
  $("startBtn").hidden = false;
  $("startBtn").focus();
}

async function init() {
  const data = await api("/api/setup");
  S.rules = data.rules;
  S.quests = data.quests;
  S.order = [...data.quests];
  S.castawaysLeft = shuffle([...data.castaways]);

  $("answerForm").addEventListener("submit", onSubmit);
  $("flare").addEventListener("click", useFlare);
  document.addEventListener("keydown", (e) => {
    if (e.key === "F2") { e.preventDefault(); forceEvent(); }
  });
  $("startBtn").addEventListener("click", () => {
    $("intro").hidden = true;
    $("answer").focus();
  });

  updateStatus();
  showQuest();
  intro();
}

init();
