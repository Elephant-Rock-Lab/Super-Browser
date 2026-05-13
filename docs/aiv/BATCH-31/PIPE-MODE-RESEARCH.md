# BATCH-31/TASK-04 — Pipe-Mode CDP Investigation: Findings

## Research Question

Can Super Browser use `--remote-debugging-pipe` (FDs 3+4) transport instead of TCP-based CDP, eliminating the listening port fingerprint surface?

## Findings

### Patchright's Architecture

Patchright uses a **channel-based server process** architecture:

1. `BrowserType.launch()` sends parameters through an internal channel to a Node.js server process
2. The server process spawns Chromium and manages the CDP connection
3. Python communicates with the server via IPC, not directly with Chromium
4. The `args` parameter passes through to Chromium's command line, but the **CDP transport is chosen by Patchright's server, not by our Python code**

### What This Means

- **We cannot use `--remote-debugging-pipe` through Patchright's `launch()` API** — Patchright's internal server decides the CDP transport, and it uses TCP (`--remote-debugging-port`)
- **We cannot access FDs 3+4** from Python because Patchright's Node.js server is the process that spawns Chromium, not our Python process
- **Passing `--remote-debugging-pipe` as an arg** would conflict with Patchright's own CDP connection setup

### Platform Assessment

| Platform | pipe-mode support | Feasibility |
|:---------|:-----------------|:------------|
| Linux | `pass_fds=[3,4]` in subprocess | ❌ Patchright manages the process |
| macOS | `pass_fds=[3,4]` in subprocess | ❌ Patchright manages the process |
| Windows | Named pipes (different from Unix FDs) | ❌ Patchright manages the process |

### Possible Paths Forward (v2.0)

1. **Bypass Patchright entirely** — Spawn Chromium directly from Python with `--remote-debugging-pipe`, implement a raw CDP client over FDs. This means reimplementing Patchright's browser lifecycle management, DOM interaction, and event handling. Significant effort (~3,000+ lines).

2. **Fork Patchright** — Modify Patchright's server to use pipe-mode internally. Maintaining a fork is expensive.

3. **Contribute upstream** — Open a PR to Patchright adding pipe-mode support. Depends on their roadmap.

4. **Accept TCP limitation** — The TCP listening port (`--remote-debugging-port`) is bound to localhost (127.0.0.1), not exposed externally. It's a detection surface for local probes but not for remote WAFs. The practical impact is low.

## Conclusion

**Pipe-mode CDP is NOT feasible through Patchright.** The limitation is architectural — Patchright's channel-based server controls the CDP transport, not our Python code. Document as a known limit.

## Recommendation

Accept the TCP limitation. Add to known limits. The practical impact is minimal:
- Port is bound to localhost — not externally accessible
- Remote WAFs cannot detect a local TCP port
- Only local detection tools (running JS on the same machine) could probe for it
- Super Browser is primarily used for remote web automation, not anti-forensics

Defer to v2.0 with a note about bypassing Patchright for pipe-mode.

---

Research completed: 2026-05-13  
Lead Sign: Lead
