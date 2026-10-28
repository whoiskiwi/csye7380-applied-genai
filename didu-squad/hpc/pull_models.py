"""Download Ollama models straight from the registry, without running an Ollama server.

The Explorer login node kills heavy processes (an Ollama server), and compute nodes have no internet,
so we fetch the manifest and blobs over HTTPS and lay them out the way Ollama stores them:
    <dest>/manifests/registry.ollama.ai/library/<name>/<tag>
    <dest>/blobs/sha256-<hex>
Interrupted downloads resume. Standard library only.

    python hpc/pull_models.py --dest /scratch/$USER/ers/ollama_models qwen2.5:3b qwen2.5:14b
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.ollama.ai/v2/library"
ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"


def _get(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": "ers-pull/1.0", **(headers or {})})
    return urllib.request.urlopen(req, timeout=60)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_blob(name: str, digest: str, size: int, blobs: Path) -> None:
    final = blobs / digest.replace(":", "-")
    if final.exists() and final.stat().st_size == size:
        print(f"  {digest[:19]} already there ({size / 1e9:.2f} GB)")
        return
    part = final.with_suffix(".partial")
    for attempt in range(1, 6):
        have = part.stat().st_size if part.exists() else 0
        if have == size:                                    # finished in an earlier run
            break
        try:
            headers = {"Range": f"bytes={have}-"} if have else {}
            with _get(f"{REGISTRY}/{name}/blobs/{digest}", headers) as r, open(part, "ab" if have else "wb") as f:
                if have and r.status != 206:                # server ignored Range: start over
                    f.seek(0), f.truncate()
                    have = 0
                done, last = have, time.time()
                while chunk := r.read(4 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - last > 5:
                        print(f"  {digest[:19]} {done / 1e9:.2f} / {size / 1e9:.2f} GB", flush=True)
                        last = time.time()
            break
        except Exception as e:                              # network hiccup: resume from where we are
            print(f"  retry {attempt}: {e}", flush=True)
            time.sleep(5)
    if part.stat().st_size != size:
        sys.exit(f"download of {digest} incomplete")
    # Hashing a 9 GB file takes long enough for the login node to kill it, so large blobs are checked by size only
    if size < 2_000_000_000 and _sha256(part) != digest.split(":", 1)[1]:
        part.unlink()
        sys.exit(f"checksum mismatch for {digest}; run again")
    part.rename(final)
    print(f"  {digest[:19]} ok")


def pull(model: str, dest: Path) -> None:
    name, tag = model.split(":") if ":" in model else (model, "latest")
    print(f"{name}:{tag}")
    with _get(f"{REGISTRY}/{name}/manifests/{tag}", {"Accept": ACCEPT}) as r:
        raw = r.read()
    manifest = json.loads(raw)
    blobs = dest / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    for layer in [manifest["config"], *manifest["layers"]]:
        fetch_blob(name, layer["digest"], layer["size"], blobs)
    mpath = dest / "manifests" / "registry.ollama.ai" / "library" / name / tag
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_bytes(raw)                                  # written last, so a model is only visible when complete
    print(f"{name}:{tag} ready")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    for m in args.models:
        pull(m, Path(args.dest))


if __name__ == "__main__":
    main()
