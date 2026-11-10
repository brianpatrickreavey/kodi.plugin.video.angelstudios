"""Show Next Episode over the playing video without taking Select away from the OSD.

Focus stays on an off-screen control. Up moves to the Next Episode button.
Select on that button plays the next title. Select anywhere else opens the
player controls. The dialog closes during the intro so Up seeks again.
"""

import json
from typing import Any, Callable, Optional, Tuple

import xbmc  # type: ignore
import xbmcgui  # type: ignore

from next_episode import NEXT_EPISODE_LABEL, handle_playback_action

_PASSTHROUGH_ID = 100
_BUTTON_ID = 200
_TITLE_ID = 302

# 1920x1080 layout. The end card is the same button, larger, with the title above it.
_PLAYER_CONTROL_BOX = (1492, 790, 380, 70)
_END_CARD_BOX = (1312, 896, 560, 88)
_TITLE_BOX = (1312, 848, 560, 40)

_BUILTINS = {
    "osd": "Action(OSD)",
    "pause": "PlayerControl(Play)",
    "stop": "PlayerControl(Stop)",
    "info": "Action(Info)",
    "volumeup": "Action(VolumeUp)",
    "volumedown": "Action(VolumeDown)",
    "mute": "Action(Mute)",
}
_SEEK_VALUES = {"smallbackward", "smallforward", "bigbackward", "bigforward"}


def _localized_label(addon: object) -> str:
    """Return the settings label, or the English words when Kodi has no string."""
    getter = getattr(addon, "getLocalizedString", None)
    if not callable(getter):
        return NEXT_EPISODE_LABEL
    try:
        text = getter(30126)
    except Exception:
        return NEXT_EPISODE_LABEL
    if isinstance(text, str):
        stripped = text.strip()
        if stripped and stripped != "30126":
            return stripped
    return NEXT_EPISODE_LABEL


def _action_id(action: object) -> Optional[int]:
    getter = getattr(action, "getId", None)
    if not callable(getter):
        return None
    try:
        value = getter()
    except Exception:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _control_id(control: object) -> Optional[int]:
    getter = getattr(control, "getId", None)
    if not callable(getter):
        return None
    try:
        value = getter()
    except Exception:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _open_dialog(overlay: "NextEpisodeOverlay", addon: object) -> Any:
    """Build the skin dialog. Tests pass a dialog_factory instead of reaching this."""
    window_type = getattr(xbmcgui, "WindowXMLDialog", None)
    if not isinstance(window_type, type):
        raise RuntimeError("Next Episode dialog is not available")

    class NextEpisodeDialog(window_type):  # type: ignore[misc]
        def onInit(self):  # type: ignore[no-untyped-def]  # noqa: N802
            overlay.on_init()

        def onAction(self, action):  # type: ignore[no-untyped-def]  # noqa: N802
            overlay.on_action(action)

        def onControl(self, control):  # type: ignore[no-untyped-def]  # noqa: N802
            overlay.on_control(control)

    path = ""
    info = getattr(addon, "getAddonInfo", None)
    if callable(info):
        found = info("path")
        if isinstance(found, str):
            path = found
    return NextEpisodeDialog("NextEpisode.xml", path, "Default", "1080i")


