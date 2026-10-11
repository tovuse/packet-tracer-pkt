---
name: packet-tracer-pkt
description: >
  Programmatically generate correct Cisco Packet Tracer .pkt/.pka files by
  decrypting reference files, surgically editing their XML, and re-encrypting;
  also decrypt/inspect existing .pkt files and verify them by driving the real
  Packet Tracer GUI. Use whenever the user wants to create/generate/build a
  .pkt or Packet Tracer lab file ("生成pkt"、"做成pkt文件"、"帮我建个拓扑文件"),
  asks what is inside a .pkt/.pka, wants to script Packet Tracer topologies for
  networking course experiments (PPP, VLAN, switching, routing labs), or needs
  automated verification that a generated file actually opens and works.
---

# Generating Packet Tracer .pkt files

Generate .pkt files by **decrypting a real reference file, surgically editing
its XML, and re-encrypting** — never by writing XML from scratch. The saved-file
schema is large, undocumented, and silently unforgiving: PT may open a file with
missing internal sections but the network inside can be dead (links unbound,
line protocol down). A reference base guarantees every section you don't touch
is exactly what PT itself writes.

## Environment (once per machine)

```bash
python "<skill-dir>/scripts/setup_env.py"   # installs twofish+pycryptodome, patches twofish for Py3.12+, self-tests
```

`<skill-dir>/scripts/ptpkt.py` is the proven codec: `decrypt_pka(bytes) -> xml`
and `encrypt_pka(xml) -> bytes`, plus CLI `python ptpkt.py -d in.pkt out.xml`
/ `-e in.xml out.pkt`. It implements the format pipeline (qCompress → XOR
obfuscation → Twofish-EAX with fixed key `{0x89}*16` / IV `{0x10}*16` → reversed
XOR obfuscation); details in `references/xml-schema.md`.

## Workflow

### 1. Mine references from the Packet Tracer installation

Locate the install (Windows example: `D:\Program Files\Cisco Packet Tracer 8.2.0`).
Two gold mines, both encrypted with the same pipeline:

- `<install>/saves/**/*.pkt` — ~260 real sample networks shipped with PT
- `<install>/templates/*.ptd` — device templates (slot trees, but no PORT details)

```bash
python <skill-dir>/scripts/decrypt_refs.py "<install>/saves" D:/tmp/pt_refs
```

Some files fail to decrypt (extra appended sections) — expected, ignore them.
Then grep the XML dump for the closest match to the target topology:

```bash
grep -l 'model="2811"' D:/tmp/pt_refs/*.xml          # by device model
grep -l 'NM-8A/S\|encapsulation ppp\|<NOTES>' ...    # by module/feature
```

Pick the base file with the right **device count and link count** first, right
models second, right config last — configs are the easiest thing to rewrite.

### 2. Understand the base before touching it

Read `references/xml-schema.md` first. Then outline the chosen base: device
element order, module/slot tree, LINKS, where configs and notes live. Port
names are derived from slot position (NM slot 1 → `Serial1/x`), never stored —
if you insert a module, the port names in `LINKS` must follow the new slot
positions.

### 3. Write the generator as surgical string surgery on the base XML

Follow `examples/build_ppp.py` (worked, verified example). Rules that make it
correct:

- **Replace whole blocks only** (whole `<DEVICE>`, whole `<LINKS>`, whole
  `<NOTES>`), splice at exact `find()` offsets, keep everything else
  byte-identical. Do not reformat or pretty-print untouched XML.
- Build replacement DEVICE blocks from cloned PORT element templates of the
  same port type found in real saved files (a `.ptd` template cannot give you
  PORT fields).
- After splicing, assert the invariants (see checklist below) and that no
  string from the old model leaks (e.g. `assert '1841' not in xml`).
- Check well-formedness: `xml.etree.ElementTree.fromstring(xml)`.

### 4. Encrypt and self-verify before involving the GUI

