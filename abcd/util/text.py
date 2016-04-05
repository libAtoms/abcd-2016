"""
Text manipulation routines

Functions that manipulate or interpret text in some way.

"""


def filename_enumerator(filename):
    """
    Determine if a filename (or other string) can be formatted with integers
    and return a function that takes an integer as an argument to generate
    enumerated filenames. Will try to format using {} formatting first and
    fall back to % formatting. Returns None for a string that
    cannot be formatted with a number.

    Parameters
    ----------
    filename : str
        The filename.

    Returns
    -------
    formatter : func or None
        A function that takes a number and returns a filename based on the
        filename argument.

    """

    try:
        if filename != filename.format(1):
            # can be {} formatted
            def formatter(number):
                """Format with number."""
                return filename.format(number)
            return formatter
    except (IndexError, ValueError):
        pass

    try:
        if filename != filename % 1:
            # can be % formatted
            def formatter(number):
                """Format with number."""
                return filename % number
            return formatter
    except TypeError:
        pass

    # Unable to format with anything
    return None
