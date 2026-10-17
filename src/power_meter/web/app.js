"use strict";

const POLL_MS = 2000;
const SVG_NS = "http://www.w3.org/2000/svg";

const baht = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const watts1 = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 1 });
const kwh3 = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const weekday = new Intl.DateTimeFormat("th-TH", { weekday: "short" });
const clock = new Intl.DateTimeFormat("th-TH", { hour: "2-digit", minute: "2-digit" });

const $ = (id) => document.getElementById(id);

function svg(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// Noon sits at the top of the dial, midnight at the bottom.
function polar(hour, r, c = 100) {
  const a = ((hour - 12) / 24) * 2 * Math.PI;
  return [c + r * Math.sin(a), c - r * Math.cos(a)];
}

function arc(fromHour, toHour, r) {
  const [x1, y1] = polar(fromHour, r);
  const [x2, y2] = polar(toHour, r);
  const large = toHour - fromHour > 12 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

function drawDial(state) {
  const dial = $("dial");
  const r = 84;
  const width = 14;
  dial.replaceChildren();

  dial.append(svg("circle", { cx: 100, cy: 100, r, class: "ring-base", "stroke-width": width }));

  if (state.is_tou) {
    dial.append(svg("circle", { cx: 100, cy: 100, r, class: "ring-off", "stroke-width": width }));
    if (!state.off_peak_all_day) {
      const [start, end] = state.peak_hours;
      dial.append(
        svg("path", { d: arc(start, end, r), class: "ring-peak", "stroke-width": width }),
      );
    }
  }

  for (const h of [0, 6, 12, 18]) {
    const [x, y] = polar(h, r - 22);
    const label = svg("text", {
      x,
      y,
      class: "tick-label",
      "text-anchor": "middle",
      "dominant-baseline": "central",
    });
    label.textContent = String(h).padStart(2, "0");
    dial.append(label);
  }

  const now = new Date(state.now);
  const hour = now.getHours() + now.getMinutes() / 60;
  const [hx, hy] = polar(hour, r);
  const [ix, iy] = polar(hour, r - 30);
  dial.append(svg("line", { x1: ix, y1: iy, x2: hx, y2: hy, class: "hand" }));
  dial.append(svg("circle", { cx: hx, cy: hy, r: 6, class: "hand-dot" }));

  $("dialPrice").textContent = baht.format(state.price);
}

function describeNextChange(state) {
  const el = $("nextChange");
  if (state.next_change == null) {
    el.textContent = "";
    return;
  }
  const mins = Math.max(0, Math.round((state.next_change - state.now) / 60000));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const wait =
    h >= 24 ? `${Math.floor(h / 24)} วัน ${h % 24} ชม.` : h ? `${h} ชม. ${m} นาที` : `${m} นาที`;
  const at = clock.format(new Date(state.next_change));
  const cheaper = state.next_price < state.price;
  const verb = cheaper ? "ราคาลดเหลือ" : "ราคาขึ้นเป็น";

  el.replaceChildren();
  el.append(`อีก ${wait} (${at} น.) ${verb} `);
  const price = document.createElement("strong");
  price.textContent = `${baht.format(state.next_price)} บาท/หน่วย`;
  el.append(price);
  if (cheaper && state.baht_per_hour) {
    const saving = 1 - state.next_price / state.price;
    el.append(` งานหนัก ๆ รอได้ก็ประหยัดไป ${Math.round(saving * 100)}%`);
  }
}

function periodText(state) {
  if (!state.is_tou) return "อัตราปกติ";
  if (state.period === "peak") return "ช่วงแพง";
  return state.off_peak_all_day ? "ช่วงถูก ทั้งวัน" : "ช่วงถูก";
}

function drawPowerChart(history) {
  const box = $("powerChart");
  if (history.length < 2) {
    box.innerHTML = '<p class="empty">กราฟจะขึ้นหลังจากวัดไปสักครู่</p>';
    return;
  }

  const w = box.clientWidth;
  const h = box.clientHeight;
  const padTop = 8;
  const padBottom = 18;
  const max = Math.max(...history.map(([, v]) => v)) * 1.15 || 1;
  const t0 = history[0][0];
  const span = history.at(-1)[0] - t0 || 1;
  const x = (t) => ((t - t0) / span) * w;
  const y = (v) => padTop + (1 - v / max) * (h - padTop - padBottom);

  const points = history.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`);
  const base = h - padBottom;

  const chart = svg("svg", { viewBox: `0 0 ${w} ${h}` });
  chart.append(svg("line", { x1: 0, x2: w, y1: base, y2: base, class: "chart-grid" }));
  chart.append(
    svg("path", { d: `M 0 ${base} L ${points.join(" L ")} L ${w} ${base} Z`, class: "chart-area" }),
  );
  chart.append(svg("polyline", { points: points.join(" "), class: "chart-line" }));

  const peak = svg("text", {
    x: 0,
    y: padTop + 2,
    class: "chart-label",
    "dominant-baseline": "hanging",
  });
  peak.textContent = `สูงสุด ${watts1.format(max / 1.15)} W`;
  chart.append(peak);

  const start = svg("text", { x: 0, y: h, class: "chart-label" });
  start.textContent = clock.format(new Date(t0));
  const end = svg("text", { x: w, y: h, class: "chart-label", "text-anchor": "end" });
  end.textContent = "ตอนนี้";
  chart.append(start, end);

  box.replaceChildren(chart);
}

function drawDayBars(days, isTou) {
  const box = $("dayBars");
  const max = Math.max(...days.map((d) => d.peak_kwh + d.off_kwh), 0.001);
  const today = days.at(-1).date;
  $("legend").hidden = !isTou;

  box.replaceChildren(
    ...days.map((d) => {
      const bar = document.createElement("div");
      bar.className = d.date === today ? "bar is-today" : "bar";

      const value = document.createElement("span");
      value.className = "bar-baht";
      value.textContent = d.baht > 0 ? baht.format(d.baht) : "–";

      const track = document.createElement("div");
      track.className = "bar-track";
      track.title = `${kwh3.format(d.peak_kwh + d.off_kwh)} kWh`;
      for (const [cls, kwh] of [
        ["bar-off", d.off_kwh],
        ["bar-peak", d.peak_kwh],
      ]) {
        const seg = document.createElement("div");
        seg.className = cls;
        seg.style.height = `${(kwh / max) * 100}%`;
        track.append(seg);
      }

      const label = document.createElement("span");
      label.className = "bar-day";
      label.textContent = d.date === today ? "วันนี้" : weekday.format(new Date(d.date));

      bar.append(value, track, label);
      return bar;
    }),
  );
}

function drawSensors(sensors) {
  const items = [
    ["แบตเตอรี่", sensors.battery],
    ["GPU", sensors.gpu],
    ["CPU", sensors.cpu],
  ];
  const box = $("sensors");
  box.replaceChildren(
    ...items.map(([name, on]) => {
      const el = document.createElement("span");
      el.className = on ? "sensor is-on" : "sensor";
      el.textContent = `${name} ${on ? "วัดได้" : "ไม่พบ"}`;
      return el;
    }),
  );
  if (!sensors.cpu) {
    const tip = document.createElement("span");
    tip.textContent = "เปิด LibreHardwareMonitor เพื่อวัดไฟ CPU จริง";
    box.append(tip);
  }
}

function render(state) {
  document.body.dataset.period = state.is_tou ? state.period : "flat";
  $("periodChip").textContent = periodText(state);

  drawDial(state);
  describeNextChange(state);

  if (state.watts == null) {
    $("bahtPerHour").textContent = "–";
    $("watts").textContent = "กำลังเริ่มวัด…";
    $("source").hidden = true;
  } else {
    $("bahtPerHour").textContent = baht.format(state.baht_per_hour);
    $("watts").textContent = `${watts1.format(state.watts)} วัตต์`;
    $("source").hidden = false;
    $("source").textContent = state.measured ? "วัดจากแบต" : "ค่าประมาณ";
    $("source").title = state.measured
      ? "ถอดปลั๊กอยู่ อ่านค่าจากแบตตรง ๆ"
      : "เสียบปลั๊กอยู่ รวมค่าจากเซนเซอร์แต่ละส่วน";
  }

  $("today").textContent = `${baht.format(state.today_baht)} ฿`;
  $("todayKwh").textContent = `${kwh3.format(state.today_kwh)} kWh`;
  $("session").textContent = `${baht.format(state.session_baht)} ฿`;
  $("month").textContent = `${baht.format(state.month_baht)} ฿`;

  drawPowerChart(state.history);
  drawDayBars(state.days, state.is_tou);
  drawSensors(state.sensors);
}

let latest = null;

async function poll() {
  try {
    latest = await window.pywebview.api.get_state();
    render(latest);
  } finally {
    setTimeout(poll, POLL_MS);
  }
}

window.addEventListener("pywebviewready", poll);
window.addEventListener("resize", () => latest && drawPowerChart(latest.history));
