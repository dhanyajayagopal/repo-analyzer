'use client';

import { useState } from 'react';

interface Repository {
  id: string;
  github_url: string;
  status: string;
  file_count?: number;
  code_elements_count?: number;
  error?: string;
  files?: Array<{
    path: string;
    size: number;
    extension: string;
  }>;
}

interface CodeElement {
  type: string;
  name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  code: string;
  docstring: string;
  language: string;
}

export default function Home() {
  const [githubUrl, setGithubUrl] = useState('');
  const [repository, setRepository] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CodeElement[]>([]);
  const [searching, setSearching] = useState(false);
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  // Add AI query function
  const handleAiQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repository || repository.status !== 'ready') return;
    
    setAiLoading(true);
    setAiResponse('');
    
    try {
      const response = await fetch(
        `http://localhost:8000/repositories/${repository.id}/ask`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ question: aiQuestion }),
        }
      );
      const data = await response.json();
      setAiResponse(data.answer);
    } catch (error) {
      console.error('AI query error:', error);
      setAiResponse('Sorry, there was an error processing your question.');
    }
    setAiLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setRepository(null);
    setSearchResults([]);
    
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

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repository || repository.status !== 'ready') return;
    
    setSearching(true);
    try {
      const response = await fetch(
        `http://localhost:8000/repositories/${repository.id}/search?q=${encodeURIComponent(searchQuery)}`
      );
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    }
    setSearching(false);
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
                   repository.status === 'parsing' ? 'Parsing code...' :
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

              {repository.code_elements_count && (
                <div>
                  <strong>Code Elements:</strong> {repository.code_elements_count} functions/classes found
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
        
        {repository && repository.status === 'ready' && (
          <div className="mt-8 bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Search Code</h2>
            <form onSubmit={handleSearch} className="mb-4">
              <div className="flex gap-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search functions, classes, or code content..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={searching}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>
            </form>
            
            {searchResults && searchResults.length > 0 && (
              <div>
                <h3 className="font-semibold mb-3">Search Results ({searchResults.length})</h3>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {searchResults.map((element, index) => (
                    <div key={index} className="border rounded-lg p-4 bg-gray-50">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-mono text-lg font-semibold text-blue-600">
                            {element.name}
                          </span>
                          <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                            {element.type}
                          </span>
                          <span className="ml-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                            {element.language}
                          </span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {element.file_path}:{element.start_line}
                        </span>
                      </div>
                      
                      {element.docstring && (
                        <p className="text-gray-600 text-sm mb-2 italic">
                          {element.docstring}
                        </p>
                      )}
                      
                      <pre className="bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto">
                        <code>{element.code?.slice(0, 300) || 'No code preview available'}...</code>
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {repository && repository.status === 'ready' && (
              <div className="mt-8 bg-white p-6 rounded-lg shadow">
                <h2 className="text-xl font-semibold mb-4">Ask AI About This Code</h2>
                <form onSubmit={handleAiQuery} className="mb-4">
                  <div className="flex gap-4">
                    <input
                      type="text"
                      value={aiQuestion}
                      onChange={(e) => setAiQuestion(e.target.value)}
                      placeholder="What does this codebase do? How does authentication work?"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      type="submit"
                      disabled={aiLoading}
                      className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                    >
                      {aiLoading ? 'Thinking...' : 'Ask AI'}
                    </button>
                  </div>
                </form>
                
                {aiResponse && (
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-2 text-purple-800">AI Response:</h3>
                    <div className="text-gray-800 whitespace-pre-wrap">{aiResponse}</div>
                  </div>
                )}
              </div>
            )}

            {searchQuery && searchResults && searchResults.length === 0 && !searching && (
              <div className="text-gray-500 text-center py-4">
                No results found for "{searchQuery}"
              </div>
            )}
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