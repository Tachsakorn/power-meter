"use strict";

const POLL_MS = 2000;
const SVG_NS = "http://www.w3.org/2000/svg";
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");

const money = new Intl.NumberFormat("th-TH", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const whole = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 0 });
const oneDp = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 1 });
const kwh = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
const weekday = new Intl.DateTimeFormat("th-TH", { weekday: "short" });
const longDay = new Intl.DateTimeFormat("th-TH", {
  weekday: "long",
  day: "numeric",
  month: "short",
});
const clock = new Intl.DateTimeFormat("th-TH", { hour: "2-digit", minute: "2-digit" });

const $ = (id) => document.getElementById(id);

function svg(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// Numbers glide to their new value so a 2-second update doesn't look like a flicker.
function tween(node, to, format) {
  const from = node._value ?? to;
  node._value = to;
  if (reduceMotion.matches || from === to) {
    node.textContent = format(to);
    return;
  }
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / 600);
    const eased = 1 - (1 - t) ** 3;
    node.textContent = format(from + (to - from) * eased);
    if (t < 1 && node._value === to) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* Time helpers */

function hourOf(ms) {
  const d = new Date(ms);
  return d.getHours() + d.getMinutes() / 60;
}

function whenLabel(state) {
  const at = new Date(state.next_change);
  const time = `${clock.format(at)} น.`;
  return state.next_change - state.now > 20 * 3600 * 1000 ? `${weekday.format(at)} ${time}` : time;
}

function countdown(ms) {
  const mins = Math.max(0, Math.round(ms / 60000));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h >= 24) return { big: `${Math.floor(h / 24)} วัน`, small: h % 24 ? `${h % 24} ชม.` : "" };
  if (h >= 1) return { big: `${h}:${String(m).padStart(2, "0")}`, small: "ชม." };
  return { big: `${m}`, small: "นาที" };
}

/* Dial: a 24-hour clock with noon at the top and midnight at the bottom */

const C = 110;
const R = 88;

function polar(hour, r) {
  const a = ((hour - 12) / 24) * 2 * Math.PI;
  return [C + r * Math.sin(a), C - r * Math.cos(a)];
}

function arc(from, to, r) {
  const span = (((to - from) % 24) + 24) % 24 || 24;
  const end = from + Math.min(span, 23.99);
  const [x1, y1] = polar(from, r);
  const [x2, y2] = polar(end, r);
  return `M ${x1} ${y1} A ${r} ${r} 0 ${span > 12 ? 1 : 0} 1 ${x2} ${y2}`;
}

function sun(x, y, size) {
  const g = svg("g", { class: "glyph-sun", transform: `translate(${x} ${y})` });
  g.append(svg("circle", { r: size * 0.32 }));
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * 2 * Math.PI;
    const [cx, cy] = [Math.cos(a) * size * 0.58, Math.sin(a) * size * 0.58];
    g.append(svg("circle", { cx, cy, r: size * 0.08 }));
  }
  return g;
}

function moon(x, y, size) {
  const r = size * 0.42;
  const d = `M ${r * 0.2} ${-r} A ${r} ${r} 0 1 0 ${r} ${r * 0.35} A ${r * 0.8} ${r * 0.8} 0 1 1 ${r * 0.2} ${-r} Z`;
  return svg("path", { d, class: "glyph-moon", transform: `translate(${x} ${y})` });
}

