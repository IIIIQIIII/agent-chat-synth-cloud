# Agent Chat Synth - Cloud Deployment

Generate realistic multi-turn coding conversations using LLM role-play for training data synthesis.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone repository
git clone https://github.com/IIIIQIIII/agent-chat-synth-cloud.git
cd agent-chat-synth-cloud

# Install dependencies
pip install openai

# Configure API keys
cp .env.example .env
# Edit .env and fill in your 4 Aliyun API keys
```

### 2. Set Environment Variables

```bash
# Export API keys
export ALIYUN_KEY_1=sk-your-key-1
export ALIYUN_KEY_2=sk-your-key-2
export ALIYUN_KEY_3=sk-your-key-3
export ALIYUN_KEY_4=sk-your-key-4

# Optional: customize settings
export CONCURRENCY=5
export MAX_TURNS=10
```

### 3. Run Generation

#### Small Scale Test (5 topics)

```bash
python generate_conversations.py --pilot 5
```

#### Full Scale (826 topics with 4 parallel shards)

```bash
# Run in 4 separate terminals or use screen/tmux
python generate_conversations.py --shard 0 > shard0.log 2>&1 &
python generate_conversations.py --shard 1 > shard1.log 2>&1 &
python generate_conversations.py --shard 2 > shard2.log 2>&1 &
python generate_conversations.py --shard 3 > shard3.log 2>&1 &

# Monitor progress
tail -f shard*.log
```

#### Merge Results

```bash
python merge_shards.py
```

#### Analyze Quality

```bash
python analyze_conversations.py outputs/conversations_all.jsonl
```

## 📊 Dataset

**Topic Seeds**: 826 diverse topics covering:
- 170 base topics (programming, data analysis, system administration)
- 656 edge case variants (version conflicts, data corruption, resource limits, etc.)

**Coverage**: 81.6% of daily development scenarios

## 🎯 Expected Output

- **826 conversations** (1 per topic)
- **~6,700 turns** total (avg 8.1 turns per conversation)
- **99% natural endings** ("thanks", "works", etc.)
- **99% code examples** (realistic code blocks)
- **~6-8 hours** total runtime (with concurrency=5, 4 accounts)

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALIYUN_KEY_1-4` | Required | 4 Aliyun DashScope API keys |
| `ALIYUN_NAME_1-4` | Account1-4 | Account names for logging |
| `CONCURRENCY` | 5 | Concurrent requests per account |
| `MAX_TURNS` | 10 | Maximum conversation turns |
| `BASE_URL` | dashscope url | API endpoint |
| `MODEL` | qwen3-coder-next | Model name |

### Recommended Settings

- **Concurrency 5**: Safe, tested to work reliably
- **Concurrency 10**: Faster but may hit rate limits
- **Total parallelism**: 4 accounts × 5 concurrency = **20 concurrent requests**

## 📂 Output Structure

```
outputs/
├── conversations_shard0.jsonl   # Shard 0 results (207 topics)
├── conversations_shard1.jsonl   # Shard 1 results (207 topics)
├── conversations_shard2.jsonl   # Shard 2 results (206 topics)
├── conversations_shard3.jsonl   # Shard 3 results (206 topics)
├── conversations_all.jsonl      # Merged results (826 topics)
└── merge_stats.json             # Statistics
```

### Output Format

Each line is a JSON object:

```json
{
  "topic_id": 1,
  "topic": "Optimize memory usage when processing large CSV files",
  "scenario": "Data Pipeline Development",
  "user_role": "Data Analyst",
  "complexity": "intermediate",
  "tech_stack": ["pandas", "duckdb"],
  "total_turns": 7,
  "elapsed_seconds": 25.3,
  "messages": [
    {"role": "user", "content": "I'm getting MemoryError..."},
    {"role": "assistant", "content": "You can use chunked reading..."},
    ...
  ]
}
```

## 🔧 Troubleshooting

### Missing API Keys

```
ValueError: Missing environment variable: ALIYUN_KEY_1
```

**Solution**: Export all 4 API keys before running.

### Rate Limiting

If you see errors like "rate limit exceeded":
- Reduce `CONCURRENCY` from 5 to 3
- Add delays between requests
- Check Aliyun dashboard for quotas

### Out of Memory

If script crashes with OOM:
- Reduce concurrency
- Process fewer topics at once with `--pilot`
- Use a machine with more RAM

## 📈 Scaling to 8K+ Conversations

To generate 8,260 conversations (10× each topic):

```bash
# Run 10 rounds sequentially
for i in {1..10}; do
  echo "Round $i/10"
  python generate_conversations.py --shard 0 > round${i}_shard0.log 2>&1 &
  python generate_conversations.py --shard 1 > round${i}_shard1.log 2>&1 &
  python generate_conversations.py --shard 2 > round${i}_shard2.log 2>&1 &
  python generate_conversations.py --shard 3 > round${i}_shard3.log 2>&1 &
  wait
done
```

Or use a loop in Python to process each topic multiple times.

## 📄 License

Internal project for research and development.

---

**Repository**: https://github.com/IIIIQIIII/agent-chat-synth-cloud
**Version**: 1.0
**Last Updated**: 2024-03-25
