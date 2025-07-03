"""
Research Tool for Zen MCP Server.

A SimpleTool that provides fast, effective web search capabilities using
Perplexity Sonar models.
Optimized for technical documentation, development resources, and current
information retrieval.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

import config
from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool

logger = logging.getLogger(__name__)


class ResearchRequest(ToolRequest):
    """
    Request model for ResearchTool.

    Extends ToolRequest with research-specific parameters for controlling
    Perplexity search behavior and result formatting.
    """

    query: str = Field(
        ...,
        description=("Search query or question for web research. Be specific for better results."),
    )

    domain_filter: Optional[list[str]] = Field(
        default=None,
        description=(
            "Domains to focus the search on (e.g., ['stackoverflow.com', 'github.com']). Use '-' prefix to exclude."
        ),
    )

    recency_filter: Optional[str] = Field(
        default=None,
        description=("How recent the information should be: 'hour', 'day', 'week', 'month', 'year'"),
    )

    search_mode: Optional[str] = Field(
        default_factory=lambda: config.RESEARCH_DEFAULT_SEARCH_MODE,
        description=("Search quality vs speed trade-off: 'web', 'high', 'medium', 'low'"),
    )

    return_related_questions: Optional[bool] = Field(
        default=True,
        description="Include suggested related questions for further research",
    )

    max_tokens: Optional[int] = Field(
        default_factory=lambda: config.RESEARCH_DEFAULT_MAX_TOKENS,
        ge=100,
        le=4096,
        description=("Maximum tokens for response. Higher values allow more comprehensive results"),
    )


class Source(BaseModel):
    """
    Model representing a source of information from web search.

    Captures key metadata about each source including title, URL,
    publication date, and optional snippet content.
    """

    title: Optional[str] = Field(None, description="Title of the source document or page")
    url: str = Field(..., description="URL of the source")
    date: Optional[str] = Field(None, description="Publication or last modified date")
    snippet: Optional[str] = Field(None, description="Brief excerpt or snippet from the source")


class ResearchResponse(BaseModel):
    """
    Response model for ResearchTool.

    Structures the AI's research findings with comprehensive metadata
    including sources, search efficiency metrics, and related questions.
    """

    answer: str = Field(..., description="Main research findings and analysis")

    sources: Optional[list[Source]] = Field(
        default=None,
        description="List of sources used in the research",
    )

    citations: Optional[list[str]] = Field(
        default=None,
        description=("List of citation URLs (fallback if sources not available)"),
    )

    related_questions: Optional[list[str]] = Field(
        default=None,
        description="Suggested questions for further research",
    )

    search_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Search performance and quality metrics",
    )


class ResearchTool(SimpleTool):
    """
    Fast web research tool using Perplexity Sonar models.

    Provides targeted web search capabilities with rich metadata including:
    - Search domain filtering (focus on technical sites)
    - Temporal filtering (recent, fresh information)
    - Quality optimization (balanced search vs performance)
    - Source citations and verification
    - Related questions for deeper exploration

    Ideal for:
    - Technical documentation lookup
    - Framework/library research
    - Best practices discovery
    - Current development trends
    - API reference verification
    """

    def get_name(self) -> str:
        """Return the tool name."""
        return "research"

    def get_description(self) -> str:
        """Return the tool description."""
        return "Fast web research using Perplexity Sonar for technical information " "and current developments"

    def get_request_model(self):
        """Return the request model class."""
        return ResearchRequest

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """
        Define the input schema for ResearchTool.

        Returns:
            Dict mapping field names to JSON schema definitions
        """
        return {
            "query": {
                "type": "string",
                "description": ("Search query or question for web research. " "Be specific for better results."),
            },
            "domain_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Domains to focus search on (e.g., ['stackoverflow.com', "
                    "'github.com']). Use '-' prefix to exclude."
                ),
                "default": [],
            },
            "recency_filter": {
                "type": "string",
                "enum": ["hour", "day", "week", "month", "year"],
                "description": ("How recent the information should be. Default: " "no filter (all time)"),
            },
            "search_mode": {
                "type": "string",
                "enum": ["web", "high", "medium", "low"],
                "description": (
                    "Search quality vs speed trade-off. "
                    "'web' for comprehensive, "
                    "'high' for detailed, "
                    "'medium' balanced, "
                    "'low' for fast"
                ),
            },
            "return_related_questions": {
                "type": "boolean",
                "description": ("Include suggested related questions for further research"),
            },
            "max_tokens": {
                "type": "integer",
                "minimum": 100,
                "maximum": 4096,
                "description": ("Maximum tokens for response. Higher values allow more " "comprehensive results"),
            },
        }

    def get_required_fields(self) -> list[str]:
        """Return list of required field names."""
        return ["query"]

    def get_default_model(self) -> str:
        """Return the default model for this tool."""
        return config.RESEARCH_DEFAULT_MODEL

    def get_system_prompt(self) -> str:
        """Get the system prompt for research tasks."""
        from systemprompts.research_prompt import RESEARCH_PROMPT

        return RESEARCH_PROMPT

    async def prepare_prompt(self, request) -> str:
        """
        Prepare the prompt for web research.

        Args:
            request: Validated ResearchRequest object

        Returns:
            Formatted prompt for the AI model
        """
        query = request.query

        # Build prompt with research context
        prompt = f"""Please research this query using web search: {query}

