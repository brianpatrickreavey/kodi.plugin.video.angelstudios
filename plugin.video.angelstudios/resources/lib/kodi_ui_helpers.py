"""
Kodi UI Helpers for Angel Studios addon.
Handles UI dialogs, notifications, logging, and utility functions.
"""

import json
import os
import time
from urllib.parse import urlencode

import xbmcgui  # type: ignore
import xbmcvfs  # type: ignore

REDACTED = "<redacted>"

angel_menu_content_mapper = {
    "movies": "movie",
    "series": "series",
    "specials": "special",
}

# Map Angel Studios content types to Kodi content types
kodi_content_mapper = {
    "movies": "movies",
    "series": "tvshows",
    "special": "videos",  # Specials are treated as generic videos
    "podcast": "videos",  # Podcasts are also generic videos
    "livestream": "videos",  # Livestreams are generic videos
}


class KodiUIHelpers:
    """Helper class for Kodi UI operations like dialogs and logging"""

    def __init__(self, parent):
        self.parent = parent
        # Trace directory setup
        profile_path = xbmcvfs.translatePath(self.parent.addon.getAddonInfo("profile"))
        self.trace_dir = os.path.join(profile_path, "temp")

    def show_error(self, message, title="Angel Studios"):
        """Show error dialog to user"""
        xbmcgui.Dialog().ok(title, message)
        self.parent.log.error(f"Error dialog shown: {title} - {message}")

    def show_notification(self, message, title="Angel Studios", time=5000):
        """Show notification to user"""
        xbmcgui.Dialog().notification(title, message, time=time)
        self.parent.log.info(f"Notification shown: {title} - {message}")

    def show_auth_details_dialog(self):
        """Show authentication/session details in a dialog."""
        if not self.parent.angel_interface or not getattr(self.parent.angel_interface, "auth_core", None):
            xbmcgui.Dialog().ok("Angel Studios Session Details", "No session available.")
            return

        try:
            details = self.parent.angel_interface.auth_core.get_session_details()
        except Exception:
            xbmcgui.Dialog().ok("Angel Studios Session Details", "Unable to read session details.")
            return

        login_email = details.get("login_email", "Unknown")
        account_id = details.get("account_id", "Unknown")
        lines = [f"{'Login email:':<18} {login_email}"]
        if account_id:
            lines.append(f"{'Account ID:':<18} {account_id}")

        lines.append(f"{'Authenticated:':<18} {details.get('authenticated', False)}")

        expires_at_local = details.get("expires_at_local", "Unknown")
        expires_at_utc = details.get("expires_at_utc", "Unknown")
        expires_in_td = details.get("expires_in_human", "Unknown")
        expires_in_seconds = details.get("expires_in_seconds")
        issued_at_local = details.get("issued_at_local", "Unknown")
        issued_at_utc = details.get("issued_at_utc", "Unknown")

        lines.append(f"{'Session Issued:':<18} {issued_at_local} ({issued_at_utc})")
        lines.append(f"{'Session Expires:':<18} {expires_at_local} ({expires_at_utc})")

        if isinstance(expires_in_seconds, int):
            days, rem = divmod(expires_in_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if seconds or not parts:
                parts.append(f"{seconds}s")
            human_remaining = " ".join(parts)
            lines.append(f"{'Session Remaining:':<18} {human_remaining} ({expires_in_td})")
        else:
            lines.append(f"{'Session Remaining:':<18} {expires_in_td}")

        if details.get("cookie_names"):
            lines.append("Cookies:")
            for cookie_name in details["cookie_names"]:
                lines.append(f"  - {cookie_name}")

        xbmcgui.Dialog().textviewer("Angel Studios Session Details", "\n".join(lines), usemono=True)

    def clear_debug_data(self):
        """Remove trace files from the temp directory."""
        try:
            if not os.path.isdir(self.trace_dir):
                self.parent.log.info("Trace directory does not exist; nothing to clear")
                return True
            files = [os.path.join(self.trace_dir, f) for f in os.listdir(self.trace_dir)]
            removed = 0
            for path in files:
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        removed += 1
                except Exception:
                    pass
            self.parent.log.info(f"Cleared {removed} trace files from {self.trace_dir}")
            return True
        except Exception as e:
            self.parent.log.error(f"Failed to clear debug data: {e}")
            return False

    def clear_debug_data_with_notification(self):
        """Clear debug trace files and log outcome; notify on success."""
        result = self.clear_debug_data()
        if result:
            self.show_notification("Debug data cleared.")
            self.parent.log.info("Debug data cleared via settings")
        else:
            self.parent.log.error("Debug data clear failed via settings")

    def force_logout_with_notification(self):
        """Force local logout via angel_interface and notify user."""
        if not self.parent.angel_interface:
            raise ValueError("Angel interface not initialized")
        result = self.parent.angel_interface.force_logout()
        if result:
            xbmcgui.Dialog().ok(
                "Angel Studios - Force Logout",
                "Successfully logged out.\n\nSession details may not update immediately.\nRestart the addon to see changes.",
            )
            self.parent.log.info("Logged out locally via settings")
        else:
            xbmcgui.Dialog().ok("Angel Studios - Force Logout", "Logout failed; please try again.")
            self.parent.log.error("Logout failed via settings")

    def _get_debug_mode(self):
        """Return debug mode setting: 'off', 'debug', or 'trace'."""
        try:
            value = self.parent.addon.getSettingString("debug_mode")
        except Exception as exc:
            self.parent.log.warning(f"debug_mode read failed; defaulting to off: {exc}")
            value = "off"

        value = (value or "off").lower()
        return value if value in {"off", "debug", "trace"} else "off"

    def _is_debug(self):
        """Return True when debug mode is enabled."""
        return self._get_debug_mode() in ("debug", "trace")

    def _is_trace(self):
        """Return True only when trace mode is enabled."""
        return self._get_debug_mode() == "trace"

    def _ensure_trace_dir(self):
        """Ensure the trace directory exists if trace mode is active.

        Returns True when the directory is present or created successfully,
        False otherwise.
        """
        if not self._is_trace():
            return False

        try:
            os.makedirs(self.trace_dir, exist_ok=True)
            return True
        except Exception as e:
            self.parent.log.error(f"Failed to create trace directory {self.trace_dir}: {e}")
            return False

    def _redact_sensitive(self, data):
        """Redact sensitive data from logs and traces."""
        if isinstance(data, dict):
            redacted = {}
            for key, val in data.items():
                key_lower = str(key).lower()
                if any(secret in key_lower for secret in ("password", "authorization", "cookie", "token")):
                    redacted[key] = REDACTED
                else:
                    redacted[key] = self._redact_sensitive(val)
            return redacted
        if isinstance(data, list):
            return [self._redact_sensitive(item) for item in data]
        if isinstance(data, str):
            data_lower = data.lower()
            if any(secret in data_lower for secret in ("password", "authorization", "cookie", "token")):
                return REDACTED
            return data
        return data

    def _trim_trace_files(self, max_files=50):
        """Trim trace files to max_files by removing oldest."""
        if not self._is_trace():
            return

        try:
            if not os.path.isdir(self.trace_dir):
                return

            files = [
                os.path.join(self.trace_dir, f)
                for f in os.listdir(self.trace_dir)
                if os.path.isfile(os.path.join(self.trace_dir, f))
            ]
            if len(files) <= max_files:
                return

            # Sort by modification time, oldest first
            files.sort(key=os.path.getmtime)
            to_remove = files[:-max_files]  # Keep the newest max_files

            for path in to_remove:
                try:
                    os.remove(path)
                    self.parent.log.debug(f"Trimmed old trace file: {os.path.basename(path)}")
                except Exception as e:
                    self.parent.log.warning(f"Failed to remove trace file {path}: {e}")

        except Exception as e:
            self.parent.log.error(f"Failed to trim trace files: {e}")

    def _trace_callback(self, payload):
        """Callback to write trace payload to file."""
        if not self._is_trace():
            return

        try:
            if not self._ensure_trace_dir():
                return

            # Generate filename with timestamp
            safe_payload = self._redact_sensitive(payload)
            ts = time.strftime("%Y%m%dT%H%M%S")
            fname = f"trace_{ts}_{int(time.time()*1000) % 1000}.json"
            filepath = os.path.join(self.trace_dir, fname)

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(safe_payload, f, indent=2)

            self.parent.log.debug(f"Trace written to {filepath}")

            # Trim old files
            self._trim_trace_files()

        except Exception as e:
            self.parent.log.error(f"Failed to write trace: {e}")

    def get_trace_callback(self):
        """Return the trace callback function if trace mode is enabled."""
        if self._is_trace():
            return self._trace_callback
        return None

    def _normalize_contentseries_episode(self, episode):
        """Normalize ContentSeries episode dict to expected keys."""
        if not isinstance(episode, dict):
            return {}
        keys = {
            "id",
            "name",
            "subtitle",
            "description",
            "episodeNumber",
            "portraitStill1",
            "landscapeStill1",
            "landscapeStill2",
        }
        return {k: episode[k] for k in keys if k in episode}

    def create_plugin_url(self, **kwargs):
        """Create a plugin URL with query parameters."""
        return self.parent.kodi_url + "?" + urlencode(kwargs)

    def _get_angel_project_type(self, menu_content_type):
        """Map menu content type to Angel Studios project type."""
        return angel_menu_content_mapper.get(menu_content_type, menu_content_type)

    def _get_kodi_content_type(self, content_type):
        """Map Angel Studios content type to Kodi content type."""
        return kodi_content_mapper.get(content_type, "videos")

    def setAngelInterface(self, angel_interface):
        """Update the angel interface reference."""
        self.parent.angel_interface = angel_interface
