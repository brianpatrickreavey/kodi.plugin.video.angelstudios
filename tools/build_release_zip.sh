#!/bin/bash
# Build the GitHub Release zip and fail unless Kodi could install it.
# Usage: tools/build_release_zip.sh ADDON_ID [vX.Y.Z]
# With no tag, the version is read from addon.xml.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
addon_id=${1:?addon id}
requested=${2:-}

if [[ -f addon.xml ]]; then
  xml=addon.xml
  nested=0
elif [[ -f "${addon_id}/addon.xml" ]]; then
  xml="${addon_id}/addon.xml"
  nested=1
else
  echo "addon.xml not found for ${addon_id}" >&2
  exit 1
fi

if [[ -n "$requested" ]]; then
  version=${requested#v}
else
  version=$(python3 -c 'import sys, xml.etree.ElementTree as ET; print(ET.parse(sys.argv[1]).getroot().get("version"))' "$xml")
fi

out="${addon_id}-v${version}.zip"
rm -f "$out"
if [[ "$nested" -eq 1 ]]; then
  git archive --format=zip --output="$out" HEAD "$addon_id"
else
  git archive --format=zip --prefix="${addon_id}/" --output="$out" HEAD
fi
python3 "$root/tools/check_addon_zip.py" "$out" "$addon_id" "$version"
