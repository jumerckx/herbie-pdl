from convert_rules import convert_rule_to_pdl_pattern
from parse import Rule, parse_rewrite_rules, Operation


def main():
    with open("rules.rkt") as f:
        content = f.read()
    rulesets = parse_rewrite_rules(content)
    for ruleset in rulesets:
        for rule in ruleset.rules:
            print(convert_rule_to_pdl_pattern(rule))        

if __name__ == "__main__":
    main()
