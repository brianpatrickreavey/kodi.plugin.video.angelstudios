"""Start one named check, or every check.

Kodi starts this file. The arguments after the script id are the check name
and a run id from the pytest command:

    RunScript(script.angelstudios.integration-testing,captions,<run id>)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "resources", "lib"))

from runner import main  # noqa: E402

main(sys.argv)
