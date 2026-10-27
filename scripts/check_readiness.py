#!/usr/bin/env python3
"""Check recorded PaperWalk preparation, not whether an AI actually understood a paper.

Python 3.9+, standard library only. Reads one JSON file without modifying it.
Exit codes: 0 recorded checks pass, 1 preparation incomplete, 2 invalid input.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


DISCLAIMER = (
    "This checks recorded coverage and consistency only. It does not prove actual "
    "reading, correct extraction, complete inventory, or scientific understanding."
)


def check_readiness(state):
    """Return human-readable issues. No filesystem/network access or state mutation."""
    issues = []

    def obj(value, label):
        if not isinstance(value, dict):
            issues.append(f"{label}: expected an object")
            return {}
        return value

    def seq(value, label):
        if not isinstance(value, list):
            issues.append(f"{label}: expected an array")
            return []
        return value

    def nonempty(value, label):
        valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            issues.append(f"{label}: a non-empty string is required")
        return valid

    def flag(value, label):
        if value is not True:
            issues.append(f"{label}: must be true after the work has been checked")

    def choice(value, allowed, label):
        if not isinstance(value, str) or value not in allowed:
            issues.append(f"{label}: expected one of {', '.join(sorted(allowed))}")

    def ids(value, label):
        values = seq(value, label)
        result = []
        for index, item in enumerate(values):
            if nonempty(item, f"{label}[{index}]"):
                result.append(item)
        if len(result) != len(set(result)):
            issues.append(f"{label}: duplicate IDs")
        return result

    state = obj(state, "session")
    if type(state.get("schema_version")) is not int or state.get("schema_version") != 1:
        issues.append("schema_version: expected integer 1")
    paper = obj(state.get("paper"), "paper")
    for field in ("title", "version", "identity"):
        nonempty(paper.get(field), f"paper.{field}")
    flag(paper.get("identity_verified"), "paper.identity_verified")
    inventory = obj(state.get("inventory"), "inventory")
    flag(inventory.get("confirmed"), "inventory.confirmed")
    flag(inventory.get("supplements_checked"), "inventory.supplements_checked")

    units = {}
    required_units = set()
    source_ids = set()
    main_count = 0
    sources = seq(state.get("sources"), "sources")
    for number, raw_source in enumerate(sources):
        label = f"sources[{number}]"
        source = obj(raw_source, label)
        source_id = source.get("id")
        if nonempty(source_id, f"{label}.id"):
            if source_id in source_ids:
                issues.append(f"{label}.id: duplicate source ID {source_id}")
            source_ids.add(source_id)
        role = source.get("role")
        choice(role, {"main", "appendix", "supplement", "external"}, f"{label}.role")
        if role == "main":
            main_count += 1
        required = source.get("required")
        if type(required) is not bool:
            issues.append(f"{label}.required: expected a boolean")
        if role in ("main", "appendix", "supplement") and required is not True:
            issues.append(f"{label}: main, appendix and in-scope supplements cannot be excluded")
        if required is False:
            nonempty(source.get("exclusion_reason"), f"{label}.exclusion_reason")
            nonempty(source.get("exclusion_impact"), f"{label}.exclusion_impact")
        nonempty(source.get("location"), f"{label}.location")
        fingerprint = source.get("sha256")
        if fingerprint is not None and (
            not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint)
        ):
            issues.append(f"{label}.sha256: expected null or a SHA-256 hex digest")
        availability = source.get("availability")
        choice(availability, {"available", "missing", "blocked"}, f"{label}.availability")
        if required is True:
            if availability != "available":
                issues.append(f"{label}: required source is not available")
            flag(source.get("inventory_complete"), f"{label}.inventory_complete")
        source_units = seq(source.get("units"), f"{label}.units")
        if required is True and not source_units:
            issues.append(f"{label}: required source has no source units")
        for index, raw_unit in enumerate(source_units):
            unit_label = f"{label}.units[{index}]"
            unit = obj(raw_unit, unit_label)
            unit_id = unit.get("id")
            valid_id = nonempty(unit_id, f"{unit_label}.id")
            if valid_id:
                if unit_id in units:
                    issues.append(f"{unit_label}.id: duplicate source-unit ID {unit_id}")
                units[unit_id] = (unit, required, availability)
                if required is True:
                    required_units.add(unit_id)
            nonempty(unit.get("locator"), f"{unit_label}.locator")
            kind = unit.get("kind")
            choice(kind, {"text", "equation", "figure", "table", "caption", "references", "frontmatter", "declaration"}, f"{unit_label}.kind")
            choice(unit.get("status"), {"unread", "partial", "read", "blocked"}, f"{unit_label}.status")
            if required is True and unit.get("status") != "read":
                issues.append(f"{unit_label}: required source unit is not fully read")
            if required is True and kind in ("figure", "table"):
                flag(unit.get("visual_verified"), f"{unit_label}.visual_verified")
            if required is True and kind == "equation":
                flag(unit.get("notation_verified"), f"{unit_label}.notation_verified")
    if main_count != 1:
        issues.append("sources: exactly one main source is required")

    def check_refs(refs, label):
        for unit_id in refs:
            if unit_id not in units:
                issues.append(f"{label}: unknown source-unit ID {unit_id}")
                continue
            unit, _, availability = units[unit_id]
            if unit.get("status") != "read" or availability != "available":
                issues.append(f"{label}: cites an unread or unavailable unit {unit_id}")
            if unit.get("kind") in ("figure", "table") and unit.get("visual_verified") is not True:
                issues.append(f"{label}: cites a visually unverified unit {unit_id}")
            if unit.get("kind") == "equation" and unit.get("notation_verified") is not True:
                issues.append(f"{label}: cites unverified notation {unit_id}")

    synthesis = obj(state.get("synthesis"), "synthesis")
    for field in ("question", "approach", "result", "boundary"):
        nonempty(synthesis.get(field), f"synthesis.{field}")
    flag(synthesis.get("understanding_checked"), "synthesis.understanding_checked")
    evidence = seq(synthesis.get("evidence"), "synthesis.evidence")
    if not evidence:
        issues.append("synthesis.evidence: at least one grounded claim is required")
    for index, raw_card in enumerate(evidence):
        label = f"synthesis.evidence[{index}]"
        card = obj(raw_card, label)
        for field in ("claim", "interpretation", "limits"):
            nonempty(card.get(field), f"{label}.{field}")
        refs = ids(card.get("source_ids"), f"{label}.source_ids")
        if not refs:
            issues.append(f"{label}: no source evidence")
        check_refs(refs, label)
    for index, raw_question in enumerate(seq(synthesis.get("unresolved"), "synthesis.unresolved")):
        label = f"synthesis.unresolved[{index}]"
        question = obj(raw_question, label)
        nonempty(question.get("question"), f"{label}.question")
        if type(question.get("blocking")) is not bool:
            issues.append(f"{label}.blocking: expected a boolean")
        choice(question.get("status"), {"open", "resolved"}, f"{label}.status")
        nonempty(question.get("note"), f"{label}.note")
        if question.get("blocking") is True and question.get("status") != "resolved":
            issues.append(f"{label}: unresolved critical question blocks teaching")

    segments = seq(state.get("segments"), "segments")
    if not segments:
        issues.append("segments: no semantic reading plan")
    segment_ids = set()
    ownership = Counter()
    for index, raw_segment in enumerate(segments):
        label = f"segments[{index}]"
        segment = obj(raw_segment, label)
        segment_id = segment.get("id")
        valid_id = nonempty(segment_id, f"{label}.id")
        if valid_id and segment_id in segment_ids:
            issues.append(f"{label}: duplicate segment ID {segment_id}")
        choice(segment.get("kind"), {"teaching", "supporting"}, f"{label}.kind")
        for field in ("focus", "split_reason"):
            nonempty(segment.get(field), f"{label}.{field}")
        refs = ids(segment.get("source_ids"), f"{label}.source_ids")
        if not refs:
            issues.append(f"{label}: no assigned source units")
        ownership.update(refs)
        check_refs(refs, label)
        if segment.get("kind") == "supporting":
            for unit_id in refs:
                if unit_id in units and units[unit_id][0].get("kind") not in ("frontmatter", "references", "declaration"):
                    issues.append(f"{label}: substantive source unit {unit_id} cannot be hidden in supporting material")
        contexts = ids(segment.get("context_ids"), f"{label}.context_ids")
        check_refs(contexts, f"{label}.context_ids")
        for dependency in ids(segment.get("depends_on"), f"{label}.depends_on"):
            if dependency not in segment_ids:
                issues.append(f"{label}: prerequisite {dependency} must be an earlier segment")
        if valid_id:
            segment_ids.add(segment_id)
    for unit_id in sorted(required_units):
        if ownership[unit_id] == 0:
            issues.append(f"segments: required source unit {unit_id} is unassigned")
    for unit_id, count in sorted(ownership.items()):
        if count > 1:
            issues.append(f"segments: {unit_id} has multiple primary owners; use context_ids for reuse")

    preferences = obj(state.get("preferences"), "preferences")
    options = {
        "setup": {"before_first_unit", "after_first_unit", "provided"},
        "question_mode": {"off", "checkpoints", "dialogue"},
        "depth": {"foundational", "standard", "advanced"},
        "formula_mode": {"intuition", "derivation", "both"},
        "pace": {"one_unit", "several_units"},
    }
    for key, allowed in options.items():
        choice(preferences.get(key), allowed, f"preferences.{key}")
    for key in ("configured", "examples", "recaps"):
        if type(preferences.get(key)) is not bool:
            issues.append(f"preferences.{key}: expected a boolean")
    progress = obj(state.get("progress"), "progress")
    for key in ("taught_segments", "deferred_segments"):
        for segment_id in ids(progress.get(key), f"progress.{key}"):
            if segment_id not in segment_ids:
                issues.append(f"progress.{key}: unknown segment ID {segment_id}")
    # Unanswered questions never block preparation or force a user to answer.
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path, help="Path to a PaperWalk session JSON file")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable result")
    args = parser.parse_args(argv)
    try:
        state = json.loads(args.session.read_text(encoding="utf-8-sig"))
        if not isinstance(state, dict):
            raise ValueError("session must be a JSON object")
    except (OSError, ValueError) as error:
        if args.json:
            print(json.dumps({"status": "INPUT ERROR", "issues": [str(error)], "notice": DISCLAIMER}, ensure_ascii=True))
        else:
            print(f"INPUT ERROR: {error}", file=sys.stderr)
        return 2
    issues = check_readiness(state)
    status = "NOT READY" if issues else "READY (recorded checks only)"
    if args.json:
        print(json.dumps({"status": status, "issues": issues, "notice": DISCLAIMER}, ensure_ascii=True, indent=2))
    else:
        print(status)
        for issue in issues:
            print(f"- {issue}")
        print(DISCLAIMER)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
