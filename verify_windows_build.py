"""Check the real PyInstaller EXE without printing embedded OAuth data."""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "dist" / "ED Hotspots & Landables Finder.exe"


def verify_archive():
    import pefile
    from PyInstaller.archive.readers import CArchiveReader

    if sys.platform != "win32":
        raise RuntimeError("The release executable must be verified on Windows")
    archive = CArchiveReader(str(EXE))
    for name in ("credentials.json", "logo.png"):
        if name not in archive.toc:
            raise RuntimeError("Missing embedded resource: " + name)
        if archive.extract(name) != (ROOT / name).read_bytes():
            raise RuntimeError("Embedded resource differs from build input: " + name)
    forbidden = {"token.json", "config.json"}
    if any(name.replace("\\", "/").split("/")[-1] in forbidden for name in archive.toc):
        raise RuntimeError("Personal token or configuration found in the EXE")

    with pefile.PE(str(EXE)) as pe:
        if pe.FILE_HEADER.Machine != 0x8664:
            raise RuntimeError("Expected a 64-bit Windows executable")
        resources = {entry.id for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}
        if not {3, 14, 16}.issubset(resources):
            raise RuntimeError("Windows icon or version resources are missing")
        info = pe.VS_FIXEDFILEINFO[0]
        if (info.FileVersionMS, info.FileVersionLS) != (7, 11 << 16):
            raise RuntimeError("Expected Windows file version 0.7.11.0")
    print("Verified Windows x64 EXE, version, icon, embedded client and logo.")


def smoke_test():
    # Launch away from the source directory, with empty per-user storage and
    # no sidecar credentials. No Google sign-in or scan is performed here.
    with tempfile.TemporaryDirectory(prefix="hf-smoke-") as temp:
        env = os.environ.copy()
        env["APPDATA"] = temp
        env["HF_SMOKE_EXE"] = str(EXE)
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        proc = subprocess.Popen([str(EXE)], cwd=temp, env=env)
        try:
            deadline = time.monotonic() + 45
            opened = False
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError("The EXE exited before its main window opened")
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "$p = Get-Process -ErrorAction SilentlyContinue | "
                     "Where-Object { $_.Path -eq $env:HF_SMOKE_EXE -and "
                     "$_.MainWindowTitle -eq 'Hotspots & Landables Finder' }; "
                     "if ($p) { exit 0 } else { exit 1 }"],
                    env=env, capture_output=True, timeout=15,
                )
                if result.returncode == 0:
                    opened = True
                    break
                time.sleep(1)
            if not opened:
                raise RuntimeError("The main GUI window was not detected")
            if not (Path(temp) / "HotspotsFinder").is_dir():
                raise RuntimeError("Per-user AppData directory was not created")
            print("GUI opened without sidecar files and created its own AppData folder.")
        finally:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True, check=False,
            )
            proc.wait(timeout=15)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    verify_archive()
    if args.smoke:
        smoke_test()
