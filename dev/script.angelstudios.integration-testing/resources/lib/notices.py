"""Build one on-screen step notice. The text cannot contain a comma."""


def step_notice(number, total, text):
    """Return the notice title and the message for this step of the run."""
    return f"Test {number} of {total}", f"{number}. {text}"
