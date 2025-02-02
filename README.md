# ollama-cli

Simple command line tool that reads a text from stdin and pipes it to Ollama. One can set all Ollama options on command line as well as define termination criteria in terms of maximum number of lines, paragraphs, or repeated lines.

Nothing stellar, but quite useful.

# Installation
If you haven't done so already, please install [uv](https://docs.astral.sh/uv/) as this Python package and project manager basically makes all headaches of Python package management go away in an instant.

Simply type `uv tool install ollama-cli` and your are good to go!

When a new version of Ollama or ollama-cli is published, do `uv tool upgrade ollama-cli` to pick up new Ollama options to be set on the command line.

# Usage / command line options

```
options:
  -h, --help            show this help message and exit
  --opthelp             show a list of Ollama options that can be set via
                        --opts and exit.
  --optdesc             show a list of Ollama options and descriptions (if
                        available) that can be set via --opts and exit.

Ollama setup options:
  --sysmsg TXT          In case no --sysin (see below) given, the Ollama model
                        will get this text as SYSTEM message. Default: "You
                        are a helpful assistant. Answer the request of the
                        user succinctly and diligently. Do not repeat the task
                        given to you or announce your result."
  --sysin FILENAME      Name of a text file with an Ollama SYSTEM msg to prime
                        the model. Overrides --sysmsg (see above)
  --model NAME          Use Ollama model <NAME>. Default:
                        llama3.1:8b-instruct-q8_0

  --opts OPTS           Semicolon separated list of options for Ollama. E.g.:
                        --options="num_ctx=16384;temperature=0.0" Default: ""

Early termination options:
  --max-linerepeats INT
                        Used to prevent models eventually getting stuck in
                        endless loops of repeated lines. If >0, stop after
                        this number of non-blank lines that are exact repeats
                        of previous lines. Lines do not need to be following
                        each other to be spotted as repeats. Default: 3
  --max-lines INT       To prevent endless output. If >0, stop after this
                        number of lines. Default: 200
  --max-paragraphs INT  To prevent endless diverse output. If >0, stop after
                        this number of paragraphs. Default: 0

Output options:
  --tostderr            Redirect the streaming monitoring output to stderr.
                        The final result will be output to stdout once
                        completed. This is useful in combination with
                        termination options --max_* where, in case the
                        termination criterion triggered, stdout will contain
                        the output without the line which led to the
                        termination.

Connection options:
  --host HOST           The default empty string will connect to
                        'localhost:11434' where Ollama is usually installed.
                        Set this to connect to any other Ollama server you
                        have access to. Default: ""
```

# Usage examples

## Default usage examples
```sh
echo "Why is the sky blue? Write an article without headlines" | ollama-cli
```

Note: ollama-cli uses *llama3.1:8b-instruct-q8_0* as default model, which I found to be a good compromise between speed, memory usage, accuracy, and text generation time. In case you want to use other models, set them like so in the command line:

```sh
echo "Why is the sky blue? Write an article without headlines" | ollama-cli --model="llama3.2"
```

## Setting Ollama options examples
Easy. Put the options in a string, separated by semicolon `;`. Like this:
```sh
echo "Why is the sky blue? Write an article without headlines" | ollama-cli --opts="temperature=0.5;num_ctx=4096"
```

In case you do not remember which options are available and what their type is, ollama-cli can help you. You can get either a quick overview

```sh
ollama-cli --opthelp
```

which produces output like this:
```
                numa : bool
             num_ctx : int
           num_batch : int
...
```

or get more details like this:

```sh
ollama-cli --optdesc
```

which produces output like this:
```
numa : bool 
This parameter seems to be new, or not described in docs as of January 2025.
dm_ollamalib does not know it, sorry.

num_ctx : int 
Sets the size of the context window used to generate the next token. (Default: 2048)

...
```
> [!IMPORTANT]
> The Ollama option names and types will always be as up-to-date as the Ollama Python module used. But as the description texts are not provided by anywhere by Ollama Python, they were scraped from official Ollama and Ollama Python documentation. Alas, not all the parameters are explained there.

## Early termination examples
Sometimes models produce way more output than you wanted. Or get stuck in endless loops.

You can terminate the output of Ollama prematurely by either number of lines, number of paragraphs or number of exact line repeats.

> [!NOTE]
> While the normal output of Ollama appears on stdout, reasons for terminations will be shown by `ollama-cli` on stderr. That allows you to redirect the normal output to a file or pipe it to other commands without having to think about removing the termination info.

## Maximum number of lines
Contrived example, terminating the output after just two lines:
```sh
echo "List the name of 10 animals. Output as dashed list." | ./ollama-cli --max-lines=2
```

The output (both stdout and stderr) of the above could look like this:
```
- Lion
- Elephant

Reading from Ollama model stopped early.
Criterion: StopCriterion.MAX_LINES
Message: Maximum number of lines reached.
Stopped at token/line: '-'
```

## Maximum number of paragraphs
Terminating the output after two paragraphs:

```sh
echo "Why is the sky blue? Write an article without headlines" | ollama-cli --max-paragraphs=2
```

## Maximum number of repeated lines
Some models sometime get stuck and produce never-ending output repeating itself. I've seen this with requests like *"extract all acronyms from the text in a dashed list"*. For this, `--max-linerepeats` can alleviate the problem.

Contrived example:
```sh
echo "List the name of 20 animals. Mention the zebra at least 4 times across the list. Output as dashed list" | ./ollama-cli --max-linerepeats=2
```

The output of the above might look like this:
```
- Zebra
- Giraffe
- Zebra
- Dolphin
- Kangaroo
- Zebra

Reading from Ollama model stopped early.
Criterion: StopCriterion.MAX_LINEREPEATS
Message: Maximum number of exact repeated lines reached.
Stopped at token/line: '- Zebra\n'
```
> [!IMPORTANT]
> On screen, but also in file in case you redirected the stdout output, you will see 3 'Zebra' although you just asked for maximum of 2 via `--max_linerepeats`. Why? The reason is that ollama-cli streams each token as it receives it, but checking for duplicate lines can be done only once an end of line is received.
> In case you really want only the 'clean' output, redirect the monitoring output to stderr via `--tostderr`. In this case, the output on stdout will be written at the end and not contain the line which led to termination. E.g.:
> ```sh
> echo "List the name of 20 animals. Mention the zebra at least 4 times across the list. Output as dashed list" | ./ollama-cli --max-linerepeats=2 --tostderr >animals.txt
> ```
> The file 'animals.txt' will contain the 'clean' output.

# Notes
The GitHub repository comes with all files I currently use for Python development across multiple platforms. Notably:

- configuration of the Python environment via `uv`: pyproject.toml and uv.lock
- configuration for linter and code formatter `ruff`: ruff.toml
- configuration for `pylint`: .pylintrc
- git ignore files: .gitignore
- configuration for `pre-commit`: .pre-commit-config.yaml. The script used to check `git commit` summary message is in devsupport/check_commitsummary.py
- configuration for VSCode editor: .vscode directory
