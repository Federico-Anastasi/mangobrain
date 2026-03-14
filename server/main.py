"""MangoBrain — Entry point: MCP server + FastAPI REST API + Dashboard."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from server.config import API_PORT, DB_PATH, EMBEDDING_DEVICE, EMBEDDING_MODEL, PACKAGE_DIR
from server.database import Database
from server.embeddings import Embedder
from server.graph import GraphManager
from server.mcp_tools import register_tools
from server.retrieval import RetrievalEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("mangobrain")


async def run_mcp_server() -> None:
    """Run the MCP server over stdio."""
    logger.info("Initializing MangoBrain MCP server...")

    db = await Database.create(DB_PATH)
    logger.info("Database ready at %s", DB_PATH)

    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    embedder.load()

    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    server = FastMCP("mango-brain")
    register_tools(server, db, embedder, graph, retrieval)
    logger.info("MCP tools registered — running on stdio")

    await server.run_stdio_async()
    await db.close()


async def run_api_server() -> None:
    """Run the FastAPI REST API server (serves dashboard + API)."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from server.api_routes import create_api_router

    db = await Database.create(DB_PATH)

    app = FastAPI(title="MangoBrain API", version="3.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(db))

    # Serve dashboard static files if the build exists
    dashboard_dist = PACKAGE_DIR / "dashboard_dist"
    if dashboard_dist.exists():
        # SPA fallback: serve index.html for non-API routes
        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Try to serve the file directly
            file_path = dashboard_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            # Fallback to index.html for SPA routing
            return FileResponse(dashboard_dist / "index.html")

        # Mount static assets before the catch-all
        app.mount("/assets", StaticFiles(directory=str(dashboard_dist / "assets")), name="static")
        logger.info("Dashboard served from %s", dashboard_dist)
    else:
        logger.warning("Dashboard build not found at %s — API only mode", dashboard_dist)

    config = uvicorn.Config(app, host="0.0.0.0", port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    logger.info("API server starting on http://localhost:%d", API_PORT)
    await server.serve()


async def run_all() -> None:
    """Run both MCP (stdio) and API server concurrently."""
    logger.info("Starting MangoBrain in full mode (MCP + API)...")

    db = await Database.create(DB_PATH)
    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    embedder.load()
    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    # MCP server
    mcp_server = FastMCP("mango-brain")
    register_tools(mcp_server, db, embedder, graph, retrieval)

    # API server
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from server.api_routes import create_api_router

    app = FastAPI(title="MangoBrain API", version="3.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(db))

    dashboard_dist = PACKAGE_DIR / "dashboard_dist"
    if dashboard_dist.exists():
        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = dashboard_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(dashboard_dist / "index.html")

        app.mount("/assets", StaticFiles(directory=str(dashboard_dist / "assets")), name="static")

    api_config = uvicorn.Config(app, host="0.0.0.0", port=API_PORT, log_level="info")
    api_server = uvicorn.Server(api_config)

    # Run both concurrently
    await asyncio.gather(
        mcp_server.run_stdio_async(),
        api_server.serve(),
    )
    await db.close()


def main() -> None:
    """Entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        asyncio.run(run_api_server())
    elif len(sys.argv) > 1 and sys.argv[1] == "all":
        asyncio.run(run_all())
    else:
        asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
