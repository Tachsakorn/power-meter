"use strict";

// Build Your Reactor: game rules only, no DOM. Everything here is fictional.
// Nothing reads or affects the real power meter, and credits are not money.

(function (root) {
  const SAVE_VERSION = 1;
  const START_SLOTS = 6;
  const MAX_SLOTS = 15;

  const BUILDINGS = {
    dynamo: {
      name: "ไดนาโม",
      cost: 10,
      cr: 0.5,
      blurb: "เครื่องปั่นไฟเล็ก ๆ จุดเริ่มต้นของทุกโรงงาน",
    },
    solar: { name: "แผงโซลาร์", cost: 75, cr: 2.5, blurb: "เงียบ เรียบร้อย ผลิตได้ทั้งวัน" },
    wind: { name: "กังหันลม", cost: 600, cr: 12, blurb: "ใบพัดยิ่งใหญ่ ยิ่งได้เยอะ" },
    lab: { name: "ห้องแล็บ", cost: 1200, rp: 0.25, blurb: "ผลิตแต้มวิจัย ใช้ปลดล็อกเทคโนโลยี" },
    battery: {
      name: "ธนาคารแบตเตอรี่",
      cost: 4000,
      boost: 0.04,
      offlineHours: 1,
      blurb: "เพิ่มผลผลิตทุกอาคาร 4% ต่อเลเวล และเก็บผลผลิตตอนไม่อยู่ได้นานขึ้น",
    },
    fission: {
      name: "เตาฟิชชัน",
      cost: 60000,
      cr: 260,
      needs: "fission",
      blurb: "แท่งเชื้อเพลิงในบ่อน้ำ เรืองแสงสีฟ้าตอนทำงาน",
    },
    fusion: {
      name: "เตาฟิวชัน",
      cost: 2.5e7,
      cr: 6000,
      needs: "fusion",
      blurb: "พลาสมาร้อนกว่าดวงอาทิตย์ วิ่งวนในวงแหวนแม่เหล็ก",
    },
  };

  const TECHS = [
    { id: "gears", name: "เฟืองลูกปืน", rp: 10, text: "ไดนาโม x3 และหมุนมือได้เครดิต x2" },
    { id: "pv_cells", name: "เซลล์แสงอาทิตย์รุ่นใหม่", rp: 15, text: "แผงโซลาร์ x2" },
    { id: "blades", name: "ใบพัดคาร์บอนไฟเบอร์", rp: 40, text: "กังหันลม x2" },
    { id: "fission", name: "ใบอนุญาตเตาฟิชชัน", rp: 120, text: "ปลดล็อกเตาฟิชชัน" },
    {
      id: "automation",
      name: "ห้องควบคุมอัตโนมัติ",
      rp: 200,
      text: "ตอนไม่อยู่ ผลิตได้ 50% แทน 25%",
    },
    {
      id: "heavy_water",
      name: "หล่อเย็นด้วยน้ำมวลหนัก",
      rp: 500,
      needs: "fission",
      text: "เตาฟิชชัน x1.5",
    },
    {
      id: "fusion",
      name: "แม่เหล็กตัวนำยิ่งยวด",
      rp: 5000,
      needs: "heavy_water",
      text: "ปลดล็อกเตาฟิวชัน",
    },
  ];

  const MULTIPLIERS = {
    gears: { dynamo: 3 },
    pv_cells: { solar: 2 },
    blades: { wind: 2 },
    heavy_water: { fission: 1.5 },
  };

  const ACHIEVEMENTS = [
    {
      id: "first_build",
      name: "เปิดโรงงาน",
      text: "สร้างอาคารแรก",
      done: (s) => built(s).length >= 1,
    },
    {
      id: "crank_100",
      name: "แขนเหล็ก",
      text: "หมุนไดนาโมด้วยมือ 100 ครั้ง",
      done: (s) => s.cranks >= 100,
    },
    {
      id: "earn_1k",
      name: "พันแรก",
      text: "หาเครดิตได้รวม 1,000 cr",
      done: (s) => s.earned >= 1e3,
    },
    {
      id: "first_tech",
      name: "นักวิจัยฝึกหัด",
      text: "ปลดล็อกเทคโนโลยีแรก",
      done: (s) => s.techs.length >= 1,
    },
    {
      id: "level_10",
      name: "ช่างประจำโรงงาน",
      text: "อัปเกรดอาคารหนึ่งหลังถึงเลเวล 10",
      done: (s) => built(s).some((b) => b.lvl >= 10),
    },
    {
      id: "full_floor",
      name: "ไม่มีที่ว่าง",
      text: "สร้างอาคารเต็มทุกช่องในโรงงาน",
      done: (s) => built(s).length === s.slots && s.slots > START_SLOTS,
    },
    {
      id: "fission_online",
      name: "แสงสีฟ้า",
      text: "เดินเครื่องเตาฟิชชันครั้งแรก",
      done: (s) => built(s).some((b) => b.t === "fission"),
    },
    {
      id: "earn_1m",
      name: "หนึ่งล้าน",
      text: "หาเครดิตได้รวม 1,000,000 cr",
      done: (s) => s.earned >= 1e6,
    },
    {
      id: "fusion_online",
      name: "ดวงอาทิตย์จำลอง",
      text: "จุดพลาสมาในเตาฟิวชัน",
      done: (s) => built(s).some((b) => b.t === "fusion"),
    },
    {
      id: "welcome_back",
      name: "กะดึก",
      text: "กลับมารับผลผลิตตอนที่ไม่อยู่",
      done: (s) => s.offlineClaims >= 1,
    },
  ];

  function newGame(now) {
    return {
      v: SAVE_VERSION,
      credits: 15,
      research: 0,
      earned: 0,
      cranks: 0,
      offlineClaims: 0,
      slots: START_SLOTS,
      floor: Array(START_SLOTS).fill(null),
      techs: [],
      ach: [],
      savedAt: now,
    };
  }

  // Accept a save from disk only if it looks like ours; otherwise start fresh.
  function restore(data, now) {
    if (!data || data.v !== SAVE_VERSION || !Array.isArray(data.floor)) return newGame(now);
    const s = { ...newGame(now), ...data };
    s.slots = Math.min(MAX_SLOTS, Math.max(START_SLOTS, s.slots | 0));
    s.floor = Array.from({ length: s.slots }, (_, i) => {
      const b = data.floor[i];
      return b && BUILDINGS[b.t] ? { t: b.t, lvl: Math.max(1, b.lvl | 0) } : null;
    });
    s.techs = (data.techs || []).filter((id) => TECHS.some((t) => t.id === id));
    s.ach = (data.ach || []).filter((id) => ACHIEVEMENTS.some((a) => a.id === id));
    for (const k of ["credits", "research", "earned", "cranks", "offlineClaims", "savedAt"]) {
      if (!Number.isFinite(s[k]) || s[k] < 0) s[k] = newGame(now)[k];
    }
    return s;
  }

  function built(s) {
    return s.floor.filter(Boolean);
  }

  function has(s, techId) {
    return s.techs.includes(techId);
  }

  function multiplier(s, type) {
    let m = 1;
    for (const id of s.techs) m *= MULTIPLIERS[id]?.[type] ?? 1;
    return m;
  }

  function boost(s) {
    return built(s)
      .filter((b) => b.t === "battery")
      .reduce((sum, b) => sum + b.lvl * BUILDINGS.battery.boost, 0);
  }

  function output(s, b) {
    const def = BUILDINGS[b.t];
    const scale = b.lvl * multiplier(s, b.t) * (1 + boost(s));
    return { cr: (def.cr ?? 0) * scale, rp: (def.rp ?? 0) * scale };
  }

  function production(s) {
    let cr = 0;
    let rp = 0;
    for (const b of built(s)) {
      const out = output(s, b);
      cr += out.cr;
      rp += out.rp;
    }
    return { cr, rp };
  }

  function count(s, type) {
    return built(s).filter((b) => b.t === type).length;
  }

  function buildCost(s, type) {
    return Math.round(BUILDINGS[type].cost * 1.15 ** count(s, type));
  }

  function upgradeCost(b) {
    return Math.round(BUILDINGS[b.t].cost * 1.8 ** b.lvl);
  }

  function slotCost(s) {
    return s.slots >= MAX_SLOTS ? Infinity : Math.round(200 * 4 ** (s.slots - START_SLOTS));
  }

  function locked(s, type) {
    const need = BUILDINGS[type].needs;
    return need && !has(s, need) ? TECHS.find((t) => t.id === need) : null;
  }

  function spend(s, amount) {
    if (s.credits < amount) return false;
    s.credits -= amount;
    return true;
  }

  function build(s, slot, type) {
    if (s.floor[slot] || locked(s, type) || !spend(s, buildCost(s, type))) return false;
    s.floor[slot] = { t: type, lvl: 1 };
    return true;
  }

  function upgrade(s, slot) {
    const b = s.floor[slot];
    if (!b || !spend(s, upgradeCost(b))) return false;
    b.lvl += 1;
    return true;
  }

  function demolish(s, slot) {
    if (!s.floor[slot]) return false;
    s.floor[slot] = null;
    return true;
  }

  function expand(s) {
    if (!spend(s, slotCost(s))) return false;
    s.slots += 1;
    s.floor.push(null);
    return true;
  }

  function techAvailable(s, tech) {
    return !has(s, tech.id) && (!tech.needs || has(s, tech.needs));
  }

  function research(s, id) {
    const tech = TECHS.find((t) => t.id === id);
    if (!tech || !techAvailable(s, tech) || s.research < tech.rp) return false;
    s.research -= tech.rp;
    s.techs.push(id);
    return true;
  }

  function crankValue(s) {
    return (1 + 0.05 * production(s).cr) * (has(s, "gears") ? 2 : 1);
  }

  function crank(s) {
    const gain = crankValue(s);
    s.credits += gain;
    s.earned += gain;
    s.cranks += 1;
    return gain;
  }

  function tick(s, seconds) {
    const { cr, rp } = production(s);
    s.credits += cr * seconds;
    s.earned += cr * seconds;
    s.research += rp * seconds;
  }

  function offlineRules(s) {
    const batteryLevels = built(s)
      .filter((b) => b.t === "battery")
      .reduce((n, b) => n + b.lvl, 0);
    return {
      capHours: 2 + batteryLevels * BUILDINGS.battery.offlineHours,
      efficiency: has(s, "automation") ? 0.5 : 0.25,
    };
  }

  // Time away is paid out at reduced efficiency and capped. It depends only
  // on the clock, never on how much electricity the computer used.
  function offlineEarnings(s, now) {
    const away = Math.max(0, (now - s.savedAt) / 1000);
    const { capHours, efficiency } = offlineRules(s);
    const seconds = Math.min(away, capHours * 3600);
    const { cr, rp } = production(s);
    return {
      away,
      seconds,
      capHours,
      efficiency,
      credits: cr * seconds * efficiency,
      research: rp * seconds * efficiency,
    };
  }

  function claimOffline(s, result) {
    s.credits += result.credits;
    s.earned += result.credits;
    s.research += result.research;
    s.offlineClaims += 1;
  }

  function newAchievements(s) {
    const fresh = ACHIEVEMENTS.filter((a) => !s.ach.includes(a.id) && a.done(s));
    for (const a of fresh) s.ach.push(a.id);
    return fresh;
  }

  function nextGoal(s) {
    if (!built(s).length) return "สร้างไดนาโมตัวแรกในช่องว่างของโรงงาน";
    if (!count(s, "lab")) return "สร้างห้องแล็บ เพื่อเริ่มเก็บแต้มวิจัย";
    if (!has(s, "fission")) return "วิจัย ใบอนุญาตเตาฟิชชัน";
    if (!count(s, "fission")) return "สร้างเตาฟิชชันเครื่องแรก";
    if (!has(s, "fusion")) return "วิจัย แม่เหล็กตัวนำยิ่งยวด เพื่อไปสู่ฟิวชัน";
    if (!count(s, "fusion")) return "สร้างเตาฟิวชัน";
    return "ขยายโรงงานให้เต็ม แล้วอัปเกรดทุกอย่างให้สุด";
  }

  const api = {
    SAVE_VERSION,
    MAX_SLOTS,
    BUILDINGS,
    TECHS,
    ACHIEVEMENTS,
    newGame,
    restore,
    production,
    output,
    buildCost,
    upgradeCost,
    slotCost,
    locked,
    build,
    upgrade,
    demolish,
    expand,
    techAvailable,
    research,
    crank,
    crankValue,
    tick,
    offlineEarnings,
    claimOffline,
    newAchievements,
    nextGoal,
  };

  if (typeof module !== "undefined") module.exports = api;
  else root.ReactorEngine = api;
})(typeof window !== "undefined" ? window : globalThis);
