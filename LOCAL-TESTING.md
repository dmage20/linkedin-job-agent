# Local Testing with Ollama

Test the LinkedIn job application agent locally using Ollama for **zero API cost** during development.

## Benefits

- ✅ **Zero cost** - Unlimited free testing
- ✅ **Fast iteration** - Test optimizations without spending credits
- ✅ **Privacy** - All processing happens locally
- ✅ **Same architecture** - Uses same MCP tools and workflow

## Installation

### 1. Install Ollama

**Linux/WSL:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download from https://ollama.com/download/OllamaSetup.exe

### 2. Pull a Model

Choose based on your available RAM:

#### Option A: llama3.1:8b (Recommended - High Quality)
```bash
ollama pull llama3.1:8b
```

**Requirements:**
- RAM needed: ~5.6 GB available
- Function calling accuracy: 91%
- Best for: Desktop/laptop with 8GB+ RAM

#### Option B: llama3.2:3b (Low-RAM Alternative)
```bash
ollama pull llama3.2:3b
```

**Requirements:**
- RAM needed: ~2 GB available
- Function calling accuracy: Good (slightly lower than 8B)
- Best for: Chromebook, limited RAM systems

### 3. Install Node Dependencies
```bash
cd ~/linkedin-job-agent
npm install
```

## Usage

### Default (llama3.1:8b)
```bash
USE_LOCAL_LLM=true npm start <job-url>
```

### Low-RAM Mode (llama3.2:3b)
```bash
OLLAMA_MODEL=llama3.2:3b USE_LOCAL_LLM=true npm start <job-url>
```

### Example
```bash
# High-quality model (needs more RAM)
USE_LOCAL_LLM=true npm start https://www.linkedin.com/jobs/view/4315263547

# Low-RAM model (Chromebook-friendly)
OLLAMA_MODEL=llama3.2:3b USE_LOCAL_LLM=true npm start https://www.linkedin.com/jobs/view/4315263547
```

## Checking Available RAM

Before choosing a model, check your available memory:

```bash
free -h
```

Look at the "available" column under "Mem:":
- **5+ GB available** → Use `llama3.1:8b`
- **3-4 GB available** → Use `llama3.2:3b`
- **< 3 GB available** → Close other applications or use smaller model

## What You'll See

### Startup
```
🤖 LinkedIn Job Application Agent - MCP Powered

🧪 Running in LOCAL MODE with Ollama
   Model: llama3.1:8b
   RAM needed: ~5.6 GB
   Cost: $0 (FREE!)

✓ User profile loaded
🚀 Starting Playwright MCP Server...
✓ Agent initialized
```

### During Execution
```
--- Iteration 3 ---

💭 Ollama is thinking...

🔧 Executing: batch_fill_fields
   📝 Batch filling 5 fields...
      - Phone number: "+1234567890" (textbox)
      - Email address: "user@example.com" (textbox)
      - City: "San Francisco" (textbox)
      - Years of experience: "5" (textbox)
      - Requires sponsorship: "No" (combobox)
   ✓ Batch filled 5 fields
```

### Final Cost
```
💰 Cost Estimate (LOCAL):
────────────────────────────────────────────────────────────────────────────────
   Iterations:     12
   Input tokens:   45,000 (estimated)
   Output tokens:  3,000 (estimated)
   Total tokens:   48,000
────────────────────────────────────────────────────────────────────────────────
   TOTAL COST:     $0.0000 (FREE! 🎉)
────────────────────────────────────────────────────────────────────────────────
   Note: Running locally with Ollama - unlimited free usage!
```

## Testing Optimizations

Use local mode to test:

### 1. Batch Filling
Verify the agent uses `batch_fill_fields` for multiple form fields instead of filling them one by one.

### 2. Snapshot Skipping
Check if the agent skips snapshots after predictable actions (type_text, batch_fill_fields) and only takes them after state-changing actions (click, navigate).

### 3. Full Workflow
Complete an end-to-end job application to verify:
- Navigate to job
- Click Easy Apply
- Fill contact info
- Handle custom questions
- Submit application

## Performance Comparison

| Aspect | Claude API | Ollama (8B) | Ollama (3B) |
|--------|-----------|-------------|-------------|
| Cost per run | ~$0.45 | $0.00 | $0.00 |
| Quality | 95% | 91% | 85% |
| Speed (per iteration) | 2-3s | 5-10s | 3-7s |
| RAM needed | N/A | 5.6 GB | 2 GB |
| Use case | Production | Testing | Low-RAM testing |

## Troubleshooting

### Error: "fetch failed"
**Cause:** Ollama isn't running or npm packages not installed

**Fix:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# If not running (Linux/macOS):
ollama serve

# Install npm packages
npm install
```

### Error: "model 'llama3.1:8b' not found"
**Cause:** Model not downloaded

**Fix:**
```bash
ollama pull llama3.1:8b
```

### Error: "model requires more system memory"
**Cause:** Not enough RAM available

**Fix:**
```bash
# Use smaller model
OLLAMA_MODEL=llama3.2:3b USE_LOCAL_LLM=true npm start <job-url>

# Or close other applications to free up RAM
```

### Ollama is slow
**Cause:** Running on CPU instead of GPU

**Note:** This is normal on systems without NVIDIA/AMD GPUs (like Chromebooks). The agent will still work, just take longer per iteration (5-15 seconds vs 1-2 seconds).

## Switching to Production

When ready to test with Claude API (after buying credits):

```bash
# Production mode (uses Anthropic API)
npm start <job-url>
```

The same optimizations (batch filling, snapshot skipping) will work with Claude for maximum efficiency.

## Development Workflow

1. **Develop locally** - Test optimizations with Ollama at zero cost
2. **Iterate quickly** - Fix issues, adjust prompts, test features
3. **Verify with Claude** - Final test with production API
4. **Deploy** - Use in production with confidence

This approach lets you develop and test without worrying about API costs!
