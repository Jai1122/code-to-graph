"""Code analysis service using LLM providers."""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from loguru import logger

from .vllm_client import VLLMClient


class CodeAnalyzer:
    """Analyze code using VLLM provider for insights and documentation."""
    
    def __init__(self, llm_client: VLLMClient):
        """Initialize code analyzer.
        
        Args:
            llm_client: VLLM client instance
        """
        self.llm_client = llm_client
        self.client_type = "vllm"
        logger.info(f"Initialized code analyzer with VLLM")
    
    def _generate_response(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int):
        """Generate response using the configured LLM client.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Response text
        """
        response = self.llm_client.generate_sync(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        # Extract text from VLLM response
        if response.choices and len(response.choices) > 0:
            return response.choices[0].get("text", "")
        return ""
    
    def analyze_code_structure(self, code: str, language: str = "unknown") -> Dict[str, Any]:
        """Analyze code structure and provide insights.
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            Analysis results dictionary
        """
        system_prompt = (
            "You are a code analysis expert. Analyze the provided code and return "
            "a structured analysis in JSON format with the following fields: "
            "functions, classes, imports, complexity, patterns, suggestions."
        )
        
        prompt = f"""
Analyze this {language} code:

```{language}
{code}
```

Provide analysis including:
1. Functions and their purposes
2. Classes and their responsibilities  
3. Import dependencies
4. Code complexity assessment
5. Design patterns identified
6. Improvement suggestions

Format as JSON.
"""
        
        try:
            response_text = self._generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            logger.info(f"Code structure analysis completed for {language} code")
            return {
                "analysis": response_text,
                "language": language,
                "code_length": len(code),
                "model_used": self.llm_client.model
            }
            
        except Exception as e:
            logger.error(f"Code structure analysis failed: {e}")
            return {
                "error": str(e),
                "analysis": None,
                "language": language
            }
    
    def generate_documentation(self, code: str, language: str = "unknown") -> str:
        """Generate documentation for code.
        
        Args:
            code: Source code to document
            language: Programming language
            
        Returns:
            Generated documentation
        """
        system_prompt = (
            "You are a technical documentation expert. Generate clear, "
            "comprehensive documentation for the provided code."
        )
        
        prompt = f"""
Generate documentation for this {language} code:

```{language}
{code}
```

Include:
1. Overview and purpose
2. Function/method descriptions
3. Parameter explanations
4. Return value descriptions
5. Usage examples
6. Dependencies

Format as Markdown.
"""
        
        try:
            response_text = self._generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=1500
            )
            
            logger.info(f"Documentation generated for {language} code")
            return response_text
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            return f"# Documentation Generation Failed\n\nError: {str(e)}"
    
    def explain_code_flow(self, code: str, language: str = "unknown") -> str:
        """Explain the execution flow of code.
        
        Args:
            code: Source code to explain
            language: Programming language
            
        Returns:
            Flow explanation
        """
        system_prompt = (
            "You are a code flow expert. Explain how code executes step by step, "
            "focusing on the logical flow and key decision points."
        )
        
        prompt = f"""
Explain the execution flow of this {language} code:

```{language}
{code}
```

Provide:
1. Step-by-step execution flow
2. Key decision points and branches
3. Data transformations
4. Error handling paths
5. Performance considerations

Make it clear and educational.
"""
        
        try:
            response_text = self._generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=1200
            )
            
            logger.info(f"Code flow explanation generated for {language} code")
            return response_text
            
        except Exception as e:
            logger.error(f"Code flow explanation failed: {e}")
            return f"Code flow explanation failed: {str(e)}"
    
    def suggest_improvements(self, code: str, language: str = "unknown") -> List[str]:
        """Suggest code improvements.
        
        Args:
            code: Source code to improve
            language: Programming language
            
        Returns:
            List of improvement suggestions
        """
        system_prompt = (
            "You are a senior code reviewer. Provide specific, actionable "
            "improvement suggestions focusing on code quality, performance, "
            "and best practices."
        )
        
        prompt = f"""
Review this {language} code and suggest improvements:

```{language}
{code}
```

Focus on:
1. Code quality and readability
2. Performance optimizations
3. Best practice adherence
4. Security considerations
5. Maintainability
6. Error handling

Provide specific, actionable suggestions.
"""
        
        try:
            response_text = self._generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.6,
                max_tokens=1000
            )
            
            # Parse suggestions from response
            suggestions = []
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                    suggestions.append(line[1:].strip())
            
            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions if suggestions else [response_text]
            
        except Exception as e:
            logger.error(f"Improvement suggestion failed: {e}")
            return [f"Suggestion generation failed: {str(e)}"]
    
    def analyze_repository_insights(self, file_paths: List[Path], max_files: int = 10) -> Dict[str, Any]:
        """Analyze multiple files for repository-level insights.
        
        Args:
            file_paths: List of file paths to analyze
            max_files: Maximum number of files to analyze
            
        Returns:
            Repository insights dictionary
        """
        if not file_paths:
            return {"error": "No files provided for analysis"}
        
        # Limit files for analysis
        files_to_analyze = file_paths[:max_files]
        
        system_prompt = (
            "You are a software architect. Analyze multiple code files "
            "and provide high-level insights about the codebase structure, "
            "patterns, and overall design."
        )
        
        file_contents = []
        for file_path in files_to_analyze:
            try:
                if file_path.exists() and file_path.is_file():
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    file_contents.append(f"File: {file_path.name}\n```\n{content[:1000]}...\n```")
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
        
        if not file_contents:
            return {"error": "No readable files found"}
        
        prompt = f"""
Analyze this codebase with {len(files_to_analyze)} files:

{chr(10).join(file_contents)}

Provide repository-level insights:
1. Overall architecture and patterns
2. Technology stack and dependencies
3. Code organization and structure
4. Potential issues or improvements
5. Development recommendations

Format as structured analysis.
"""
        
        try:
            response_text = self._generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=1500
            )
            
            logger.info(f"Repository insights generated for {len(files_to_analyze)} files")
            return {
                "insights": response_text,
                "files_analyzed": len(files_to_analyze),
                "total_files": len(file_paths),
                "model_used": self.llm_client.model
            }
            
        except Exception as e:
            logger.error(f"Repository insights analysis failed: {e}")
            return {
                "error": str(e),
                "files_analyzed": 0,
                "total_files": len(file_paths)
            }