"""Bulk-decrypt Packet Tracer .pkt/.pka/.ptd files to XML for reference mining.

Usage:
  python decrypt_refs.py <source-dir-or-glob> <out-dir>

Decrypts every matching file into <out-dir>/<flattened-name>.xml. Files that
fail (some shipped samples append extra sections after the encrypted XML) are
reported and skipped — that is expected, not a bug.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ptpkt


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    files = sorted(set(glob.glob(src) if any(c in src for c in "*?[]")
                       else glob.glob(os.path.join(src, "**", "*.pkt"), recursive=True)
                       + glob.glob(os.path.join(src, "**", "*.pka"), recursive=True)
                       + glob.glob(os.path.join(src, "**", "*.ptd"), recursive=True)))
    ok = fail = 0
    for f in files:
        rel = os.path.basename(f)  # flatten; collisions are rare in practice
        dst = os.path.join(out, rel + ".xml")
        if os.path.exists(dst):
            ok += 1
            continue
        try:
            xml = ptpkt.decrypt_pka(open(f, "rb").read())
            open(dst, "wb").write(xml)
            ok += 1
        except Exception as e:
            fail += 1
            print("FAIL", rel, type(e).__name__)
    print(f"total {len(files)}, ok {ok}, fail {fail}, output -> {out}")


if __name__ == "__main__":
    main()
