# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the HTML files you point it at, and it never rewrites a file and never changes anything. It writes nothing except the report on standard output (and usage errors on standard error). It never fetches a URL: a meta description is read from a local file, not from a live page.

It only checks that each page carries a meta description of 50–160 characters. It never loads a page, never runs JavaScript, and never contacts a search engine.

If you find a case where the tool rewrites a file, opens a URL, or reports a pass for an HTML file with a missing, empty, or out-of-range meta description, please open an issue describing the exact commands and input. Do not include any real secret in the report.
