#!/usr/bin/env python3
"""Fail unless a zip unpacks the way Kodi installs an addon."""

import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def main(argv):
    if len(argv) < 4:
        print(
            "usage: check_addon_zip.py ZIP ADDON_ID VERSION [RELATIVE_FILE ...]",
            file=sys.stderr,
        )
        return 2
    zip_path, addon_id, version, *required = argv[1:]
    if version.startswith("v"):
        version = version[1:]

    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            parts = Path(info.filename).parts
            if info.filename.startswith("/") or ".." in parts:
                print(f"unsafe path in zip: {info.filename}", file=sys.stderr)
                return 1
        with tempfile.TemporaryDirectory() as tmp:
            archive.extractall(tmp)
            children = list(Path(tmp).iterdir())
            names = [child.name for child in children]
            if len(children) != 1 or not children[0].is_dir() or children[0].name != addon_id:
                print(
                    f"zip must unpack to one directory named {addon_id}, found {names}",
                    file=sys.stderr,
                )
                return 1
            addon_dir = children[0]
            addon_xml = addon_dir / "addon.xml"
            if not addon_xml.is_file():
                print("addon.xml missing after unpack", file=sys.stderr)
                return 1
            root = ET.parse(addon_xml).getroot()
            if root.tag != "addon" or root.get("id") != addon_id:
                print(f"addon.xml id is {root.get('id')}", file=sys.stderr)
                return 1
            if root.get("version") != version:
                print(
                    f"addon.xml version is {root.get('version')}, expected {version}",
                    file=sys.stderr,
                )
                return 1
            for rel in required:
                path = addon_dir / rel
                if not path.is_file():
                    print(f"missing {rel} after unpack", file=sys.stderr)
                    return 1
    print(f"{zip_path} unpacks as {addon_id} {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
