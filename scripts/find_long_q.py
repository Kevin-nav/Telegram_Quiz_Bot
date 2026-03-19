import json

with open(
    "q_and_a/differential-equations/consolidated_scored_with_latex.json",
    "r",
    encoding="utf-8",
) as f:
    data = json.load(f)

latex_qs = [q for q in data if q.get("has_latex")]
latex_qs.sort(
    key=lambda q: str(q["question_text"] + "".join(q["options"])).count("\\"),
    reverse=True,
)

for i in range(3):
    print("===================")
    print("Q:", latex_qs[i]["question_text"])
    for j, opt in enumerate(latex_qs[i]["options"]):
        print(f"Opt {j + 1}:", opt)
