#!/usr/bin/env python3
"""BriefBot Cookie Bridge - Setup Script.

One-time setup that:
1. Creates a .bat wrapper for the native messaging host (Windows requirement)
2. Writes the native messaging host manifest (com.briefbot.cookies.json)
3. Registers the host in Windows registry

Usage:
    python setup.py <chrome-extension-id>

The extension ID is shown on chrome://extensions after loading the
BriefBot Cookie Bridge extension as an unpacked extension.

Example:
    python setup.py abcdefghijklmnopabcdefghijklmnop
"""

import json
import os
import shutil
import sys
import winreg
from pathlib import Path

HOST_NAME = "com.briefbot.cookies"
HOST_DIR = Path(__file__).parent / "host"
HOST_SCRIPT = HOST_DIR / "briefbot_cookie_host.py"


def find_python() -> str:
    """Find the Python executable path."""
    # Try python3 first, then python
    for name in ("python3", "python"):
        path = shutil.which(name)
        if path:
            return path
    # Fallback to current interpreter
    return sys.executable


def create_bat_wrapper(python_path: str) -> Path:
    """Create a .bat wrapper that Chrome can invoke as native messaging host."""
    bat_path = HOST_DIR / "briefbot_cookie_host.bat"
    script_path = str(HOST_SCRIPT).replace("/", "\\")
    python_path = python_path.replace("/", "\\")

    bat_content = f'@echo off\n"{python_path}" "{script_path}"\n'
    with open(bat_path, "w") as f:
        f.write(bat_content)

    print(f"  Created batch wrapper: {bat_path}")
    return bat_path


def write_host_manifest(bat_path: Path, extension_id: str) -> Path:
    """Write the native messaging host manifest JSON."""
    manifest_path = HOST_DIR / f"{HOST_NAME}.json"

    manifest = {
        "name": HOST_NAME,
        "description": "BriefBot Cookie Bridge - exports X/Twitter cookies for search",
        "path": str(bat_path).replace("/", "\\"),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Created host manifest: {manifest_path}")
    return manifest_path


def register_in_registry(manifest_path: Path):
    """Register the native messaging host in Windows registry (HKCU)."""
    reg_key = f"SOFTWARE\\Google\\Chrome\\NativeMessagingHosts\\{HOST_NAME}"
    manifest_str = str(manifest_path).replace("/", "\\")

    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_str)
        winreg.CloseKey(key)
        print(f"  Registered in registry: HKCU\\{reg_key}")
    except PermissionError:
        print(f"  ERROR: Could not write to registry. Run as administrator?")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("BriefBot Cookie Bridge Setup")
        print("=" * 40)
        print()
        print("Usage: python setup.py <chrome-extension-id>")
        print()
        print("Steps:")
        print("  1. Open Chrome and go to chrome://extensions")
        print("  2. Enable 'Developer mode' (top-right toggle)")
        print("  3. Click 'Load unpacked' and select:")
        ext_dir = str(Path(__file__).parent / "extension").replace("/", "\\")
        print(f"     {ext_dir}")
        print("  4. Copy the extension ID (32-character string shown under the extension)")
        print("  5. Run: python setup.py <that-id>")
        print()
        sys.exit(1)

    extension_id = sys.argv[1].strip().lower()

    # Validate extension ID (32 lowercase letters a-p)
    if len(extension_id) != 32 or not all(c in "abcdefghijklmnop" for c in extension_id):
        print(f"ERROR: Invalid extension ID: {extension_id}")
        print("Extension IDs are 32 characters using only letters a-p.")
        print("Find it on chrome://extensions after loading the extension.")
        sys.exit(1)

    print("BriefBot Cookie Bridge Setup")
    print("=" * 40)

    # Step 1: Find Python
    python_path = find_python()
    print(f"\n  Using Python: {python_path}")

    # Step 2: Create .bat wrapper
    bat_path = create_bat_wrapper(python_path)

    # Step 3: Write host manifest
    manifest_path = write_host_manifest(bat_path, extension_id)

    # Step 4: Register in Windows registry
    register_in_registry(manifest_path)

    print()
    print("Setup complete!")
    print()
    print("The extension will now automatically export X/Twitter cookies")
    print("to ~/.config/briefbot/.env whenever you're logged into X in Chrome.")
    print("BriefBot's Bird search will pick them up automatically.")


if __name__ == "__main__":
    main()
