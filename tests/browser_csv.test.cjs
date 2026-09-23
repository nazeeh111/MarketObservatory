// Run with `node --test tests/browser_csv.test.cjs`. Uses the production browser decoder.
const assert = require("node:assert/strict");
const test = require("node:test");
const { decodeCsvBytes } = require("../market_observatory/static/csv-input.js");

test("CSV decoding preserves original UTF-8 bytes, BOM and all newline forms", () => {
  for (const newline of ["\n", "\r\n", "\r"]) {
    for (const bom of ["", "\ufeff"]) {
      const original = Buffer.from(`${bom}date,symbol,close${newline}2024-01-01,A,12${newline}`, "utf8");
      const decoded = decodeCsvBytes(original);
      assert.deepEqual(Buffer.from(decoded, "utf8"), original);
    }
  }
});

test("CSV decoding rejects malformed UTF-8 rather than replacing bytes", () => {
  assert.throws(() => decodeCsvBytes(Uint8Array.from([0x64, 0xff, 0x0a])), TypeError);
});
