# Capgemini Discovery Timeout Fix

The verified Capgemini connectivity request returns HTTP 200 with a small prompt. Discovery is therefore deliberately bounded:

- discovery evidence budget: 6,000 characters
- per-document contribution: 2,000 characters
- model output budget: 600 tokens
- temperature: 0
- streaming: false
- one compact retry on HTTP 504
- Blueprint is not started when Discovery fails

This keeps the first LLM call small. Detailed documents are consumed by later stages after Discovery produces a structured intermediate result.
