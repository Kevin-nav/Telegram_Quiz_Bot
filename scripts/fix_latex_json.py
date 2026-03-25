import re
import glob
from pathlib import Path

# The file literally contains three backslashes followed by specific characters like f, n, r, t, b, v.
# e.g., "\\\frac" which parses as "\" + "\f" + "rac" in json.
# We want to replace it with "\\frac", which parses as "\" + "frac" in json.

patterns_to_fix = [
    (r'\\\\\\frac', r'\\\\frac'),
    (r'\\\\\\tan', r'\\\\tan'),
    (r'\\\\\\text', r'\\\\text'),
    (r'\\\\\\times', r'\\\\times'),
    (r'\\\\\\theta', r'\\\\theta'),
    (r'\\\\\\triangle', r'\\\\triangle'),
    (r'\\\\\\nabla', r'\\\\nabla'),
    (r'\\\\\\neq', r'\\\\neq'),
    (r'\\\\\\notin', r'\\\\notin'),
    (r'\\\\\\right', r'\\\\right'),
    (r'\\\\\\rho', r'\\\\rho'),
    (r'\\\\\\rightarrow', r'\\\\rightarrow'),
    (r'\\\\\\beta', r'\\\\beta'),
    (r'\\\\\\begin', r'\\\\begin'),
    (r'\\\\\\big', r'\\\\big'),
    (r'\\\\\\boldsymbol', r'\\\\boldsymbol'),
    (r'\\\\\\vec', r'\\\\vec'),
    (r'\\\\\\varepsilon', r'\\\\varepsilon'),
]

def fix_json_file(file_path):
    path = Path(file_path)
    content = path.read_text(encoding='utf-8')
    original_content = content
    
    for old, new in patterns_to_fix:
        # Replace occurrences of 3 backslashes + command with 2 backslashes + command
        content = re.sub(old, new, content)

    # We also have cases where it might just be 1 backslash (e.g. "\frac").
    # If the file specifically has "\frac" (which parses to form feed), let's replace it with "\\frac".
    # Note: in regex, literal "\f" is matched by r'\\f'.
    # To check if there's ONLY ONE backslash before 'frac', we can use lookbehind:
    # (?<!\\)\\frac matches a single backslash followed by frac.
    
    other_patterns = [
        (r'(?<!\\)\\frac', r'\\\\frac'),
        (r'(?<!\\)\\tan', r'\\\\tan'),
        (r'(?<!\\)\\text', r'\\\\text'),
        (r'(?<!\\)\\times', r'\\\\times'),
        (r'(?<!\\)\\theta', r'\\\\theta'),
        (r'(?<!\\)\\triangle', r'\\\\triangle'),
        (r'(?<!\\)\\nabla', r'\\\\nabla'),
        (r'(?<!\\)\\neq', r'\\\\neq'),
        (r'(?<!\\)\\notin', r'\\\\notin'),
        (r'(?<!\\)\\right', r'\\\\right'),
        (r'(?<!\\)\\rho', r'\\\\rho'),
        (r'(?<!\\)\\rightarrow', r'\\\\rightarrow'),
        (r'(?<!\\)\\beta', r'\\\\beta'),
        (r'(?<!\\)\\begin', r'\\\\begin'),
        (r'(?<!\\)\\big', r'\\\\big'),
        (r'(?<!\\)\\boldsymbol', r'\\\\boldsymbol'),
        (r'(?<!\\)\\vec', r'\\\\vec'),
        (r'(?<!\\)\\varepsilon', r'\\\\varepsilon'),
    ]
    
    for old, new in other_patterns:
        content = re.sub(old, new, content)

    if content != original_content:
        path.write_text(content, encoding='utf-8')
        print(f"Fixed {file_path}")

for f in glob.glob('../q_and_a/**/*.json', recursive=True):
    fix_json_file(f)

print("Done.")
