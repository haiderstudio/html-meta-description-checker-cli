#!/usr/bin/env python3
"""Tests for html_meta_description_checker — stdlib unittest only.

Every HTML document in this file is made up for testing.
No real secret appears anywhere in this file.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import html_meta_description_checker as checker

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src/html_meta_description_checker.py"

GOOD = ("A small guide to checking the meta description on "
        "every page of a site before it ships to search.")


def run_cli(argv):
    """Run main(argv), capture stdout/stderr, return (code, out, err)."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = checker.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding=encoding)
    return str(path)


def findings_of(text):
    return checker.check_text(text)


def page_with(content=None, name="description"):
    if content is None:
        return "<html><head><title>T</title></head><body></body></html>"
    return ('<html><head><title>T</title>'
            '<meta name="%s" content="%s"></head>'
            '<body></body></html>' % (name, content))


class TestDescriptionJudgement(unittest.TestCase):
    def test_good_description_passes(self):
        self.assertEqual(findings_of(page_with(GOOD)), [])
        self.assertEqual(len(GOOD), 97)

    def test_missing_description_fails_on_line_1(self):
        bad = findings_of(page_with())
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_empty_content_fails(self):
        bad = findings_of(page_with(""))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "meta description is empty")

    def test_spaces_only_content_fails_as_empty(self):
        bad = findings_of(page_with("   "))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "meta description is empty")

    def test_missing_content_attribute_fails_as_empty(self):
        bad = findings_of(
            '<html><head><meta name="description"></head></html>')
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "meta description is empty")

    def test_too_short_reports_character_count(self):
        bad = findings_of(page_with("Too short."))
        self.assertEqual(len(bad), 1)
        self.assertEqual(
            bad[0]["reason"],
            "meta description is too short (10 characters)")

    def test_too_long_reports_character_count(self):
        bad = findings_of(page_with("x" * 161))
        self.assertEqual(len(bad), 1)
        self.assertEqual(
            bad[0]["reason"],
            "meta description is too long (161 characters)")

    def test_exactly_50_characters_passes(self):
        self.assertEqual(findings_of(page_with("x" * 50)), [])

    def test_exactly_160_characters_passes(self):
        self.assertEqual(findings_of(page_with("x" * 160)), [])

    def test_49_characters_fails(self):
        bad = findings_of(page_with("x" * 49))
        self.assertEqual(len(bad), 1)
        self.assertIn("too short (49 characters)", bad[0]["reason"])

    def test_161_characters_fails(self):
        bad = findings_of(page_with("x" * 161))
        self.assertEqual(len(bad), 1)
        self.assertIn("too long (161 characters)", bad[0]["reason"])

    def test_leading_and_trailing_spaces_do_not_count(self):
        bad = findings_of(page_with("  " + "x" * 40 + "  "))
        self.assertEqual(len(bad), 1)
        self.assertIn("too short (40 characters)", bad[0]["reason"])

    def test_uppercase_meta_and_name(self):
        text = ('<html><head><META NAME="Description" CONTENT="%s">'
                '</head></html>' % GOOD)
        self.assertEqual(findings_of(text), [])

    def test_description_reports_its_own_line(self):
        text = ('<html>\n<head>\n<title>T</title>\n'
                '<meta name="description" content="Too short.">\n'
                '</head>\n</html>\n')
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 4)

    def test_other_meta_tags_are_ignored(self):
        text = ('<html><head>'
                '<meta name="viewport" content="width=device-width">'
                '<meta property="og:description" content="Short.">'
                '<meta name="description" content="%s">'
                '</head></html>' % GOOD)
        self.assertEqual(findings_of(text), [])

    def test_og_description_alone_does_not_count(self):
        text = ('<html><head>'
                '<meta property="og:description" content="%s">'
                '</head></html>' % GOOD)
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_second_description_is_a_finding(self):
        text = ('<html><head>'
                '<meta name="description" content="%s">'
                '<meta name="description" content="%s">'
                '</head></html>' % (GOOD, GOOD))
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"],
                         "more than one meta description")

    def test_first_too_short_plus_duplicate_is_two_findings(self):
        text = ('<html><head>'
                '<meta name="description" content="Short.">'
                '<meta name="description" content="%s">'
                '</head></html>' % GOOD)
        bad = findings_of(text)
        self.assertEqual(len(bad), 2)
        self.assertIn("too short", bad[0]["reason"])
        self.assertEqual(bad[1]["reason"],
                         "more than one meta description")

    def test_description_outside_head_still_counts(self):
        text = ('<html><body>'
                '<meta name="description" content="%s">'
                '</body></html>' % GOOD)
        self.assertEqual(findings_of(text), [])

    def test_empty_document_fails_as_missing(self):
        bad = findings_of("")
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_file_with_no_meta_fails(self):
        bad = findings_of('<html><body><p>Hello</p></body></html>')
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")


