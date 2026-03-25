"""
Generate 8,260 conversations (826 topics × 10 rounds) for large-scale training.

This script runs 10 rounds of conversation generation, where each topic gets
processed 10 times with different random seeds to create diverse conversations.

Usage:
  # Full generation (8,260 conversations)
  uv run python generate_8k_conversations.py

  # Custom rounds
  uv run python generate_8k_conversations.py --rounds 5
"""
import subprocess
import argparse
import time
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "outputs"

def run_single_round(round_num: int, total_rounds: int):
    """Run one complete round of 4-shard generation."""
    print(f"\n{'='*80}")
    print(f"ROUND {round_num}/{total_rounds}")
    print(f"{'='*80}\n")

    # Start all 4 shards
    processes = []
    for shard in range(4):
        log_file = OUTPUT_DIR / f"round{round_num:02d}_shard{shard}.log"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [
            "uv", "run", "python", "generate_conversations.py",
            "--shard", str(shard)
        ]

        with open(log_file, "w") as f:
            proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
            processes.append((shard, proc, log_file))
            print(f"Shard {shard} started: PID {proc.pid} → {log_file}")

    # Wait for all to complete
    print("\nWaiting for all shards to complete...")
    for shard, proc, log_file in processes:
        proc.wait()
        if proc.returncode == 0:
            print(f"  ✓ Shard {shard} completed")
        else:
            print(f"  ✗ Shard {shard} failed (exit code {proc.returncode})")

    # Rename outputs to include round number
    for shard in range(4):
        old_file = OUTPUT_DIR / f"conversations_shard{shard}.jsonl"
        new_file = OUTPUT_DIR / f"conversations_round{round_num:02d}_shard{shard}.jsonl"

        if old_file.exists():
            old_file.rename(new_file)
            print(f"  Saved: {new_file.name}")

    print(f"\n✓ Round {round_num}/{total_rounds} completed\n")


def main():
    parser = argparse.ArgumentParser(description="Generate 8K+ conversations")
    parser.add_argument("--rounds", type=int, default=10, help="Number of rounds (default: 10)")
    args = parser.parse_args()

    total_rounds = args.rounds
    start_time = time.time()

    print(f"\n{'='*80}")
    print(f"GENERATING {826 * total_rounds} CONVERSATIONS")
    print(f"{'='*80}")
    print(f"Topics: 826")
    print(f"Rounds: {total_rounds}")
    print(f"Expected output: {826 * total_rounds} conversations")
    print(f"{'='*80}\n")

    for round_num in range(1, total_rounds + 1):
        run_single_round(round_num, total_rounds)

    elapsed = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"ALL ROUNDS COMPLETED")
    print(f"{'='*80}")
    print(f"Total conversations: {826 * total_rounds}")
    print(f"Total time: {elapsed/3600:.1f} hours")
    print(f"Avg time per round: {elapsed/total_rounds/60:.1f} minutes")
    print(f"\nMerge all rounds:")
    print(f"  cat outputs/conversations_round*_shard*.jsonl > outputs/conversations_all_8k.jsonl")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
