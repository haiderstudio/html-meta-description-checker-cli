#!/usr/bin/env python3
"""Check every HTML file carries a meta description of 50-160 characters.

Run: python3 src/html_meta_description_checker.py page.html
     python3 src/html_meta_description_checker.py site/
     python3 src/html_meta_description_checker.py --stdin < page.html

A missing meta description hands the search snippet
to the search engine's guesswork, and a 400-character
one gets cut off mid-word on the results page. This
tool reads each HTML file, finds its <meta
name="description">, and reports each page whose
description is missing, empty, shorter than 50
characters, or longer than 160 characters, with the
file and the line number. It exits 1 when any page
fails, so it can fail a CI run. A page whose
description sits inside 50–160 characters exits 0.

The length is counted on the description with
leading and trailing spaces removed. A description
of exactly 50 or exactly 160 characters passes.
A page with more than one meta description is
reported too — the first one is judged for length,
and each extra one is a finding of its own.

A file given directly on the command line is always
checked, whatever its name. A folder is walked for
files ending in .html or .htm only, recursively by
default (--no-recursive stops at the top level).
.git folders are never walked, and directory links
are never followed.

A meta tag inside an HTML comment is not a meta tag
— the parser skips it. Markup inside <script> and
<style> blocks is not parsed as HTML either, so a
"<meta>" written in a JavaScript string or a
stylesheet is left alone. Tag and attribute names
are matched without regard to case, as HTML
requires — <META> and NAME="Description" are
checked exactly like <meta> and name="description".

It never rewrites a file, never touches the network,
and reads only the files and folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

__version__ = "1.0.0"

HTML_SUFFIXES = (".html", ".htm")

MIN_LENGTH = 50
MAX_LENGTH = 160


class MetaDescriptionParser(HTMLParser):
    """Collect every meta description problem in one document.

    HTMLParser already treats <script> and <style>
    content as character data, so markup written
    inside those blocks never reaches handle_starttag.
    Comments never reach it either.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.descriptions = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        values = dict(attrs)
        if (values.get("name") or "").strip().lower() != "description":
            return
        line, _offset = self.getpos()
        self.descriptions.append({
            "line": line,
            "content": values.get("content") or "",
        })

    def close(self):
        super().close()
        self.findings = self._judge()

    def _judge(self):
        if not self.descriptions:
            return [{"line": 1,
                     "reason": "has no meta description"}]
        findings = []
        first = self.descriptions[0]
        length = len(first["content"].strip())
        if length == 0:
            findings.append({
                "line": first["line"],
                "reason": "meta description is empty",
            })
        elif length < MIN_LENGTH:
            findings.append({
                "line": first["line"],
                "reason": "meta description is too short "
                          "(%d characters)" % length,
            })
        elif length > MAX_LENGTH:
            findings.append({
                "line": first["line"],
                "reason": "meta description is too long "
                          "(%d characters)" % length,
            })
        for extra in self.descriptions[1:]:
            findings.append({
                "line": extra["line"],
                "reason": "more than one meta description",
            })
        findings.sort(key=lambda item: item["line"])
        return findings


def check_text(text):
    """Check one document's text.

    Returns a list of findings, each {"line": int,
    "reason": str}, in document order.
    """
    parser = MetaDescriptionParser()
    parser.feed(text)
    parser.close()
    return parser.findings


def check_file(path):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    try:
        return check_text(text), None
    except Exception as exc:  # malformed markup the parser rejects
        return [], "could not be parsed: %s" % exc


def _is_html_file(path):
    return Path(path).name.lower().endswith(HTML_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of HTML files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .html
    or .htm only. .git folders are never walked, and
    directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_html_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one description problem."""
    return ("FAIL %s: line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d meta description "
                  "problem(s) in %d file(s)."
                  % (len(files), findings, files_with_findings))
        else:
            print("OK — %d file(s) checked, every page carries "
                  "a meta description of 50–160 characters."
                  % len(files))
    return 1 if findings else 0


def run_stdin(as_json=False):
    """Check one HTML document read from standard input."""
    text = sys.stdin.read()
    bad = check_text(text)
    findings = len(bad)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": None}],
             "checked": 1, "findings": findings},
            indent=2))
    else:
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if findings:
            print("Checked 1 file(s), %d meta description "
                  "problem(s) in 1 file(s)." % findings)
        else:
            print("OK — 1 file(s) checked, every page carries "
                  "a meta description of 50–160 characters.")
    return 1 if findings else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="html_meta_description_checker",
        description="Check every HTML file carries a <meta "
                    "name=\"description\"> of 50–160 characters, "
                    "fail CI when one does not.")
    parser.add_argument("paths", nargs="*",
                        help="HTML files or folders to walk")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one HTML document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no file or folder arguments")
        return run_stdin(as_json=args.json)
    if not args.paths:
        parser.error("give at least one HTML file or folder")
    return run(args.paths, recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
