"""Main CLI entry point for CodeToGraph."""

from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from ..core.config import settings
from ..core.logger import setup_logging
from ..processors.chunked_processor import ChunkedRepositoryProcessor
from ..processors.repository_analyzer import RepositoryAnalyzer
from ..parsers.hybrid_parser import HybridParser
from ..storage.neo4j_client import Neo4jClient
from ..storage.graph_importer import GraphImporter
from ..llm.ollama_client import OllamaClient
from ..llm.vllm_client import VLLMClient
from ..llm.code_analyzer import CodeAnalyzer
from ..llm.llm_factory import LLMFactory

console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--log-level', default='INFO', help='Set log level')
def main(debug: bool, log_level: str) -> None:
    """CodeToGraph: Scalable repository analysis and graph database system."""
    if debug:
        settings.debug = True
        log_level = 'DEBUG'
    
    setup_logging(log_level=log_level)
    logger.info(f"CodeToGraph v{settings.version} initialized")


@main.command()
@click.option('--repo-path', '-r', required=True, type=click.Path(exists=True, path_type=Path),
              help='Path to repository to analyze')
@click.option('--language', '-l', type=click.Choice(['go', 'java', 'python', 'javascript', 'typescript']),
              help='Primary language (auto-detected if not specified)')
@click.option('--chunk-size', '-c', default=50, type=int, help='Maximum files per chunk')
@click.option('--chunk-strategy', type=click.Choice(['package', 'size', 'hybrid']), 
              default='hybrid', help='Chunking strategy')
@click.option('--enable-tree-sitter/--disable-tree-sitter', default=True,
              help='Enable/disable Tree-sitter parsing')
@click.option('--enable-joern/--disable-joern', default=True,
              help='Enable/disable Joern CPG parsing')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Output directory for analysis results')
def analyze(
    repo_path: Path,
    language: Optional[str],
    chunk_size: int,
    chunk_strategy: str,
    enable_tree_sitter: bool,
    enable_joern: bool,
    output_dir: Optional[Path]
) -> None:
    """Analyze a repository and store in graph database."""
    
    console.print(f"\n[bold blue]Analyzing repository:[/bold blue] {repo_path}")
    
    # Initialize components
    processor = ChunkedRepositoryProcessor(repo_path)
    parser = HybridParser(enable_tree_sitter=enable_tree_sitter, enable_joern=enable_joern)
    
    # Override settings
    settings.processing.max_chunk_size = chunk_size
    settings.processing.chunk_strategy = chunk_strategy
    
    try:
        with Progress() as progress:
            # Discover files
            console.print("\n[yellow]Discovering source files...[/yellow]")
            files = processor.discover_files()
            
            if not files:
                console.print("[red]No source files found![/red]")
                return
            
            console.print(f"Found {len(files)} source files")
            
            # Create chunks
            console.print(f"\n[yellow]Creating chunks using {chunk_strategy} strategy...[/yellow]")
            chunks = processor.create_chunks(files, chunk_strategy)
            
            console.print(f"Created {len(chunks)} chunks")
            
            # Process chunks
            task = progress.add_task("[green]Processing chunks...", total=len(chunks))
            
            total_entities = 0
            total_relations = 0
            
            for i, chunk in enumerate(chunks):
                progress.update(task, description=f"[green]Processing chunk {chunk.id}...[/green]")
                
                # Parse chunk
                entities, relations = parser.parse_chunk(chunk)
                
                total_entities += len(entities)
                total_relations += len(relations)
                
                console.print(f"Chunk {chunk.id}: {len(entities)} entities, {len(relations)} relations")
                
                progress.update(task, advance=1)
            
            console.print(f"\n[bold green]Analysis completed![/bold green]")
            console.print(f"Total entities: {total_entities}")
            console.print(f"Total relations: {total_relations}")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        console.print(f"[red]Analysis failed: {e}[/red]")
        raise


@main.command()
@click.argument('query_text')
@click.option('--limit', '-l', default=10, type=int, help='Maximum results to return')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'cypher']), 
              default='table', help='Output format')
