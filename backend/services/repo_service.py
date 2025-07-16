import git
import os
import shutil
from pathlib import Path
import tempfile

class RepositoryService:
    def __init__(self):
        self.repos_dir = Path("./repos")
        self.repos_dir.mkdir(exist_ok=True)
    
    def clone_repository(self, github_url: str, repo_id: str):
        """Clone a GitHub repository locally"""
        try:
            repo_path = self.repos_dir / repo_id
            
            # Remove if exists
            if repo_path.exists():
                shutil.rmtree(repo_path)
            
            # Clone repository
            print(f"Cloning {github_url} to {repo_path}")
            git.Repo.clone_from(github_url, repo_path)
            
            return str(repo_path)
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    def get_file_structure(self, repo_path: str):
        """Get basic file structure"""
        repo_path = Path(repo_path)
        files = []
        
        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and not self._should_ignore(file_path):
                relative_path = file_path.relative_to(repo_path)
                files.append({
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "extension": file_path.suffix
                })
        
        return files
    
    def _should_ignore(self, file_path: Path):
        """Skip common non-code files"""
        ignore_patterns = ['.git', '__pycache__', 'node_modules', '.env']
        ignore_extensions = ['.pyc', '.log', '.tmp']
        
        path_str = str(file_path)
        return (
            any(pattern in path_str for pattern in ignore_patterns) or
            any(path_str.endswith(ext) for ext in ignore_extensions) or
            file_path.stat().st_size > 1024 * 1024  # Skip files > 1MB
        )