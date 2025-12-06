# generate_site.py

html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>My Python-Generated Site</title>
</head>
<body>
    <h1>Hello from Python and GitHub Actions!</h1>
    <p>This page was generated automatically.</p>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html generated successfully.")
