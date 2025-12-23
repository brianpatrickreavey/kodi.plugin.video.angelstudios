#!/usr/bin/env python3

import semver
import re
import sys

ADDON_XML = "plugin.video.angelstudios/addon.xml"

# Read current version
with open(ADDON_XML, 'r') as f:
    content = f.read()
match = re.search(r'<addon[^>]*version="([^"]+)"', content)
if not match:
    print("Version not found in addon.xml")
    sys.exit(1)
current = match.group(1)
print(f"Current version: {current}")

# Prompt for bump type
bump_type = input("Bump type (major/minor/patch): ").strip().lower()
if bump_type not in ['major', 'minor', 'patch']:
    print("Invalid type")
    sys.exit(1)

# Calculate new version
v = semver.VersionInfo.parse(current)
if bump_type == 'major':
    new_v = v.bump_major()
elif bump_type == 'minor':
    new_v = v.bump_minor()
elif bump_type == 'patch':
    new_v = v.bump_patch()
else:
    print("Invalid type")
    sys.exit(1)
new_version = str(new_v)
print(f"New version: {new_version}")

news_text = input("Enter news for this version: ")

# Update addon.xml version number
replacement_version = r'\g<1>' + new_version + r'\g<2>'
updated_content = re.sub(r'(<addon[^>]*version=")[^"]+(")', replacement_version, content)
# Update addon.xml news section
replacement_news = r'\g<1>' + new_version + ' - ' + news_text + r'\g<2>'
updated_content = re.sub(r'(<news>)[^<]*(</news>)', replacement_news, updated_content)

# Write updated content to addon.xml
with open(ADDON_XML, 'w') as f:
    f.write(updated_content)
print(f"Updated from {current} to {new_version}")
print(f"News: {news_text}")