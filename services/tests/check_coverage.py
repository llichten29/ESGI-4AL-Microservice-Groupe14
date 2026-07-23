import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

THRESHOLD = 80.0


def coverage_by_service(xml_path):
    tree = ET.parse(xml_path)
    stats = defaultdict(lambda: [0, 0])
    for cls in tree.iter('class'):
        filename = cls.get('filename').replace('\\', '/')
        parts = filename.split('/')
        if len(parts) < 2:
            continue
        service = parts[0]
        for line in cls.iter('line'):
            stats[service][0] += 1
            if int(line.get('hits')) > 0:
                stats[service][1] += 1
    return stats


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else 'coverage.xml'
    stats = coverage_by_service(xml_path)
    failures = []
    total_lines = total_covered = 0
    print(f"{'Service':<24}{'Couvert':>10}{'Lignes':>10}{'%':>8}")
    for service in sorted(stats):
        lines, covered = stats[service]
        total_lines += lines
        total_covered += covered
        percent = 100.0 * covered / lines
        marker = '' if percent >= THRESHOLD else '  << sous le seuil'
        print(f"{service:<24}{covered:>10}{lines:>10}{percent:>7.1f}{marker}")
        if percent < THRESHOLD:
            failures.append((service, percent))
    print(f"{'TOTAL':<24}{total_covered:>10}{total_lines:>10}{100.0 * total_covered / total_lines:>7.1f}")
    if failures:
        names = ', '.join(f"{svc} ({pct:.1f}%)" for svc, pct in failures)
        print(f"ECHEC : services sous {THRESHOLD:.0f}% : {names}")
        return 1
    print(f"OK : tous les services sont >= {THRESHOLD:.0f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
