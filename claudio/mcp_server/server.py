"""MCP server setup for Claudio video generation tools."""

import asyncio
from typing import Any

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from claudio.mcp_server.tools import TOOLS

logger = structlog.get_logger(__name__)


class ClaudioMCPServer:
    """MCP server for Claudio video generation tools."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.server = Server("claudio-video-generator")
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            tools = []
            for tool_def in TOOLS:
                tools.append(
                    Tool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        inputSchema=tool_def["inputSchema"],
                    )
                )
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
            """Call a tool by name with the given arguments."""
            # Find the tool
            tool_def = None
            for t in TOOLS:
                if t["name"] == name:
                    tool_def = t
                    break

            if not tool_def:
                raise ValueError(f"Unknown tool: {name}")

            # Call the tool handler
            handler = tool_def["handler"]

            try:
                result = await handler(**arguments)
                return [result]
            except Exception as e:
                logger.error("tool_call_failed", tool=name, error=str(e))
                return [{"success": False, "error": str(e)}]

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            logger.info("mcp_server_started", name="claudio-video-generator")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Main entry point for the MCP server."""
    server = ClaudioMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
