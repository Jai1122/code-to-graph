"""Main CLI entry point for CodeToGraph - Go-focused repository analysis."""

from pathlib import Path
from typing import Optional, List
import time

import click
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ..core.config import settings
from ..core.logger import setup_logging
from ..parsers.intelligent_parser import IntelligentParserFactory
from ..storage.neo4j_client import Neo4jClient
from ..storage.graph_importer import GraphImporter
from ..llm.vllm_client import VLLMClient
from ..llm.code_analyzer import CodeAnalyzer
from ..visualization.dash_server import DashVisualizationServer

console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--log-level', default='INFO', help='Set log level')
def main(debug: bool, log_level: str) -> None:
    """CodeToGraph: Go-focused repository analysis and graph visualization."""
    if debug:
        settings.debug = True
        log_level = 'DEBUG'
    
    setup_logging(log_level=log_level)
    logger.info(f"CodeToGraph v{settings.version} - Go Analysis Platform")


@main.command()
@click.option('--repo-path', '-r', required=True, type=click.Path(exists=True, path_type=Path),
              help='Path to Go repository to analyze')
@click.option('--language', '-l', type=click.Choice(['go', 'java', 'python', 'javascript', 'typescript']),
              default='go', help='Primary language (defaults to Go)')
@click.option('--exclude-dirs', '-e', multiple=True, 
              help='Directories to exclude (e.g., vendor, node_modules)')
@click.option('--exclude-patterns', multiple=True,
              help='File patterns to exclude (e.g., *_test.go, *.pb.go)')
@click.option('--include-tests', is_flag=True, default=False,
              help='Include test files in analysis')
@click.option('--enable-deep-analysis', is_flag=True, default=False,
              help='Enable deep static analysis (CFG, complexity)')
def analyze(repo_path: Path, language: str, exclude_dirs: tuple, exclude_patterns: tuple,
           include_tests: bool, enable_deep_analysis: bool) -> None:
    """Analyze a repository and display results (no database storage)."""
    
    console.print(f"🔍 Analyzing repository: [bold]{repo_path}[/bold]")
    console.print(f"📝 Primary language: [bold]{language}[/bold]")
    
    # Configure exclusions
    exclusions = _configure_exclusions(exclude_dirs, exclude_patterns, include_tests)
    
    try:
        # Initialize parser
        parser = IntelligentParserFactory.create_go_optimized_parser()
        
        # Parse repository
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing repository...", total=100)
            
            start_time = time.time()
            entities, relationships = parser.parse_repository(
                repo_path,
                language=language,
                exclude_patterns=exclusions,
                enable_deep_analysis=enable_deep_analysis
            )
            duration = time.time() - start_time
            progress.update(task, completed=100)
        
        # Display results
        _display_analysis_results(entities, relationships, duration)
        
    except Exception as e:
        console.print(f"❌ [red]Analysis failed: {e}[/red]")
        logger.error(f"Analysis failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option('--repo-path', '-r', required=True, type=click.Path(exists=True, path_type=Path),
              help='Path to Go repository to analyze')
@click.option('--language', '-l', type=click.Choice(['go', 'java', 'python', 'javascript', 'typescript']),
              default='go', help='Primary language (defaults to Go)')
@click.option('--exclude-dirs', '-e', multiple=True, 
              help='Directories to exclude (e.g., vendor, node_modules)')
@click.option('--exclude-patterns', multiple=True,
              help='File patterns to exclude (e.g., *_test.go, *.pb.go)')
@click.option('--include-tests', is_flag=True, default=False,
              help='Include test files in analysis')
@click.option('--enable-deep-analysis', is_flag=True, default=False,
              help='Enable deep static analysis (CFG, complexity)')
@click.option('--clear-db', is_flag=True, default=True,
              help='Clear existing data before import (recommended)')
@click.option('--create-indexes', is_flag=True, default=True,
              help='Create database indexes for performance')
