"""
Generate realistic multi-turn coding conversations using 2-role simulation.

Architecture:
1. User-Simulator: Knows full topic, simulates real user step-by-step questions
2. Assistant: Pure responses, doesn't know the topic context

Flow:
- User-Simulator generates first question based on topic
- Assistant responds with full conversation history
- User-Simulator decides: ask follow-up OR say "thanks, works!"
- Repeat until User-Simulator is satisfied (4-10 turns)

Usage:
  # Set environment variables first (copy .env.example to .env)
  export ALIYUN_KEY_1=sk-xxx
  export ALIYUN_KEY_2=sk-xxx
  export ALIYUN_KEY_3=sk-xxx
  export ALIYUN_KEY_4=sk-xxx

  # Pilot mode: 5 topics
  python generate_conversations.py --pilot 5

  # Full mode with sharding (4 accounts)
  python generate_conversations.py --shard 0
  python generate_conversations.py --shard 1
  python generate_conversations.py --shard 2
  python generate_conversations.py --shard 3
"""
import json
import argparse
import time
import asyncio
import os
from pathlib import Path
from openai import OpenAI

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
TOPICS_FILE = BASE_DIR / "topic_seeds_combined.jsonl"
OUTPUT_DIR = BASE_DIR / "outputs"

# ── API Config from Environment ──────────────────────────────────────────
def load_api_configs():
    """Load API configurations from environment variables."""
    configs = []
    for i in range(1, 5):
        key = os.getenv(f"ALIYUN_KEY_{i}")
        if not key:
            raise ValueError(f"Missing environment variable: ALIYUN_KEY_{i}")

        name = os.getenv(f"ALIYUN_NAME_{i}", f"Account{i}")
        concurrency = int(os.getenv("CONCURRENCY", "5"))

        configs.append({
            "key": key,
            "name": name,
            "concurrency": concurrency
        })

    return configs

API_CONFIGS = load_api_configs()
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.getenv("MODEL", "qwen3-coder-next")
MAX_TURNS = int(os.getenv("MAX_TURNS", "10"))

# ── Prompts ──────────────────────────────────────────────────────────────

USER_SIMULATOR_SYSTEM = """You are simulating a REAL software engineer asking questions.

Your role:
- You have a technical problem/task (given in context)
- Ask questions step-by-step like a real person would
- Start with initial question, then follow up based on assistant's response
- Show realistic behavior: ask for clarifications, edge cases, examples
- When problem is solved, say something like "thanks, that works!" or "perfect, got it!"

Rules:
- Ask ONE question at a time (not multiple in one message)
- Be concise but natural (typos/abbreviations OK)
- Don't reveal you're simulating - act like a real user
- End conversation when satisfied (usually 4-8 turns total)
- Use realistic language: "hmm", "wait", "oh I see", etc.
"""

USER_SIMULATOR_FIRST_TURN = """You are starting a conversation about this technical problem:

**Topic**: {topic}
**Scenario**: {scenario}
**Your Role**: {user_role}
**Complexity**: {complexity}
**Tech Stack**: {tech_stack}
{error_context}

Generate the FIRST question a real {user_role} would ask about this topic.
Be natural and concise. Output ONLY the question text, no extra explanation.
"""

USER_SIMULATOR_CONTINUE = """Previous conversation:
{conversation_history}

Your original goal was: {topic}

The assistant just responded. Decide what to do next:
1. If problem is solved → say "thanks, works!" or similar
2. If need clarification → ask follow-up question
3. If want to see example → ask for code/demo
4. If edge case unclear → ask about it

Output ONLY your next message (question or thanks). Be natural and concise.
"""

ASSISTANT_SYSTEM = """You are an expert coding assistant helping with programming, data analysis, and system administration.

Provide:
- Concise, accurate answers
- Code examples when relevant
- Specific commands/solutions
- Clear explanations

Be helpful but brief. Don't ask unnecessary questions unless genuinely unclear.
"""


# ── Core Logic ───────────────────────────────────────────────────────────

def create_clients(api_key: str) -> tuple[OpenAI, OpenAI]:
    """Create separate clients for user-simulator and assistant."""
    user_client = OpenAI(api_key=api_key, base_url=BASE_URL)
    assistant_client = OpenAI(api_key=api_key, base_url=BASE_URL)
    return user_client, assistant_client


