import json
import logging
from pathlib import Path
from src.domains.question_bank.latex_renderer import (
    build_question_latex,
    build_explanation_latex,
    render_latex_to_png,
)
from src.domains.question_bank.schemas import ImportedQuestion, build_question_key

# We will temporarily modify latex_renderer to print the output
import src.domains.question_bank.latex_renderer as lr

# Save original render function
_orig_run = lr.subprocess.run

def _debug_run(*args, **kwargs):
    result = _orig_run(*args, **kwargs)
    if result.returncode != 0:
        print("====== PDFLATEX ERROR ======")
        print(result.stdout)
        print(result.stderr)
        print("============================")
    return result

lr.subprocess.run = _debug_run

json_path = Path("../q_and_a/linear-electronics/scored_cleaned.json")
with json_path.open(encoding="utf-8") as f:
    data = json.load(f)

failed_keys = [
    "linear-electronics-summing-amplifier-2b40cc17bb2d",
    "linear-electronics-op-amp-integrator-e9b96fb2bb3e",
    "linear-electronics-op-amp-differentiator-d981effb7bdf",
    "linear-electronics-non-inverting-amplifier-fbf29cb7b2e1",
    "linear-electronics-feedback-180c9dfc11bd",
    "linear-electronics-feedback-d9d4b9b1ccfe",
    "linear-electronics-summing-amplifier-f62be110c029",
    "linear-electronics-feedback-161e4eeaa8f4",
]

for row in data:
    try:
        q = ImportedQuestion.from_dict(row)
        key = build_question_key("linear-electronics", q)
        if key in failed_keys:
            print(f"\nDebugging {key}...")
            
            # Try question
            tex = build_question_latex(q.question_text, q.options)
            print(f"Question text: {q.question_text}")
            success = render_latex_to_png(tex, "_debug.png")
            if not success:
                print("-> Question render failed!")
                continue
                
            # Try explanation
            tex = build_explanation_latex(q.correct_option_text, q.short_explanation)
            success = render_latex_to_png(tex, "_debug.png")
            if not success:
                print("-> Explanation render failed!")
                
    except Exception as e:
        print(f"Error parsing row: {e}")
