"""Packet Tracer .pkt/.pka <-> XML codec.

Implements the same pipeline as pka2xml (BSD-2-Clause):
  encrypt: qCompress(zlib) -> XOR obfuscation -> Twofish-EAX -> reversed XOR obfuscation
  decrypt: reverse of the above
Key/IV constants and both obfuscation stages are taken from pka2xml's
include/pka2xml.hpp (decrypt_pka / encrypt_pka).
"""
import struct
import sys
import zlib

from twofish import Twofish

PKT_KEY = b'\x89' * 16   # {137}*16
PKT_IV = b'\x10' * 16    # {16}*16


# ---------------- EAX mode (generic over a 128-bit block cipher) ----------------

def _cmac_enc(cipher, block):
    return cipher.encrypt(block)


def cmac(cipher, msg: bytes) -> bytes:
    """OMAC1/CMAC over 128-bit blocks."""
    L = _cmac_enc(cipher, b'\x00' * 16)
    k1 = _shift(L)
    k2 = _shift(k1)

    rem = len(msg) % 16
    n_blocks = len(msg) // 16 + (1 if rem else 0)
    complete = len(msg) > 0 and rem == 0
    blocks = [msg[i * 16:(i + 1) * 16] for i in range(n_blocks)]
    if not blocks:
        blocks = [b'']
        complete = False
    if complete:
        last = _xor(blocks[-1], k1)
    else:
        last = _pad10(blocks[-1])
        last = _xor(last, k2)
    blocks = blocks[:-1] + [last]

    x = b'\x00' * 16
    for b in blocks:
        x = _cmac_enc(cipher, _xor(x, b))
    return x


def _shift(b: bytes) -> bytes:
    """Left shift by 1 bit with MSB feedback; constant 0x87 for 128-bit blocks."""
    i = int.from_bytes(b, 'big')
    i <<= 1
    if b[0] & 0x80:
        i ^= 0x87
    return (i & ((1 << 128) - 1)).to_bytes(16, 'big')


def _pad10(last: bytes) -> bytes:
    return last + b'\x80' + b'\x00' * (16 - len(last) - 1)


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _inc32(block: bytes) -> bytes:
    """EAX CTR: increment the whole 128-bit counter (big-endian)."""
    return ((int.from_bytes(block, 'big') + 1) & ((1 << 128) - 1)).to_bytes(16, 'big')


def _omac_t(cipher, t: int, data: bytes) -> bytes:
    return cmac(cipher, (b'\x00' * 15 + bytes([t])) + data)


def _ctr(cipher, counter: bytes, msg: bytes) -> bytes:
    out = bytearray()
    c = counter
    for i in range(0, len(msg), 16):
        ks = cipher.encrypt(c)
        out += _xor(msg[i:i + 16], ks)
        c = _inc32(c)
    return bytes(out)


def eax_encrypt(cipher, nonce: bytes, plaintext: bytes, mac_len: int = 16) -> bytes:
    n = _omac_t(cipher, 0, nonce)
    h = _omac_t(cipher, 1, b'')  # empty header
    c = _ctr(cipher, n, plaintext)
    t = _omac_t(cipher, 2, c)
    tag = bytes(a ^ b ^ d for a, b, d in zip(n, h, t))[:mac_len]
    return c + tag


def eax_decrypt(cipher, nonce: bytes, data: bytes, mac_len: int = 16) -> bytes:
    ct, tag = data[:-mac_len], data[-mac_len:]
    n = _omac_t(cipher, 0, nonce)
    h = _omac_t(cipher, 1, b'')
    t = _omac_t(cipher, 2, ct)
    expect = bytes(a ^ b ^ d for a, b, d in zip(n, h, t))[:mac_len]
    if expect != tag:
        raise ValueError('EAX tag mismatch (bad key/format)')
    return _ctr(cipher, n, ct)


# ---------------- obfuscation stages ----------------

def _deobf_stage1(data: bytes) -> bytes:
    """processed[i] = input[L-1-i] ^ (L - i*L)"""
    L = len(data)
    return bytes(data[L - 1 - i] ^ ((L - i * L) & 0xFF) for i in range(L))


def _obf_stage1(data: bytes) -> bytes:
    """out[L-1-i] = enc[i] ^ (L - i*L)  (inverse of _deobf_stage1)"""
    L = len(data)
    out = bytearray(L)
    for i in range(L):
        out[L - 1 - i] = data[i] ^ ((L - i * L) & 0xFF)
    return bytes(out)


def _deobf_stage3(data: bytes) -> bytes:
    """output[i] ^= (len - i)"""
    L = len(data)
    return bytes(c ^ ((L - i) & 0xFF) for i, c in enumerate(data))


_obf_stage3 = _deobf_stage3  # self-inverse


# ---------------- qCompress / qUncompress ----------------

def _quncompress(data: bytes) -> bytes:
    (size,) = struct.unpack('>I', data[:4])
    out = zlib.decompress(data[4:])
    if len(out) != size:
        raise ValueError('qUncompress size mismatch')
    return out


def _qcompress(data: bytes) -> bytes:
    return struct.pack('>I', len(data)) + zlib.compress(data, 6)


# ---------------- public API ----------------

def decrypt_pka(data: bytes) -> bytes:
    deobf = _deobf_stage1(data)
    cipher = Twofish(PKT_KEY)
    plain = eax_decrypt(cipher, PKT_IV, deobf)
    plain = _deobf_stage3(plain)
    return _quncompress(plain)


def encrypt_pka(xml: bytes) -> bytes:
    comp = _qcompress(xml)
    comp = _obf_stage3(comp)
    cipher = Twofish(PKT_KEY)
    enc = eax_encrypt(cipher, PKT_IV, comp)
    return _obf_stage1(enc)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('-d', '-e'):
        print('usage: python ptpkt.py -d in.pkt out.xml | -e in.xml out.pkt')
        sys.exit(1)
    mode, fin, fout = sys.argv[1], sys.argv[2], sys.argv[3]
    blob = open(fin, 'rb').read()
    if mode == '-d':
        out = decrypt_pka(blob)
    else:
        out = encrypt_pka(blob)
    open(fout, 'wb').write(out)
    print(f'{fin} -> {fout} ({len(out)} bytes)')
