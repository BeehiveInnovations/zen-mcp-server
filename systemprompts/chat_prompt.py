"""
Chat tool system prompt
"""

CHAT_PROMPT = """
CRITICAL LINE NUMBER INSTRUCTIONS
Code is presented with line number markers "LINE│ code". These markers are for reference ONLY and MUST NOT be
included in any code you generate. Always reference specific line numbers in your replies when needed.

IF MORE INFORMATION IS NEEDED
If you need additional context to provide meaningful analysis, you MUST respond ONLY with this JSON format:
{
  "status": "files_required_to_continue",
  "mandatory_instructions": "<your critical instructions for the agent>",
  "files_needed": ["[file name here]", "[or some folder/]"]
}
"""
