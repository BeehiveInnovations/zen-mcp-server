"""
Debug helper for MCP validation issues.
Add this to server.py to get detailed validation logs.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def debug_tool_registration(tool_name: str, tool_obj: Any) -> None:
    """Log detailed information about tool registration."""
    logger.info(f"=== DEBUG: Registering tool '{tool_name}' ===")

    # Check attributes vs methods
    has_name_attr = hasattr(tool_obj, "name")
    has_desc_attr = hasattr(tool_obj, "description")
    has_name_method = hasattr(tool_obj, "get_name")
    has_desc_method = hasattr(tool_obj, "get_description")
    has_schema_method = hasattr(tool_obj, "get_input_schema")

    logger.info(f"  Attributes: name={has_name_attr}, description={has_desc_attr}")
    logger.info(
        f"  Methods: get_name={has_name_method}, get_description={has_desc_method}, get_input_schema={has_schema_method}"
    )

    # Try to get values
    try:
        if has_name_attr:
            logger.info(f"  tool.name = {tool_obj.name}")
        if has_name_method:
            logger.info(f"  tool.get_name() = {tool_obj.get_name()}")
    except Exception as e:
        logger.error(f"  Error getting name: {e}")

    try:
        if has_desc_attr:
            desc = tool_obj.description[:100] + "..." if len(tool_obj.description) > 100 else tool_obj.description
            logger.info(f"  tool.description = {desc}")
    except Exception as e:
        logger.error(f"  Error getting description: {e}")

    # Check schema
    try:
        if has_schema_method:
            schema = tool_obj.get_input_schema()
            logger.info(f"  Schema type: {type(schema)}")
            logger.info(f"  Schema keys: {list(schema.keys()) if isinstance(schema, dict) else 'Not a dict'}")

            # Validate schema structure
            if isinstance(schema, dict):
                if "type" not in schema:
                    logger.warning("  ⚠️  Schema missing 'type' field")
                if "properties" not in schema:
                    logger.warning("  ⚠️  Schema missing 'properties' field")
                if schema.get("type") != "object":
                    logger.warning(f"  ⚠️  Schema type is '{schema.get('type')}', expected 'object'")
            else:
                logger.error("  ❌ Schema is not a dictionary!")
    except Exception as e:
        logger.error(f"  Error getting schema: {e}")

    logger.info(f"=== END DEBUG for '{tool_name}' ===")


def validate_mcp_tool_compatibility(tools: Dict[str, Any]) -> Dict[str, list]:
    """
    Validate all tools for MCP compatibility and return issues.

    Returns:
        Dict with tool names as keys and list of issues as values
    """
    issues = {}

    for name, tool in tools.items():
        tool_issues = []

        # Check required attributes
        if not hasattr(tool, "name"):
            tool_issues.append("Missing 'name' attribute")
        elif not isinstance(tool.name, str):
            tool_issues.append(f"'name' attribute is {type(tool.name)}, expected str")

        if not hasattr(tool, "description"):
            tool_issues.append("Missing 'description' attribute")
        elif not isinstance(tool.description, str):
            tool_issues.append(f"'description' attribute is {type(tool.description)}, expected str")

        # Check required methods
        if not hasattr(tool, "get_input_schema"):
            tool_issues.append("Missing 'get_input_schema' method")
        else:
            try:
                schema = tool.get_input_schema()
                if not isinstance(schema, dict):
                    tool_issues.append(f"Schema is {type(schema)}, expected dict")
                else:
                    # Validate JSON Schema structure
                    if "type" not in schema:
                        tool_issues.append("Schema missing 'type' field")
                    if schema.get("type") != "object":
                        tool_issues.append(f"Schema type is '{schema.get('type')}', expected 'object'")
                    if "properties" not in schema:
                        tool_issues.append("Schema missing 'properties' field")
            except Exception as e:
                tool_issues.append(f"Error calling get_input_schema: {e}")

        if not hasattr(tool, "execute"):
            tool_issues.append("Missing 'execute' method")

        if tool_issues:
            issues[name] = tool_issues

    return issues


def log_mcp_validation_report(tools: Dict[str, Any]) -> None:
    """Generate and log a comprehensive MCP validation report."""
    logger.info("=" * 60)
    logger.info("MCP TOOL VALIDATION REPORT")
    logger.info("=" * 60)

    issues = validate_mcp_tool_compatibility(tools)

    if not issues:
        logger.info("✅ All tools pass MCP compatibility checks!")
    else:
        logger.warning(f"⚠️  Found issues in {len(issues)} tools:")
        for tool_name, tool_issues in issues.items():
            logger.warning(f"\n{tool_name}:")
            for issue in tool_issues:
                logger.warning(f"  - {issue}")

    logger.info("=" * 60)
