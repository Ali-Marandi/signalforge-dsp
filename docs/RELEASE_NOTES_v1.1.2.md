# SignalForge Studio v1.1.2

## Summary

This patch release hardens local file import behavior and improves validation of PCA diagnostic configuration. It preserves the local-first research boundary: the reviewed application workflow imports locally selected CSV/text data, executes diagnostics locally, and exports only to a user-selected destination.

## Improvements

### Safer local imports

SignalForge now rejects import files larger than **16 MiB** before the file is read into memory. This complements the existing sample-count limit and helps keep the desktop workflow responsive when a user selects an unexpectedly large CSV or text file.

Operating-system read errors, including a denied file read, are now normalized into a clear user-facing validation error instead of surfacing an unhandled system exception.

### Clearer PCA validation

PCA diagnostics now reject two invalid configurations before they reach third-party library internals:

- A variance-ratio `n_components` setting requires the `full` PCA solver.
- An integer `n_components` setting cannot exceed the smaller of the observation count and asset count.

These checks produce stable `DiagnosticValidationError` messages that can be handled consistently by the desktop application and callers.

### Expanded regression coverage

The regression suite now checks oversized-file rejection, file-access error conversion, PCA solver compatibility, component-dimension limits, and the output contract between sign-aligned PCA loadings and scores.

## Validation

The v1.1.2 source line passed the complete local quality gate before tagging:

| Gate | Result |
|---|---|
| Unit and desktop smoke tests | 20 passed |
| Bytecode compilation | Passed |
| Dependency integrity (`pip check`) | Passed |
| Diff whitespace validation | Passed |
| Local PyInstaller package and offscreen smoke test | Passed |

## Notes and limitations

SignalForge is a local research and diagnostic application. It does not submit trades, connect to brokers, provide personalized investment advice, make credit decisions, or claim security/regulatory certification. A local-first workflow reduces routine vendor-side custody of data, but the customer remains responsible for endpoint hardening, storage policy, data licensing, and appropriate model governance.

For Windows, verify the downloaded executable using the accompanying SHA-256 file. This release does not claim Authenticode code signing.