function drawDial(state) {
  const dial = $("dial");
  dial.replaceChildren();
  dial.append(svg("circle", { cx: C, cy: C, r: R, class: "ring-base", "stroke-width": 16 }));

  if (state.is_tou) {
    dial.append(svg("circle", { cx: C, cy: C, r: R, class: "ring-off", "stroke-width": 8 }));
    if (!state.off_peak_all_day) {
      const [start, end] = state.peak_hours;
      dial.append(svg("path", { d: arc(start, end, R), class: "ring-peak", "stroke-width": 16 }));
      for (const h of [start, end]) {
        const [x1, y1] = polar(h, R - 10);
        const [x2, y2] = polar(h, R + 10);
        const [lx, ly] = polar(h, R + 21);
        dial.append(svg("line", { x1, y1, x2, y2, class: "ring-tick" }));
        const label = svg("text", {
          x: lx,
          y: ly,
          class: "ring-label",
          "text-anchor": "middle",
          "dominant-baseline": "central",
        });
        label.textContent = `${String(h).padStart(2, "0")}:00`;
        dial.append(label);
      }
    }
  }

  dial.append(sun(...polar(12, R - 27), 16), moon(...polar(0, R - 27), 15));

  const now = hourOf(state.now);
  const hours = (state.next_change - state.now) / 3600000;
  // Beyond most of a day the arc would wrap into a full circle and say nothing.
  if (state.next_change != null && hours < 20) {
    dial.append(
      svg("path", {
        d: arc(now, now + Math.min(hours, 23.99), R - 16),
        class: "ring-remaining",
        "stroke-width": 3,
      }),
    );
  }
  const [mx, my] = polar(now, R);
  dial.append(svg("circle", { cx: mx, cy: my, r: 7, class: "now-marker" }));

  const center = $("dialCenter");
  center.replaceChildren();
  if (state.next_change == null) {
    center.append(el("span", "dial-kicker", "ค่าไฟ"));
    const big = el("span", "dial-big", money.format(state.price));
    big.append(el("small", null, "฿/หน่วย"));
    center.append(big);
    return;
  }
  const cheaper = state.next_price < state.price;
  const { big, small } = countdown(state.next_change - state.now);
  const bigNode = el("span", "dial-big", big);
  if (small) bigNode.append(el("small", null, small));
  center.append(
    el("span", "dial-kicker", cheaper ? "ถูกลงในอีก" : "แพงขึ้นในอีก"),
    bigNode,
    el("span", "dial-at", whenLabel(state)),
  );
}

/* Header, hero and totals */

function drawPeriod(state) {
  const box = $("period");
  box.replaceChildren();
  const icon = svg("svg", { viewBox: "-10 -10 20 20", "aria-hidden": "true" });
  if (state.is_tou) {
    icon.append(state.period === "peak" ? sun(0, 0, 16) : moon(0, 0, 16));
    box.append(icon);
  }

  let text = "อัตราปกติ";
  if (state.is_tou && state.period === "peak") {
    text = `ช่วงแพง ถึง ${clock.format(new Date(state.next_change))} น.`;
  } else if (state.is_tou && state.off_peak_all_day) {
    text = state.holiday ? "ถูกทั้งวัน (วันหยุดราชการ)" : "ถูกทั้งวัน (เสาร์–อาทิตย์)";
  } else if (state.is_tou) {
    text = `ช่วงถูก ถึง ${whenLabel(state)}`;
  }
  box.append(text);
}

function drawRate(state) {
  if (state.watts == null) {
    $("bahtPerHour").textContent = "–";
    $("watts").textContent = "กำลังเริ่มวัด…";
    $("estimate").hidden = true;
  } else {
    tween($("bahtPerHour"), state.baht_per_hour, (v) => money.format(v));
    tween($("watts"), state.watts, (v) => `${oneDp.format(v)} วัตต์`);
    $("estimate").hidden = state.measured;
  }

  const price = $("price");
  price.replaceChildren("ค่าไฟตอนนี้ ", el("strong", null, `${money.format(state.price)} ฿/หน่วย`));

  const advice = $("advice");
  advice.hidden = !state.is_tou;
  if (!state.is_tou) return;
  if (state.next_price < state.price) {
    const saving = Math.round((1 - state.next_price / state.price) * 100);
    advice.textContent = `งานหนัก ๆ อย่างเกมหรือเรนเดอร์ ถ้ารอถึง ${whenLabel(state)} ค่าไฟจะถูกลง ${saving}%`;
  } else {
    advice.textContent = "ตอนนี้ค่าไฟถูก งานหนัก ๆ ทำตอนนี้คุ้มที่สุด";
  }
}

function drawTotals(state) {
  tween($("today"), state.today_baht, (v) => `${money.format(v)} ฿`);
  $("todaySub").textContent = `${kwh.format(state.today_kwh)} kWh`;
  tween($("month"), state.month_baht, (v) => `${money.format(v)} ฿`);
  $("monthSub").textContent = `${kwh.format(state.month_kwh)} kWh`;

  if (state.month_days >= 1) {
    tween($("projection"), state.month_projection, (v) => `≈ ${whole.format(v)} ฿`);
    $("projectionSub").textContent = `จากค่าเฉลี่ย ${state.month_days} วันที่วัดไว้`;
  } else {
    $("projection").textContent = "–";
    $("projectionSub").textContent = "รอข้อมูลอย่างน้อย 1 วัน";
  }
}

