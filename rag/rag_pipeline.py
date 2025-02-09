import sys
import os
import logging
import threading

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from typing import List, Optional, Dict
import threading
from contextlib import asynccontextmanager

import grpc

from context_fetcher import ContextFetcher
from faiss_indexer import FaissIndexer
from llm_interface import LlmInterface
from raft.raft_server import RaftNode
from raft.raft_server import start_server, send_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    query: str = Field(..., description="The query string to process")

class QueryResponse(BaseModel):
    response: str
    status: str = Field(default="success")

class NodeConfig(BaseModel):
    node_id: int = Field(..., description="Unique identifier for the node")
    port: int = Field(..., description="Port number for the service")
    peers: List[str] = Field(default_factory=list, description="List of peer node addresses")
    embedding_model: str = Field(..., description="Name of the embedding model to use")
    doc_path: str = Field(..., description="Path to the document directory")
    llm_model: str = Field(..., description="Name of the language model to use")


class Pipeline:
    def __init__(self, embedding_model_name, doc_path, model, raft):
        self.llm = LlmInterface(model)
        self.faiss = FaissIndexer(embedding_model_name, doc_path, raft)
        self.faiss.create_faiss_index()
        self.context_engine = ContextFetcher(self.faiss)
        self.raft = raft
        self.is_running = True

    def refresh_rag(self, doc_path):
        if not self.is_running:
            raise Exception("Pipeline is not running")
        self.faiss.add_documents_to_index(doc_path)

    def query(self, query):
        if not self.is_running:
            raise Exception("Pipeline is not running")
            
        if not self.raft.is_leader():
            leader = self.raft.is_leader()
            if leader:
                raise Exception(f"Not the leader. Forward request to {leader}")
            raise Exception("No leader available")
            
        context = self.context_engine.retrieve(query=query)
        return self.llm.query(query, context)
    
    def stop(self):
        self.is_running = False
        
    def start(self):
        self.is_running = True


def cleanup_ports(ports):
    import socket
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up RAG pipeline service")
    yield
    # Shutdown
    logger.info("Shutting down RAG pipeline service")
    if pipeline:
        pipeline.stop()
    # Cleanup ports on shutdown
    if node_config:
        cleanup_ports([node_config.port])

app = FastAPI(
    title="RAG Pipeline Service",
    description="A distributed RAG (Retrieval-Augmented Generation) service with RAFT consensus",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = None
node_config = None

@app.post("/query", response_model=QueryResponse, 
         description="Process a query using the RAG pipeline")
async def handle_query(request: QueryRequest):
    try:
        if not pipeline:
            logger.error("Pipeline not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Service not initialized"
            )
        
        if not pipeline.is_running:
            logger.error("Pipeline is not running")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Service is not running"
            )
        
        logger.info(f"Processing query: {request.query}")
        response = pipeline.query(request.query)
        return QueryResponse(response=response, status="success")
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/start", 
         description="Start the RAG pipeline service")
async def start_node():
    try:
        if not pipeline:
            logger.error("Cannot start: Pipeline not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
            
        pipeline.start()
        logger.info("Node started successfully")
        return {"status": "success", "message": "Node started"}
        
    except Exception as e:
        logger.error(f"Error starting node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/stop", 
         description="Stop the RAG pipeline service")
async def stop_node():
    try:
        if not pipeline:
            logger.error("Cannot stop: Pipeline not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized"
            )
            
        pipeline.stop()
        logger.info("Node stopped successfully")
        return {"status": "success", "message": "Node stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/status",
         description="Get the current status of the RAG pipeline service")
async def get_status():
    try:
        if not pipeline:
            return {
                "status": "not_initialized",
                "message": "Service not initialized"
            }
            
        status_info = {
            "status": "running" if pipeline.is_running else "stopped",
            "is_leader": pipeline.raft.is_leader(),
            # "leader": pipeline.raft.get_leader(),
            "node_id": node_config.node_id if node_config else None,
            "embedding_model": node_config.embedding_model if node_config else None
        }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/health",
         description="Health check endpoint")
async def health_check():
    return {"status": "healthy"}

def start_raft_server(node_config: NodeConfig):
    try:
        import socket
        # Test if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('0.0.0.0', node_config.port))
        sock.close()
        
        if result == 0:
            raise Exception(f"Port {node_config.port} is already in use")
            
        logger.info(f"Starting RAFT server with node_id={node_config.node_id}")
        raft_node = RaftNode(node_config.node_id, node_config.peers)
        raft_thread = threading.Thread(
            target=start_server,
            args=(node_config.node_id, node_config.port + 1000, node_config.peers, raft_node),
            daemon=True
        )
        raft_thread.start()
        return raft_node
    except Exception as e:
        logger.error(f"Failed to start RAFT server: {str(e)}", exc_info=True)
        raise

def run_server(host: str, port: int):
    try:
        import socket
        # Test if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            raise Exception(f"Port {port} is already in use")
            
        logger.info(f"Starting FastAPI server on {host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        if len(sys.argv) < 8:
            logger.error("Insufficient arguments provided")
            print("Usage: python rag_pipeline.py <node_id> <port> <peer1> <peer2> <embedding_model> <doc_path> <llm_model>")
            sys.exit(1)
            
        node_config = NodeConfig(
            node_id=int(sys.argv[1]),
            port=int(sys.argv[2]),
            peers=sys.argv[3:5],
            embedding_model=sys.argv[5],
            doc_path=sys.argv[6],
            llm_model=sys.argv[7]
        )
        
        logger.info(f"Initializing node with config: {node_config.dict()}")
        
        # Clean up ports before starting
        cleanup_ports([node_config.port])
        
        # Start RAFT in a separate thread
        raft_node = start_raft_server(node_config)
        
        # Initialize pipeline
        pipeline = Pipeline(
            node_config.embedding_model,
            node_config.doc_path,
            node_config.llm_model,
            raft_node
        )
        
        # Run FastAPI server
        run_server("0.0.0.0", node_config.port)
        
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}", exc_info=True)
        # Cleanup on error
        if node_config:
            cleanup_ports([node_config.port])
        sys.exit(1)