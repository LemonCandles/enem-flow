"""Deterministic objective scoring, never an estimate of an official TRI score."""
from collections import defaultdict


def score(items: list, answers: dict):
    eligible = [i for i in items if not i["content"]["annulled"]]
    correct = sum(answers.get(i["id"]) == i["content"]["correct_answer"] for i in eligible)
    answered = sum(answers.get(i["id"]) is not None for i in eligible)
    return {"correct": correct, "total": len(eligible), "answered": answered,
            "unanswered": len(eligible) - answered, "incorrect": answered - correct,
            "annulled": len(items) - len(eligible),
            "percentage": round(correct / len(eligible) * 100, 1) if eligible else None}


def aggregate(runs: list):
    groups = {kind: defaultdict(list) for kind in ("area", "discipline", "theme", "skill")}
    coverage = {kind: 0 for kind in groups}
    total = 0
    all_items, all_answers = [], {}
    for run in runs:
        for item in run.items:
            c = item["content"]
            unique_id = f"{run.id}:{item['id']}"
            all_items.append({**item, "id": unique_id})
            all_answers[unique_id] = run.answers.get(item["id"])
            if c["annulled"]:
                continue
            total += 1
            labels = c["labels"]
            keys = {"area": [c["area"]], "discipline": [labels["discipline"]] if labels["discipline"] else [],
                    "theme": labels["themes"], "skill": labels["skills"]}
            for kind, values in keys.items():
                if values:
                    coverage[kind] += 1
                for value in set(values) or {"Ainda não classificado"}:
                    groups[kind][value].append((item, run.answers.get(item["id"])))
    breakdown = {}
    for kind, values in groups.items():
        breakdown[kind] = []
        for name, rows in sorted(values.items()):
            correct = sum(answer == item["content"]["correct_answer"] for item, answer in rows)
            breakdown[kind].append({"name": name, "attempts": len(rows), "correct": correct,
                                    "percentage": round(correct / len(rows) * 100, 1)})
    return {"completed_runs": len(runs), "summary": score(all_items, all_answers), "breakdown": breakdown,
            "coverage": {kind: {"classified": count, "total": total,
                                  "percentage": round(count / total * 100, 1) if total else 0}
                         for kind, count in coverage.items()}}
