"""Write the sign-out recovery file without following a symlink.

The path is predictable and the file holds a password. A file that is already
there can be readable by others, and a symlink would point the write at some
other file. This writes a new private file, then replaces the path.
"""

import json
import os
import tempfile


def write_recovery(path, username, password):
    """Replace path with a mode-600 file containing the saved login.

    An existing symlink at path is replaced. The write does not follow it.
    """
    directory = os.path.dirname(path) or "."
    descriptor, temporary = tempfile.mkstemp(prefix=".angel-login-recovery-", dir=directory)
    replaced = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"username": username, "password": password}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        replaced = True
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    finally:
        if not replaced:
            try:
                os.unlink(temporary)
            except OSError:
                pass