Research Guidelines:
- Focus on accurate, up-to-date information
- Prioritize authoritative sources (official docs, well-known tech sites)
- Include specific examples and practical information
- Provide clear citations and source references
- Synthesize information from multiple sources when relevant

Query to research: {query}"""

        return prompt

    def get_perplexity_params(self, request) -> dict[str, Any]:
        """
        Extract Perplexity-specific parameters from the request.

        Args:
            request: Validated request object

        Returns:
            Dictionary of Perplexity API parameters
        """
        params = {
            "search_mode": request.search_mode,
            "return_related_questions": request.return_related_questions,
            "max_tokens": request.max_tokens,
        }

        # Domain filtering (optional)
        if request.domain_filter:
            params["search_domain_filter"] = request.domain_filter

        # Recency filtering (optional)
        if request.recency_filter:
            params["search_recency_filter"] = request.recency_filter

        return params

    def format_response(
        self,
        response: str,
        request,
        model_info: Optional[dict] = None,
    ) -> str:
        """
        Format the research response with robust extraction and display of all
        possible source URLs in ideal Markdown format.
        """
        formatted_response = response

        # Extract citation information from metadata
        citations_found = []
        if model_info and "metadata" in model_info:
            metadata = model_info["metadata"]

            # 1. Priority: search_results (structured format)
            if "search_results" in metadata and metadata["search_results"]:
                for result in metadata["search_results"]:
                    url = result.get("url")
                    title = result.get("title", "").strip()
                    date = result.get("date", "").strip()

                    if url:
                        # Create Markdown link with title if available
                        if title:
                            citation = f"[{title}]({url})"
                            if date:
                                citation += f" ({date})"
                        else:
                            citation = url
                        citations_found.append(citation)

            # 2. Fallback: other metadata fields (legacy compatibility)
            if not citations_found:
                # Try different metadata field names
                url_sources = []
                field_names = ["citations", "source_urls", "citation_urls"]
                for field_name in field_names:
                    if field_name in metadata and metadata[field_name]:
                        url_sources.extend(metadata[field_name])

                # Handle sources field (list of objects)
                if "sources" in metadata and metadata["sources"]:
                    for source in metadata["sources"]:
                        if isinstance(source, dict):
                            url = source.get("url")
                            title = source.get("title", "").strip()
                            if url:
                                if title:
                                    cite = f"[{title}]({url})"
                                    citations_found.append(cite)
                                else:
                                    citations_found.append(url)
                        elif isinstance(source, str):
                            url_sources.append(source)

                # Convert simple URLs to citations
                for url in url_sources:
                    if url and url not in citations_found:
                        citations_found.append(url)

        # 3. Extract URLs from response text as fallback
        if not citations_found:
            import re

            markdown_pattern = r"\[([^\]]+)\]\((https?://[^)]+)\)"
            markdown_urls = re.findall(markdown_pattern, response)
            for title, url in markdown_urls:
                citations_found.append(f"[{title}]({url})")

            # Also look for plain URLs
            plain_urls = re.findall(r"https?://[^\s\)]+", response)
            for url in plain_urls:
                if url not in citations_found:
                    citations_found.append(url)

        # Remove duplicates while preserving order
        unique_citations = []
        seen_urls = set()
        for citation in citations_found:
            # Extract URL from citation to check for duplicates
            if citation.startswith("["):
                import re

                url_match = re.search(r"\]\((https?://[^)]+)\)", citation)
                url = url_match.group(1) if url_match else citation
            else:
                url = citation

            if url not in seen_urls:
                unique_citations.append(citation)
                seen_urls.add(url)

        # Add citations section if we found any sources
        if unique_citations:
            # Remove any existing citation blocks from response
            import re

            # Remove various citation block patterns
            patterns = [
                r"\n\n##\s*Sources?\s*\n.*?(?=\n\n[A-Z]|\n\n##|\Z)",
                r"\n\n##\s*Citations?\s*\n.*?(?=\n\n[A-Z]|\n\n##|\Z)",
                (r"\n\*\*?Sources?\s*cit[ée]es?\s*:?\*\*?\n.*?" r"(?=\n\n[A-Z]|\n\n##|\Z)"),
                (r"\n\*\*?Citations?\s*:?\*\*?\n.*?" r"(?=\n\n[A-Z]|\n\n##|\Z)"),
            ]

            for pattern in patterns:
                formatted_response = re.sub(
                    pattern,
                    "",
                    formatted_response,
                    flags=re.DOTALL | re.IGNORECASE,
                )

            # Add clean citations section
            # Use "Citations" for fallback metadata, otherwise "Sources"
            is_citations_fallback = model_info and "metadata" in model_info and "citations" in model_info["metadata"]
            header = "## Citations" if is_citations_fallback else "## Sources"
            formatted_response += f"\n\n{header}\n"
            for i, citation in enumerate(unique_citations, 1):
                formatted_response += f"\n{i}. {citation}"

        # Add related questions if available
        if model_info and "metadata" in model_info:
            metadata = model_info["metadata"]
            if "related_questions" in metadata:
                related_questions = metadata["related_questions"]
                if related_questions:
                    formatted_response += "\n\n## Related Questions\n"
                    for question in related_questions:
                        formatted_response += f"\n- {question}"

            # Add search efficiency info if available
            if "search_efficiency" in metadata:
                efficiency = metadata["search_efficiency"]
                queries_count = metadata.get("search_queries_count", "unknown")
                formatted_response += (
                    f"\n\n---\n*Search efficiency: {efficiency:.2f} | " f"Queries used: {queries_count}*"
                )

        # Export to markdown file if enabled (for tests)
        if config.RESEARCH_EXPORT_TO_MD and not os.environ.get("RESEARCH_DISABLE_EXPORT", "false").lower() == "true":
            try:
                export_status = self._export_to_markdown(formatted_response, request)
                formatted_response += f"\n\n---\n*{export_status}*"
            except Exception as e:
                formatted_response += f"\n\n---\n*Export failed: {str(e)}*"

        return formatted_response

    def _export_to_markdown(self, content: str, request) -> str:
        """
        Export research results to a markdown file.

        Args:
            content: The formatted research content
            request: The original research request

        Returns:
            Status message about the export
        """
        # Create export directory if it doesn't exist
        export_dir = Path(config.RESEARCH_EXPORT_DIR)
        export_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Clean query for filename (remove special characters)
        clean_query = "".join(c for c in request.query[:50] if c.isalnum() or c in (" ", "-", "_")).strip()
        clean_query = clean_query.replace(" ", "_")
        filename = f"research_{timestamp}_{clean_query}.md"

        # Create full file path
        file_path = export_dir / filename

        # Prepare markdown content with metadata header
        markdown_content = f"""# Research Report: {request.query}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Search Mode:** {request.search_mode}
**Max Tokens:** {request.max_tokens}

---

{content}
"""

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return f"Research report saved to {file_path}"

    async def execute(self, arguments: dict[str, Any]) -> list:
        """
        Execute the research tool with Perplexity-specific parameters.

        This overrides the base execute method to inject Perplexity parameters
        before calling the parent implementation.
        """
        # Create request object to access parameters
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Get Perplexity-specific parameters
        perplexity_params = self.get_perplexity_params(request)

        # Inject Perplexity parameters into arguments
        enhanced_arguments = {**arguments, **perplexity_params}

        # Call parent execute with enhanced arguments
        return await super().execute(enhanced_arguments)
