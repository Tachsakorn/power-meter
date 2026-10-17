"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const E = require("../../src/power_meter/web/reactor/engine.js");

const T0 = 1_800_000_000_000;

test("a new game can afford its first dynamo", () => {
  const s = E.newGame(T0);
  assert.ok(E.build(s, 0, "dynamo"));
  assert.equal(s.floor[0].t, "dynamo");
  assert.equal(s.credits, 5);
  assert.equal(E.production(s).cr, 0.5);
});

test("cannot build locked reactors or on a taken slot", () => {
  const s = E.newGame(T0);
  s.credits = 1e9;
  assert.equal(E.build(s, 0, "fission"), false);
  E.build(s, 0, "dynamo");
  assert.equal(E.build(s, 0, "solar"), false);
  s.research = 1e6;
  assert.ok(E.research(s, "fission"));
  assert.ok(E.build(s, 1, "fission"));
});

test("costs rise with count and level", () => {
  const s = E.newGame(T0);
  s.credits = 1e6;
  const first = E.buildCost(s, "solar");
  E.build(s, 0, "solar");
  assert.ok(E.buildCost(s, "solar") > first);
  const before = E.upgradeCost(s.floor[0]);
  E.upgrade(s, 0);
  assert.equal(s.floor[0].lvl, 2);
  assert.ok(E.upgradeCost(s.floor[0]) > before);
});

test("techs multiply output and batteries boost everything", () => {
  const s = E.newGame(T0);
  s.credits = 1e6;
  s.research = 1e3;
  E.build(s, 0, "solar");
  assert.equal(E.production(s).cr, 2.5);
  E.research(s, "pv_cells");
  assert.equal(E.production(s).cr, 5);
  E.build(s, 1, "battery");
  assert.ok(Math.abs(E.production(s).cr - 5 * 1.04) < 1e-9);
});

test("research respects prerequisites", () => {
  const s = E.newGame(T0);
  s.research = 1e6;
  assert.equal(E.research(s, "heavy_water"), false);
  assert.ok(E.research(s, "fission"));
  assert.ok(E.research(s, "heavy_water"));
  assert.equal(E.research(s, "heavy_water"), false);
});

test("offline earnings are capped and at reduced efficiency", () => {
  const s = E.newGame(T0);
  s.floor[0] = { t: "wind", lvl: 1 };
  const day = E.offlineEarnings(s, T0 + 24 * 3600 * 1000);
  assert.equal(day.seconds, 2 * 3600);
  assert.equal(day.credits, 12 * 2 * 3600 * 0.25);

  s.techs.push("automation");
  s.floor[1] = { t: "battery", lvl: 2 };
  const better = E.offlineEarnings(s, T0 + 24 * 3600 * 1000);
  assert.equal(better.capHours, 4);
  assert.equal(better.efficiency, 0.5);
});

test("expanding the floor costs credits and stops at the max", () => {
  const s = E.newGame(T0);
  s.credits = 1e12;
  while (E.expand(s));
  assert.equal(s.slots, E.MAX_SLOTS);
  assert.equal(s.floor.length, E.MAX_SLOTS);
});

test("achievements unlock once", () => {
  const s = E.newGame(T0);
  E.build(s, 0, "dynamo");
  assert.deepEqual(
    E.newAchievements(s).map((a) => a.id),
    ["first_build"],
  );
  assert.deepEqual(E.newAchievements(s), []);
});

test("restore drops anything that isn't part of the game", () => {
  const s = E.restore(
    {
      v: 1,
      credits: -5,
      slots: 99,
      floor: [{ t: "dynamo", lvl: 3 }, { t: "nope", lvl: 2 }, null],
      techs: ["gears", "hack"],
    },
    T0,
  );
  assert.equal(s.credits, 15);
  assert.equal(s.slots, E.MAX_SLOTS);
  assert.deepEqual(s.floor[0], { t: "dynamo", lvl: 3 });
  assert.equal(s.floor[1], null);
  assert.deepEqual(s.techs, ["gears"]);
  assert.equal(E.restore("garbage", T0).credits, 15);
});

test("cranking scales with production and gears", () => {
  const s = E.newGame(T0);
  assert.equal(E.crank(s), 1);
  s.floor[0] = { t: "wind", lvl: 10 };
  s.techs.push("gears");
  assert.equal(E.crankValue(s), (1 + 0.05 * 120) * 2);
});
