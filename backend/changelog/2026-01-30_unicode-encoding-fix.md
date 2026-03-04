# Unicode Encoding Fix

**Date:** 2026-01-30

## Issue
- UnicodeEncodeError when logging messages with Unicode characters (✓, ✗, ₹)
- Windows cp1252 encoding couldn't handle Unicode symbols
- LLM returning markdown text instead of JSON format

## Changes Made

### 1. Fixed UTF-8 Encoding in Log Files
- **File:** `utils/logging_config.py`
  - Added `encoding='utf-8'` to chat_file_handler
  - Added `encoding='utf-8'` to error_file_handler

- **File:** `services/semantic_layer/flow_logger.py`
  - Added `encoding='utf-8'` to file_handler

- **File:** `utils/response_parser.py`
  - Added `encoding='utf-8'` to error log file writing in `log_error_to_file()` function

### 2. Removed Unicode Characters from System Prompts
- **File:** `services/llm_service.py`
  - Replaced ✓ (checkmark) with `-` (bullet point)
  - Replaced ✗ (X mark) with `-` (bullet point)
  - Updated in `create_semantic_prompt()` method

### 3. Strengthened JSON Format Enforcement
- **File:** `services/llm_service.py`
  - Added "YOU MUST RESPOND WITH VALID JSON ONLY" at start of system prompt
  - Added multiple reminders about JSON-only output (no markdown, no plain text)
  - Emphasized format requirements in both system and user prompts
  - Added explicit instruction: "Start with { and end with }. Nothing else."

## Impact
- All log files now properly handle Unicode characters (₹, emojis, special symbols)
- No more encoding errors on Windows systems
- Clearer instructions for LLM to return JSON format

## Testing Required
- Restart FastAPI server to apply changes
- Test queries with Rupee symbol (₹) in responses
- Verify LLM returns valid JSON instead of markdown
- Check all log files are written correctly

## Notes
- If local LLM (qwen2.5:7b) still returns markdown, consider switching to OpenAI or a model with better instruction following
- All file operations now explicitly use UTF-8 encoding to prevent future encoding issues
