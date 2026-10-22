"""MCP 1.x SDK server: real initialization, discovery and tool calls (stdio/HTTP)."""
import argparse
from functools import lru_cache
from mcp.server.fastmcp import FastMCP
from .service import ResearchService


def build_server(service=None, host='127.0.0.1', port=8001):
    mcp = FastMCP('Kabyle Research', host=host, port=port, stateless_http=True, json_response=True)
    @lru_cache(maxsize=1)
    def get_service():
        return service or ResearchService()
    @mcp.tool()
    def search_catalog(query: str) -> dict:
        """Find validated catalog entries with checked citations, without LLM generation."""
        return get_service().ask(query)
    @mcp.tool()
    def get_fiche(fiche_id: str) -> dict:
        """Read one validated catalog entry by its exact identifier."""
        record = get_service().get_fiche(fiche_id)
        if record is None:
            raise ValueError('Unknown or unvalidated fiche')
        return record
    return mcp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8001)
    args = parser.parse_args()
    build_server(host=args.host, port=args.port).run(transport=args.transport)


if __name__ == '__main__':
    main()