def call_llm(client: OpenAI, system: str, user_msg: str, temperature: float = 0.8) -> str:
    """Call LLM with system prompt and user message."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        temperature=temperature,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def call_llm_with_history(client: OpenAI, system: str, messages: list[dict], temperature: float = 0.7) -> str:
    """Call LLM with full conversation history."""
    full_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=temperature,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def generate_conversation(topic_data: dict, user_client: OpenAI, assistant_client: OpenAI) -> dict:
    """Generate one multi-turn conversation."""
    topic_id = topic_data["id"]
    topic = topic_data["topic"]
    scenario = topic_data["scenario"]
    user_role = topic_data["user_role"]
    complexity = topic_data["complexity"]
    tech_stack = ", ".join(topic_data["tech_stack"])
    error_context = f"\n**Error Context**: {topic_data['error']}" if topic_data.get("error") else ""

    messages = []

    # Turn 1: User-Simulator generates first question
    first_turn_prompt = USER_SIMULATOR_FIRST_TURN.format(
        topic=topic,
        scenario=scenario,
        user_role=user_role,
        complexity=complexity,
        tech_stack=tech_stack,
        error_context=error_context,
    )

    user_question = call_llm(user_client, USER_SIMULATOR_SYSTEM, first_turn_prompt)
    messages.append({"role": "user", "content": user_question})

    print(f"  [T1 User] {user_question[:80]}...")

    # Multi-turn conversation
    for turn in range(1, MAX_TURNS):
        # Assistant responds with full context
        assistant_response = call_llm_with_history(
            assistant_client,
            ASSISTANT_SYSTEM,
            messages,
            temperature=0.7
        )
        messages.append({"role": "assistant", "content": assistant_response})

        print(f"  [T{turn} Asst] {assistant_response[:80]}...")

        # Build conversation history for user-simulator
        conversation_history = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in messages
        ])

        # Check if conversation should end
        if turn >= 3:  # Minimum 3 turns
            # User-Simulator decides next move
            continue_prompt = USER_SIMULATOR_CONTINUE.format(
                conversation_history=conversation_history,
                topic=topic
            )

            user_next = call_llm(user_client, USER_SIMULATOR_SYSTEM, continue_prompt, temperature=0.9)
            messages.append({"role": "user", "content": user_next})

            print(f"  [T{turn+1} User] {user_next[:80]}...")

            # Check if user is satisfied (thanks, works, perfect, etc.)
            end_signals = ["thanks", "perfect", "got it", "works", "thank you", "great", "awesome"]
            if any(signal in user_next.lower() for signal in end_signals):
                print(f"  → Conversation ended naturally at turn {turn+1}")
                break
        else:
            # Early turns: User-Simulator always follows up
            continue_prompt = USER_SIMULATOR_CONTINUE.format(
                conversation_history=conversation_history,
                topic=topic
            )
            user_next = call_llm(user_client, USER_SIMULATOR_SYSTEM, continue_prompt)
            messages.append({"role": "user", "content": user_next})
            print(f"  [T{turn+1} User] {user_next[:80]}...")

    return {
        "topic_id": topic_id,
        "topic": topic,
        "scenario": scenario,
        "user_role": user_role,
        "complexity": complexity,
        "tech_stack": topic_data["tech_stack"],
        "total_turns": len(messages),
        "messages": messages,
    }


def run_single_topic(topic_data: dict, user_client: OpenAI, assistant_client: OpenAI) -> dict:
    """Run conversation generation for one topic."""
    topic_id = topic_data["id"]
    print(f"\n[Topic {topic_id}] {topic_data['topic'][:60]}...")

    t0 = time.time()
    result = generate_conversation(topic_data, user_client, assistant_client)
    elapsed = time.time() - t0

    result["elapsed_seconds"] = round(elapsed, 1)

    print(f"  ✓ Completed in {elapsed:.1f}s ({result['total_turns']} turns)")

    return result


async def run_topic_async(
    topic_data: dict,
    user_client: OpenAI,
    assistant_client: OpenAI,
    sem: asyncio.Semaphore
) -> dict:
    """Run topic generation in thread pool."""
    async with sem:
        return await asyncio.to_thread(run_single_topic, topic_data, user_client, assistant_client)


async def process_shard(topics: list[dict], shard_id: int | str | None, config: dict):
    """Process a shard of topics with concurrency control."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    user_client, assistant_client = create_clients(config["key"])
    concurrency = config["concurrency"]
    sem = asyncio.Semaphore(concurrency)

    label = f"Shard {shard_id} ({config['name']})" if shard_id is not None else config['name']
    print(f"\n{'='*80}")
    print(f"{label}: {len(topics)} topics, concurrency={concurrency}")
    print(f"{'='*80}")

    # Build tasks
    tasks = [run_topic_async(topic, user_client, assistant_client, sem) for topic in topics]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    successful = []
    errors = 0

    for r in results:
        if isinstance(r, Exception):
            errors += 1
            print(f"  ERROR: {r}")
        else:
            successful.append(r)

    # Save results
    suffix = f"_shard{shard_id}" if shard_id is not None else ""
    output_file = OUTPUT_DIR / f"conversations{suffix}.jsonl"

    with open(output_file, "w", encoding="utf-8") as f:
        for result in successful:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # Summary
    total_turns = sum(r["total_turns"] for r in successful)
    avg_turns = total_turns / len(successful) if successful else 0
    total_time = sum(r["elapsed_seconds"] for r in successful)

    print(f"\n{'='*80}")
    print(f"SUMMARY ({label})")
    print(f"{'='*80}")
    print(f"Successful: {len(successful)} | Errors: {errors}")
    print(f"Total turns: {total_turns} | Avg turns: {avg_turns:.1f}")
    print(f"Total time: {total_time:.1f}s | Avg time: {total_time/len(successful):.1f}s/topic")
    print(f"Output: {output_file}")


def load_topics(pilot: int | None = None) -> list[dict]:
    """Load topics from JSONL file."""
    topics = []
    with open(TOPICS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                topics.append(json.loads(line))

    if pilot:
        topics = topics[:pilot]

    return topics


def main():
    parser = argparse.ArgumentParser(description="Generate multi-turn conversations")
    parser.add_argument("--pilot", type=int, help="Pilot mode: process first N topics")
    parser.add_argument("--shard", type=int, help="Shard ID (0-3) for parallel processing")
    args = parser.parse_args()

    topics = load_topics(args.pilot)

    if args.shard is not None:
        # Sharded mode: divide topics among 4 accounts
        n_shards = len(API_CONFIGS)
        shard_topics = [t for i, t in enumerate(topics) if i % n_shards == args.shard]
        config = API_CONFIGS[args.shard]

        asyncio.run(process_shard(shard_topics, args.shard, config))
    else:
        # Pilot mode: use first account
        config = API_CONFIGS[0]
        asyncio.run(process_shard(topics, None, config))


if __name__ == "__main__":
    main()