class TestSkipping(unittest.TestCase):
    def test_meta_in_comment_skipped(self):
        text = ('<!-- <meta name="description" content="%s"> -->'
                % GOOD)
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_meta_in_script_string_skipped(self):
        text = ('<script>\n'
                "var markup = '<meta name=\"description\" "
                "content=\"%s\">';\n"
                '</script>\n' % GOOD)
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_meta_in_style_block_skipped(self):
        text = ('<style>\n'
                '.fake { content: "<meta name=\\"description\\" '
                'content=\\"%s\\">"; }\n'
                '</style>\n' % GOOD)
        bad = findings_of(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["reason"], "has no meta description")

    def test_real_meta_after_script_checked(self):
        text = ('<script>var x = 1;</script>\n'
                '<meta name="description" content="%s">\n' % GOOD)
        self.assertEqual(findings_of(text), [])


class TestCLI(unittest.TestCase):
    def test_clean_file_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "page.html", page_with(GOOD) + "\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 0)
            self.assertIn("every page carries a meta description", out)
            self.assertEqual(err, "")

    def test_flagged_file_exit_1_with_file_and_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "page.html", page_with() + "\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("line 1", out)
            self.assertIn("has no meta description", out)
            self.assertIn(path, out)

    def test_too_short_file_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "page.html",
                         page_with("Too short.") + "\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("too short (10 characters)", out)

    def test_folder_walk_finds_html_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page_with(GOOD) + "\n")
            write(tmp, "b.htm", page_with() + "\n")
            write(tmp, "notes.txt", page_with() + "\n")
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Checked 2 file(s)", out)
            self.assertIn("b.htm", out)
            self.assertNotIn("notes.txt", out)

    def test_folder_walk_skips_nested_with_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page_with(GOOD) + "\n")
            write(tmp, "sub/b.html", page_with() + "\n")
            code, out, err = run_cli([tmp, "--no-recursive"])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Checked 2 file(s)", out)

    def test_exclude_skips_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page_with(GOOD) + "\n")
            write(tmp, "b.html", page_with() + "\n")
            code, out, err = run_cli([tmp, "--exclude", "b.html"])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_git_folder_skipped_in_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page_with(GOOD) + "\n")
            write(tmp, ".git/b.html", page_with() + "\n")
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_direct_file_checked_whatever_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "template.txt", page_with() + "\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("template.txt", out)

    def test_duplicate_paths_checked_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page_with(GOOD) + "\n")
            code, out, err = run_cli([path, path])
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) checked", out)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page_with() + "\n")
            code, out, err = run_cli(["--json", path])
            self.assertEqual(code, 1)
            data = json.loads(out)
            self.assertEqual(data["checked"], 1)
            self.assertEqual(data["findings"], 1)
            self.assertEqual(data["files"][0]["path"], path)
            self.assertEqual(
                data["files"][0]["findings"][0]["line"], 1)
            self.assertEqual(
                data["files"][0]["findings"][0]["reason"],
                "has no meta description")
            self.assertIsNone(data["files"][0]["error"])

    def test_stdin_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), "--stdin"],
                input=page_with(GOOD) + "\n", cwd=tmp,
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("every page carries a meta description",
                          result.stdout)

    def test_stdin_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), "--stdin"],
                input=page_with("Too short.") + "\n", cwd=tmp,
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FAIL <stdin>: line 1 meta description "
                          "is too short (10 characters)",
                          result.stdout)

    def test_stdin_with_paths_is_usage_error(self):
        code, out, err = run_cli(["--stdin", "page.html"])
        self.assertEqual(code, 2)

    def test_no_paths_is_usage_error(self):
        code, out, err = run_cli([])
        self.assertEqual(code, 2)

    def test_missing_path_exit_2(self):
        code, out, err = run_cli(["/nonexistent/path/xyz"])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_empty_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 2)
            self.assertIn("no HTML files found", err)

    def test_bad_flag_exit_2(self):
        code, out, err = run_cli(["--nope"])
        self.assertEqual(code, 2)

    def test_version(self):
        code, out, err = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("html_meta_description_checker 1.0.0", out)

    def test_non_utf8_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", b"\xff\xfe<meta>\n")
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn("not valid UTF-8", out)

    def test_input_files_left_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page_with() + "\n")
            before = Path(path).read_text()
            run_cli([path])
            self.assertEqual(Path(path).read_text(), before)

    def test_cli_runs_from_another_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page_with(GOOD) + "\n")
            result = subprocess.run(
                [sys.executable, str(SRC), "a.html"],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("every page carries a meta description",
                          result.stdout)

    def test_cli_runs_under_fake_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page_with(GOOD) + "\n")
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                code, out, err = run_cli([path])
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
            self.assertEqual(code, 0)


