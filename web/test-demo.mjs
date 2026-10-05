import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
const source = fs.readFileSync("lib/demo.ts", "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2017,
    esModuleInterop: true,
  },
}).outputText;
const data = JSON.parse(fs.readFileSync("lib/demo-data.json", "utf8"));
const mod = { exports: {} };
new Function("exports", "module", "require", compiled)(
  mod.exports,
  mod,
  () => data,
);
const {
  demoJobs,
  demoEvidence,
  matchesCareerLevel,
  cleanPreferences,
  families,
} = mod.exports;
assert.ok(demoJobs.length > 0);
assert.ok(
  demoJobs.every((job) => job.countries.includes("NL") && job.url === ""),
);
assert.ok(demoJobs.some((job) => job.employment === "part-time"));
assert.ok(demoEvidence.length > 0);
assert.equal(
  matchesCareerLevel({ employment: "internship", career_level: "internship" }, [
    "junior",
  ]),
  true,
);
assert.equal(
  matchesCareerLevel({ employment: "full-time", career_level: "senior" }, [
    "junior",
  ]),
  false,
);
assert.deepEqual(
  cleanPreferences({
    families: ["AI Consultant", "AI Solutions & Implementation"],
  }).families,
  ["AI Consulting & Solutions"],
);
assert.ok(!families.includes("AI Consultant"));
assert.deepEqual(
  cleanPreferences({ career_levels: ["internship", "junior"] }).career_levels,
  ["junior"],
);
console.log("Demo fixture and preference checks passed");
