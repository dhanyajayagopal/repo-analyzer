from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services.repo_service import RepositoryService
from parsers.code_parser import CodeParser
import os
from dotenv import load_dotenv

# Debug environment loading
print("=== DEBUG START ===")
print(f"Current directory: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")

# Load environment
load_dotenv()

# Check what was loaded
api_key = os.getenv("OPENAI_API_KEY")

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

class AskRequest(BaseModel):
    question: str

@app.post("/repositories/{repo_id}/ask")
async def ask_about_code(repo_id: str, request: AskRequest):
    """Ask natural language questions about the codebase"""
    question = request.question
    print(f"AI query for repo {repo_id}: '{question}'")
    
    if repo_id not in parsed_code:
        raise HTTPException(status_code=404, detail="Repository not found or not parsed")
    
    elements = parsed_code[repo_id]
    
    if not elements:
        return {"answer": "No code elements found in this repository."}
    
    # Analyze code structure for intelligent responses
    functions = [e for e in elements if e['type'] == 'function']
    classes = [e for e in elements if e['type'] == 'class']
    languages = list(set(e['language'] for e in elements))
    
    # Use real OpenAI if available, otherwise use smart mock
    if client:
        try:
            # Create context from code elements
            context_parts = []
            for element in elements[:15]:
                context_parts.append(
                    f"File: {element['file_path']}\n"
                    f"Type: {element['type']}\n"
                    f"Name: {element['name']}\n"
                    f"Code:\n{element['code'][:150]}...\n"
                )
            
            context = "\n---\n".join(context_parts)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a code analysis assistant. Answer questions about the provided codebase clearly and concisely."
                    },
                    {
                        "role": "user", 
                        "content": f"Here's a codebase:\n\n{context}\n\nQuestion: {question}"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return {
                "answer": response.choices[0].message.content,
                "context_elements": len(elements)
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fall back to mock if API fails
    
    # Smart mock response based on actual code analysis
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['what', 'does', 'do', 'purpose']):
        answer = f"This is a {languages[0]} project with {len(functions)} functions and {len(classes)} classes. Based on the function names like {', '.join([f['name'] for f in functions[:3]])}, it appears to handle HTTP requests and web API functionality."
    elif any(word in question_lower for word in ['how many', 'count']):
        answer = f"Code statistics:\n• {len(functions)} functions\n• {len(classes)} classes\n• {len(set(e['file_path'] for e in elements))} files\n• Language: {', '.join(languages)}"
    elif any(word in question_lower for word in ['main', 'key', 'important']):
        main_items = [f['name'] for f in functions if not f['name'].startswith('_')][:5]
        answer = f"Key components:\n• Main functions: {', '.join(main_items)}\n• Classes: {', '.join([c['name'] for c in classes[:3]])}"
    else:
        answer = f"I analyzed {len(elements)} code elements in this {languages[0]} codebase. Try asking: 'What does this do?', 'How many functions?', or 'What are the main components?'"
    
    return {
        "answer": answer + "\n\n(Using code analysis - add OpenAI key for AI responses)",
        "context_elements": len(elements)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)