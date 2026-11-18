# ABOUTME: Loads pinned website fingerprints and resolves technology relationships.
# ABOUTME: Compiles confidence and version tags without vendoring upstream rules.

from dataclasses import dataclass
import json
from pathlib import Path
import re

import regex


RULES_COMMIT = "9e52f10a9533c8f7f8d0703c843f7295d56c95a3"
FIELDS = ("headers", "cookies", "meta", "scriptSrc", "html", "url")


def as_list(value):
    return value if isinstance(value, list) else [value]


def tagged(value: str) -> tuple[str, dict[str, str]]:
    parts = re.split(r"\\;|;(?=(?:confidence|version):)", value)
    return parts[0], dict(part.split(":", 1) for part in parts[1:] if ":" in part)


@dataclass(frozen=True)
class Pattern:
    expression: object
    confidence: int
    version: str

    @classmethod
    def compile(cls, value: str):
        expression, tags = tagged(value)
        return cls(
            regex.compile(expression, regex.IGNORECASE),
            max(0, min(100, int(tags.get("confidence", "100")))),
            tags.get("version", ""),
        )

    def search(self, value: str):
        # Public HTML is untrusted input, including for upstream regex patterns.
        return self.expression.search(value, timeout=0.05)

    def get_version(self, match) -> str:
        def replace(reference):
            index = int(reference[1])
            captured = (match[index] or "") if index <= match.re.groups else ""
            if reference[2] is not None:
                return reference[2] if captured else reference[3]
            return captured

        return re.sub(r"\\(\d+)(?:\?([^:]*):([^\\]*))?", replace, self.version)[:256]


class RuleSet:
    def __init__(self, technologies: dict, categories: dict, groups: dict):
        self.technologies = technologies
        self.categories = categories
        self.groups = groups
        self.patterns = {}
        for name, technology in technologies.items():
            patterns = []
            for field in FIELDS:
                values = technology.get(field, {})
                if not isinstance(values, dict):
                    values = {"": values}
                for key, raw in values.items():
                    for value in as_list(raw):
                        patterns.append((field, key.lower(), Pattern.compile(value)))
            self.patterns[name] = patterns

    @classmethod
    def load(cls, directory: str | Path):
        directory = Path(directory)
        technologies = {}
        paths = sorted((directory / "technologies").glob("*.json"))
        if not paths:
            raise ValueError("Technology rule files are missing")
        for path in paths:
            technologies.update(json.loads(path.read_text()))
        return cls(
            technologies,
            json.loads((directory / "categories.json").read_text()),
            json.loads((directory / "groups.json").read_text()),
        )

    def _requirements_met(self, name: str, detected: dict) -> bool:
        technology = self.technologies[name]
        required = as_list(technology.get("requires", []))
        if required and not any(item in detected for item in required):
            return False
        categories = as_list(technology.get("requiresCategory", []))
        return not categories or any(
            category in self.technologies[item].get("cats", [])
            for item in detected for category in categories
        )

    def resolve(self, evidence: dict) -> list[dict]:
        def expand(forbidden):
            detected = {}
            changed = True
            while changed:
                changed = False
                candidates = dict(evidence)
                for source, (source_confidence, _) in detected.items():
                    for raw in as_list(self.technologies[source].get("implies", [])):
                        name, tags = tagged(raw)
                        confidence = min(source_confidence, int(tags.get("confidence", "100")))
                        previous = candidates.get(name, (0, ""))
                        candidates[name] = (
                            max(confidence, previous[0]),
                            previous[1] or tags.get("version", ""),
                        )
                for name, result in candidates.items():
                    if (name in forbidden or name not in self.technologies
                            or not self._requirements_met(name, detected)):
                        continue
                    previous = detected.get(name, (0, ""))
                    merged = (max(previous[0], result[0]), previous[1] or result[1])
                    if merged != previous:
                        detected[name] = merged
                        changed = True
            return detected

        detected = expand(set())
        excluded = {
            tagged(raw)[0]
            for name in detected
            for raw in as_list(self.technologies[name].get("excludes", []))
        }
        # Recompute so a removed technology cannot keep its implied descendants.
        detected = expand(excluded)
        results = []
        for name, (confidence, version) in sorted(detected.items()):
            technology = self.technologies[name]
            categories = []
            for category_id in technology.get("cats", []):
                category = self.categories.get(str(category_id), {})
                categories.append({
                    "id": category_id, "name": category.get("name", ""),
                    "groups": [
                        {"id": group, "name": self.groups.get(str(group), {}).get("name", "")}
                        for group in category.get("groups", [])
                    ],
                })
            results.append({
                "name": name, "version": version, "confidence": min(100, confidence),
                "categories": categories, "website": technology.get("website", ""),
            })
        return results
