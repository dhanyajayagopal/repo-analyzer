'use client';

import { useState } from 'react';

interface Repository {
  id: string;
  github_url: string;
  status: string;
  file_count?: number;
  error?: string;
  files?: Array<{
    path: string;
    size: number;
    extension: string;
  }>;
}

export default function Home() {
  const [githubUrl, setGithubUrl] = useState('');
  const [repository, setRepository] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setRepository(null);
    
    try {
      const response = await fetch('http://localhost:8000/repositories', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ github_url: githubUrl }),
      });
      
      const data = await response.json();
      
      // Poll for completion
      const repoId = data.repo_id;
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`http://localhost:8000/repositories/${repoId}`);
          const statusData = await statusResponse.json();
          
          setRepository(statusData);
          
          if (statusData.status === 'ready' || statusData.status === 'error') {
            clearInterval(pollInterval);
            setLoading(false);
          }
        } catch (error) {
          console.error('Polling error:', error);
          clearInterval(pollInterval);
          setLoading(false);
        }
      }, 1000);
      
    } catch (error) {
      console.error('Error:', error);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-4">
          Repo Analyzer
        </h1>
        <p className="text-gray-600 text-center mb-12">
          Upload a GitHub repository and analyze its code structure
        </p>
        
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="flex gap-4">
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Analyzing...' : 'Analyze Repository'}
            </button>
          </div>
        </form>
        
        {repository && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Repository Analysis</h2>
            <div className="space-y-3">
              <div>
                <strong>URL:</strong> 
                <a 
                  href={repository.github_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="ml-2 text-blue-600 hover:underline"
                >
                  {repository.github_url}
                </a>
              </div>
              
              <div>
                <strong>Status:</strong>
                <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${
                  repository.status === 'ready' ? 'bg-green-100 text-green-800' :
                  repository.status === 'error' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {repository.status === 'cloning' ? 'Cloning repository...' :
                   repository.status === 'ready' ? 'Ready for analysis' :
                   repository.status === 'error' ? 'Error occurred' :
                   repository.status}
                </span>
              </div>
              
              {repository.file_count && (
                <div>
                  <strong>Files Found:</strong> {repository.file_count}
                </div>
              )}
              
              {repository.error && (
                <div className="text-red-600">
                  <strong>Error:</strong> {repository.error}
                </div>
              )}
              
              {repository.files && repository.files.length > 0 && (
                <div>
                  <strong>Sample Files:</strong>
                  <div className="mt-2 max-h-60 overflow-y-auto">
                    <div className="grid gap-1">
                      {repository.files.slice(0, 20).map((file, index) => (
                        <div 
                          key={index}
                          className="flex justify-between items-center py-1 px-2 bg-gray-50 rounded text-sm"
                        >
                          <span className="font-mono">{file.path}</span>
                          <span className="text-gray-500">
                            {(file.size / 1024).toFixed(1)}KB
                          </span>
                        </div>
                      ))}
                      {repository.files.length > 20 && (
                        <div className="text-gray-500 text-center py-2">
                          ... and {repository.files.length - 20} more files
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {!repository && !loading && (
          <div className="text-center text-gray-500">
            Enter a GitHub repository URL to get started
          </div>
        )}
      </div>
    </div>
  );
}