# NVIDIA API Model Recommendations for OpenSentinel

## Current Configuration

**Primary Model**: `nvidia/nemotron-3-super-120b-a12b`
- **Why**: Optimized for agentic workflows (reasoning, coding, planning, tool calling)
- **Rate Limits**: Lower traffic than popular models like Qwen/DeepSeek
- **Performance**: 120B MoE (Mixture of Experts) - efficient and powerful

**Fallback Model**: `meta/llama-3.3-70b-instruct`
- **Why**: Good general-purpose model with reasonable availability
- **Rate Limits**: Medium traffic, better than Qwen 397B
- **Performance**: Solid for most tasks

## Rate Limit Info

NVIDIA free tier has **40 RPM (requests per minute)** across all models. However, popular models get hit harder due to user demand.

## Alternative Models (If Still Rate-Limited)

### Good Options:
1. **nvidia/llama-3.1-nemotron-51b-instruct**
   - Smaller = faster + less popular
   - Good for most agent tasks

2. **mistralai/mistral-small-4-119b-2603**
   - 119B MoE with 256k context
   - Good reasoning capabilities

3. **nvidia/llama-3.1-nemotron-70b-instruct**
   - NVIDIA's fine-tuned Llama
   - Balanced performance/availability

### Avoid (High Traffic):
- ❌ `qwen/qwen3.5-397b-a17b` - Very popular, constant 429 errors
- ❌ `deepseek/deepseek-r1` - Extremely popular, always overloaded
- ❌ `meta/llama-3.3-70b-instruct` - Popular but usable as fallback

## Retry Configuration

Current settings in `.env`:
```bash
OPENSENTINEL_PROVIDER_RETRY_ATTEMPTS=3
OPENSENTINEL_PROVIDER_RETRY_BASE_DELAY_SECONDS=2.0
```

This gives retry delays of: 2s, 4s, 8s (total ~14s wait time)

## Testing

After changing models, restart the server:
```bash
# Press Ctrl+C in langgraph dev terminal
# Then: langgraph dev
```

Test with simple query to verify no 429 errors:
```bash
# In OpenSentinel CLI
You > what's 2+2?
```

If you still get 429 errors after trying all models, you may need to:
1. Wait for your rate limit window to reset (usually hourly)
2. Use a different API provider (OpenAI, Anthropic, etc.)
3. Set up local inference with Ollama

## Model Performance Notes

**Nemotron-3-super-120b-a12b** is specifically designed for:
- ✅ Agentic reasoning
- ✅ Tool calling (perfect for OpenSentinel)
- ✅ Planning and multi-step workflows
- ✅ Coding tasks

This makes it ideal for your agent's workflow!
