from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services.repo_service import RepositoryService
from parsers.code_parser import CodeParser

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
code_parser = CodeParser()
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
        print(f"Starting to process repository {repo_id} from {github_url}")
        
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
        
        # Parse code elements
        repositories[repo_id]["status"] = "parsing"
        print(f"Starting code parsing for {repo_id}")
        
        code_elements = await loop.run_in_executor(
            executor,
            code_parser.parse_repository,
            repo_path
        )
        
        print(f"Parsed {len(code_elements)} code elements")
        
        # Store parsed code
        parsed_code[repo_id] = code_elements
        print(f"Stored code elements for {repo_id}")
        
        # Update repository info
        repositories[repo_id].update({
            "status": "ready",
            "repo_path": repo_path,
            "file_count": len(files),
            "code_elements_count": len(code_elements),
            "files": files[:100]  # Limit for API response
        })
        
        print(f"Repository {repo_id} processing complete")
        
    except Exception as e:
        print(f"Error processing repository {repo_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        repositories[repo_id]["status"] = "error"
        repositories[repo_id]["error"] = str(e)

@app.get("/repositories/{repo_id}")
async def get_repository(repo_id: str):
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repositories[repo_id]

@app.get("/repositories/{repo_id}/search")
async def search_code(repo_id: str, q: str = ""):
    """Search for code elements by name or content"""
    print(f"Search request for repo {repo_id} with query: '{q}'")
    
    if repo_id not in parsed_code:
        print(f"Repository {repo_id} not found in parsed_code. Available: {list(parsed_code.keys())}")
        raise HTTPException(status_code=404, detail="Repository not found or not parsed")
    
    elements = parsed_code[repo_id]
    print(f"Found {len(elements)} total elements in {repo_id}")
    
    if not q:
        print("No query provided, returning first 20 elements")
        return {"results": elements[:20]}  # Return first 20 if no query
    
    # Simple text search
    query_lower = q.lower()
    results = []
    
    for element in elements:
        if (query_lower in element['name'].lower() or 
            query_lower in element.get('docstring', '').lower() or
            query_lower in element.get('code', '').lower()):
            results.append(element)
    
    print(f"Search for '{q}' returned {len(results)} results")
    return {"results": results[:20]}  # Limit results

@app.get("/repositories/{repo_id}/debug")
async def debug_repository(repo_id: str):
    """Debug endpoint to see what was parsed"""
    print(f"Debug request for repo {repo_id}")
    
    if repo_id not in parsed_code:
        print(f"Repository {repo_id} not found in parsed_code. Available: {list(parsed_code.keys())}")
        return {"error": "Repository not found or not parsed", "available_repos": list(parsed_code.keys())}
    
    elements = parsed_code[repo_id]
    return {
        "total_elements": len(elements),
        "sample_elements": elements[:5],  # First 5 elements
        "element_types": list(set(e['type'] for e in elements)) if elements else [],
        "languages": list(set(e['language'] for e in elements)) if elements else []
    }

@app.get("/debug/repositories")
async def list_repositories():
    """List all repositories for debugging"""
    return {
        "repositories": repositories,
        "parsed_code_keys": list(parsed_code.keys())
    }

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