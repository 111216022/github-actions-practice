"""ECDH P-256 + HKDF-SHA256 + AES-256-GCM testcase encryption."""

import argparse
import io
import json
import os
from pathlib import Path
import sys

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


MAGIC = b"TESTCASES-ENC-v1\x00"
INFO = b"testcases/ecdh-p256/hkdf-sha256/aes-256-gcm/v1"


def validate_cases(data):
    cases = json.loads(data.decode("utf-8-sig"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Testcases must be a nonempty JSON array")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or any(
            not isinstance(case.get(field), str) for field in ("id", "input", "expected")
        ):
            raise ValueError("Each testcase needs string id, input and expected")
        if not case["id"] or case["id"] in ids:
            raise ValueError("Testcase ids must be nonempty and unique")
        ids.add(case["id"])
        for field in ("id", "input", "expected"):
            case[field].encode("utf-8")
    return cases


def derive_key(private, public, salt):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=INFO).derive(
        private.exchange(ec.ECDH(), public)
    )


def check_key(key, private=False):
    kind = ec.EllipticCurvePrivateKey if private else ec.EllipticCurvePublicKey
    if not isinstance(key, kind) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("Expected a P-256 EC key")
    return key


def generate_keys(private_path, public_path):
    if private_path.resolve() == public_path.resolve():
        raise ValueError("Public and private key paths must differ")
    if private_path.exists() or public_path.exists():
        raise ValueError("Key files already exist; refusing to overwrite")
    key = ec.generate_private_key(ec.SECP256R1())
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation and owner-only permissions on POSIX; Windows uses directory ACLs.
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(key.private_bytes(serialization.Encoding.PEM,
                                      serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))
    with public_path.open("xb") as stream:
        stream.write(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                  serialization.PublicFormat.SubjectPublicKeyInfo))


def encrypt(data, public_pem):
    validate_cases(data)
    public = check_key(serialization.load_pem_public_key(public_pem))
    ephemeral = ec.generate_private_key(ec.SECP256R1())
    salt, nonce = os.urandom(32), os.urandom(12)
    point = ephemeral.public_key().public_bytes(serialization.Encoding.X962,
                                               serialization.PublicFormat.UncompressedPoint)
    header = MAGIC + point + salt + nonce
    return header + AESGCM(derive_key(ephemeral, public, salt)).encrypt(nonce, data, header)


def decrypt(data, private_pem):
    header_size = len(MAGIC) + 65 + 32 + 12
    if not data.startswith(MAGIC) or len(data) < header_size + 16:
        raise ValueError("Invalid encrypted testcase format/version")
    private = check_key(serialization.load_pem_private_key(private_pem, password=None), True)
    offset = len(MAGIC)
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), data[offset:offset + 65])
    salt = data[offset + 65:offset + 97]
    nonce = data[offset + 97:header_size]
    plain = AESGCM(derive_key(private, public, salt)).decrypt(nonce, data[header_size:], data[:header_size])
    validate_cases(plain)
    return plain


def read_frame(stream):
    size = stream.readline()
    if not size.endswith(b"\n") or not size[:-1].isdigit():
        raise ValueError("Invalid validator request")
    data = stream.read(int(size))
    if len(data) != int(size):
        raise ValueError("Truncated validator request")
    return data.decode("utf-8")


def validator_frames():
    # No command-line arguments: internal bridge used by validator.cpp.
    encrypted = Path(read_frame(sys.stdin.buffer))
    private_pem = read_frame(sys.stdin.buffer).encode("utf-8")
    if sys.stdin.buffer.read(1):
        raise ValueError("Unexpected validator request data")
    cases = validate_cases(decrypt(encrypted.read_bytes(), private_pem))
    result = io.BytesIO()
    result.write(f"{len(cases)}\n".encode("ascii"))
    for case in cases:
        for field in ("id", "input", "expected"):
            value = case[field].encode("utf-8")
            result.write(f"{len(value)}\n".encode("ascii") + value)
    sys.stdout.buffer.write(result.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    keygen = commands.add_parser("keygen")
    keygen.add_argument("--private-key", type=Path, default=Path("keys/private_key.pem"))
    keygen.add_argument("--public-key", type=Path, default=Path("keys/public_key.pem"))
    for name, key in (("encrypt", "public"), ("decrypt", "private")):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument(f"--{key}-key", type=Path, required=True)
    try:
        if len(sys.argv) == 1:
            validator_frames()
            return
        args = parser.parse_args()
        if args.command == "keygen":
            generate_keys(args.private_key, args.public_key)
        else:
            key_path = args.public_key if args.command == "encrypt" else args.private_key
            if args.output.resolve() in (args.input.resolve(), key_path.resolve()):
                raise ValueError("Output must not overwrite the input or key")
            transform = encrypt if args.command == "encrypt" else decrypt
            data = transform(args.input.read_bytes(), key_path.read_bytes())
            args.output.write_bytes(data)
    except InvalidTag:
        parser.exit(2, "error: Decryption failed: wrong key or modified ciphertext\n")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
