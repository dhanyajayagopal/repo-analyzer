import re
from pathlib import Path

class CodeParser:
    def __init__(self):
        print("Initialized simple regex-based code parser")
    
    def parse_repository(self, repo_path: str):
        """Parse all code files in repository using regex"""
        print(f"Starting to parse repository: {repo_path}")
        repo_path = Path(repo_path)
        parsed_elements = []
        
        # Find Python files
        python_files = list(repo_path.rglob("*.py"))
        js_files = list(repo_path.rglob("*.js"))
        
        print(f"Found {len(python_files)} Python files and {len(js_files)} JS files")
        
        for file_path in python_files:
            try:
                elements = self.parse_python_file(file_path, repo_path)
                parsed_elements.extend(elements)
                if elements:
                    print(f"Parsed {file_path.name}: found {len(elements)} elements")
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        
        for file_path in js_files:
            try:
                elements = self.parse_js_file(file_path, repo_path)
                parsed_elements.extend(elements)
                if elements:
                    print(f"Parsed {file_path.name}: found {len(elements)} elements")
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        
        print(f"Total parsed elements: {len(parsed_elements)}")
        return parsed_elements
    
    def parse_python_file(self, file_path: Path, repo_root: Path):
        """Simple regex-based Python parsing"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            return []
        
        elements = []
        lines = content.split('\n')
        
        # Find function definitions
        for i, line in enumerate(lines):
            # Match function definitions
            func_match = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
            if func_match:
                indent = len(func_match.group(1))
                func_name = func_match.group(2)
                
                # Skip private methods and magic methods for cleaner results
                if func_name.startswith('_'):
                    continue
                
                # Find end of function (simple approach - next 10 lines or less)
                end_line = min(i + 10, len(lines))
                code_snippet = '\n'.join(lines[i:end_line])
                
                # Try to get relative path from repo root
                try:
                    relative_path = file_path.relative_to(repo_root)
                except:
                    relative_path = file_path.name
                
                elements.append({
                    'type': 'function',
                    'name': func_name,
                    'file_path': str(relative_path),
                    'start_line': i + 1,
                    'end_line': end_line,
                    'code': code_snippet,
                    'docstring': self._extract_python_docstring(lines, i),
                    'language': 'python'
                })
            
            # Match class definitions
            class_match = re.match(r'^(\s*)class\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(2)
                code_snippet = '\n'.join(lines[i:min(i + 5, len(lines))])
                
                try:
                    relative_path = file_path.relative_to(repo_root)
                except:
                    relative_path = file_path.name
                
                elements.append({
                    'type': 'class',
                    'name': class_name,
                    'file_path': str(relative_path),
                    'start_line': i + 1,
                    'end_line': min(i + 5, len(lines)),
                    'code': code_snippet,
                    'docstring': self._extract_python_docstring(lines, i),
                    'language': 'python'
                })
        
        return elements
    
    def parse_js_file(self, file_path: Path, repo_root: Path):
        """Simple regex-based JavaScript parsing"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            return []
        
        elements = []
        lines = content.split('\n')
        
        # Find function definitions
        for i, line in enumerate(lines):
            func_name = None
            
            # Match various function patterns
            patterns = [
                (r'function\s+(\w+)\s*\(', 1),  # function name()
                (r'(\w+)\s*:\s*function\s*\(', 1),  # name: function()
                (r'const\s+(\w+)\s*=\s*.*=>', 1),  # const name = () =>
                (r'let\s+(\w+)\s*=\s*.*=>', 1),  # let name = () =>
                (r'var\s+(\w+)\s*=\s*.*=>', 1),  # var name = () =>
                (r'(\w+)\s*=\s*.*=>', 1),  # name = () =>
            ]
            
            for pattern, group in patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(group)
                    break
            
            if func_name:
                code_snippet = '\n'.join(lines[i:min(i + 8, len(lines))])
                
                try:
                    relative_path = file_path.relative_to(repo_root)
                except:
                    relative_path = file_path.name
                
                elements.append({
                    'type': 'function',
                    'name': func_name,
                    'file_path': str(relative_path),
                    'start_line': i + 1,
                    'end_line': min(i + 8, len(lines)),
                    'code': code_snippet,
                    'docstring': '',
                    'language': 'javascript'
                })
        
        return elements
    
    def _extract_python_docstring(self, lines, func_line):
        """Extract docstring from Python function/class"""
        try:
            # Look for docstring in the next few lines
            for i in range(func_line + 1, min(func_line + 5, len(lines))):
                line = lines[i].strip()
                if line.startswith('"""') or line.startswith("'''"):
                    # Single line docstring
                    if line.count('"""') == 2 or line.count("'''") == 2:
                        return line.strip('"""').strip("'''").strip()
                    # Multi-line docstring start
                    elif line.startswith('"""') or line.startswith("'''"):
                        docstring_lines = [line.strip('"""').strip("'''")]
                        quote_type = '"""' if '"""' in line else "'''"
                        
                        # Look for end of docstring
                        for j in range(i + 1, min(i + 10, len(lines))):
                            if quote_type in lines[j]:
                                docstring_lines.append(lines[j].split(quote_type)[0])
                                return ' '.join(docstring_lines).strip()
                            else:
                                docstring_lines.append(lines[j].strip())
                        
                        return ' '.join(docstring_lines).strip()
            return ''
        except:
            return ''