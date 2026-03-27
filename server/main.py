"""MangoBrain — Entry point: MCP server + FastAPI REST API + Dashboard."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from server.config import API_PORT, DB_PATH, EMBEDDING_DEVICE, EMBEDDING_MODEL, PACKAGE_DIR
from server.database import Database
from server.graph import GraphManager
from server.mcp_tools import register_tools


def _check_embedding_deps() -> None:
    """Check that torch and sentence-transformers are installed."""
    try:
        import torch  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        print(
            "\n[MangoBrain] Error: Embedding engine not installed.\n"
            "\n"
            "  torch and sentence-transformers are required to run the server.\n"
            "  They are installed during 'mangobrain install' (step 2).\n"
            "\n"
            "  To fix, run:\n"
            "    cd /path/to/your/project\n"
            "    mangobrain install\n"
            "\n"
            "  Or install manually:\n"
            "    pip install torch sentence-transformers numpy scipy\n"
        )
        sys.exit(1)


def _load_embedder():
    """Load embedder (import here to defer heavy imports)."""
    from server.embeddings import Embedder
    from server.retrieval import RetrievalEngine
    return Embedder, RetrievalEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("mangobrain")


async def _load_embedding_model(embedder) -> None:
    """Load embedding model in a thread to avoid blocking the event loop.

    Wraps the synchronous SentenceTransformer load in asyncio.to_thread
    so the MCP stdio connection can be established immediately.
    """
    try:
        await asyncio.to_thread(embedder.load)
        logger.info("Embedding model ready")
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
        # Don't crash — server stays alive but tools that need embeddings
        # will return errors via ping(model_loaded=false)


async def run_mcp_server() -> None:
    """Run the MCP server over stdio."""
    _check_embedding_deps()
    Embedder, RetrievalEngine = _load_embedder()

    logger.info("Initializing MangoBrain MCP server...")

    db = await Database.create(DB_PATH)
    logger.info("Database ready at %s", DB_PATH)

    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)

    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    server = FastMCP("mangobrain")
    register_tools(server, db, embedder, graph, retrieval)
    logger.info("MCP tools registered — running on stdio")

    # Load embedding model in background thread — don't block stdio
    asyncio.create_task(_load_embedding_model(embedder))

    await server.run_stdio_async()
    await db.close()


async def run_api_server() -> None:
    """Run the FastAPI REST API server (serves dashboard + API)."""
    _check_embedding_deps()
    Embedder, RetrievalEngine = _load_embedder()

    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from server.api_routes import create_api_router

    db = await Database.create(DB_PATH)
    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    # API server: load synchronously (no MCP timeout constraint)
    try:
        embedder.load()
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    app = FastAPI(title="MangoBrain API", version="3.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(db, retrieval))

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
    _check_embedding_deps()
    Embedder, RetrievalEngine = _load_embedder()

    logger.info("Starting MangoBrain in full mode (MCP + API)...")

    db = await Database.create(DB_PATH)
    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    # MCP server — register tools first, load model in background
    mcp_server = FastMCP("mangobrain")
    register_tools(mcp_server, db, embedder, graph, retrieval)

    # Load embedding model in background thread — don't block MCP stdio
    asyncio.create_task(_load_embedding_model(embedder))

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
    app.include_router(create_api_router(db, retrieval))

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