def import_graph(repo_path: Path, language: str, exclude_dirs: tuple, exclude_patterns: tuple,
                include_tests: bool, enable_deep_analysis: bool, clear_db: bool, create_indexes: bool) -> None:
    """Analyze repository and import results into Neo4j graph database."""
    
    console.print(f"🚀 Importing repository to Neo4j: [bold]{repo_path}[/bold]")
    console.print(f"📝 Primary language: [bold]{language}[/bold]")
    
    # Configure exclusions
    exclusions = _configure_exclusions(exclude_dirs, exclude_patterns, include_tests)
    
    try:
        # Test Neo4j connection
        with console.status("🔗 Testing Neo4j connection..."):
            with Neo4jClient() as client:
                stats = client.get_database_stats()
                console.print(f"✅ Connected to Neo4j: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
        
        # Clear database if requested
        if clear_db:
            with console.status("🗑️ Clearing existing data..."):
                with Neo4jClient() as client:
                    client.execute_query("MATCH (n) DETACH DELETE n")
                console.print("✅ Database cleared")
        
        # Initialize parser
        parser = IntelligentParserFactory.create_go_optimized_parser()
        
        # Parse repository
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            parse_task = progress.add_task("Analyzing repository...", total=50)
            
            start_time = time.time()
            entities, relationships = parser.parse_repository(
                repo_path,
                language=language,
                exclude_patterns=exclusions,
                enable_deep_analysis=enable_deep_analysis
            )
            parse_duration = time.time() - start_time
            progress.update(parse_task, completed=50)
            
            # Import to Neo4j
            import_task = progress.add_task("Importing to Neo4j...", total=50)
            
            importer = GraphImporter()
            import_start = time.time()
            importer.import_graph(entities, relationships, clear_existing=clear_db, create_indexes=create_indexes)
            import_duration = time.time() - import_start
            progress.update(import_task, completed=50)
        
        # Create indexes
        if create_indexes:
            with console.status("📊 Creating database indexes..."):
                with Neo4jClient() as client:
                    # Create unique constraint and index on Entity.id
                    client.execute_query(
                        "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE"
                    )
                    # Create index on name for fast lookups
                    client.execute_query(
                        "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)"
                    )
                    # Create index on type for filtering
                    client.execute_query(
                        "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)"
                    )
                    # Create index on file_path for file-based queries
                    client.execute_query(
                        "CREATE INDEX entity_file_index IF NOT EXISTS FOR (e:Entity) ON (e.file_path)"
                    )
                console.print("✅ Database indexes created")
        
        # Final stats
        with Neo4jClient() as client:
            final_stats = client.get_database_stats()
        
        console.print("\n🎉 [bold green]Import completed successfully![/bold green]")
        console.print(f"⏱️  Analysis time: {parse_duration:.2f}s")
        console.print(f"⏱️  Import time: {import_duration:.2f}s") 
        console.print(f"📊 Total entities: {final_stats['total_nodes']}")
        console.print(f"🔗 Total relationships: {final_stats['total_relationships']}")
        
    except Exception as e:
        console.print(f"❌ [red]Import failed: {e}[/red]")
        logger.error(f"Import failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option('--host', default='localhost', help='Visualization server host')
@click.option('--port', default=8080, type=int, help='Visualization server port')
@click.option('--debug-mode', is_flag=True, default=False, help='Enable Dash debug mode')
def visualize(host: str, port: int, debug_mode: bool) -> None:
    """Start the interactive web visualization server."""
    
    console.print(f"🌐 Starting visualization server at [bold]http://{host}:{port}[/bold]")
    
    try:
        # Test Neo4j connection first
        with console.status("🔗 Testing Neo4j connection..."):
            with Neo4jClient() as client:
                stats = client.get_database_stats()
                if stats['total_nodes'] == 0:
                    console.print("⚠️  [yellow]Warning: No data found in Neo4j. Run 'import-graph' first.[/yellow]")
                else:
                    console.print(f"✅ Found {stats['total_nodes']} nodes and {stats['total_relationships']} relationships")
        
        # Start visualization server
        server = DashVisualizationServer(host=host, port=port, debug=debug_mode)
        console.print(f"🚀 Server starting... Open [bold blue]http://{host}:{port}[/bold blue] in your browser")
        console.print("💡 Press [bold]Ctrl+C[/bold] to stop the server")
        
        server.run()
        
    except KeyboardInterrupt:
        console.print("\n👋 Visualization server stopped")
    except Exception as e:
        console.print(f"❌ [red]Server failed to start: {e}[/red]")
        logger.error(f"Visualization server failed: {e}")
        raise click.ClickException(str(e))


@main.command()
@click.option('--file-path', '-f', required=True, type=click.Path(exists=True, path_type=Path),
              help='Path to Go file to analyze')
@click.option('--model', default='qwen3:14b', help='LLM model to use')
def analyze_code(file_path: Path, model: str) -> None:
    """Analyze a single Go file with LLM assistance."""
    
    console.print(f"🧠 Analyzing file with LLM: [bold]{file_path}[/bold]")
    
    try:
        # Initialize LLM client
        with console.status("🔗 Connecting to VLLM server..."):
            llm_client = VLLMClient(model=model)
            health = llm_client.check_health()
            if not health:
                raise Exception("VLLM server is not healthy")
        
        # Read file content
        content = file_path.read_text(encoding='utf-8')
        
        # Analyze with LLM
        analyzer = CodeAnalyzer(llm_client)
        with console.status("🤖 Analyzing code with LLM..."):
            analysis = analyzer.analyze_code_structure(content, str(file_path))
        
        console.print(f"\n📋 [bold]Analysis Results for {file_path.name}:[/bold]")
        console.print(analysis)
        
    except Exception as e:
        console.print(f"❌ [red]LLM analysis failed: {e}[/red]")
        logger.error(f"LLM analysis failed: {e}")
        raise click.ClickException(str(e))


@main.command()
def status() -> None:
    """Show system status and configuration."""
    
    table = Table(title="CodeToGraph System Status", show_header=True, header_style="bold blue")
    table.add_column("Component", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    
    # Go Native Parser
    try:
        from ..parsers.go_native_parser import GoNativeParserFactory
        parser = GoNativeParserFactory.create_parser()
        if parser and parser.is_available():
            go_info = parser.get_parser_info()
            table.add_row(
                "Go Native Parser", 
                "✅ Available", 
                f"Go version: {go_info.get('go_version', 'Unknown')}"
            )
        else:
            table.add_row("Go Native Parser", "❌ Not available", "Go binary not found")
    except Exception as e:
        table.add_row("Go Native Parser", "❌ Error", str(e))
    
    # Tree-sitter Parser
    try:
        from ..parsers.tree_sitter_parser import TreeSitterParser
        TreeSitterParser()
        table.add_row("Tree-sitter", "✅ Available", "Multi-language syntax parsing")
    except Exception as e:
        table.add_row("Tree-sitter", "❌ Error", str(e))
    
    # Neo4j Database
    try:
        with Neo4jClient() as client:
            stats = client.get_database_stats()
            table.add_row(
                "Neo4j Database", 
                "✅ Connected", 
                f"{stats['total_nodes']} nodes, {stats['total_relationships']} relationships"
            )
    except Exception as e:
        table.add_row("Neo4j Database", "❌ Connection Failed", str(e))
    
    # VLLM Client
    try:
        llm_client = VLLMClient()
        if llm_client.check_health():
            table.add_row(
                "VLLM Server", 
                "✅ Healthy", 
                f"Model: {settings.llm.vllm_model}"
            )
        else:
            table.add_row("VLLM Server", "❌ Unhealthy", "Server not responding")
    except Exception as e:
        table.add_row("VLLM Server", "❌ Error", str(e))
    
    console.print(table)
    
    # Configuration summary
    console.print(f"\n📋 [bold]Configuration:[/bold]")
    console.print(f"  • Neo4j URI: {settings.neo4j.uri}")
    console.print(f"  • VLLM URL: {settings.llm.vllm_base_url}")
    console.print(f"  • Go Native: {'Enabled' if settings.processing.enable_go_native else 'Disabled'}")
    console.print(f"  • Tree-sitter: {'Enabled' if settings.processing.enable_tree_sitter else 'Disabled'}")


def _configure_exclusions(exclude_dirs: tuple, exclude_patterns: tuple, include_tests: bool) -> List[str]:
    """Configure file and directory exclusions."""
    exclusions = list(settings.processing.exclude_patterns)
    
    # Add custom exclusions
    for dir_name in exclude_dirs:
        exclusions.append(f"**/{dir_name}/**")
    
    exclusions.extend(exclude_patterns)
    
    # Add common exclusions
    default_exclusions = [
        "**/vendor/**",      # Go vendor directory
        "**/node_modules/**", # Node.js modules
        "**/.git/**",        # Git directory
        "**/build/**",       # Build outputs
        "**/dist/**",        # Distribution files
        "**/*.pb.go",        # Protocol buffer generated files
        "**/*_gen.go",       # Generated Go files
    ]
    
    exclusions.extend(default_exclusions)
    
    # Handle test files
    if not include_tests:
        test_exclusions = [
            "**/*_test.go",
            "**/*Test.java", 
            "**/test_*.py",
            "**/*.test.js",
            "**/tests/**",
            "**/test/**",
        ]
        exclusions.extend(test_exclusions)
    
    return list(set(exclusions))  # Remove duplicates


def _display_analysis_results(entities: list, relationships: list, duration: float) -> None:
    """Display analysis results in a formatted table."""
    
    # Create summary table
    table = Table(title=f"Analysis Results ({duration:.2f}s)", show_header=True, header_style="bold green")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right", style="bold blue")
    
    table.add_row("Total Entities", str(len(entities)))
    table.add_row("Total Relationships", str(len(relationships)))
    
    # Count by entity type
    entity_types = {}
    for entity in entities:
        entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
    
    for entity_type, count in sorted(entity_types.items()):
        table.add_row(f"  └─ {entity_type.title()}", str(count))
    
    # Count by relationship type
    relationship_types = {}
    for rel in relationships:
        relationship_types[rel.relation_type] = relationship_types.get(rel.relation_type, 0) + 1
    
    table.add_row("", "")  # Separator
    for rel_type, count in sorted(relationship_types.items()):
        table.add_row(f"  └─ {rel_type.replace('_', ' ').title()}", str(count))
    
    console.print(table)


if __name__ == '__main__':
    main()