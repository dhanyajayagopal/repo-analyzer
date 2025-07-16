from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

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

class RepositoryRequest(BaseModel):
    github_url: str

class QueryRequest(BaseModel):
    query: str
    repo_id: str

# In-memory storage for now (we'll add real DB later)
repositories = {}
parsed_code = {}

@app.get("/")
async def root():
    return {"message": "Repo Analyzer API is running"}

@app.post("/repositories")
async def create_repository(request: RepositoryRequest):
    repo_id = f"repo_{len(repositories) + 1}"
    repositories[repo_id] = {
        "id": repo_id,
        "github_url": request.github_url,
        "status": "processing"
    }
    return {"repo_id": repo_id, "status": "created"}

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