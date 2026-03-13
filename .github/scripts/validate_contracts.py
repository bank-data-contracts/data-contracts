"""
Data Contract Validator - v2
Validates all .yml/.yaml data contract files in team folders.
"""

import os
import sys
import yaml

TEAM_FOLDERS = [
    "team1-digi",
    "team2-Data-Governance",
    "team3-client-service",
    "team4-steering-data",
    "team5-esg-risk",
    "team6-strategy",
    "team7-gen-ai",
    "team8-investment-banking",
]

REQUIRED_TOP_LEVEL = ["id", "info", "servers", "schema"]
REQUIRED_INFO = ["title", "version", "status", "description", "owner"]
REQUIRED_FIELD_ATTRS = ["name", "type", "description"]
VALID_STATUSES = ["draft", "in development", "active", "deprecated"]
VALID_FIELD_TYPES = [
    "string", "integer", "decimal", "float", "double",
    "boolean", "date", "timestamp", "array", "object", "number", "bigint", "long"
]
VALID_QUALITY_RULES = [
    "not_null", "unique", "accepted_values",
    "min_value", "max_value", "regex", "row_count", "range"
]

def check(errors, condition, message):
    if not condition:
        errors.append(f"  ❌ {message}")

def validate_contract(path):
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            contract = yaml.safe_load(f)
        if contract is None:
            return ["  ❌ Soubor je prázdný"]
    except yaml.YAMLError as e:
        return [f"  ❌ YAML syntax error: {e}"]
    except Exception as e:
        return [f"  ❌ Nelze načíst: {e}"]

    # Top level - jen základní pole
    for field in REQUIRED_TOP_LEVEL:
        check(errors, field in contract, f"Chybí povinné pole: `{field}`")

    # Info
    info = contract.get("info", {})
    if isinstance(info, dict):
        for field in REQUIRED_INFO:
            check(errors, field in info, f"Chybí `info.{field}`")
        status = info.get("status", "")
        check(errors, status in VALID_STATUSES,
              f"`info.status` musí být jeden z {VALID_STATUSES} (aktuálně: '{status}')")
        version = str(info.get("version", ""))
        parts = version.split(".")
        check(errors, len(parts) >= 2 and all(p.isdigit() for p in parts),
              f"`info.version` musí být ve formátu major.minor[.patch] (aktuálně: '{version}')")
    else:
        errors.append("  ❌ Sekce `info` musí být objekt")

    # Servers
    servers = contract.get("servers", {})
    if isinstance(servers, dict) and len(servers) > 0:
        for sname, srv in servers.items():
            if isinstance(srv, dict):
                check(errors, "type" in srv, f"Server `{sname}` chybí `type`")
    else:
        errors.append("  ❌ Sekce `servers` musí obsahovat alespoň jeden server")

    # Schema
    schema = contract.get("schema", [])
    all_fields = set()
    if isinstance(schema, list) and len(schema) > 0:
        for table in schema:
            if not isinstance(table, dict):
                continue
            tname = table.get("name", "?")
            fields = table.get("fields", [])
            if isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        all_fields.add(field.get("name", ""))
                        check(errors, "name" in field,
                              f"Pole v `{tname}` chybí `name`")
                        check(errors, "type" in field,
                              f"Pole `{field.get('name','?')}` v `{tname}` chybí `type`")
                        ft = field.get("type", "")
                        check(errors, ft in VALID_FIELD_TYPES,
                              f"Pole `{field.get('name','?')}` má neplatný typ `{ft}` (povolené: {VALID_FIELD_TYPES})")
    else:
        errors.append("  ❌ Sekce `schema` musí obsahovat alespoň jednu tabulku")

    # Quality - volitelná sekce, ale pokud existuje, validujeme
    quality = contract.get("quality", [])
    if isinstance(quality, list) and len(quality) > 0:
        for rule in quality:
            if isinstance(rule, dict):
                check(errors, "rule" in rule, "Quality pravidlo chybí `rule`")
                check(errors, "field" in rule, "Quality pravidlo chybí `field`")
                rt = rule.get("rule", "")
                check(errors, rt in VALID_QUALITY_RULES,
                      f"Neplatný quality rule `{rt}` (povolené: {VALID_QUALITY_RULES})")

    return errors

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    report_lines = []
    total_files = 0
    total_errors = 0
    failed_files = []

    print("\n" + "=" * 60)
    print("  DATA CONTRACT VALIDATOR v2")
    print("=" * 60)

    for team_folder in TEAM_FOLDERS:
        folder_path = os.path.join(repo_root, team_folder)
        if not os.path.exists(folder_path):
            msg = f"\n⚠️  [{team_folder}] složka nenalezena"
            print(msg); report_lines.append(msg)
            continue

        yml_files = sorted([f for f in os.listdir(folder_path)
                     if f.endswith(".yml") or f.endswith(".yaml")])

        if not yml_files:
            msg = f"\n⚠️  [{team_folder}] žádné .yml soubory"
            print(msg); report_lines.append(msg)
            continue

        for yml_file in yml_files:
            path = os.path.join(folder_path, yml_file)
            total_files += 1
            errors = validate_contract(path)
            label = f"[{team_folder}/{yml_file}]"

            if errors:
                total_errors += len(errors)
                failed_files.append(label)
                header = f"\n❌ {label} FAILED ({len(errors)} chyb)"
                print(header); report_lines.append(header)
                for e in errors:
                    print(e); report_lines.append(e)
            else:
                ok = f"\n✅ {label} OK"
                print(ok); report_lines.append(ok)

    summary = f"""
{"=" * 60}
VÝSLEDEK VALIDACE v2
{"=" * 60}
Celkem souborů:  {total_files}
Bez chyb:        {total_files - len(failed_files)}
S chybami:       {len(failed_files)}
Celkem chyb:     {total_errors}
{"=" * 60}
"""
    print(summary); report_lines.append(summary)

    report_path = os.path.join(repo_root, "validation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    if failed_files:
        sys.exit(1)
    else:
        print("✅ Všechny data contracty jsou validní!")
        sys.exit(0)

if __name__ == "__main__":
    main()