def query(query_text: str, limit: int, format: str) -> None:
    """Query the graph database using natural language."""
    
    console.print(f"\n[bold blue]Query:[/bold blue] {query_text}")
    
    try:
        # TODO: Implement LLM query processing
        console.print("[yellow]LLM query processing not yet implemented[/yellow]")
        
        # For now, show a placeholder Cypher query
        sample_cypher = f"""
        MATCH (e:Entity) 
        WHERE e.name CONTAINS '{query_text}' 
        RETURN e.name, e.type, e.file_path 
        LIMIT {limit}
        """
        
        console.print(f"\n[cyan]Generated Cypher:[/cyan]")
        console.print(sample_cypher)
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        console.print(f"[red]Query failed: {e}[/red]")


@main.command()
@click.option('--port', '-p', default=8080, type=int, help='Server port')
@click.option('--host', '-h', default='localhost', help='Server host')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def visualize(port: int, host: str, debug: bool) -> None:
    """Start the interactive visualization server."""
    
    console.print(f"\n[bold blue]Starting CodeToGraph visualization server...[/bold blue]")
    console.print(f"URL: http://{host}:{port}")
    console.print("\n[yellow]Features:[/yellow]")
    console.print("  🕸️  Interactive network graph with drag & zoom")
    console.print("  📊  Code statistics and metrics")
    console.print("  🔍  Search and filter entities")
    console.print("  🗂️  File explorer with entity breakdown")
    
    try:
        from ..visualization.dash_server import DashVisualizationServer
        from ..storage.neo4j_client import Neo4jClient
        
        # Check Neo4j connection first
        with Neo4jClient() as client:
            stats = client.get_database_stats()
            if stats['total_nodes'] == 0:
                console.print("\n[red]⚠️  No data found in Neo4j database![/red]")
                console.print("Run the import command first:")
                console.print("  code-to-graph import-graph --repo-path /path/to/repo")
                return
            
            console.print(f"\n[green]✓ Connected to Neo4j: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships[/green]")
        
        # Start visualization server
        server = DashVisualizationServer(debug=debug)
        
        console.print(f"\n[bold green]🚀 Server starting...[/bold green]")
        console.print(f"[bold cyan]Open your browser: http://{host}:{port}[/bold cyan]")
        console.print("\n[dim]Press Ctrl+C to stop the server[/dim]")
        
        # Run server (blocks until interrupted)
        server.run(host=host, port=port, threaded=False)
        
    except ImportError as e:
        logger.error(f"Visualization dependencies missing: {e}")
        console.print(f"[red]Missing dependencies: {e}[/red]")
        console.print("Install with: pip install dash plotly networkx pandas")
    except Exception as e:
        logger.error(f"Visualization server failed: {e}")
        console.print(f"[red]Server failed: {e}[/red]")


@main.command()
@click.option('--repo-path', '-r', type=click.Path(exists=True, path_type=Path),
              help='Path to repository to analyze and import (required if no existing data)')
@click.option('--clear', is_flag=True, help='Clear all data before import')
@click.option('--create-indexes', is_flag=True, help='Create performance indexes after import')
@click.option('--language', '-l', type=click.Choice(['go', 'java', 'python', 'javascript', 'typescript']),
              help='Primary language (auto-detected if not specified)')
@click.option('--chunk-size', '-c', default=50, type=int, help='Maximum files per chunk')
@click.option('--enable-tree-sitter/--disable-tree-sitter', default=True,
              help='Enable/disable Tree-sitter parsing')
@click.option('--enable-joern/--disable-joern', default=True,
              help='Enable/disable Joern CPG parsing')