```python
import ptpkt
blob = ptpkt.encrypt_pka(xml.encode())
assert ptpkt.decrypt_pka(blob) == xml.encode()   # round-trip must be identical
```

### 5. Validate in the real application (mandatory, not optional)

A file that encrypts cleanly can still be wrong. Gate on the real thing:

1. Copy the .pkt somewhere writable — the PT install dir under Program Files is
   NOT writable; use `~/Documents/...`.
2. `"D:\Program Files\Cisco Packet Tracer 8.2.0\bin\PacketTracer.exe" <file>`
   (spawns a new instance even if one runs). Wait ~20 s.
3. Capture and **Read** the window: bundled `scripts/pt_capture.ps1 -ProcId <pid>`.
   Expect: window title contains the file path, topology rendered, correct
   device models, serial links drawn as red lightning (normal), green port
   lights on up ports.
4. To prove protocol-level correctness (e.g. PPP CHAP actually negotiating),
   drive the GUI: `scripts/pt_windows.ps1` (enumerate), `scripts/pt_click.ps1
   -ProcId <pid> -X <x> -Y <y> -Double` (opens device dialog), then send
   keystrokes to the CLI pane and re-capture (`enable`, `ping <ip>`; expect
   `!!!!!  Success rate is 100 percent`, `show interfaces ...` →
   `Encapsulation PPP, LCP Open`).

**DPI trap:** PT (Qt6) renders in physical pixels; a stock PowerShell 5.1
process sees logical pixels (150% scaling → 1.5× off). Every bundled script
calls `SetProcessDPIAware()` so capture and click share one coordinate space —
keep it that way in any new script. Also: the Read tool downscales large
screenshots, so measure click coordinates from a cropped image with a known
zoom factor, never from the displayed image.

### 6. Deliver

Report the file path, how to open it (double-click, or 文件→打开), and the
10-second manual check the user can run (open device → CLI → ping).

## Correctness checklist (run before encrypting AND before delivering)

- [ ] `LINKS` FROM/TO indexes match the DEVICE order; PORT names match slot tree
- [ ] Per port: `IP`/`SUBNET` ↔ config `ip address`; `POWER` ↔ `shutdown`; DCE
      `CLOCKRATE` ↔ config `clock rate`
- [ ] `SYS_NAME` ↔ config `hostname`
- [ ] `CURRENT_COMMAND_SET` + `CURRENT_BOOT_FILE` + flash `.bin` `SET_NAME` match the model
      (2811 → `2800_advip_12.4` + `c2800nm-advipservicesk9-mz.124-15.T1.bin`)
- [ ] Link-level agreements hold in config text only (encapsulation, auth):
      both ends must match
- [ ] MACs unique per port; `IPV6_DEFAULT_LINK_LOCAL` = EUI-64 of MAC
- [ ] `<VERSION>` kept from the reference (older versions open fine in PT 8.2)
- [ ] Round-trip `decrypt(encrypt(xml)) == xml`; XML well-formed; no leaked
      source-model strings
- [ ] Real PT 8.2 opened it and the screenshot shows the intended topology

## Gotchas learned the hard way

- Writing into the PT install directory needs admin — deliverables go to
  `~/Documents/`.
- A fresh router's IOS hostname is `Router`, not its display name. For CHAP set
  explicit hostnames and pair each side's `username <peer-hostname> password <pw>`.
- NM-8A/S = 8 × `eSmartSerial` ports `Serial1/0..1/7`, `BANDWIDTH` 128; WIC-2T /
  HWIC-2T = 1544; onboard FE = 100000.
- Device config dialogs are separate top-level windows — enumerate with
  `pt_windows.ps1` instead of trusting `MainWindowHandle`.
- A minimized window reports rect at `(-32000,-32000)`; `pt_click.ps1` restores
  it first.
- When the target needs a device type you have never seen serialized (unknown
  module, IoT device), decrypt more references until you find that exact model —
  do not guess field values; PT's palette names are the model strings.
