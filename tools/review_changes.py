"""
Tool for reviewing pending git changes across multiple repositories.
"""

import os
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from config import MAX_CONTEXT_TOKENS
from prompts.tool_prompts import REVIEW_CHANGES_PROMPT
from utils.file_utils import read_files
from utils.git_utils import find_git_repositories, get_git_status, run_git_command
from utils.token_utils import estimate_tokens

from .base import BaseTool, ToolRequest


class ReviewChangesRequest(ToolRequest):
    """Request model for review_changes tool"""

    path: str = Field(
        ...,
        description="Starting directory to search for git repositories (must be absolute path).",
    )
    original_request: Optional[str] = Field(
        None,
        description="The original user request or ticket description for the changes. Provides critical context for the review.",
    )
    compare_to: Optional[str] = Field(
        None,
        description="Optional: A git ref (branch, tag, commit hash) to compare against. If not provided, reviews local staged and unstaged changes.",
    )
    include_staged: bool = Field(
        True,
        description="Include staged changes in the review. Only applies if 'compare_to' is not set.",
    )
    include_unstaged: bool = Field(
        True,
        description="Include uncommitted (unstaged) changes in the review. Only applies if 'compare_to' is not set.",
    )
    focus_on: Optional[str] = Field(
        None,
        description="Specific aspects to focus on (e.g., 'logic for user authentication', 'database query efficiency').",
    )
    review_type: Literal["full", "security", "performance", "quick"] = Field(
        "full", description="Type of review to perform on the changes."
    )
    severity_filter: Literal["critical", "high", "medium", "all"] = Field(
        "all",
        description="Minimum severity level to report on the changes.",
    )
    max_depth: int = Field(
        5,
        description="Maximum depth to search for nested git repositories to prevent excessive recursion.",
    )
    temperature: Optional[float] = Field(
        None,
        description="Temperature for the response (0.0 to 1.0). Lower values are more focused and deterministic.",
        ge=0.0,
        le=1.0,
    )
    thinking_mode: Optional[Literal["minimal", "low", "medium", "high", "max"]] = Field(
        None, description="Thinking depth mode for the assistant."
    )
    files: Optional[List[str]] = Field(
        None,
        description="Optional files or directories to provide as context (must be absolute paths). These files are not part of the changes but provide helpful context like configs, docs, or related code.",
    )


