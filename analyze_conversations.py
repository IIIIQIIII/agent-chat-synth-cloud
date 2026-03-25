"""
Analyze generated conversations for quality metrics.

Usage:
  uv run python scripts/analyze_conversations.py outputs/conversations.jsonl
"""
import json
import sys
from pathlib import Path
from collections import Counter

def analyze_conversations(filepath: Path):
    """Analyze conversation quality metrics."""
    conversations = []

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                conversations.append(json.loads(line))

    if not conversations:
        print("No conversations found!")
        return

    # Basic stats
    total = len(conversations)
    turn_counts = [c["total_turns"] for c in conversations]
    elapsed_times = [c["elapsed_seconds"] for c in conversations]

    # Ending analysis
    endings = []
    for c in conversations:
        last_msg = c["messages"][-1]["content"].lower()
        if any(word in last_msg for word in ["thanks", "thank", "perfect", "great", "awesome", "works", "got it"]):
            endings.append("natural")
        else:
            endings.append("abrupt")

    # Code presence
    has_code = sum(1 for c in conversations if any("```" in m["content"] for m in c["messages"]))

    # Complexity distribution
    complexity_dist = Counter(c["complexity"] for c in conversations)
    scenario_dist = Counter(c["scenario"] for c in conversations)

    # Print report
    print("="*70)
    print(f"📊 CONVERSATION QUALITY ANALYSIS")
    print("="*70)
    print(f"Total Conversations: {total}")
    print()

    print("🔢 TURN STATISTICS:")
    print(f"  Min turns: {min(turn_counts)}")
    print(f"  Max turns: {max(turn_counts)}")
    print(f"  Avg turns: {sum(turn_counts)/len(turn_counts):.1f}")
    print(f"  Median turns: {sorted(turn_counts)[len(turn_counts)//2]}")
    print()

    print("⏱️  TIME STATISTICS:")
    print(f"  Min time: {min(elapsed_times):.1f}s")
    print(f"  Max time: {max(elapsed_times):.1f}s")
    print(f"  Avg time: {sum(elapsed_times)/len(elapsed_times):.1f}s")
    print(f"  Total time: {sum(elapsed_times):.1f}s ({sum(elapsed_times)/60:.1f} min)")
    print()

    print("🎯 ENDING QUALITY:")
    natural_count = endings.count("natural")
    print(f"  Natural endings: {natural_count}/{total} ({natural_count/total*100:.1f}%)")
    print(f"  Abrupt endings: {endings.count('abrupt')}/{total} ({endings.count('abrupt')/total*100:.1f}%)")
    print()

    print("💻 CODE EXAMPLES:")
    print(f"  Conversations with code: {has_code}/{total} ({has_code/total*100:.1f}%)")
    print()

    print("📈 COMPLEXITY DISTRIBUTION:")
    for complexity, count in complexity_dist.most_common():
        print(f"  {complexity:.<20} {count:>3} ({count/total*100:>5.1f}%)")
    print()

    print("📂 TOP SCENARIOS:")
    for scenario, count in scenario_dist.most_common(10):
        print(f"  {scenario:.<45} {count:>2}")
    print()

    print("✅ QUALITY ASSESSMENT:")
    score = 0
    checks = []

    # Check 1: Average turns (should be 5-8)
    avg_turns = sum(turn_counts)/len(turn_counts)
    if 5 <= avg_turns <= 8:
        checks.append("✓ Avg turns in ideal range (5-8)")
        score += 25
    else:
        checks.append(f"⚠ Avg turns {avg_turns:.1f} (expected 5-8)")

    # Check 2: Natural endings (should be >70%)
    natural_pct = natural_count/total*100
    if natural_pct >= 70:
        checks.append(f"✓ Natural endings: {natural_pct:.0f}% (target: 70%+)")
        score += 25
    else:
        checks.append(f"⚠ Natural endings: {natural_pct:.0f}% (target: 70%+)")

    # Check 3: Code examples (should be >60%)
    code_pct = has_code/total*100
    if code_pct >= 60:
        checks.append(f"✓ Code examples: {code_pct:.0f}% (target: 60%+)")
        score += 25
    else:
        checks.append(f"⚠ Code examples: {code_pct:.0f}% (target: 60%+)")

    # Check 4: Time efficiency (should be <60s avg)
    avg_time = sum(elapsed_times)/len(elapsed_times)
    if avg_time <= 60:
        checks.append(f"✓ Avg time: {avg_time:.0f}s (target: <60s)")
        score += 25
    else:
        checks.append(f"⚠ Avg time: {avg_time:.0f}s (target: <60s)")

    for check in checks:
        print(f"  {check}")
    print()
    print(f"Overall Quality Score: {score}/100")

    if score >= 75:
        print("🎉 Excellent quality! Ready for training.")
    elif score >= 50:
        print("✓  Good quality, minor adjustments recommended.")
    else:
        print("⚠  Quality issues detected, review prompts.")

    print("="*70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_conversations.py <conversations.jsonl>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    analyze_conversations(filepath)
