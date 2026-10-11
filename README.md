# packet-tracer-pkt

**Programmatically generate correct Cisco Packet Tracer `.pkt` files** — as an
agent skill (ZCode / any tool that loads `SKILL.md` skills) plus a standalone
Python codec.

It packages a verified end-to-end methodology: decrypt a real reference file
mined from the Packet Tracer installation, surgically edit its XML, re-encrypt,
and validate inside the real application. Used to build complete lab files
(devices, modules, links, IOS configs, annotations) that Packet Tracer 8.2
opens and runs — e.g. a two-router PPP-with-CHAP topology — without touching
the GUI to build anything.

一个把这套方法沉淀成 agent skill 的仓库：**用脚本生成"真正能打开、能跑通"的
Packet Tracer .pkt 文件**。核心思路是解密 Packet Tracer 自带的真实示例文件、
在其 XML 上做外科手术式修改、再加密回去，最后在真实 Packet Tracer 里验证。
已用该方法完整生成《计算机网络》实验的 PPP + CHAP 拓扑文件。

---

## Why not just write a .pkt?

`.pkt` is not a plain file. It is a 4-stage encrypted container:

```
XML (Packet Tracer scene)
  ↓ zlib compress (qCompress: 4-byte big-endian size + deflate stream)
  ↓ XOR obfuscation (position-dependent)
  ↓ Twofish-EAX  (fixed key {0x89}×16, IV {0x10}×16 — embedded in the PT binary)
  ↓ XOR obfuscation (reversed + position-dependent)
.pkt
```

Encryption is only half the problem. The decrypted XML schema is large,
undocumented, and **silently unforgiving**: Packet Tracer will happily open a
file whose network is dead — links unbound, line protocol down. Two things make
generated files actually work:

1. **Reference-first editing.** Never synthesize XML from scratch. Decrypt one
   of the ~260 real sample networks shipped inside the Packet Tracer
   installation (`saves/**/*.pkt`, `templates/*.ptd`), pick the closest
   topology, and replace whole blocks only.
2. **Consistency invariants + real-app validation.** Port state fields must
   agree with the IOS config text (IP, shutdown, clock rate), link endpoints
   with the slot-derived port names, IOS command set with the device model,
   and so on — then the result is proven by opening it in real Packet Tracer
   and pinging through the topology.

`SKILL.md` encodes all of it as an executable workflow, including the
correctness checklist and the DPI/coordinate traps of automating the
Packet Tracer GUI on Windows.

## Repository layout

```
SKILL.md                     # the skill: methodology, validation gates, gotchas
references/xml-schema.md     # reverse-engineered XML schema + consistency contract
scripts/
  ptpkt.py                   # proven codec: decrypt_pka() / encrypt_pka() + CLI
  setup_env.py               # one-shot env setup + self-test (installs & patches twofish)
  decrypt_refs.py            # bulk-decrypt the bundled sample .pkt/.ptd files
  pt_capture.ps1             # capture PT window content (DPI-aware PrintWindow)
  pt_click.ps1               # DPI-aware click into the PT window
  pt_windows.ps1             # enumerate PT's top-level windows (dialogs included)
examples/
  build_ppp.py               # worked example: full PPP+CHAP lab generator
```

## Install (ZCode)

Clone straight into the user-level skills directory so it is available in every
workspace:

```bash
git clone https://github.com/<you>/packet-tracer-pkt ~/.agents/skills/packet-tracer-pkt
```

(or per-project: `<project>/.zcode/skills/packet-tracer-pkt`, or
`<project>/.agents/skills/...`).

Then set up Python dependencies once:

```bash
python ~/.agents/skills/packet-tracer-pkt/scripts/setup_env.py
```

Requires Windows, Python 3.10+, and a licensed Cisco Packet Tracer 8.x
installation (for reference mining and validation). On Python 3.12/3.13 the
`twofish` package needs a one-line patch — `setup_env.py` applies it
automatically and runs a self-test (official Twofish test vector, EAX
cross-checked against pycryptodome, full .pkt round-trip).

## Quick start

Standalone codec:

```bash
python scripts/ptpkt.py -d "C:/Program Files/Cisco Packet Tracer 8.2.0/saves/.../sample.pkt" out.xml
python scripts/ptpkt.py -e out.xml my_lab.pkt
```

Bulk-decrypt the bundled samples to mine references:

```bash
python scripts/decrypt_refs.py "C:/Program Files/Cisco Packet Tracer 8.2.0/saves" D:/tmp/pt_refs
grep -l 'model="2811"' D:/tmp/pt_refs/*.xml
```

Then follow `SKILL.md` — or hand it to your agent and say
*“生成实验一（2）的 pkt 文件”*.

## Legal

- Code: BSD-2-Clause (see `LICENSE`). The file-format pipeline and constants
  come from the open-source [pka2xml](https://github.com/mircodz/pka2xml)
  project (BSD-2-Clause, © 2020 Mirco De Zorzi); its notice is reproduced in
  `LICENSE` as its license requires.
- Packet Tracer itself is Cisco's product and requires a Cisco Networking
  Academy account; the sample files referenced by the workflow ship inside
  your own installation and are not redistributed here.
- This project is educational tooling for networking courses and is not
  affiliated with or endorsed by Cisco.