def import_graph(
    repo_path: Optional[Path],
    clear: bool, 
    create_indexes: bool,
    language: Optional[str],
    chunk_size: int,
    enable_tree_sitter: bool,
    enable_joern: bool
) -> None:
    """Import parsed data into Neo4j database."""
    
    if not repo_path:
        console.print("[red]Repository path is required for import[/red]")
        console.print("Usage: code-to-graph import-graph --repo-path /path/to/repo")
        return
    
    console.print(f"\n[bold blue]Analyzing and importing repository:[/bold blue] {repo_path}")
    
    try:
        with Progress() as progress:
            # Initialize components
            processor = ChunkedRepositoryProcessor(repo_path)
            parser = HybridParser(enable_tree_sitter=enable_tree_sitter, enable_joern=enable_joern)
            
            # Override settings
            settings.processing.max_chunk_size = chunk_size
            
            # Discover and process files
            console.print("\n[yellow]Discovering source files...[/yellow]")
            files = processor.discover_files()
            
            if not files:
                console.print("[red]No source files found![/red]")
                return
            
            console.print(f"Found {len(files)} source files")
            
            # Create chunks
            console.print(f"\n[yellow]Creating chunks...[/yellow]")
            chunks = processor.create_chunks(files, settings.processing.chunk_strategy)
            console.print(f"Created {len(chunks)} chunks")
            
            # Process chunks and collect entities/relations
            task = progress.add_task("[green]Processing chunks...", total=len(chunks))
            
            all_entities = []
            all_relations = []
            
            for i, chunk in enumerate(chunks):
                progress.update(task, description=f"[green]Processing chunk {chunk.id}...[/green]")
                
                # Parse chunk
                entities, relations = parser.parse_chunk(chunk)
                
                all_entities.extend(entities)
                all_relations.extend(relations)
                
                progress.update(task, advance=1)
            
            console.print(f"\n[bold green]Analysis completed![/bold green]")
            console.print(f"Total entities: {len(all_entities)}")
            console.print(f"Total relations: {len(all_relations)}")
            
            # Import to Neo4j
            console.print(f"\n[bold blue]Importing to Neo4j...[/bold blue]")
            
            with GraphImporter() as importer:
                importer.import_graph(
                    entities=all_entities,
                    relationships=all_relations,
                    clear_existing=clear,
                    create_indexes=create_indexes,
                    prefix=f"{repo_path.name}_graph"
                )
            
            console.print(f"\n[bold green]Import completed successfully![/bold green]")
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        console.print(f"[red]Import failed: {e}[/red]")


@main.command()
@click.option('--model', help='Override the configured model name')
@click.argument('file_path', type=click.Path(exists=True, path_type=Path))
def analyze_code(model: Optional[str], file_path: Path) -> None:
    """Analyze code using configured LLM provider."""
    
    console.print(f"\n[bold blue]Analyzing code file:[/bold blue] {file_path}")
    
    # Override model if specified
    if model:
        if settings.llm.provider == "ollama":
            settings.llm.ollama_model = model
        elif settings.llm.provider == "vllm":
            settings.llm.vllm_model = model
    
    try:
        # Read file content
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        language = file_path.suffix.lstrip('.')
        
        # Initialize LLM client using factory
        with LLMFactory.create_client() as llm_client:
            if not llm_client.check_health():
                console.print(f"[red]Cannot connect to {settings.llm.provider.upper()} server[/red]")
                console.print(f"Provider: {settings.llm.provider}")
                if settings.llm.provider == "ollama":
                    console.print(f"URL: {settings.llm.ollama_base_url}")
                elif settings.llm.provider == "vllm":
                    console.print(f"URL: {settings.llm.vllm_base_url}")
                return
            
            analyzer = CodeAnalyzer(llm_client)
            
            with Progress() as progress:
                task = progress.add_task("[green]Analyzing code...", total=3)
                
                # Structure analysis
                progress.update(task, description="[green]Analyzing structure...", advance=1)
                structure = analyzer.analyze_code_structure(content, language)
                
                # Generate documentation
                progress.update(task, description="[green]Generating docs...", advance=1)
                docs = analyzer.generate_documentation(content, language)
                
                # Get improvements
                progress.update(task, description="[green]Getting suggestions...", advance=1)
                suggestions = analyzer.suggest_improvements(content, language)
        
        # Display results
        console.print(f"\n[bold green]Analysis Results for {file_path.name}[/bold green]")
        console.print(f"[dim]Provider: {settings.llm.provider.upper()} | Model: {LLMFactory.get_model_name()}[/dim]")
        
        if 'error' not in structure:
            console.print(f"\n[cyan]Structure Analysis:[/cyan]")
            console.print(structure.get('analysis', 'No analysis available'))
        
        console.print(f"\n[cyan]Documentation:[/cyan]")
        console.print(docs)
        
        console.print(f"\n[cyan]Improvement Suggestions:[/cyan]")
        for i, suggestion in enumerate(suggestions[:5], 1):
            console.print(f"{i}. {suggestion}")
            
    except Exception as e:
        logger.error(f"Code analysis failed: {e}")
        console.print(f"[red]Analysis failed: {e}[/red]")


@main.command()
@click.option('--model', help='Override the configured model name')
@click.option('--repo-path', '-r', required=True, type=click.Path(exists=True, path_type=Path),
              help='Path to repository to analyze')
