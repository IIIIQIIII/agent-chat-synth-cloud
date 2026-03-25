"""
Merge conversation shards into single file.

Usage:
  uv run python scripts/merge_shards.py
"""
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"


def merge_shards():
    """Merge all shard files into single output."""
    shard_files = sorted(OUTPUT_DIR.glob("conversations_shard*.jsonl"))

    if not shard_files:
        print("No shard files found!")
        return

    print(f"Found {len(shard_files)} shard files:")
    for f in shard_files:
        print(f"  {f.name}")
    print()

    all_conversations = []
    stats = {
        "total_conversations": 0,
        "total_turns": 0,
        "total_time": 0,
        "by_shard": {},
    }

    # Load all shards
    for shard_file in shard_files:
        shard_name = shard_file.stem.replace("conversations_", "")
        conversations = []

        with open(shard_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    conv = json.loads(line)
                    conversations.append(conv)
                    all_conversations.append(conv)

        turns = sum(c["total_turns"] for c in conversations)
        time = sum(c["elapsed_seconds"] for c in conversations)

        stats["by_shard"][shard_name] = {
            "count": len(conversations),
            "turns": turns,
            "time": time,
        }

        print(f"{shard_name}: {len(conversations)} conversations, "
              f"{turns} turns, {time:.0f}s")

    stats["total_conversations"] = len(all_conversations)
    stats["total_turns"] = sum(c["total_turns"] for c in all_conversations)
    stats["total_time"] = sum(c["elapsed_seconds"] for c in all_conversations)

    # Sort by topic_id for consistency
    all_conversations.sort(key=lambda x: x["topic_id"])

    # Save merged file
    output_file = OUTPUT_DIR / "conversations_all.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for conv in all_conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")

    # Save stats
    stats_file = OUTPUT_DIR / "merge_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print()
    print("="*70)
    print("MERGE SUMMARY")
    print("="*70)
    print(f"Total conversations: {stats['total_conversations']}")
    print(f"Total turns: {stats['total_turns']} "
          f"(avg: {stats['total_turns']/stats['total_conversations']:.1f})")
    print(f"Total time: {stats['total_time']:.0f}s "
          f"({stats['total_time']/60:.1f} min)")
    print(f"Avg time/conversation: {stats['total_time']/stats['total_conversations']:.1f}s")
    print()
    print(f"Output: {output_file}")
    print(f"Stats: {stats_file}")
    print("="*70)


if __name__ == "__main__":
    merge_shards()
