#!/usr/bin/env python3

"""Reads a text from stdin and pipes it to Ollama. One can set all
Ollama options on commandline as well as define termination criteria in terms of
maximum number of lines, paragraphs, or repeated lines."""

import argparse
import sys

# Jan 2025. Weird pylint E0401 bug, see https://github.com/pylint-dev/pylint/issues/10112
from collections.abc import Callable, Iterable  # pylint: disable = E0401
from pathlib import Path
from typing import Any

import httpx
import ollama
from dm_ollamalib.optionhelper import help_long, help_overview, to_ollama_options
from dm_streamvalve.streamvalve import StopCriterion, StreamValve

from ollama_cli import __version__


def parse_cmd_line() -> argparse.Namespace:
    """Setup of commandline parser"""

    parser = argparse.ArgumentParser(
        usage="%(prog)s [options]",
        description=(
            "Reads a text from stdin and pipes it to Ollama. One can set all"
            " Ollama options on commandline as well as define termination criteria in terms of"
            " maximum number of lines, paragraphs, or repeated lines."
        ),
    )

    parser.add_argument(
        "-v",
        "--version",
        default=False,
        action="store_true",
        help=("print version of %(prog)s and exit."),
    )
    parser.add_argument(
        "--opthelp",
        default=False,
        action="store_true",
        help=("show a list of Ollama options that can be set via --opts and exit."),
    )
    parser.add_argument(
        "--optdesc",
        default=False,
        action="store_true",
        help=(
            "show a list of Ollama options and descriptions (if available) that can be"
            " set via --opts and exit."
        ),
    )

    group = parser.add_argument_group("Ollama setup options")
    group.add_argument(
        "--sysmsg",
        default=(
            "You are a helpful assistant. Answer the request of the user succinctly and diligently."
            " Do not repeat the task given to you or announce your result."
        ),
        type=str,
        metavar="TXT",
        help=(
            "In case no --sysin (see below) given, the Ollama model will get this text"
            ' as SYSTEM message. Default: "%(default)s"'
        ),
    )
    group.add_argument(
        "--sysin",
        default="",
        type=str,
        metavar="FILENAME",
        help=(
            "Name of a text file with an Ollama SYSTEM msg to prime the model. Overrides"
            " --sysmsg (see above)"
        ),
    )
    group.add_argument(
        "--model",
        default="llama3.1:8b-instruct-q8_0",
        metavar="NAME",
        type=str,
        help="Use Ollama model <NAME>. Default: %(default)s",
    )
    group.add_argument(
        "--opts",
        default="",
        metavar="OPTS",
        type=str,
        help=(
            "Semicolon separated list of options for Ollama."
            ' E.g.: --options="num_ctx=16384;temperature=0.0"'
            ' Default: "%(default)s"'
        ),
    )

    group = parser.add_argument_group("Early termination options")
    group.add_argument(
        "--max-linerepeats",
        default=3,
        metavar="INT",
        type=int,
        help=(
            "Used to prevent models eventually getting stuck in endless loops of repeated lines."
            " If >0, stop after this number of non-blank lines that are exact repeats of previous"
            " lines. Lines do not need to be following each other to be spotted as repeats."
            " Default: %(default)i"
        ),
    )
    group.add_argument(
        "--max-lines",
        default=200,
        metavar="INT",
        type=int,
        help=(
            "To prevent endless output. If >0, stop after this number of lines."
            " Default: %(default)i"
        ),
    )
    group.add_argument(
        "--max-paragraphs",
        default=0,
        metavar="INT",
        type=int,
        help=(
            "To prevent endless diverse output. If >0, stop after this number of paragraphs."
            " Default: %(default)i"
        ),
    )

    group = parser.add_argument_group("Output options")
    group.add_argument(
        "--tostderr",
        default=False,
        action="store_true",
        help=(
            "Redirect the streaming monitoring output to stderr. The final result will be output"
            " to stdout once completed. This is useful in combination with termination options"
            " --max_* where,"
            " in case the termination criterion triggered, stdout will contain the output without"
            " the line which led to the termination. "
        ),
    )

    group = parser.add_argument_group("Connection options")
    group.add_argument(
        "--host",
        default="",
        type=str,
        help=(
            "The default empty string will connect to 'localhost:11434' where Ollama"
            " is usually installed. Set this to connect to any other Ollama server you have"
            " access to."
            ' Default: "%(default)s"'
        ),
    )

    opts = parser.parse_args()

    return opts


def setup_ollama(
    sysmsg: str, usrmsg: str, model: str, params: ollama.Options, host: str | None = None
) -> Iterable[ollama.ChatResponse]:
    """Starts an Ollama model and returns a stream to it
    Parameters:
    - sysmsg: string with SYSTEM message for Ollama
    - usrmsg: string with USER message for Ollama
    - model: model to run with ollama
    - params: ollama parameter structure
    """

    try:
        client = ollama.Client(host=host)
        ostream: Iterable[ollama.ChatResponse] = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": sysmsg},
                {"role": "user", "content": f"{usrmsg}\n"},
            ],
            options=params,
            stream=True,
        )
    except Exception as err:
        raise RuntimeError("Could not connect to ollama?") from err

    # we get an ostream object back regardless whether there's a working
    #  Ollama server present ... ouch.

    return ostream