class TestExamples(unittest.TestCase):
    def test_run_example_output_matches_sample(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        expected = (REPO / "examples/sample-output.md").read_text()
        self.assertEqual(result.stdout, expected)

    def test_readme_quotes_match_real_runs(self):
        readme = (REPO / "README.md").read_text()
        clean = subprocess.run(
            [sys.executable, "src/html_meta_description_checker.py",
             "examples/clean.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)
        self.assertIn(clean.stdout.strip(), readme)
        flagged = subprocess.run(
            [sys.executable, "src/html_meta_description_checker.py",
             "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(flagged.returncode, 1)
        self.assertIn(flagged.stdout.strip(), readme)
        folder = subprocess.run(
            [sys.executable, "src/html_meta_description_checker.py",
             "examples/"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(folder.returncode, 1)
        self.assertIn("Checked 3 file(s), 1 meta description "
                      "problem(s) in 1 file(s).", folder.stdout)
        self.assertIn("Checked 3 file(s), 1 meta description "
                      "problem(s) in 1 file(s).", readme)
        edge = subprocess.run(
            [sys.executable, "src/html_meta_description_checker.py",
             "examples/edge.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(edge.returncode, 0)
        self.assertIn(edge.stdout.strip(), readme)
        js = subprocess.run(
            [sys.executable, "src/html_meta_description_checker.py",
             "--json", "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(js.returncode, 1)
        self.assertIn(js.stdout.strip(), readme)


class TestHygiene(unittest.TestCase):
    def _repo_files(self, skip_tests=True, skip_examples=True):
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__")
                       and not (skip_tests and d == "tests")
                       and not (skip_examples and d == "examples")]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                yield Path(root) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "FIXME", "XXX"]
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for word in banned:
                if word in text:
                    hits.append("%s: %s" % (path.name, word))
        self.assertEqual(hits, [])

    def test_no_absolute_paths(self):
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for marker in ("/home/", "/Users/", "C:\\"):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_no_real_secrets_outside_tests_and_examples(self):
        # The source holds no key values at all; the tests
        # and examples hold fake values only, so they are
        # excluded from this scan.
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
            re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
            re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
            re.compile(r"AIza[0-9A-Za-z_-]{35}"),
            re.compile(r"[rs]k_(?:live|test)_[A-Za-z0-9]{16,}"),
            re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
            re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ"),
        ]
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append("%s: %s" % (path.name, pattern.pattern))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        stdlib = set(sys.stdlib_module_names)
        for target in (REPO / "src/html_meta_description_checker.py",
                       REPO / "tests/test_html_meta_description_checker.py"):
            tree = ast.parse(target.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(
                imported - stdlib - {"html_meta_description_checker"},
                (target.name, imported))
            self.assertNotIn("yaml", imported)

    def test_no_network_use_in_src(self):
        src = (REPO / "src/html_meta_description_checker.py").read_text()
        for marker in ("urllib.request", "requests", "socket",
                       "http.client", "urlopen", "urlretrieve"):
            self.assertNotIn(marker, src, marker)

    def test_gitignore_lists_env_first(self):
        lines = (REPO / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn("tests/test_html_meta_description_checker.py", ci)
        self.assertIn("ubuntu-latest", ci)
        self.assertIn("3.12", ci)
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)

    def test_readme_names_the_neighbouring_repos(self):
        readme = (REPO / "README.md").read_text()
        self.assertIn("html-title-checker-cli", readme)
        self.assertIn("seo-meta-audit", readme)

    def test_readme_names_the_live_page_rivals(self):
        readme = (REPO / "README.md").read_text()
        self.assertIn("title-and-description-checker", readme)
        self.assertIn("seo-meta-tag-checker", readme)


if __name__ == "__main__":
    unittest.main()
