"use strict";

// Build Your Reactor: the optional game tab. It only talks to the meter page
// to (a) add a tab and (b) read the live baht-per-hour text so the real cost
// stays on screen. It never writes to anything the meter uses.

(() => {
  const E = window.ReactorEngine;
  const ART = window.ReactorArt;
  const TICK_MS = 250;
  const SAVE_MS = 15000;
  const AWAY_NOTICE_SEC = 60;

  const view = document.getElementById("reactorView");
  const tabs = [...document.querySelectorAll(".views button")];

  let state = null;
  let loading = null;
  let timer = null;
  let lastTick = 0;
  let lastSave = 0;
  let shown = { credits: "", research: "", rate: "" };

  const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
  const small = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 1 });

  function fmt(n) {
    if (!Number.isFinite(n)) return "–";
    return n < 1000 ? small.format(Math.floor(n * 10) / 10) : compact.format(n);
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /* Tabs */

  function setView(name) {
    document.body.dataset.view = name;
    for (const b of tabs) b.setAttribute("aria-pressed", String(b.dataset.view === name));
    view.hidden = name !== "reactor";
    if (name === "reactor") open();
    else pause();
  }

  for (const b of tabs) b.addEventListener("click", () => setView(b.dataset.view));

  // Widget mode is for the meter; drop back to it if the window shrinks.
  new MutationObserver(() => {
    if (document.body.classList.contains("compact") && document.body.dataset.view === "reactor") {
      setView("meter");
    }
  }).observe(document.body, { attributes: true, attributeFilter: ["class"] });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
    else if (document.body.dataset.view === "reactor") resume();
  });

  /* Loading, saving, running */

  async function open() {
    if (!state) {
      loading ??= load();
      await loading;
    }
    resume();
  }

  async function load() {
    buildShell();
    let saved = null;
    try {
      saved = await window.pywebview.api.load_game();
    } catch (err) {
      console.error("load_game failed", err);
    }
    const now = Date.now();
    state = E.restore(saved, now);
    if (saved) {
      const away = E.offlineEarnings(state, now);
      if (away.away >= AWAY_NOTICE_SEC && away.credits + away.research > 0) showAway(away);
    }
    state.savedAt = now;
    renderAll();
  }

  function resume() {
    if (!state || timer) return;
    view.classList.add("is-running");
    // Time the tab spent hidden still counts, at full rate: the app was open.
    tick(true);
    timer = setInterval(() => tick(false), TICK_MS);
  }

  function pause() {
    view.classList.remove("is-running");
    if (!timer) return;
    clearInterval(timer);
    timer = null;
    save();
  }

  function tick(catchUp) {
    const now = Date.now();
    if (lastTick && (catchUp || now > lastTick)) E.tick(state, (now - lastTick) / 1000);
    lastTick = now;
    for (const a of E.newAchievements(state)) toast(`ความสำเร็จ: ${a.name}`);
    renderNumbers();
    if (now - lastSave > SAVE_MS) save();
  }

  async function save() {
    if (!state) return;
    lastSave = Date.now();
    state.savedAt = lastSave;
    try {
      await window.pywebview.api.save_game(state);
    } catch (err) {
      console.error("save_game failed", err);
    }
  }

  window.addEventListener("pagehide", save);

  /* Layout */

  const $ = (sel) => view.querySelector(sel);

  function buildShell() {
    view.innerHTML = `
      <p class="rx-realcost" role="note">
        ค่าไฟจริงของคอมตอนนี้ <strong data-real-rate>–</strong>
        <span>มาจากมิเตอร์ ไม่เกี่ยวกับเกม</span>
      </p>

      <section class="rx-console" aria-label="แผงควบคุม">
        <header class="rx-console-head">
          <h2>Build Your Reactor</h2>
          <span class="rx-plate">เกมจำลอง เครดิตในเกมไม่ใช่เงินจริง</span>
        </header>
        <div class="rx-readouts">
          <div class="rx-readout">
            <div class="rx-nixie" data-credits aria-live="off"></div>
            <span class="rx-plate">เครดิต (cr)</span>
          </div>
          <div class="rx-readout">
            <svg class="rx-gauge" viewBox="0 0 160 92" aria-hidden="true"></svg>
            <span class="rx-plate">ผลิต <b data-rate>0</b> cr/วินาที</span>
          </div>
          <div class="rx-readout">
            <div class="rx-counter" data-research></div>
            <span class="rx-plate">แต้มวิจัย</span>
          </div>
          <div class="rx-readout">
            <button type="button" class="rx-crank" data-crank aria-label="หมุนไดนาโมด้วยมือ">
              <svg viewBox="0 0 80 80" aria-hidden="true">
                <circle cx="40" cy="40" r="30" class="rx-crank-plate"/>
                <g class="rx-crank-arm">
                  <path d="M40 40L40 14" class="rx-crank-bar"/>
                  <circle cx="40" cy="14" r="8" class="rx-crank-knob"/>
                </g>
                <circle cx="40" cy="40" r="6" class="rx-ink-fill"/>
              </svg>
            </button>
            <span class="rx-plate">หมุนมือ +<b data-crank-value>1</b> cr</span>
          </div>
        </div>
      </section>

      <section class="rx-floor-wrap" aria-label="โรงงาน">
        <div class="rx-section-head">
          <h3>ผังโรงงาน</h3>
          <p class="rx-goal" data-goal></p>
        </div>
        <div class="rx-floor" data-floor></div>
      </section>

      <div class="rx-lower">
        <section aria-label="วิจัย">
          <h3>ห้องวิจัย</h3>
          <ul class="rx-list" data-techs></ul>
        </section>
        <section aria-label="ความสำเร็จ">
          <h3>ความสำเร็จ <span data-ach-count></span></h3>
          <ul class="rx-list rx-ach" data-achievements></ul>
          <button type="button" class="rx-text-button" data-reset>เริ่มเกมใหม่</button>
        </section>
      </div>

      <dialog class="rx-dialog" data-build-dialog>
        <form method="dialog">
          <header>
            <h3>สร้างอาคารในช่อง <span data-build-slot></span></h3>
            <button value="cancel" class="rx-text-button">ปิด</button>
          </header>
          <ul class="rx-list" data-build-list></ul>
        </form>
      </dialog>

      <dialog class="rx-dialog" data-away-dialog>
        <form method="dialog">
          <h3>ระหว่างที่ไม่อยู่</h3>
          <p data-away-text></p>
          <p class="rx-fine" data-away-rule></p>
          <button value="ok" class="rx-switch">รับผลผลิต</button>
        </form>
      </dialog>

      <div class="rx-toasts" aria-live="polite"></div>
    `;

    $("[data-crank]").addEventListener("click", onCrank);
    $("[data-reset]").addEventListener("click", onReset);
    drawGaugeFace();
  }

  /* Rendering */

  function renderAll() {
    renderFloor();
    renderTechs();
    renderAchievements();
    renderNumbers();
  }

  function renderNumbers() {
    const prod = E.production(state);
    const credits = fmt(state.credits);
    if (credits !== shown.credits) {
      shown.credits = credits;
      $("[data-credits]").replaceChildren(...[...credits].map((c) => el("span", "rx-tube", c)));
    }
    const research = fmt(state.research);
    if (research !== shown.research) {
      shown.research = research;
      $("[data-research]").textContent = research;
    }
    const rate = fmt(prod.cr);
    if (rate !== shown.rate) {
      shown.rate = rate;
      $("[data-rate]").textContent = rate;
      setNeedle(prod.cr);
    }
    $("[data-crank-value]").textContent = fmt(E.crankValue(state));
    $("[data-goal]").textContent = `เป้าหมายถัดไป: ${E.nextGoal(state)}`;

    for (const btn of view.querySelectorAll("[data-cost]")) {
      btn.disabled = state.credits < Number(btn.dataset.cost);
    }
    for (const btn of view.querySelectorAll("[data-rp]")) {
      btn.disabled = state.research < Number(btn.dataset.rp);
    }

    const real = document.getElementById("bahtPerHour")?.textContent?.trim();
    $("[data-real-rate]").textContent = real && real !== "–" ? `${real} ฿/ชม.` : "กำลังวัด…";
  }

  function renderFloor() {
    const floor = $("[data-floor]");
    const bays = state.floor.map((b, i) => (b ? builtBay(b, i) : emptyBay(i)));
    if (state.slots < E.MAX_SLOTS) bays.push(expandBay());
    floor.replaceChildren(...bays);
  }

  function emptyBay(i) {
    const bay = el("button", "rx-bay rx-bay-empty");
    bay.type = "button";
    bay.append(
      el("span", "rx-bay-no", String(i + 1).padStart(2, "0")),
      el("span", null, "ช่องว่าง กดเพื่อสร้าง"),
    );
    bay.addEventListener("click", () => openBuild(i));
    return bay;
  }

  function expandBay() {
    const bay = el("div", "rx-bay rx-bay-expand");
    const cost = E.slotCost(state);
    const btn = el("button", "rx-switch", `ต่อเติมโรงงาน ${fmt(cost)} cr`);
    btn.type = "button";
    btn.dataset.cost = cost;
    btn.addEventListener("click", () => {
      if (E.expand(state)) {
        renderFloor();
        renderNumbers();
      }
    });
    bay.append(el("span", null, `เพิ่มช่องที่ ${state.slots + 1}`), btn);
    return bay;
  }

  function builtBay(b, i) {
    const def = E.BUILDINGS[b.t];
    const out = E.output(state, b);
    const bay = el("article", `rx-bay rx-bay-built rx-type-${b.t}`);
    bay.dataset.slot = i;
    // Faster machines at higher levels, capped so nothing turns into a blur.
    bay.style.setProperty("--speed", String(Math.min(3, 1 + (b.lvl - 1) * 0.25)));

    const head = el("header", "rx-bay-head");
    head.append(el("span", "rx-bay-no", String(i + 1).padStart(2, "0")), el("h4", null, def.name));
    head.append(el("span", "rx-lamp-dot"));

    const art = el("div", "rx-art");
    art.innerHTML = ART[b.t];

    const stats = el("p", "rx-bay-stats");
    stats.append(el("span", "rx-level", `เลเวล ${b.lvl}`));
    if (out.cr) stats.append(el("span", null, `${fmt(out.cr)} cr/วิ`));
    if (out.rp) stats.append(el("span", null, `${fmt(out.rp)} วิจัย/วิ`));
    if (b.t === "battery")
      stats.append(el("span", null, `เสริม +${Math.round(b.lvl * def.boost * 100)}%`));

    const cost = E.upgradeCost(b);
    const up = el("button", "rx-switch", `อัปเกรด ${fmt(cost)} cr`);
    up.type = "button";
    up.dataset.cost = cost;
    up.addEventListener("click", () => {
      if (!E.upgrade(state, i)) return;
      renderFloor();
      renderNumbers();
      const fresh = $(`[data-slot="${i}"]`);
      fresh?.classList.add("is-upgraded");
      fresh?.querySelector(".rx-switch")?.focus();
    });

    const scrap = el("button", "rx-text-button rx-scrap", "รื้อ");
    scrap.type = "button";
    scrap.title = "รื้ออาคารนี้ทิ้ง ไม่ได้เครดิตคืน";
    scrap.addEventListener("click", () => {
      if (scrap.dataset.armed) {
        E.demolish(state, i);
        renderFloor();
        renderNumbers();
        return;
      }
      scrap.dataset.armed = "1";
      scrap.textContent = "กดอีกครั้งเพื่อรื้อ";
      setTimeout(() => {
        delete scrap.dataset.armed;
        scrap.textContent = "รื้อ";
      }, 3000);
    });

    const actions = el("div", "rx-bay-actions");
    actions.append(up, scrap);
    bay.append(head, art, stats, actions);
    return bay;
  }

  function openBuild(slot) {
    const dialog = $("[data-build-dialog]");
    $("[data-build-slot]").textContent = String(slot + 1).padStart(2, "0");
    const list = $("[data-build-list]");
    list.replaceChildren(
      ...Object.entries(E.BUILDINGS).map(([type, def]) => {
        const li = el("li", "rx-option");
        const art = el("div", "rx-art rx-art-small");
        art.innerHTML = ART[type];
        const text = el("div");
        text.append(el("strong", null, def.name), el("p", null, def.blurb));
        const yieldText = def.cr
          ? `${fmt(def.cr)} cr/วิ ต่อเลเวล`
          : def.rp
            ? `${def.rp} วิจัย/วิ ต่อเลเวล`
            : "";
        if (yieldText) text.append(el("p", "rx-fine", yieldText));

        const needs = E.locked(state, type);
        let btn;
        if (needs) {
          btn = el("span", "rx-fine rx-locked", `ต้องวิจัย "${needs.name}" ก่อน`);
        } else {
          const cost = E.buildCost(state, type);
          btn = el("button", "rx-switch", `สร้าง ${fmt(cost)} cr`);
          btn.type = "button";
          btn.dataset.cost = cost;
          btn.disabled = state.credits < cost;
          btn.addEventListener("click", () => {
            if (!E.build(state, slot, type)) return;
            dialog.close();
            renderFloor();
            renderNumbers();
            $(`[data-slot="${slot}"]`)?.classList.add("is-new");
          });
        }
        li.append(art, text, btn);
        return li;
      }),
    );
    dialog.showModal();
  }

  function renderTechs() {
    const list = $("[data-techs]");
    list.replaceChildren(
      ...E.TECHS.map((tech) => {
        const owned = state.techs.includes(tech.id);
        const li = el("li", owned ? "rx-tech is-owned" : "rx-tech");
        const text = el("div");
        text.append(el("strong", null, tech.name), el("p", null, tech.text));
        li.append(text);
        if (owned) {
          li.append(el("span", "rx-fine", "ติดตั้งแล้ว"));
        } else if (!E.techAvailable(state, tech)) {
          const need = E.TECHS.find((t) => t.id === tech.needs);
          li.append(el("span", "rx-fine rx-locked", `ต้องมี "${need.name}" ก่อน`));
        } else {
          const btn = el("button", "rx-switch", `วิจัย ${tech.rp} แต้ม`);
          btn.type = "button";
          btn.dataset.rp = tech.rp;
          btn.disabled = state.research < tech.rp;
          btn.addEventListener("click", () => {
            if (!E.research(state, tech.id)) return;
            toast(`วิจัยสำเร็จ: ${tech.name}`);
            renderAll();
          });
          li.append(btn);
        }
        return li;
      }),
    );
  }

  function renderAchievements() {
    $("[data-ach-count]").textContent = `${state.ach.length}/${E.ACHIEVEMENTS.length}`;
    $("[data-achievements]").replaceChildren(
      ...E.ACHIEVEMENTS.map((a) => {
        const got = state.ach.includes(a.id);
        const li = el("li", got ? "rx-badge is-earned" : "rx-badge");
        li.append(el("strong", null, a.name), el("p", null, a.text));
        return li;
      }),
    );
  }

  /* Gauge */

  const GX = 80;
  const GY = 82;
  const GR = 64;
  const DECADES = 7;

  function gaugeAngle(value) {
    return Math.min(1, Math.log10(value + 1) / DECADES) * 180 - 90;
  }

  function drawGaugeFace() {
    const svg = $(".rx-gauge");
    const parts = [
      `<path d="M${GX - GR} ${GY}A${GR} ${GR} 0 0 1 ${GX + GR} ${GY}" class="rx-gauge-arc"/>`,
    ];
    const labels = ["0", "10", "100", "1K", "10K", "100K", "1M", "10M"];
    labels.forEach((label, i) => {
      const a = ((i / DECADES) * 180 - 90) * (Math.PI / 180);
      const [sx, sy] = [GX + Math.sin(a) * GR, GY - Math.cos(a) * GR];
      const [ex, ey] = [GX + Math.sin(a) * (GR - 8), GY - Math.cos(a) * (GR - 8)];
      const [lx, ly] = [GX + Math.sin(a) * (GR - 18), GY - Math.cos(a) * (GR - 18)];
      parts.push(`<path d="M${sx} ${sy}L${ex} ${ey}" class="rx-gauge-tick"/>`);
      parts.push(
        `<text x="${lx}" y="${ly}" class="rx-gauge-label" text-anchor="middle" dominant-baseline="central">${label}</text>`,
      );
    });
    parts.push(`<path d="M${GX} ${GY}L${GX} ${GY - GR + 6}" class="rx-needle"/>`);
    parts.push(`<circle cx="${GX}" cy="${GY}" r="5" class="rx-ink-fill"/>`);
    svg.innerHTML = parts.join("");
    svg.querySelector(".rx-needle").style.transformOrigin = `${GX}px ${GY}px`;
    setNeedle(0);
  }

  function setNeedle(value) {
    const needle = $(".rx-needle");
    if (needle) needle.style.transform = `rotate(${gaugeAngle(value)}deg)`;
  }

  /* Interactions */

  let crankTurns = 0;

  function onCrank(e) {
    const gain = E.crank(state);
    crankTurns += 1;
    $(".rx-crank-arm").style.transform = `rotate(${crankTurns * 360}deg)`;
    const pop = el("span", "rx-pop", `+${fmt(gain)}`);
    const box = e.currentTarget.getBoundingClientRect();
    pop.style.left = `${box.width / 2}px`;
    e.currentTarget.append(pop);
    pop.addEventListener("animationend", () => pop.remove());
    renderNumbers();
  }

  function onReset(e) {
    const btn = e.currentTarget;
    if (!btn.dataset.armed) {
      btn.dataset.armed = "1";
      btn.textContent = "แน่ใจไหม กดอีกครั้งเพื่อลบความคืบหน้าทั้งหมด";
      setTimeout(() => {
        delete btn.dataset.armed;
        btn.textContent = "เริ่มเกมใหม่";
      }, 4000);
      return;
    }
    state = E.newGame(Date.now());
    shown = { credits: "", research: "", rate: "" };
    renderAll();
    save();
    btn.textContent = "เริ่มเกมใหม่";
    delete btn.dataset.armed;
  }

  function showAway(away) {
    const hours = Math.floor(away.seconds / 3600);
    const mins = Math.round((away.seconds % 3600) / 60);
    const span = hours ? `${hours} ชม. ${mins} นาที` : `${mins} นาที`;
    let text = `โรงงานเดินเครื่องต่อ ${span} ผลิตได้ ${fmt(away.credits)} cr`;
    if (away.research >= 0.1) text += ` และ ${fmt(away.research)} แต้มวิจัย`;
    $("[data-away-text]").textContent = text;
    $("[data-away-rule]").textContent =
      `ตอนไม่อยู่ โรงงานผลิตได้ ${Math.round(away.efficiency * 100)}% นานสุด ${away.capHours} ชม. ` +
      "สร้างแบตเตอรี่หรือวิจัยห้องควบคุมอัตโนมัติเพื่อเพิ่ม";
    const dialog = $("[data-away-dialog]");
    dialog.addEventListener(
      "close",
      () => {
        E.claimOffline(state, away);
        renderAll();
        save();
      },
      { once: true },
    );
    dialog.showModal();
  }

  function toast(text) {
    const box = $(".rx-toasts");
    const t = el("p", "rx-toast", text);
    box.append(t);
    setTimeout(() => t.remove(), 3500);
    renderAchievements();
  }
})();
