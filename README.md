# html-meta-description-checker-cli

Check every HTML file carries a `<meta name="description">` of 50–160 characters — fail CI when one does not.

[![CI](https://github.com/haiderstudio/html-meta-description-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-meta-description-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_meta_description_checker` reads each HTML
file, finds its `<meta name="description">`, and
reports each page whose description is missing,
empty, shorter than 50 characters, or longer than
160 characters, with the file and the line number.
It exits 1 when any page fails, so it can fail a
CI run. A page whose description sits inside
50–160 characters exits 0.

- A missing meta description hands the search
  snippet to the search engine's guesswork, and a
  400-character one gets cut off mid-word on the
  results page. This names the exact line, and the
  fix is one tag per page once found.
- The length is counted on the description with
  leading and trailing spaces removed. A
  description of exactly 50 or exactly 160
  characters passes. A page with more than one
  meta description is reported too — the first one
  is judged for length, and each extra one is a
  finding of its own.
- A file given directly on the command line is always
  checked, whatever its name. A folder is walked for
  files ending in `.html` or `.htm` only, recursively
  by default (`--no-recursive` stops at the top
  level). `.git` folders are never walked, and
  directory links are never followed.
- `--json` prints the result as JSON, and `--stdin`
  checks one HTML document read from standard input.
- A meta tag inside an HTML comment is not a meta
  tag — the parser skips it. Markup inside
  `<script>` and `<style>` blocks is not parsed as
  HTML either, so a `"<meta>"` written in a
  JavaScript string or a stylesheet is left alone.
  Tag and attribute names are matched without
  regard to case, as HTML requires — `<META>` and
  `NAME="Description"` are checked exactly like
  `<meta>` and `name="description"`.

## Who it is for

Every site owner with pages that show up in search
results. One page with no description, and the
snippet under its link is whatever the search
engine guesses — usually the navigation text. This
is the gate that stops it at the pull request.

## What it does NOT do

- It does not check the `<title>` tag. That is repo
  #50, html-title-checker-cli — the description is
  a different tag on the same pages.
- It does not check Open Graph or Twitter
  descriptions (`og:description` is a different
  tag, for social previews, not search snippets).
- It does not judge the wording of a description —
  only that one exists and its length is sensible.
- It does not fetch live pages — it reads local
  files only.
- It never rewrites a file, and it never touches the
  network.

## How this differs

- A fresh search of GitHub on Nov 16, 2026 found 0
  results for `"html-meta-description-checker-cli"`
  and 6 results for `html meta description
  checker` — and every one of them is a live-page
  or web tool, not a local-file CLI gate:
  ridetored/title-and-description-checker, 1 star
  (a PHP project: upload a CSV of URLs, it fetches
  each page live); shayaneali/seo-meta-tag-checker,
  0 stars (paste HTML or a URL, get a score out of
  100 — a web tool); tberlin-om/website-checker, 0
  stars (checks predefined values from a CSV on a
  URL basis, emails on change); taleblou/
  SEOPageChecker_Python, 1 star (a Python script
  analysing live pages); Rakeshfrom/page-pulse, 1
  star (a FastAPI website health checker).
- No rival checks meta descriptions in local files
  offline, with a CI exit code. Repo #9,
  seo-meta-audit, is a skill, not a CLI gate.

## Install

```sh
git clone https://github.com/haiderstudio/html-meta-description-checker-cli.git
cd html-meta-description-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_meta_description_checker.py page.html
```

A file with a description of a sensible length passes:

```sh
$ python3 src/html_meta_description_checker.py examples/clean.html
OK — 1 file(s) checked, every page carries a meta description of 50–160 characters.
```

A file with no meta description fails, with the
file and line:

```sh
$ python3 src/html_meta_description_checker.py examples/flagged.html
FAIL examples/flagged.html: line 1 has no meta description
Checked 1 file(s), 1 meta description problem(s) in 1 file(s).
```

Check a whole folder (`.html` / `.htm` files only):

```sh
$ python3 src/html_meta_description_checker.py examples/
FAIL examples/flagged.html: line 1 has no meta description
Checked 3 file(s), 1 meta description problem(s) in 1 file(s).
```

Check one document from standard input:

```sh
$ printf '<html><head><meta name="description" content="Too short."></head></html>\n' | python3 src/html_meta_description_checker.py --stdin
FAIL <stdin>: line 1 meta description is too short (10 characters)
Checked 1 file(s), 1 meta description problem(s) in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/html_meta_description_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 1,
          "reason": "has no meta description"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 1
}
```

Exit codes: 0 when every page carries a meta
description of 50–160 characters, 1 when any page
fails or a file cannot be read, 2 for a usage error
(a missing path, a bad flag, or no HTML files
found).

## Examples

A description of exactly 50 characters passes —
the lower bound is inclusive — and uppercase tags
are handled. `examples/edge.html` holds a
50-character description, and it passes:

```sh
$ python3 src/html_meta_description_checker.py examples/edge.html
OK — 1 file(s) checked, every page carries a meta description of 50–160 characters.
```

A meta tag in a comment and a meta tag written
inside a script string are not meta tags, and
`examples/edge.html` holds both — they change
nothing:

```sh
$ python3 src/html_meta_description_checker.py examples/edge.html
OK — 1 file(s) checked, every page carries a meta description of 50–160 characters.
```

A page with two meta descriptions still fails —
one description per page, the extra one is
reported:

```sh
$ printf '<html><head><meta name="description" content="A small guide to checking the meta description on every page of a site before it ships to search."><meta name="description" content="A small guide to checking the meta description on every page of a site before it ships to search."></head></html>\n' | python3 src/html_meta_description_checker.py --stdin
FAIL <stdin>: line 1 more than one meta description
Checked 1 file(s), 1 meta description problem(s) in 1 file(s).
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_meta_description_checker.py
```

The tests cover description judgement (a good
description passes, a missing description fails on
line 1, an empty content fails, a spaces-only
content fails as empty, a missing content attribute
fails as empty, a too-short description reports its
character count, a too-long description reports its
character count, exactly 50 characters passes,
exactly 160 characters passes, 49 characters fails,
161 characters fails, leading and trailing spaces
do not count, an uppercase `<META>` and
`NAME="Description"`, a description reports its own
line, other meta tags are ignored, an
`og:description` alone does not count, a second
description is a finding, a too-short first
description plus a duplicate is two findings, a
description outside `<head>` still counts, an empty
document fails as missing, a file with no meta
fails), skipping (a meta tag in a comment, a meta
tag in a script string, a meta tag in a style
block, a real meta tag after a script checked), the
CLI (exit 0/1/2, folder walking for several HTML
files including `.htm`, nested folders,
`--no-recursive`, `--exclude`, `.git` skipped, a
direct file checked whatever its name, duplicate
paths checked once, `--json` output, `--stdin`
clean and dirty, bad flags, missing paths, empty
folders, `--version`, a non-UTF-8 file reported,
input files left unchanged, the tool run from
another folder and under a changed HOME), the
bundled examples (sample output compared
byte-for-byte against a fresh run, and the
README-quoted outputs checked against it), and
hygiene checks (no placeholder text, no absolute
paths, no real secrets outside the tests and
examples, stdlib imports only, no network use in
the source, `.env` first in `.gitignore`, CI file
runs the test file, README names the neighbouring
repos and the live-page rivals).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The
idea of checking meta descriptions is not new, and
the parsing follows Python's own standard-library
HTML parser — but no existing tool does this one
job, checking that every local HTML file carries a
meta description of a sensible length, as a tested
command-line gate with a CI exit code, as the search
above shows — and every line of code here is
original, built on nothing but Python's standard
library.
