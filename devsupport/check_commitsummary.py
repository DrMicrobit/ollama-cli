#!/usr/bin/env python3

"""Simplistic script to check summary line of a commit-msg for adhering
(mostly) to Conventional Commits style. Does NOT check body of commit message.

Developed to run with any basic install of python with python standard libs,
no other dependecies.

Usage:
  check_commitsummary.py filename

Exits with 0 if all seems ok
Else exit code is 1 and reasons found are printed to stdout.

This is ready to run, e.g., in a git commit-msg hook.
"""

import re
import sys

# using a dict instead of a set to guarantee ordering
ALLOWED_COMMIT_TYPES = {
    # things possibly impacting user
    "feat": None,
    "fix": None,
    "docs": None,
    "perf": None,
    # things interesting developers only (mostly)
    "test": None,
    "style": None,
    "refactor": None,
    "chore": None,
    "build": None,
    "ci": None,
    "ops": None,
    "revert": None,
}

MAX_SUMLINE_LEN = 72
MAX_SCOPE_LEN = 20

# ----------------------------------------------------------------------------
# No user serviceable part below this line
# ----------------------------------------------------------------------------


# Yes, this function has too many branches ... idc atm
def check_commit_summary_line(line: str) -> list[tuple[str, str]]:  # noqa: PLR0912
    """Check a line with commit summary rules.

    On success returns empty list.
    On failure returns list of possible causes as tuple (short error code, longer message for user)
    Will try to collect as many causes as possible.
    """

    retval: list[tuple[str, str]] = []

    # full line lengthcheck first to allow early return after following regex
    #  (which does not check line length)

    if len(line) > MAX_SUMLINE_LEN:
        retval.append(
            ("max_line_len", f"The commit summary line is longer than {MAX_SUMLINE_LEN} characters!")
        )

    # Check the whole line with a regex first. Only try to find the likely cause
    #   if the regex fails ...

    allowed_commit_types = "|".join(ALLOWED_COMMIT_TYPES)
    re_sumline = rf"^({allowed_commit_types})(\(.{{1,{MAX_SCOPE_LEN}}}\))?[!]?: [^ ].+"

    if len(retval) == 0 and re.match(re_sumline, line):
        # All good, we can return
        return retval

    # OK there is a problem. Let's try to find out why.

    sumline_precolon = line
    if ":" not in line:
        retval.append(("no_colon", "The commit summary line does not contain a colon!"))
    else:
        sumline_precolon, sumline_postcolon = line.split(":", 1)
        if len(sumline_postcolon.strip()) == 0:
            retval.append(
                ("no_desc", f'The commit summary line has no description after\n  "{sumline_precolon}"')
            )
        if len(sumline_postcolon) > 0 and sumline_postcolon[0] != " ":
            retval.append(
                ("no_blank_after_colon", f'The commit summary line has no blank after the colon\n  "{line}"')
            )
        if len(sumline_postcolon) > 1 and sumline_postcolon[1] == " ":
            retval.append(
                (
                    "more_blanks_after_colon",
                    f'The commit summary line has more than one blank after the colon\n  "{line}"',
                )
            )
        del sumline_postcolon

    has_scope = False
    has_scope_close = False
    if "(" in sumline_precolon:
        if ")" in sumline_precolon:
            has_scope_close = True
        else:
            retval.append(
                (
                    "no_scope_close",
                    f'Missing closing bracket for scope in this part:\n\n  "{sumline_precolon}"',
                )
            )
        has_scope = True
        commit_type = sumline_precolon.split("(")[0]
    else:
        commit_type = sumline_precolon

    if commit_type not in ALLOWED_COMMIT_TYPES:
        atypes = "|".join(ALLOWED_COMMIT_TYPES)
        errmsg = [f"Bad commit type. You gave type '{commit_type}', but it must be one of\n  {atypes}"]
        if any(blank in commit_type for blank in " \t\r\n"):
            errmsg.append("\nWatch out, there were blanks in your type, that is not allowed.")
        retval.append(("bad_type", "".join(errmsg)))

    # at this point, either the scope itself or some additional characters after scope
    #  are the culprit
    if has_scope:
        scope = sumline_precolon.split("(", 1)[1]
        if has_scope_close:
            scope = scope[: scope.rfind(")")]
        if len(scope) > MAX_SCOPE_LEN:
            retval.append(
                (
                    "scope_len",
                    f"The scope needs to have between 1 and {MAX_SCOPE_LEN} characters. Your scope"
                    f'\n  "{scope}"'
                    f"\nhas {len(scope)} characters",
                )
            )
        # if there was a closing bracket, it could be characters after it
        if has_scope_close:
            sumline_lastchars = sumline_precolon.split(")")[-1]
            if sumline_lastchars != "!":
                retval.append(
                    (
                        "after_scope",
                        "After the scope, only an optional exclamation mark is allowed before the colon."
                        f'\nYou have:\n  "{sumline_lastchars}"'
                        f'\nafter the scope.\n  "{sumline_precolon}"',
                    )
                )

    return retval


def exit_errmsg(msg: str) -> None:  # pragma: no cover
    """Print reason for failing check and exit with status code 1"""
    print(
        "Summary line does not follow Conventional Commits standard."
        f"\nSpecifically:\n--\n{msg}"
        "\n--"
        "\nExamples for valid commit summary lines:"
        '\n"fix: [your text]"\n"fix(scope)!: [your text]"'
    )
    sys.exit(1)


def main() -> None:  # pragma: no cover
    """Simplistic main"""
    with open(sys.argv[1], encoding="utf-8") as fin:  # noqa: PTH123
        ret = check_commit_summary_line(fin.readline().rstrip("\r\n"))
        if len(ret) > 0:
            exit_errmsg("\n--\n".join([m for c, m in ret]))


if __name__ == "__main__":  # pragma: no cover
    main()
