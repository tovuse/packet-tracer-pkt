"""One-time environment setup for the packet-tracer-pkt skill.

Installs/patches Python dependencies and verifies the codec end-to-end:
  1. pip install twofish pycryptodome
  2. The `twofish` PyPI package uses the `imp` module (removed in Python 3.12+);
     patch it to load its ctypes extension via a direct path.
  3. Self-test: official Twofish ECB vector + generic EAX cross-checked against
     pycryptodome's AES-EAX + a real qCompress round-trip.

Run:  python setup_env.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def patch_twofish():
    try:
        import twofish  # noqa: F401
        print("twofish imports fine")
        return
    except Exception as e:
        print("twofish import failed:", e)
    import site
    pkg = os.path.join(site.getsitepackages()[0], "twofish.py")
    src = open(pkg, encoding="utf-8").read()
    if "import imp" in src:
        src = src.replace("import imp\nimport sys", "import os\nimport sys")
        src = src.replace(
            "_twofish = cdll.LoadLibrary(imp.find_module('_twofish')[1])",
            "_twofish = cdll.LoadLibrary(os.path.join(os.path.dirname("
            "os.path.abspath(__file__)), '_twofish.cp313-win_amd64.pyd'))",
        )
        open(pkg, "w", encoding="utf-8").write(src)
        print("patched", pkg)
    # importlib cache may hold the failed import
    import importlib
    import twofish  # noqa: F401
    print("twofish OK after patch")


def self_test():
    from twofish import Twofish
    import ptpkt

    # official Twofish 128-bit vector
    ct = Twofish(b"\x00" * 16).encrypt(b"\x00" * 16)
    assert ct == bytes.fromhex("9F589F5CF6122C32B6BFEC2F2AE8C35A"), ct.hex()

    # EAX implementation vs pycryptodome AES-EAX
    from Crypto.Cipher import AES
    key = bytes(range(16))
    nonce = bytes(range(16, 32))
    for ln in (0, 1, 16, 33, 50, 64):
        pt = bytes(range(256))[:ln]
        ref = AES.new(key, AES.MODE_EAX, nonce=nonce, mac_len=16)
        ct_ref, tag_ref = ref.encrypt_and_digest(pt)
        mine = ptpkt.eax_encrypt(AES.new(key, AES.MODE_ECB), nonce, pt)
        assert mine == ct_ref + tag_ref, f"EAX mismatch at len {ln}"
        assert ptpkt.eax_decrypt(AES.new(key, AES.MODE_ECB), nonce, mine) == pt

    # qCompress round-trip through the real .pkt pipeline
    xml = b"<PACKETTRACER5><hello/>\x00\xe4\xb8\xad\xe6\x96\x87</PACKETTRACER5>" * 40
    assert ptpkt.decrypt_pka(ptpkt.encrypt_pka(xml)) == xml
    print("self-test OK (Twofish vector, EAX vs pycryptodome, pkt round-trip)")


if __name__ == "__main__":
    run([sys.executable, "-m", "pip", "install", "twofish", "pycryptodome"])
    patch_twofish()
    self_test()
