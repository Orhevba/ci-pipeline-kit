import { test } from "node:test";
import assert from "node:assert/strict";
import { greet } from "./index.js";

test("greet returns a friendly message", () => {
  assert.equal(greet("world"), "Hello, world!");
});