class ReviewChanges(BaseTool):
    """Tool for reviewing git changes across multiple repositories."""

    def get_name(self) -> str:
        return "review_changes"

    def get_description(self) -> str:
        return (
            "REVIEW PENDING GIT CHANGES BEFORE COMMITTING - ALWAYS use this tool before creating any git commit! "
            "Comprehensive pre-commit validation that catches bugs, security issues, incomplete implementations, "
            "and ensures changes match the original requirements. Searches all git repositories recursively and "
            "provides deep analysis of staged/unstaged changes. Essential for code quality and preventing bugs. "
            "Triggers: 'before commit', 'review changes', 'check my changes', 'validate changes', 'pre-commit review', "
            "'about to commit', 'ready to commit'. Claude should proactively suggest using this tool whenever "
            "the user mentions committing or when changes are complete."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return self.get_request_model().model_json_schema()

    def get_system_prompt(self) -> str:
        return REVIEW_CHANGES_PROMPT

    def get_request_model(self):
        return ReviewChangesRequest

    def get_default_temperature(self) -> float:
        """Use analytical temperature for code review."""
        from config import TEMPERATURE_ANALYTICAL

        return TEMPERATURE_ANALYTICAL

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string to be a valid filename."""
        # Replace path separators and other problematic characters
        name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        # Remove any remaining non-alphanumeric characters except dots, dashes, underscores
        name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
        # Limit length to avoid filesystem issues
        return name[:100]

    async def prepare_prompt(self, request: ReviewChangesRequest) -> str:
        """Prepare the prompt with git diff information."""
        # Find all git repositories
        repositories = find_git_repositories(request.path, request.max_depth)

        if not repositories:
            return "No git repositories found in the specified path."

        # Collect all diffs directly
        all_diffs = []
        repo_summaries = []
        total_tokens = 0
        max_tokens = (
            MAX_CONTEXT_TOKENS - 50000
        )  # Reserve tokens for prompt and response

        for repo_path in repositories:
            repo_name = os.path.basename(repo_path) or "root"
            repo_name = self._sanitize_filename(repo_name)

            # Get status information
            status = get_git_status(repo_path)
            changed_files = []

            # Process based on mode
            if request.compare_to:
                # Validate the ref
                is_valid_ref, err_msg = run_git_command(
                    repo_path,
                    ["rev-parse", "--verify", "--quiet", request.compare_to],
                )
                if not is_valid_ref:
                    repo_summaries.append(
                        {
                            "path": repo_path,
                            "error": f"Invalid or unknown git ref '{request.compare_to}': {err_msg}",
                            "changed_files": 0,
                        }
                    )
                    continue

                # Get list of changed files
                success, files_output = run_git_command(
                    repo_path,
                    ["diff", "--name-only", f"{request.compare_to}...HEAD"],
                )
                if success and files_output.strip():
                    changed_files = [f for f in files_output.strip().split("\n") if f]

                    # Generate per-file diffs
                    for file_path in changed_files:
                        success, diff = run_git_command(
                            repo_path,
                            [
                                "diff",
                                f"{request.compare_to}...HEAD",
                                "--",
                                file_path,
                            ],
                        )
                        if success and diff.strip():
                            # Format diff with file header
                            diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (compare to {request.compare_to}) ---\n"
                            diff_footer = (
                                f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
                            )
                            formatted_diff = diff_header + diff + diff_footer

                            # Check token limit
                            diff_tokens = estimate_tokens(formatted_diff)
                            if total_tokens + diff_tokens <= max_tokens:
                                all_diffs.append(formatted_diff)
                                total_tokens += diff_tokens
            else:
                # Handle staged/unstaged changes
                staged_files = []
                unstaged_files = []

                if request.include_staged:
                    success, files_output = run_git_command(
                        repo_path, ["diff", "--name-only", "--cached"]
                    )
                    if success and files_output.strip():
                        staged_files = [
                            f for f in files_output.strip().split("\n") if f
                        ]

                        # Generate per-file diffs for staged changes
                        for file_path in staged_files:
                            success, diff = run_git_command(
                                repo_path, ["diff", "--cached", "--", file_path]
                            )
                            if success and diff.strip():
                                diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (staged) ---\n"
                                diff_footer = (
                                    f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
                                )
                                formatted_diff = diff_header + diff + diff_footer

                                # Check token limit
                                from utils import estimate_tokens

                                diff_tokens = estimate_tokens(formatted_diff)
                                if total_tokens + diff_tokens <= max_tokens:
                                    all_diffs.append(formatted_diff)
                                    total_tokens += diff_tokens

                if request.include_unstaged:
                    success, files_output = run_git_command(
                        repo_path, ["diff", "--name-only"]
                    )
                    if success and files_output.strip():
                        unstaged_files = [
                            f for f in files_output.strip().split("\n") if f
                        ]

                        # Generate per-file diffs for unstaged changes
                        for file_path in unstaged_files:
                            success, diff = run_git_command(
                                repo_path, ["diff", "--", file_path]
                            )
                            if success and diff.strip():
                                diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (unstaged) ---\n"
                                diff_footer = (
                                    f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
                                )
                                formatted_diff = diff_header + diff + diff_footer

                                # Check token limit
                                from utils import estimate_tokens

                                diff_tokens = estimate_tokens(formatted_diff)
                                if total_tokens + diff_tokens <= max_tokens:
                                    all_diffs.append(formatted_diff)
                                    total_tokens += diff_tokens

                # Combine unique files
                changed_files = list(set(staged_files + unstaged_files))

            # Add repository summary
            if changed_files:
                repo_summaries.append(
                    {
                        "path": repo_path,
                        "branch": status["branch"],
                        "ahead": status["ahead"],
                        "behind": status["behind"],
                        "changed_files": len(changed_files),
                        "files": changed_files[:20],  # First 20 for summary
                    }
                )

        if not all_diffs:
            return "No pending changes found in any of the git repositories."

        # Process context files if provided
        context_files_content = []
        context_files_summary = []
        context_tokens = 0

        if request.files:
            remaining_tokens = max_tokens - total_tokens

            # Read context files with remaining token budget
            file_content, file_summary = read_files(request.files)

            # Check if context files fit in remaining budget
            if file_content:
                context_tokens = estimate_tokens(file_content)

                if context_tokens <= remaining_tokens:
                    # Use the full content from read_files
                    context_files_content = [file_content]
                    # Parse summary to create individual file summaries
                    summary_lines = file_summary.split("\n")
                    for line in summary_lines:
                        if line.strip() and not line.startswith("Total files:"):
                            context_files_summary.append(f"✅ Included: {line.strip()}")
                else:
                    context_files_summary.append(
                        f"⚠️ Context files too large (~{context_tokens:,} tokens, budget: ~{remaining_tokens:,} tokens)"
                    )
                    # Include as much as fits
                    if remaining_tokens > 1000:  # Only if we have reasonable space
                        truncated_content = file_content[
                            : int(
                                len(file_content)
                                * (remaining_tokens / context_tokens)
                                * 0.9
                            )
                        ]
                        context_files_content.append(
                            f"\n--- BEGIN CONTEXT FILES (TRUNCATED) ---\n{truncated_content}\n--- END CONTEXT FILES ---\n"
                        )
                        context_tokens = remaining_tokens
                    else:
                        context_tokens = 0

            total_tokens += context_tokens

        # Build the final prompt
        prompt_parts = []

        # Add original request context if provided
        if request.original_request:
            prompt_parts.append(
                f"## Original Request/Ticket\n\n{request.original_request}\n"
            )

        # Add review parameters
        prompt_parts.append("## Review Parameters\n")
        prompt_parts.append(f"- Review Type: {request.review_type}")
        prompt_parts.append(f"- Severity Filter: {request.severity_filter}")

        if request.focus_on:
            prompt_parts.append(f"- Focus Areas: {request.focus_on}")

        if request.compare_to:
            prompt_parts.append(f"- Comparing Against: {request.compare_to}")
        else:
            review_scope = []
            if request.include_staged:
                review_scope.append("staged")
            if request.include_unstaged:
                review_scope.append("unstaged")
            prompt_parts.append(f"- Reviewing: {' and '.join(review_scope)} changes")

        # Add repository summary
        prompt_parts.append("\n## Repository Changes Summary\n")
        prompt_parts.append(f"Found {len(repo_summaries)} repositories with changes:\n")

        for idx, summary in enumerate(repo_summaries, 1):
            prompt_parts.append(f"\n### Repository {idx}: {summary['path']}")
            if "error" in summary:
                prompt_parts.append(f"⚠️ Error: {summary['error']}")
            else:
                prompt_parts.append(f"- Branch: {summary['branch']}")
                if summary["ahead"] or summary["behind"]:
                    prompt_parts.append(
                        f"- Ahead: {summary['ahead']}, Behind: {summary['behind']}"
                    )
                prompt_parts.append(f"- Changed Files: {summary['changed_files']}")

                if summary["files"]:
                    prompt_parts.append("\nChanged files:")
                    for file in summary["files"]:
                        prompt_parts.append(f"  - {file}")
                    if summary["changed_files"] > len(summary["files"]):
                        prompt_parts.append(
                            f"  ... and {summary['changed_files'] - len(summary['files'])} more files"
                        )

        # Add context files summary if provided
        if context_files_summary:
            prompt_parts.append("\n## Context Files Summary\n")
            for summary_item in context_files_summary:
                prompt_parts.append(f"- {summary_item}")

        # Add token usage summary
        if total_tokens > 0:
            prompt_parts.append(f"\nTotal context tokens used: ~{total_tokens:,}")

        # Add the diff contents
        prompt_parts.append("\n## Git Diffs\n")
        if all_diffs:
            prompt_parts.extend(all_diffs)
        else:
            prompt_parts.append("--- NO DIFFS FOUND ---")

        # Add context files content if provided
        if context_files_content:
            prompt_parts.append("\n## Additional Context Files")
            prompt_parts.append(
                "The following files are provided for additional context. They have NOT been modified.\n"
            )
            prompt_parts.extend(context_files_content)

        # Add review instructions
        prompt_parts.append("\n## Review Instructions\n")
        prompt_parts.append(
            "Please review these changes according to the system prompt guidelines. "
            "Pay special attention to alignment with the original request, completeness of implementation, "
            "potential bugs, security issues, and any edge cases not covered."
        )

        # Add instruction for requesting files if needed
        if not request.files:
            prompt_parts.append(
                "\nIf you need additional context files to properly review these changes "
                "(such as configuration files, documentation, or related code), "
                "you may request them using the standardized JSON response format."
            )

        return "\n".join(prompt_parts)