@click.option('--max-files', default=10, help='Maximum files to analyze')
def repo_insights(model: Optional[str], repo_path: Path, max_files: int) -> None:
    """Get repository-level insights using configured LLM provider."""
    
    console.print(f"\n[bold blue]Analyzing repository:[/bold blue] {repo_path}")
    
    # Override model if specified
    if model:
        if settings.llm.provider == "ollama":
            settings.llm.ollama_model = model
        elif settings.llm.provider == "vllm":
            settings.llm.vllm_model = model
    
    try:
        # Find source files
        source_extensions = {'.py', '.go', '.java', '.js', '.ts', '.cpp', '.c', '.h', '.hpp'}
        source_files = []
        
        for ext in source_extensions:
            source_files.extend(repo_path.glob(f"**/*{ext}"))
        
        if not source_files:
            console.print("[red]No source files found![/red]")
            return
        
        console.print(f"Found {len(source_files)} source files")
        
        # Initialize LLM client using factory
        with LLMFactory.create_client() as llm_client:
            if not llm_client.check_health():
                console.print(f"[red]Cannot connect to {settings.llm.provider.upper()} server[/red]")
                return
            
            analyzer = CodeAnalyzer(llm_client)
            
            with Progress() as progress:
                task = progress.add_task("[green]Analyzing repository...", total=1)
                insights = analyzer.analyze_repository_insights(source_files, max_files)
                progress.update(task, advance=1)
        
        # Display results
        console.print(f"\n[bold green]Repository Insights[/bold green]")
        console.print(f"[dim]Provider: {settings.llm.provider.upper()} | Model: {LLMFactory.get_model_name()}[/dim]")
        
        if 'error' not in insights:
            console.print(f"\n[cyan]Analysis ({insights['files_analyzed']} files):[/cyan]")
            console.print(insights.get('insights', 'No insights available'))
            console.print(f"\n[dim]Model: {insights.get('model_used', 'Unknown')}[/dim]")
        else:
            console.print(f"[red]Analysis failed: {insights['error']}[/red]")
            
    except Exception as e:
        logger.error(f"Repository insights failed: {e}")
        console.print(f"[red]Analysis failed: {e}[/red]")


@main.command()
def llm_status() -> None:
    """Check LLM provider status and list models."""
    
    provider = settings.llm.provider.upper()
    console.print(f"\n[bold blue]{provider} Server Status[/bold blue]")
    
    try:
        with LLMFactory.create_client() as client:
            # Check health
            if client.check_health():
                if settings.llm.provider == "ollama":
                    console.print(f"[green]✓ Connected to {settings.llm.ollama_base_url}[/green]")
                elif settings.llm.provider == "vllm":
                    console.print(f"[green]✓ Connected to {settings.llm.vllm_base_url}[/green]")
                
                # List models
                models = client.list_models()
                
                if models:
                    table = Table(title="Available Models")
                    table.add_column("Model", style="cyan")
                    
                    if settings.llm.provider == "ollama":
                        table.add_column("Size", style="magenta")
                        table.add_column("Modified", style="green")
                        
                        for model in models:
                            size = model.get('size', 0)
                            size_str = f"{size / (1024**3):.1f}GB" if size > 0 else "Unknown"
                            modified = model.get('modified_at', 'Unknown')[:19] if 'modified_at' in model else 'Unknown'
                            table.add_row(
                                model.get('name', 'Unknown'),
                                size_str,
                                modified
                            )
                    else:  # VLLM
                        table.add_column("ID", style="magenta")
                        table.add_column("Object", style="green")
                        
                        for model in models:
                            table.add_row(
                                model.get('id', 'Unknown'),
                                model.get('id', 'Unknown'),
                                model.get('object', 'model')
                            )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No models found[/yellow]")
            else:
                base_url = settings.llm.ollama_base_url if settings.llm.provider == "ollama" else settings.llm.vllm_base_url
                console.print(f"[red]✗ Cannot connect to {base_url}[/red]")
                console.print(f"Make sure {provider} server is running and accessible")
                if settings.llm.provider == "vllm" and not settings.llm.vllm_api_key:
                    console.print("[yellow]Note: VLLM API key may be required[/yellow]")
                
    except Exception as e:
        logger.error(f"{provider} status check failed: {e}")
        console.print(f"[red]Status check failed: {e}[/red]")


