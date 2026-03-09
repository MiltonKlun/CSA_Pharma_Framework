"""
CSA Evidence Integrity Utilities
Provides cryptographic hashing for all generated evidence files per PIC/S PI 041 §6.9.
"""
import hashlib
import os
from datetime import datetime


def compute_sha256(filepath: str) -> str:
    """Compute a SHA-256 hash of a file, reading in blocks to handle large files efficiently."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def write_sha256_sidecar(filepath: str) -> str:
    """
    Compute the SHA-256 hash of a file and write it to a companion `.sha256` sidecar file.
    The sidecar file contains the hash and metadata for chain-of-custody traceability.

    Returns the computed hash string.
    """
    digest = compute_sha256(filepath)
    sidecar_path = filepath + ".sha256"

    with open(sidecar_path, "w") as f:
        f.write(f"# CSA Evidence Integrity Record\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Regulatory Basis: PIC/S PI 041 §6.9\n")
        f.write(f"SHA256({os.path.basename(filepath)}) = {digest}\n")

    return digest


def verify_sha256_sidecar(filepath: str) -> tuple[bool, str]:
    """
    Verify a file against its `.sha256` sidecar.

    Returns:
        (True, digest) if the file matches the recorded hash.
        (False, error_message) if the file has been tampered with or the sidecar is missing.
    """
    sidecar_path = filepath + ".sha256"

    if not os.path.exists(sidecar_path):
        return False, f"Sidecar not found: {sidecar_path}"

    # Parse the expected hash from the sidecar
    with open(sidecar_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            # Format: "SHA256(filename) = <digest>"
            if "=" in line:
                expected_digest = line.split("=")[1].strip()
                break
        else:
            return False, "Could not parse hash from sidecar file."

    current_digest = compute_sha256(filepath)

    if current_digest == expected_digest:
        return True, current_digest
    else:
        return False, (
            f"INTEGRITY VIOLATION: Hash mismatch for {os.path.basename(filepath)}.\n"
            f"  Expected : {expected_digest}\n"
            f"  Computed : {current_digest}"
        )