def monitor_accepted_chat_response_stdout(s: str):
    """Callback for streamvalve to monitor chat response"""
    print(s, end="", flush=True)


def monitor_accepted_chat_response_stderr(s: str):
    """Callback for streamvalve to monitor chat response"""
    print(s, file=sys.stderr, end="", flush=True)


def run_ostream_via_streamvalve(
    ostream: Iterable[ollama.ChatResponse],
    max_linerepeats: int = 0,
    max_lines: int = 0,
    max_paragraphs: int = 0,
    monitor_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Setup a StreamValve and run the Ollama stream through it. Try to handle known errors
    gracefully with a message and a sys.exit(1)

    Return:
    - the return value from streamvalve

    Parameters:
    - ostream: an Iterable[ChatResponse]. Basically the return value of ollama.chat()
    - max_linerepeats: if >0, stop after this number of non-empty lines that are repeated.
      Lines do not need to be following each other to be spotted as repeats.
    - max_lines: if > 0, max number of complete lines read from Ollama
    - max_paragraphs: if > 0, max number of complete lines read from Ollama
    - monitor_callback: a callback to pass to streamvalve for monitoring the stream

    Returns
    - Tuple. First elem is all text collected from ollama,
      second is stop criterion as text if not None
    """

    def extract_chat_response(cr: ollama.ChatResponse) -> str:
        """Callback for streamvalve to extract chat response as str"""
        return cr["message"]["content"]

    sv = StreamValve(
        ostream,
        callback_extract=extract_chat_response,
        callback_token=monitor_callback,
        max_linerepeats=max_linerepeats,
        max_lines=max_lines,
        max_paragraphs=max_paragraphs,
    )
    ret = sv.process()

    # streams sometimes end without a newline at the end. In this case, and if the stream
    #  was monitored, simply emit a newline on the stream to make it look nice when returning
    #  to the command line
    #
    # pylint cannot infer ret["text"] being a str
    if monitor_callback and len(ret["text"]) > 0 and ret["text"][-1] != "\n":  # pylint: disable = E1136
        monitor_callback("\n")

    if ret["stopcrit"] != StopCriterion.END_OF_STREAM:
        print(
            "\nReading from Ollama model stopped early."
            f"\nCriterion: {ret['stopcrit']}\nMessage: {ret['stopmsg']}"
            f"\nStopped at token/line: {ret['stopat']!r}\n",
            file=sys.stderr,
        )

    return ret


def main():
    """Entry point to ollama-cli.

    Parse cmd line, get SYSTEM and USR msg, setup the Ollama model, and stream answer back.
    """
    opts = parse_cmd_line()

    # Early exists: version or help on Ollama options?
    if opts.version:
        print(__version__)
        sys.exit(0)
    if opts.opthelp:
        print(help_overview())
        sys.exit(0)
    if opts.optdesc:
        print(help_long())
        sys.exit(0)

    # quick check of --opt for an early bail out if there's an error there.
    try:
        oparams = to_ollama_options(opts.opts)
    except ValueError as e:
        print(e)
        print("Aborting.", file=sys.stderr)
        sys.exit(1)

    # Set up SYSTEM and USER messages
    if len(opts.sysin) > 0:
        with Path(opts.sysin).open(encoding="utf-8") as fin:
            sysmsg = fin.read()
    else:
        sysmsg = opts.sysmsg

    usrmsg = f"{sys.stdin.read()}\n"

    # Setup the Ollama stream and stream
    monitor = None
    if opts.tostderr:
        monitor = monitor_accepted_chat_response_stderr
    else:
        monitor = monitor_accepted_chat_response_stdout

    ostream = setup_ollama(
        sysmsg,
        usrmsg,
        opts.model,
        params=oparams,
        host=opts.host,
    )

    try:
        result = run_ostream_via_streamvalve(
            ostream,
            max_linerepeats=opts.max_linerepeats,
            max_lines=opts.max_lines,
            max_paragraphs=opts.max_paragraphs,
            monitor_callback=monitor,
        )
    except ollama.ResponseError as e:
        print(
            f"Ollama response error: {e}\n\nNo further information available, sorry.",
            file=sys.stderr,
        )
        sys.exit(1)
    except httpx.ConnectError as e:
        machine = "on your computer?" if len(opts.host) == 0 else f"at {opts.host} ?"
        print(
            f"Connection error: {e}\n\nIs Ollama running {machine}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Done streaming

    # Print result to stdout in case monitoring was on stderr
    if opts.tostderr:
        print(result["text"])