@main.command()
@click.option('--ollama-url', default='http://localhost:11434', help='OLLAMA server URL')
def ollama_status(ollama_url: str) -> None:
    """Check OLLAMA server status and list models (legacy command)."""
    
    console.print(f"\n[bold yellow]⚠️  This command is deprecated. Use 'llm-status' instead.[/bold yellow]")
    console.print(f"\n[bold blue]OLLAMA Server Status[/bold blue]")
    
    try:
        with OllamaClient(base_url=ollama_url) as ollama:
            # Check health
            if ollama.check_health():
                console.print(f"[green]✓ Connected to {ollama_url}[/green]")
                
                # List models
                models = ollama.list_models()
                
                if models:
                    table = Table(title="Available Models")
                    table.add_column("Model", style="cyan")
                    table.add_column("Size", style="magenta")
                    table.add_column("Modified", style="green")
                    
                    for model in models:
                        size = model.get('size', 0)
                        size_str = f"{size / (1024**3):.1f}GB" if size > 0 else "Unknown"
                        modified = model.get('modified_at', 'Unknown')[:19] if 'modified_at' in model else 'Unknown'
                        table.add_row(
                            model.get('name', 'Unknown'),
                            size_str,
                            modified
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No models found[/yellow]")
            else:
                console.print(f"[red]✗ Cannot connect to {ollama_url}[/red]")
                console.print("Make sure OLLAMA is running")
                
    except Exception as e:
        logger.error(f"OLLAMA status check failed: {e}")
        console.print(f"[red]Status check failed: {e}[/red]")


@main.command()
def status() -> None:
    """Show system status and configuration."""
    
    table = Table(title="CodeToGraph Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    # Neo4j connection
    try:
        with Neo4jClient() as client:
            stats = client.get_database_stats()
            table.add_row("Neo4j", "✓ Connected", f"{stats['total_nodes']} nodes, {stats['total_relationships']} rels")
    except Exception as e:
        table.add_row("Neo4j", "✗ Failed", str(e))
    
    # Tree-sitter
    if settings.processing.enable_tree_sitter:
        table.add_row("Tree-sitter", "✓ Enabled", f"Languages: {', '.join(settings.processing.supported_languages)}")
    else:
        table.add_row("Tree-sitter", "✗ Disabled", "")
    
    # Joern
    if settings.processing.enable_joern:
        table.add_row("Joern", "? Unknown", "Path detection needed")
    else:
        table.add_row("Joern", "✗ Disabled", "")
    
    # LLM Provider
    try:
        provider = settings.llm.provider.upper()
        if LLMFactory.check_health():
            model_name = LLMFactory.get_model_name()
            table.add_row(f"LLM ({provider})", "✓ Connected", f"Model: {model_name}")
        else:
            table.add_row(f"LLM ({provider})", "✗ Failed", "Server not responding")
    except Exception as e:
        table.add_row(f"LLM ({settings.llm.provider.upper()})", "✗ Failed", f"Error: {str(e)[:50]}")
    
    # Add LLM configuration details
    if settings.llm.provider == "ollama":
        table.add_row("LLM URL", "ℹ Info", settings.llm.ollama_base_url)
        table.add_row("LLM Model", "ℹ Info", settings.llm.ollama_model)
    elif settings.llm.provider == "vllm":
        table.add_row("LLM URL", "ℹ Info", settings.llm.vllm_base_url)
        api_key_status = "Configured" if settings.llm.vllm_api_key else "❌ Missing"
        table.add_row("API Key", "ℹ Info", api_key_status)
        table.add_row("LLM Model", "ℹ Info", settings.llm.vllm_model)
        # Add VLLM-specific info for VPN environments
        if "vllm" in settings.llm.vllm_base_url.lower():
            table.add_row("Environment", "ℹ Info", "VPN/Secured")
    elif settings.llm.provider == "openai":
        api_key_status = "Configured" if settings.llm.openai_api_key else "❌ Missing"
        table.add_row("OpenAI Key", "ℹ Info", api_key_status)
        table.add_row("LLM Model", "ℹ Info", settings.llm.openai_model)
    
    # Configuration
    table.add_row("Chunk Size", "ℹ Info", str(settings.processing.max_chunk_size))
    table.add_row("Memory Limit", "ℹ Info", f"{settings.processing.max_memory_gb}GB")
    table.add_row("Strategy", "ℹ Info", settings.processing.chunk_strategy)
    
    console.print(table)


if __name__ == '__main__':
    main()