"""
Hardcore Rules Registry (HR-001)

This module provides programmatic access to the HARDCORE_RULES - the immutable
foundation document that defines WHO WE ARE.

The Ten Rules are not just guidelines - they are the IDENTITY of Ralph Mode.
This registry makes them queryable and referenceable from code.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HardcoreRule:
    """Represents a single hardcore rule"""
    number: int
    title: str
    description: str
    category: str = "FOUNDATIONAL"

    def __str__(self) -> str:
        return f"Rule #{self.number}: {self.title}"

    def full_text(self) -> str:
        return f"""Rule #{self.number}: {self.title}
{self.description}
"""


class HardcoreRulesRegistry:
    """
    Registry of the Ten Hardcore Rules.

    These rules define WHO WE ARE. They are FOUNDATIONAL and IMMUTABLE.
    Changes require deliberation (see rule_manager.py).
    """

    # The Ten Rules - defined inline as the canonical source
    RULES = [
        HardcoreRule(
            number=1,
            title="Family safe, all ages, no trash",
            description="No exceptions. No edge cases. No 'but what if.' Family safe. Period.",
            category="CONTENT"
        ),
        HardcoreRule(
            number=2,
            title="Ralph is innocent, not dumb",
            description="He sees good in everything because that's who he IS. Not because he can't see bad.",
            category="PERSONALITY"
        ),
        HardcoreRule(
            number=3,
            title="Mr. Worms is always the boss",
            description="The user is Mr. Worms. They make the decisions. We serve.",
            category="HIERARCHY"
        ),
        HardcoreRule(
            number=4,
            title="Entertainment wraps productivity, never replaces it",
            description="The work must actually work. The fun is the wrapper, not the product.",
            category="PRODUCT"
        ),
        HardcoreRule(
            number=5,
            title="No sycophancy",
            description="Honest feedback over flattery. Always. We don't lie to make people feel good.",
            category="COMMUNICATION"
        ),
        HardcoreRule(
            number=6,
            title="The work must actually work",
            description="Ship code that runs. Fix bugs that exist. Build features that function.",
            category="QUALITY"
        ),
        HardcoreRule(
            number=7,
            title="Respect faith and family values",
            description="No blasphemy. No mockery. No preaching. Just respect.",
            category="VALUES"
        ),
        HardcoreRule(
            number=8,
            title="Joy is the fruit, not the bait",
            description="Real joy from real accomplishment. Not fake dopamine to trap people.",
            category="ETHICS"
        ),
        HardcoreRule(
            number=9,
            title="When work is done, let them go",
            description="No dark patterns. No addiction loops. They finished? Celebrate and release.",
            category="ETHICS"
        ),
        HardcoreRule(
            number=10,
            title="We're a tool, not a god",
            description="We help. We don't replace. We serve. We don't rule.",
            category="POSITIONING"
        ),
    ]

    def __init__(self, rules_file_path: str = "FOUNDATION/HARDCORE_RULES.md"):
        """
        Initialize the registry.

        Args:
            rules_file_path: Path to HARDCORE_RULES.md (for validation)
        """
        self.rules_file = Path(rules_file_path)
        self._rules_dict = {rule.number: rule for rule in self.RULES}

    def get_rule(self, number: int) -> Optional[HardcoreRule]:
        """Get a specific rule by number (1-10)"""
        return self._rules_dict.get(number)

    def get_all_rules(self) -> List[HardcoreRule]:
        """Get all ten rules"""
        return self.RULES

    def get_rules_by_category(self, category: str) -> List[HardcoreRule]:
        """Get all rules in a specific category"""
        return [rule for rule in self.RULES if rule.category == category]

    def validate_against_rule(self, rule_number: int, text: str) -> Dict[str, any]:
        """
        Validate some text/action against a specific rule.

        Returns:
            dict with 'compliant', 'rule', 'reason'
        """
        rule = self.get_rule(rule_number)
        if not rule:
            return {
                'compliant': None,
                'rule': None,
                'reason': f'Rule #{rule_number} not found'
            }

        # Basic validation - can be extended
        result = {
            'compliant': True,  # Default to compliant unless proven otherwise
            'rule': rule,
            'reason': 'No violations detected'
        }

        # Rule-specific checks
        if rule_number == 1:  # Family safe
            unsafe_keywords = ['nsfw', 'adult', 'explicit']
            text_lower = text.lower()
            for keyword in unsafe_keywords:
                if keyword in text_lower:
                    result['compliant'] = False
                    result['reason'] = f'Content contains unsafe keyword: {keyword}'
                    break

        return result

    def get_registry_summary(self) -> str:
        """Get a formatted summary of all rules"""
        lines = []
        lines.append("=" * 80)
        lines.append("HARDCORE RULES REGISTRY")
        lines.append("=" * 80)
        lines.append("")
        lines.append("These ten rules define WHO WE ARE.")
        lines.append("They are FOUNDATIONAL and IMMUTABLE.")
        lines.append("Changes require deliberation (see rule_manager.py).")
        lines.append("")

        for rule in self.RULES:
            lines.append(f"#{rule.number}. {rule.title}")
            lines.append(f"   {rule.description}")
            lines.append(f"   Category: {rule.category}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")
        lines.append("To propose a rule change:")
        lines.append("  python3 rule_manager.py <rule_number> \"<proposed_change>\" \"Your Name\"")
        lines.append("")
        lines.append("Only Mr. Worms can approve rule changes.")
        lines.append("")

        return "\n".join(lines)

    def check_file_exists(self) -> bool:
        """Verify that HARDCORE_RULES.md exists"""
        return self.rules_file.exists()

    def get_metadata(self) -> Dict[str, any]:
        """Get metadata about the rules registry"""
        return {
            'total_rules': len(self.RULES),
            'rules_file': str(self.rules_file),
            'file_exists': self.check_file_exists(),
            'categories': list(set(rule.category for rule in self.RULES)),
            'last_checked': datetime.now().isoformat()
        }


# Singleton instance
_registry: Optional[HardcoreRulesRegistry] = None


def get_rules_registry() -> HardcoreRulesRegistry:
    """Get the singleton HardcoreRulesRegistry instance"""
    global _registry
    if _registry is None:
        _registry = HardcoreRulesRegistry()
    return _registry


# CLI interface for testing
if __name__ == "__main__":
    import sys

    registry = get_rules_registry()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            print(registry.get_registry_summary())

        elif command == "get" and len(sys.argv) > 2:
            rule_num = int(sys.argv[2])
            rule = registry.get_rule(rule_num)
            if rule:
                print(rule.full_text())
            else:
                print(f"Rule #{rule_num} not found")

        elif command == "metadata":
            import json
            print(json.dumps(registry.get_metadata(), indent=2))

        else:
            print("Usage:")
            print("  python3 hardcore_rules_registry.py list          # List all rules")
            print("  python3 hardcore_rules_registry.py get <number>  # Get specific rule")
            print("  python3 hardcore_rules_registry.py metadata      # Show metadata")
    else:
        print(registry.get_registry_summary())
