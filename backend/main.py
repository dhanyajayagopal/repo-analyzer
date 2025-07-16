from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services.repo_service import RepositoryService

load_dotenv()

app = FastAPI(title="Repo Analyzer API")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
repo_service = RepositoryService()
executor = ThreadPoolExecutor(max_workers=3)

class RepositoryRequest(BaseModel):
    github_url: str

class QueryRequest(BaseModel):
    query: str
    repo_id: str

# In-memory storage
repositories = {}
parsed_code = {}

@app.get("/")
async def root():
    return {"message": "Repo Analyzer API is running"}

@app.post("/repositories")
async def create_repository(request: RepositoryRequest):
    repo_id = f"repo_{len(repositories) + 1}"
    
    # Store initial state
    repositories[repo_id] = {
        "id": repo_id,
        "github_url": request.github_url,
        "status": "cloning"
    }
    
    # Start background processing
    asyncio.create_task(process_repository(repo_id, request.github_url))
    
    return {"repo_id": repo_id, "status": "cloning"}

async def process_repository(repo_id: str, github_url: str):
    """Process repository in background"""
    try:
        print(f"Starting to process repository {repo_id}")
        
        # Clone repository
        loop = asyncio.get_event_loop()
        repo_path = await loop.run_in_executor(
            executor, 
            repo_service.clone_repository, 
            github_url, 
            repo_id
        )
        
        print(f"Repository cloned to {repo_path}")
        
        # Get file structure
        files = await loop.run_in_executor(
            executor,
            repo_service.get_file_structure,
            repo_path
        )
        
        print(f"Found {len(files)} files")
        
        # Update repository info
        repositories[repo_id].update({
            "status": "ready",
            "repo_path": repo_path,
            "file_count": len(files),
            "files": files[:100]  # Limit for API response
        })
        
        print(f"Repository {repo_id} processing complete")
        
    except Exception as e:
        print(f"Error processing repository {repo_id}: {str(e)}")
        repositories[repo_id]["status"] = "error"
        repositories[repo_id]["error"] = str(e)

@app.get("/repositories/{repo_id}")
async def get_repository(repo_id: str):
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repositories[repo_id]

@app.post("/query")
async def query_codebase(request: QueryRequest):
    return {
        "query": request.query,
        "response": "This is a placeholder response",
        "relevant_files": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)