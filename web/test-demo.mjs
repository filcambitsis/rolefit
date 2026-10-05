// Guard the score contract shared with the API and the fictional demo filters.
import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
const source = fs.readFileSync("lib/demo.ts", "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const mod = { exports: {} };
new Function("exports", "module", compiled)(mod.exports, mod);
const { requirementScore, demoJobs } = mod.exports;
const cases = [
  [[], null],
  [[[true, "met"]], 100],
  [[[false, "met"]], 100],
  [[[true, "not_verified"]], 0],
  [
    [
      [true, "met"],
      [false, "not_verified"],
    ],
    85,
  ],
  [
    [
      [true, "met"],
      [true, "not_verified"],
      [false, "not_verified"],
    ],
    43,
  ],
];
for (const [rows, expected] of cases) {
  assert.equal(
    requirementScore(rows.map(([required, status]) => ({ required, status }))),
    expected,
  );
}
assert.ok(demoJobs([]).some((job) => job.employment === "part-time"));
console.log("Demo scoring and employment checks passed");

assert.ok(demoJobs([]).every((job) => job.countries.includes("NL")));
assert.equal(
  "countries" in mod.exports.cleanPreferences({ countries: ["US"] }),
  false,
);
for (const [title, employment, expected] of [
  ["Software Engineer", "full-time", "unknown"],
  ["Junior Developer", "full-time", "junior"],
  ["Senior ML Engineer", "full-time", "senior"],
  ["Staff Data Engineer", "full-time", "lead"],
  ["Medior Software Engineer", "full-time", "mid"],
  ["Research Engineer", "internship", "internship"],
])
  assert.equal(mod.exports.careerLevel(title, employment), expected);
assert.ok(demoJobs([]).some((job) => job.family === "Software Engineer"));
assert.ok(demoJobs([]).some((job) => job.family === "Data Engineer"));

assert.equal(
  mod.exports.matchesCareerLevel(
    { title: "ML Intern", employment: "internship" },
    ["junior"],
  ),
  true,
);
assert.equal(
  mod.exports.matchesCareerLevel(
    { title: "Senior Engineer", employment: "full-time" },
    ["junior"],
  ),
  false,
);
assert.deepEqual(
  mod.exports.cleanPreferences({ career_levels: ["internship", "junior"] })
    .career_levels,
  ["junior"],
);
assert.ok(!mod.exports.careerLevels.some(([value]) => value === "internship"));