/* Tooltip */

function showTip(rows, x, y) {
  const tip = $("tip");
  tip.replaceChildren(...rows);
  tip.hidden = false;
  const { width, height } = tip.getBoundingClientRect();
  const left = Math.min(Math.max(8, x - width / 2), innerWidth - width - 8);
  const top = y - height - 12 < 8 ? y + 16 : y - height - 12;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function hideTip() {
  $("tip").hidden = true;
}

function tipRow(color, text) {
  const row = el("div", "row", text);
  row.style.setProperty("--key", color);
  return row;
}

/* Power over the last 10 minutes */

function niceStep(max) {
  const raw = max / 2;
  const mag = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
}

function drawPowerChart(history) {
  const box = $("powerChart");
  box.onpointermove = box.onpointerleave = null;
  if (history.length < 2) {
    box.replaceChildren(el("p", "empty", "กราฟจะขึ้นหลังจากวัดไปสักครู่"));
    return;
  }

  const w = box.clientWidth;
  const h = box.clientHeight;
  const right = 64;
  const top = 10;
  const bottom = 20;
  const step = niceStep(Math.max(...history.map(([, v]) => v)));
  const max = step * Math.ceil(Math.max(...history.map(([, v]) => v)) / step);
  const t0 = history[0][0];
  const span = history.at(-1)[0] - t0 || 1;
  const x = (t) => ((t - t0) / span) * (w - right);
  const y = (v) => top + (1 - v / max) * (h - top - bottom);
  const base = h - bottom;

  const chart = svg("svg", { viewBox: `0 0 ${w} ${h}` });
  for (let v = step; v <= max; v += step) {
    chart.append(svg("line", { x1: 0, x2: w - right, y1: y(v), y2: y(v), class: "chart-grid" }));
    const label = svg("text", { x: 0, y: y(v) - 4, class: "chart-label" });
    label.textContent = `${whole.format(v)} W`;
    chart.append(label);
  }
  chart.append(svg("line", { x1: 0, x2: w - right, y1: base, y2: base, class: "chart-grid" }));

  const points = history.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`);
  const lastX = x(history.at(-1)[0]);
  chart.append(
    svg("path", {
      d: `M 0 ${base} L ${points.join(" L ")} L ${lastX} ${base} Z`,
      class: "chart-area",
    }),
    svg("polyline", { points: points.join(" "), class: "chart-line" }),
  );

  const [, lastW] = history.at(-1);
  chart.append(svg("circle", { cx: lastX, cy: y(lastW), r: 4, class: "chart-end" }));
  const now = svg("text", {
    x: lastX + 10,
    y: y(lastW),
    class: "chart-value",
    "dominant-baseline": "central",
  });
  now.textContent = `${whole.format(lastW)} W`;
  chart.append(now);

  const start = svg("text", { x: 0, y: h, class: "chart-label" });
  start.textContent = clock.format(new Date(t0));
  const end = svg("text", { x: lastX, y: h, class: "chart-label", "text-anchor": "end" });
  end.textContent = "ตอนนี้";
  chart.append(start, end);

  const cross = svg("line", { y1: top, y2: base, class: "chart-cross", visibility: "hidden" });
  const dot = svg("circle", { r: 4, class: "chart-end", visibility: "hidden" });
  chart.append(cross, dot);
  box.replaceChildren(chart);

  box.onpointermove = (e) => {
    const rect = box.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const target = t0 + (Math.min(px, w - right) / (w - right)) * span;
    let best = history[0];
    for (const p of history) if (Math.abs(p[0] - target) < Math.abs(best[0] - target)) best = p;
    const bx = x(best[0]);
    const by = y(best[1]);
    cross.setAttribute("x1", bx);
    cross.setAttribute("x2", bx);
    dot.setAttribute("cx", bx);
    dot.setAttribute("cy", by);
    cross.setAttribute("visibility", "visible");
    dot.setAttribute("visibility", "visible");
    const strong = el("strong", null, `${oneDp.format(best[1])} W`);
    showTip(
      [strong, el("div", null, `${clock.format(new Date(best[0]))} น.`)],
      rect.left + bx,
      rect.top + by,
    );
  };
  box.onpointerleave = () => {
    cross.setAttribute("visibility", "hidden");
    dot.setAttribute("visibility", "hidden");
    hideTip();
  };
}

/* Cost over the last 7 days */

function drawDays(days, isTou) {
  const box = $("days");
  const today = days.at(-1).date;
  const max = Math.max(...days.map((d) => d.peak_baht + d.off_baht), 0.01);
  const room = box.clientHeight - 30;
  $("legend").hidden = !isTou;

  const styles = getComputedStyle(document.body);
  const peakColor = styles.getPropertyValue("--peak");
  const offColor = styles.getPropertyValue("--off");

  const columns = days.map((d) => {
    const total = d.peak_baht + d.off_baht;
    const date = new Date(d.date);
    const dayName = d.date === today ? "วันนี้" : longDay.format(date);
    const col = el("div", "day");
    col.tabIndex = 0;
    col.setAttribute("role", "img");
    col.setAttribute(
      "aria-label",
      `${dayName} ${money.format(total)} บาท ช่วงแพง ${money.format(d.peak_baht)} ช่วงถูก ${money.format(d.off_baht)}`,
    );

    const stack = el("div", "day-stack");
    for (const [cls, value] of [
      ["seg-off", d.off_baht],
      ["seg-peak", d.peak_baht],
    ]) {
      if (value <= 0) continue;
      const seg = el("div", cls);
      seg.style.height = `${Math.max(2, (value / max) * room)}px`;
      stack.append(seg);
    }
    col.append(el("span", "day-baht", total > 0 ? money.format(total) : "–"), stack);

    const tipFor = (x, y) => {
      const rows = [el("strong", null, `${money.format(total)} ฿`), el("div", null, dayName)];
      if (isTou) {
        rows.push(
          tipRow(
            peakColor,
            `ช่วงแพง ${money.format(d.peak_baht)} ฿ (${kwh.format(d.peak_kwh)} kWh)`,
          ),
          tipRow(offColor, `ช่วงถูก ${money.format(d.off_baht)} ฿ (${kwh.format(d.off_kwh)} kWh)`),
        );
      } else {
        rows.push(el("div", null, `${kwh.format(d.peak_kwh + d.off_kwh)} kWh`));
      }
      showTip(rows, x, y);
    };
    col.onpointermove = (e) => tipFor(e.clientX, e.clientY);
    col.onpointerleave = hideTip;
    col.onfocus = () => {
      const r = stack.getBoundingClientRect();
      tipFor(r.left + r.width / 2, r.top);
    };
    col.onblur = hideTip;
    return col;
  });
  box.replaceChildren(...columns);

  let labels = box.nextElementSibling;
  if (!labels?.classList.contains("day-labels")) {
    labels = el("div", "day-labels");
    labels.setAttribute("aria-hidden", "true");
    box.after(labels);
  }
  labels.replaceChildren(
    ...days.map((d) =>
      d.date === today
        ? el("span", "is-today", "วันนี้")
        : el("span", null, weekday.format(new Date(d.date))),
    ),
  );
}

/* Sources panel */

const SOURCE_TEXT = {
  measured: "วัดจริง",
  load: "ประมาณจาก % ใช้งาน",
  fixed: "ค่าคงที่",
  parts: "ประมาณจากชิ้นส่วน",
  none: "ไม่พบ",
};

function percent(util) {
  return util == null ? "" : ` (ใช้งาน ${Math.round(util * 100)}%)`;
}

function drawSources(state) {
  const hw = state.hardware;
  const { battery, cpu, gpu } = state.sensors;

  let note;
  if (state.measured) {
    note = "ตอนนี้ถอดปลั๊กอยู่ แอปอ่านไฟทั้งเครื่องจากแบตได้ตรง ๆ ตัวเลขแม่นที่สุด";
  } else if (hw.laptop) {
    note = "ตอนเสียบปลั๊ก แอปรวมไฟจาก CPU, การ์ดจอ และส่วนอื่น ๆ ของเครื่อง ตัวเลขจึงเป็นค่าประมาณ";
  } else {
    note =
      "คอมตั้งโต๊ะไม่มีแบตให้วัดทั้งเครื่อง แอปเลยรวมไฟจาก CPU, การ์ดจอ และส่วนอื่น ๆ " +
      "ตามการใช้งานจริง ตัวเลขจึงเป็นค่าประมาณ ไม่รวมจอ";
  }
  $("sourceNote").textContent = note;

  const rows = [
    {
      name: "CPU",
      source: cpu.source,
      detail: `${hw.cpu}${percent(cpu.util)}${cpu.source === "load" ? `, ราว ${Math.round(hw.cpu_tdp)} W เต็มกำลัง` : ""}`,
    },
    {
      name: "การ์ดจอ",
      source: gpu.source,
      detail: hw.gpu
        ? `${hw.gpu}${percent(gpu.util)}${gpu.source === "load" ? `, ราว ${Math.round(hw.gpu_board)} W เต็มกำลัง` : ""}`
        : "ใช้กราฟิกในตัว CPU (รวมอยู่ในไฟ CPU แล้ว)",
    },
    {
      name: "เมนบอร์ด, RAM, พัดลม, ไดรฟ์",
      source: "parts",
      detail:
        `ราว ${Math.round(hw.base_watts)} W จากชิ้นส่วนที่ตรวจเจอ` +
        (hw.ram_modules ? ` (RAM ${hw.ram_modules} แถว, ไดรฟ์ ${hw.drives.length} ตัว)` : ""),
    },
  ];
  if (hw.laptop) {
    rows.unshift({ name: "แบตเตอรี่", source: battery.source, detail: battery.detail });
  }

  $("sensors").replaceChildren(
    ...rows.map(({ name, source, detail }) => {
      const li = el("li", source === "measured" ? "sensor is-on" : "sensor");
      li.append(el("span", null, name), el("span", null, SOURCE_TEXT[source] ?? source));
      if (detail) li.append(el("small", "sensor-detail", detail));
      return li;
    }),
  );
  $("cpuTip").hidden = cpu.source === "measured";

  const meter = state.meter === "tou" ? "มิเตอร์ TOU" : "มิเตอร์ปกติ";
  $("meterInfo").textContent =
    `${meter}, Ft ${state.ft.toFixed(4)} บาท/หน่วย ` +
    `(อัตราค่าไฟอัปเดตเอง ข้อมูลวันที่ ${state.rates_updated})`;
}

/* Meter type: asked once, changeable from the sources panel */

let askingMeter = false;

function drawSetup(state) {
  $("meterSetup").hidden = state.meter_chosen && !askingMeter;
}

for (const btn of document.querySelectorAll("[data-meter]")) {
  btn.addEventListener("click", async () => {
    askingMeter = false;
    $("meterSetup").hidden = true;
    await window.pywebview.api.set_meter(btn.dataset.meter);
    render(await window.pywebview.api.get_state());
  });
}

$("changeMeter").addEventListener("click", () => {
  askingMeter = true;
  $("meterSetup").hidden = false;
  document.querySelector(".info").open = false;
  $("meterSetup").querySelector("button").focus();
});

let latest = null;

function render(state) {
  latest = state;
  document.body.dataset.period = state.is_tou ? state.period : "flat";
  drawPeriod(state);
  drawDial(state);
  drawRate(state);
  drawTotals(state);
  drawPowerChart(state.history);
  drawDays(state.days, state.is_tou);
  drawSources(state);
  drawSetup(state);
}

async function poll() {
  try {
    render(await window.pywebview.api.get_state());
  } catch (err) {
    console.error("get_state failed", err);
  } finally {
    setTimeout(poll, POLL_MS);
  }
}

$("compactToggle").addEventListener("click", async (e) => {
  const compact = !document.body.classList.contains("compact");
  document.body.classList.toggle("compact", compact);
  e.currentTarget.setAttribute("aria-pressed", String(compact));
  e.currentTarget.textContent = compact ? "ขยาย" : "ย่อเป็นวิดเจ็ต";
  hideTip();
  await window.pywebview.api.set_compact(compact);
});

window.addEventListener("pywebviewready", poll);
window.addEventListener("resize", () => latest && render(latest));
