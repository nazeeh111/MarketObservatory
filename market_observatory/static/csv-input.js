"use strict";

// Shared by the browser import flow and dependency-free decoder tests.
function decodeCsvBytes(bytes) {
  // ignoreBOM=true retains the marker as text so UTF-8 re-encoding preserves source bytes.
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { decodeCsvBytes };
}