class NextEpisodeOverlay:
    """The Next Episode button and end card for one playback."""

    def __init__(self, addon: object, player: object, log: object, dialog_factory: Optional[Callable[[], Any]] = None):
        self.addon = addon
        self.player = player
        self.log = log
        self._dialog_factory = dialog_factory
        self._label = _localized_label(addon)
        self.chosen = False
        self._applying = False
        self._dismissed = False
        self._failed = False
        self._shown = False
        self._dialog: Any = None
        self._pending: Any = None
        self._focus_on_open = False
        self._controls_waiting = False
        self._logged: Optional[Tuple[bool, bool, str]] = None

    def update(self, state: Any) -> None:
        """Show, move, or hide the offer for this playhead position."""
        if self._dismissed or self._failed or self.chosen:
            return
        self._log_state(state)
        if not state.player_control and not state.end_card:
            self.close()
            return
        try:
            self._show(state)
        except Exception as exc:
            self._failed = True
            self._warn(f"Next Episode offer could not be shown: {exc}")
            self.close()

    def close(self) -> None:
        """Hide the dialog. Safe to call when it is already hidden."""
        was_shown = self._shown
        self._shown = False
        self._pending = None
        self._focus_on_open = False
        if not was_shown or self._dialog is None:
            return
        closer = getattr(self._dialog, "close", None)
        if not callable(closer):
            return
        try:
            closer()
        except Exception as exc:
            self._warn(f"Next Episode offer could not be closed: {exc}")

    def on_init(self) -> None:
        """Apply the offer once Kodi has created the dialog controls."""
        pending = self._pending
        if pending is not None:
            self._apply(pending)
        if not self._focus_on_open:
            return
        self._focus_on_open = False
        try:
            self._set_focus(_PASSTHROUGH_ID)
        except Exception:
            return

    def on_action(self, action: object) -> None:
        """Translate one remote action into a player or offer command."""
        if self._applying or self._failed or self.chosen or self._dismissed:
            return
        action_id = _action_id(action)
        if action_id is None:
            return
        command = handle_playback_action(action_id, self._focused_on_button())
        if command is None:
            return
        self._handle(command)

    def on_control(self, control: object) -> None:
        """A click on the Next Episode button plays the next title."""
        if self._applying or self._failed or self.chosen or self._dismissed:
            return
        if _control_id(control) == _BUTTON_ID:
            self._handle("choose")

    def _show(self, state: Any) -> None:
        """Open the dialog, then lay out the controls.

        Kodi creates the controls in onInit. getControl before that raises
        Non-Existent Control, so a miss here waits for onInit or the next tick.
        """
        dialog = self._ensure_dialog()
        self._pending = state
        opening = not self._shown or not self._is_active(dialog)
        if opening:
            # Mark it shown before show() so a failure still gets closed.
            self._shown = True
            self._focus_on_open = True
            dialog.show()
        if self._apply(state) and self._focus_on_open:
            self._focus_on_open = False
            self._set_focus(_PASSTHROUGH_ID)

    def _apply(self, state: Any) -> bool:
        """Move the button and title. False means the controls are not created yet."""
        dialog = self._dialog
        if dialog is None:
            return False
        try:
            button = dialog.getControl(_BUTTON_ID)
            title = dialog.getControl(_TITLE_ID)
        except Exception as exc:
            self._note_controls_waiting(exc)
            return False
        self._controls_waiting = False
        button.setLabel(self._label)
        if state.end_card:
            self._place(button, _END_CARD_BOX)
            self._place(title, _TITLE_BOX)
            title.setLabel(state.title)
            title.setVisible(True)
        else:
            self._place(button, _PLAYER_CONTROL_BOX)
            title.setVisible(False)
        return True

    def _note_controls_waiting(self, exc: Exception) -> None:
        if self._controls_waiting:
            return
        self._controls_waiting = True
        self._warn(f"Next Episode controls are not ready: {exc}")

    def _ensure_dialog(self) -> Any:
        if self._dialog is not None:
            return self._dialog
        if self._dialog_factory is not None:
            dialog = self._dialog_factory()
        else:
            dialog = _open_dialog(self, self.addon)
        self._dialog = dialog
        return dialog

    def _handle(self, command: str) -> None:
        if self._applying:
            return
        self._applying = True
        try:
            if command == "choose":
                self._choose()
            elif command == "focus":
                self._set_focus(_BUTTON_ID)
            elif command == "unfocus":
                self._set_focus(_PASSTHROUGH_ID)
            elif command == "back":
                self._back()
            elif command in _SEEK_VALUES:
                self._seek(command)
            elif command in _BUILTINS:
                self._builtin(_BUILTINS[command])
        finally:
            self._applying = False

    def _choose(self) -> None:
        """Stop this episode. The monitor then opens the next title at the beginning."""
        if self.chosen:
            return
        self.chosen = True
        self.close()
        stopper = getattr(self.player, "stop", None)
        if not callable(stopper):
            return
        try:
            stopper()
        except Exception as exc:
            self._warn(f"Could not stop playback for the next episode: {exc}")

    def _back(self) -> None:
        """Leave the video. This is a stop, so the next title must not auto-start."""
        self._dismissed = True
        self.close()
        self._builtin("Action(Back)")

    def _seek(self, value: str) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Player.Seek",
            "params": {"playerid": 1, "value": value},
        }
        try:
            xbmc.executeJSONRPC(json.dumps(request))
        except Exception as exc:
            self._warn(f"Could not seek: {exc}")

    def _builtin(self, command: str) -> None:
        try:
            xbmc.executebuiltin(command)
        except Exception as exc:
            self._warn(f"Could not run {command}: {exc}")

    def _focused_on_button(self) -> bool:
        dialog = self._dialog
        if dialog is None:
            return False
        getter = getattr(dialog, "getFocusId", None)
        if not callable(getter):
            return False
        try:
            return getter() == _BUTTON_ID
        except Exception:
            return False

    def _set_focus(self, control_id: int) -> None:
        dialog = self._dialog
        if dialog is None:
            return
        setter = getattr(dialog, "setFocusId", None)
        if not callable(setter):
            return
        setter(control_id)

    def _is_active(self, dialog: object) -> bool:
        active = getattr(dialog, "isActive", None)
        if not callable(active):
            return self._shown
        try:
            return active() is True
        except Exception:
            return self._shown

    def _place(self, control: Any, box: Tuple[int, int, int, int]) -> None:
        left, top, width, height = box
        control.setPosition(left, top)
        control.setWidth(width)
        control.setHeight(height)

    def _log_state(self, state: Any) -> None:
        key = (bool(state.player_control), bool(state.end_card), state.title if state.end_card else "")
        if key == self._logged:
            return
        self._logged = key
        if state.end_card:
            self.log.info(f"Next Episode end card: {state.title}")
        elif state.player_control:
            self.log.info("Next Episode")
        else:
            self.log.info("Next Episode hidden")

    def _warn(self, message: str) -> None:
        warning = getattr(self.log, "warning", None)
        if callable(warning):
            warning(message)
