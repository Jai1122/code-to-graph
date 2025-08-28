"""Dash-based web server for interactive graph visualization."""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
from typing import Optional, Dict, Any
from loguru import logger
import threading
import time

from .graph_visualizer import GraphVisualizer
from ..storage.neo4j_client import Neo4jClient


class DashVisualizationServer:
    """Interactive web-based visualization server using Dash."""
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None, debug: bool = False, 
                 host: str = "127.0.0.1", port: int = 8080):
        """Initialize the Dash visualization server.
        
        Args:
            neo4j_client: Neo4j client instance
            debug: Enable debug mode
            host: Server host address
            port: Server port number
        """
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.visualizer = GraphVisualizer(self.neo4j_client)
        self.debug = debug
        self.host = host
        self.port = port
        
        # Initialize Dash app
        self.app = dash.Dash(__name__, title="CodeToGraph Visualizer")
        self.app.layout = self._create_layout()
        self._setup_callbacks()
        
    def _create_layout(self) -> html.Div:
        """Create the main dashboard layout."""
        return html.Div([
            # Header
            html.Div([
                html.H1("🕸️ CodeToGraph Visualizer", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 20}),
                html.P("Interactive exploration of code relationships and dependencies",
                      style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': 16})
            ], style={'padding': '20px', 'backgroundColor': '#ecf0f1', 'marginBottom': 20}),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.Label("🔍 Search Filter:", style={'fontWeight': 'bold', 'marginBottom': 5}),
                    dcc.Input(
                        id='search-input',
                        type='text',
                        placeholder='Enter entity name, file name, or pattern...',
                        style={'width': '100%', 'padding': '8px', 'marginBottom': 10}
                    ),
                ], style={'width': '30%', 'display': 'inline-block', 'paddingRight': 20}),
                
                html.Div([
                    html.Label("📊 Max Entities:", style={'fontWeight': 'bold', 'marginBottom': 5}),
                    dcc.Slider(
                        id='limit-slider',
                        min=20,
                        max=500,
                        step=20,
                        value=100,
                        marks={i: str(i) for i in range(50, 501, 100)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={'width': '30%', 'display': 'inline-block', 'paddingRight': 20}),
                
                html.Div([
                    html.Label("🎨 Layout:", style={'fontWeight': 'bold', 'marginBottom': 5}),
                    dcc.Dropdown(
                        id='layout-dropdown',
                        options=[
                            {'label': '🌸 Spring Layout', 'value': 'spring'},
                            {'label': '⭕ Circular Layout', 'value': 'circular'},
                            {'label': '🎲 Random Layout', 'value': 'random'}
                        ],
                        value='spring',
                        style={'marginBottom': 10}
                    ),
                ], style={'width': '20%', 'display': 'inline-block', 'paddingRight': 20}),
                
                html.Div([
                    html.Button('🔄 Update Graph', id='update-button', 
                              style={'padding': '10px 20px', 'backgroundColor': '#3498db', 
                                   'color': 'white', 'border': 'none', 'borderRadius': '5px',
                                   'cursor': 'pointer', 'fontSize': '14px', 'marginTop': 20})
                ], style={'width': '20%', 'display': 'inline-block', 'textAlign': 'center'}),
                
            ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'marginBottom': 20}),
            
            # Tabs for different views
            dcc.Tabs(id="tabs", value='graph-tab', children=[
                dcc.Tab(label='🕸️ Network Graph', value='graph-tab'),
                dcc.Tab(label='📊 Statistics', value='stats-tab'),
                dcc.Tab(label='🗂️ File Explorer', value='files-tab'),
                dcc.Tab(label='🤔 Ask Questions', value='query-tab'),
            ], style={'marginBottom': 20}),
            
            # Content area
            html.Div(id='tab-content'),
            
            # Status bar
            html.Div(id='status-bar', 
                    style={'padding': '10px', 'backgroundColor': '#2c3e50', 'color': 'white',
                          'textAlign': 'center', 'position': 'fixed', 'bottom': 0, 
                          'width': '100%', 'zIndex': 1000}),
            
            # Hidden div to store data
            html.Div(id='graph-data-store', style={'display': 'none'}),
            
        ], style={'fontFamily': 'Arial, sans-serif', 'margin': 0, 'paddingBottom': '60px'})
    
    def _setup_callbacks(self):
        """Setup Dash callbacks for interactivity."""
        
        @self.app.callback(
            Output('tab-content', 'children'),
            Input('tabs', 'value'),
            Input('update-button', 'n_clicks'),
            State('search-input', 'value'),
            State('limit-slider', 'value'),
            State('layout-dropdown', 'value')
        )
        def render_tab_content(active_tab, n_clicks, search_filter, limit, layout):
            """Render content based on active tab."""
            if active_tab == 'graph-tab':
                return self._render_graph_tab(search_filter, limit, layout)
            elif active_tab == 'stats-tab':
                return self._render_stats_tab()
            elif active_tab == 'files-tab':
                return self._render_files_tab(search_filter, limit)
            elif active_tab == 'query-tab':
                return self._render_query_tab()
            return html.Div("Select a tab to view content")
        
        @self.app.callback(
            Output('status-bar', 'children'),
            Input('update-button', 'n_clicks'),
            State('search-input', 'value'),
            State('limit-slider', 'value')
        )
        def update_status_bar(n_clicks, search_filter, limit):
            """Update status bar with current query info."""
            filter_text = f" | Filter: '{search_filter}'" if search_filter else ""
            return f"📊 Limit: {limit} entities{filter_text} | Last updated: {time.strftime('%H:%M:%S')}"
        
        # Callback for natural language queries (button click or Enter key)
        @self.app.callback(
            Output('query-results', 'children'),
            [Input('ask-button', 'n_clicks'), Input('question-input', 'n_submit')],
            [State('question-input', 'value'), State('query-limit-dropdown', 'value')],
            prevent_initial_call=True
        )
        def process_query(n_clicks, question, limit):
            """Process natural language queries and display results."""
            if not n_clicks or not question:
                return html.Div([
                    html.H4("💡 Ready to Answer Your Questions", style={'textAlign': 'center', 'color': '#7f8c8d'}),
                    html.P("Type a question above and click 'Ask' to get started!", style={'textAlign': 'center', 'color': '#bdc3c7'})
                ], style={'padding': '40px', 'textAlign': 'center'})
            
            try:
                # Generate Cypher query from natural language
                cypher_query = self._generate_cypher_from_question(question, limit)
                
                # Execute the query
                results = self.neo4j_client.execute_query(cypher_query)
                
                if not results:
                    return html.Div([
                        html.H4("🔍 Question Processed", style={'color': '#2c3e50'}),
                        html.P(f"Question: {question}", style={'fontStyle': 'italic', 'color': '#7f8c8d'}),
                        html.Hr(),
                        html.H5("Generated Cypher Query:", style={'color': '#34495e', 'marginTop': 20}),
                        html.Pre(cypher_query, style={'backgroundColor': '#ecf0f1', 'padding': '10px', 'borderRadius': '5px', 'fontSize': '12px'}),
                        html.Hr(),
                        html.H5("📭 No Results Found", style={'color': '#e67e22'}),
                        html.P("Try rephrasing your question or check if the entities exist in your codebase.", style={'color': '#7f8c8d'})
                    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '10px', 'border': '1px solid #ddd'})
                
                # Create results table
                headers = list(results[0].keys()) if results else []
                
                results_content = [
                    html.H4("🔍 Question Processed", style={'color': '#2c3e50'}),
                    html.P(f"Question: {question}", style={'fontStyle': 'italic', 'color': '#7f8c8d'}),
                    html.Hr(),
                    html.H5("Generated Cypher Query:", style={'color': '#34495e', 'marginTop': 20}),
                    html.Pre(cypher_query, style={'backgroundColor': '#ecf0f1', 'padding': '10px', 'borderRadius': '5px', 'fontSize': '12px'}),
                    html.Hr(),
                    html.H5(f"📊 Results ({len(results)} found):", style={'color': '#27ae60', 'marginTop': 20}),
                ]
                
                if results:
                    # Create a table for results
                    table_header = html.Tr([html.Th(header, style={'padding': '10px', 'backgroundColor': '#3498db', 'color': 'white'}) for header in headers])
                    
                    table_rows = []
                    for result in results:
                        row = []
                        for header in headers:
                            value = result.get(header, '')
                            # Truncate long strings for display
                            if isinstance(value, str) and len(value) > 100:
                                value = value[:97] + "..."
                            row.append(html.Td(str(value), style={'padding': '8px', 'borderBottom': '1px solid #ddd'}))
                        table_rows.append(html.Tr(row))
                    
                    results_table = html.Table([
                        html.Thead(table_header),
                        html.Tbody(table_rows)
                    ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginTop': '10px'})
                    
                    results_content.append(results_table)
                
                return html.Div(results_content, style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '10px', 'border': '1px solid #ddd'})
                
            except Exception as e:
                logger.error(f"Query processing failed: {e}")
                return html.Div([
                    html.H4("❌ Query Failed", style={'color': '#e74c3c'}),
                    html.P(f"Question: {question}", style={'fontStyle': 'italic', 'color': '#7f8c8d'}),
                    html.Hr(),
                    html.P(f"Error: {str(e)}", style={'color': '#e74c3c', 'backgroundColor': '#fadbd8', 'padding': '10px', 'borderRadius': '5px'}),
                    html.P("Please try rephrasing your question or check the system logs for more details.", style={'color': '#7f8c8d'})
                ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '10px', 'border': '1px solid #ddd'})
    
    def _render_graph_tab(self, search_filter: str = "", limit: int = 100, layout: str = "spring") -> html.Div:
        """Render the network graph tab."""
        try:
            # Fetch data
            nodes_df, rel_df = self.visualizer.fetch_graph_data(limit, search_filter or "")
            
            if nodes_df.empty:
                return html.Div([
                    html.H3("No data found", style={'textAlign': 'center', 'color': '#e74c3c'}),
                    html.P("Try adjusting your search filter or increasing the limit.", 
                          style={'textAlign': 'center', 'color': '#7f8c8d'})
                ])
            
            # Create graph
            fig = self.visualizer.create_network_graph(nodes_df, rel_df, layout)
            
            return html.Div([
                dcc.Graph(
                    id='network-graph',
                    figure=fig,
                    style={'height': '70vh'},
                    config={'displayModeBar': True, 'toImageButtonOptions': {'format': 'png'}}
                ),
                html.Div([
                    html.H4("Graph Statistics:", style={'marginTop': 20}),
                    html.P(f"📊 Nodes: {len(nodes_df)} | Edges: {len(rel_df)} | Layout: {layout.title()}")
                ], style={'padding': '20px', 'backgroundColor': '#f8f9fa'})
            ])
            
        except Exception as e:
            logger.error(f"Error rendering graph tab: {e}")
            return html.Div([
                html.H3("Error loading graph", style={'color': '#e74c3c'}),
                html.P(f"Error: {str(e)}", style={'color': '#7f8c8d'})
            ])
    
    def _render_stats_tab(self) -> html.Div:
        """Render the statistics tab."""
        try:
            charts = self.visualizer.create_statistics_charts()
            
            if not charts:
                return html.Div([
                    html.H3("No statistics available", style={'textAlign': 'center'})
                ])
            
            # Create a grid of charts
            chart_divs = []
            for chart_name, fig in charts.items():
                chart_divs.append(
                    html.Div([
                        dcc.Graph(figure=fig, style={'height': '400px'})
                    ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
                )
            
            return html.Div(chart_divs)
            
        except Exception as e:
            logger.error(f"Error rendering stats tab: {e}")
            return html.Div([
                html.H3("Error loading statistics", style={'color': '#e74c3c'}),
                html.P(f"Error: {str(e)}", style={'color': '#7f8c8d'})
            ])
    
    def _render_files_tab(self, search_filter: str = "", limit: int = 100) -> html.Div:
        """Render the file explorer tab."""
        try:
            # Query for file-based data
            query = f"""
            MATCH (n:Entity)
            {"WHERE n.file_path CONTAINS '" + search_filter + "'" if search_filter else ""}
            WITH split(n.file_path, '/')[-1] as filename, 
                 n.file_path as full_path,
                 collect(distinct n.entity_type) as types,
                 count(*) as entity_count
            RETURN filename, full_path, types, entity_count
            ORDER BY entity_count DESC
            LIMIT {limit}
            """
            
            result = self.neo4j_client.execute_query(query)
            
            if not result:
                return html.Div([
                    html.H3("No files found", style={'textAlign': 'center'})
                ])
            
            # Create file cards
            file_cards = []
            for record in result:
                filename = record['filename']
                full_path = record['full_path']
                types = record['types']
                entity_count = record['entity_count']
                
                file_cards.append(
                    html.Div([
                        html.H4(filename, style={'color': '#2c3e50', 'marginBottom': 5}),
                        html.P(full_path, style={'color': '#7f8c8d', 'fontSize': 12, 'marginBottom': 10}),
                        html.P(f"Entities: {entity_count} | Types: {', '.join(types)}", 
                              style={'color': '#27ae60', 'fontSize': 14})
                    ], style={
                        'border': '1px solid #bdc3c7', 'borderRadius': '5px', 
                        'padding': '15px', 'margin': '10px', 'backgroundColor': '#ffffff'
                    })
                )
            
            return html.Div([
                html.H3(f"📁 Files ({len(file_cards)} found)", style={'marginBottom': 20}),
                html.Div(file_cards, style={'maxHeight': '70vh', 'overflowY': 'auto'})
            ])
            
        except Exception as e:
            logger.error(f"Error rendering files tab: {e}")
            return html.Div([
                html.H3("Error loading files", style={'color': '#e74c3c'}),
                html.P(f"Error: {str(e)}", style={'color': '#7f8c8d'})
            ])
    
    def run(self, threaded: bool = True):
        """Start the visualization server.
        
        Args:
            threaded: Whether to run in threaded mode
        """
        logger.info(f"Starting CodeToGraph visualization server at http://{self.host}:{self.port}")
        
        try:
            if threaded:
                # Run in a separate thread
                server_thread = threading.Thread(
                    target=lambda: self.app.run(
                        host=self.host, 
                        port=self.port, 
                        debug=self.debug
                    )
                )
                server_thread.daemon = True
                server_thread.start()
                return server_thread
            else:
                # Run in main thread
                self.app.run(host=self.host, port=self.port, debug=self.debug)
                
        except Exception as e:
            logger.error(f"Failed to start visualization server: {e}")
            raise
    
    def _render_query_tab(self) -> html.Div:
        """Render the natural language query tab."""
        return html.Div([
            html.Div([
                html.H3("🤔 Ask Questions About Your Codebase", style={'marginBottom': 20, 'color': '#2c3e50'}),
                html.P("Ask natural language questions about your code. Examples:", style={'marginBottom': 10}),
                html.Ul([
                    html.Li("What functions are in main.go?"),
                    html.Li("What does the GetUsers function call?"),
                    html.Li("Show all methods"),
                    html.Li("What structs are defined?"),
                    html.Li("What calls the CreateUser method?"),
                ], style={'marginBottom': 20, 'color': '#7f8c8d'}),
                
                html.Div([
                    html.Label("Your Question:", style={'fontWeight': 'bold', 'marginBottom': 5}),
                    dcc.Input(
                        id='question-input',
                        type='text',
                        placeholder='e.g., "What functions are in main.go?"',
                        style={'width': '70%', 'padding': '12px', 'fontSize': '16px', 'marginRight': '10px'},
                        value=''
                    ),
                    html.Button(
                        '🔍 Ask',
                        id='ask-button',
                        n_clicks=0,
                        style={
                            'padding': '12px 24px',
                            'backgroundColor': '#3498db',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '16px',
                            'fontWeight': 'bold'
                        }
                    ),
                ], style={'marginBottom': 30}),
                
                html.Div([
                    html.Label("Result Limit:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='query-limit-dropdown',
                        options=[
                            {'label': '5 results', 'value': 5},
                            {'label': '10 results', 'value': 10},
                            {'label': '20 results', 'value': 20},
                            {'label': '50 results', 'value': 50},
                        ],
                        value=10,
                        style={'width': '150px', 'display': 'inline-block'}
                    ),
                ], style={'marginBottom': 20}),
                
            ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px', 'marginBottom': 20}),
            
            # Results area
            html.Div(id='query-results', children=[
                html.Div([
                    html.H4("💡 Ready to Answer Your Questions", style={'textAlign': 'center', 'color': '#7f8c8d'}),
                    html.P("Type a question above and click 'Ask' to get started!", style={'textAlign': 'center', 'color': '#bdc3c7'})
                ], style={'padding': '40px', 'textAlign': 'center'})
            ]),
            
        ])
    
    def _generate_cypher_from_question(self, question: str, limit: int = 10) -> str:
        """Generate a Cypher query from a natural language question using pattern matching."""
        question_lower = question.lower()
        
        # Pattern 1: Functions in a specific file
        if "function" in question_lower and ("main.go" in question_lower or ".go" in question_lower):
            if "main.go" in question_lower:
                return f"MATCH (n:Entity) WHERE n.file_path CONTAINS 'main.go' AND n.type = 'function' RETURN n.name, n.type, n.line_number ORDER BY n.line_number LIMIT {limit}"
            else:
                # Extract filename
                words = question.split()
                go_files = [w for w in words if w.endswith('.go')]
                if go_files:
                    filename = go_files[0]
                    return f"MATCH (n:Entity) WHERE n.file_path CONTAINS '{filename}' AND n.type = 'function' RETURN n.name, n.type, n.line_number ORDER BY n.line_number LIMIT {limit}"
        
        # Pattern 2: What does X function call?
        if ("what" in question_lower and "call" in question_lower) or ("calls" in question_lower):
            # Extract function name (look for capitalized words, excluding "What")
            words = question.split()
            function_names = [w for w in words if w[0].isupper() and len(w) > 1 and w.lower() not in ['what', 'does', 'function']]
            if function_names:
                func_name = function_names[0]
                return f"MATCH (source:Entity {{name: '{func_name}'}})-[r:RELATES]->(target:Entity) WHERE r.relation_type = 'calls' RETURN target.name, target.type, target.file_path LIMIT {limit}"
        
        # Pattern 3: What calls X function?
        if "what calls" in question_lower or "who calls" in question_lower:
            words = question.split()
            function_names = [w for w in words if w[0].isupper() and len(w) > 1]
            if function_names:
                func_name = function_names[0]
                return f"MATCH (source:Entity)-[r:RELATES]->(target:Entity {{name: '{func_name}'}}) WHERE r.relation_type = 'calls' RETURN source.name, source.type, source.file_path LIMIT {limit}"
        
        # Pattern 4: Functions in package
        if "function" in question_lower and "package" in question_lower:
            words = question.split()
            if "main" in words:
                return f"MATCH (n:Entity) WHERE n.type = 'function' AND (n.package = 'main' OR n.file_path CONTAINS 'main') RETURN n.name, n.type, n.file_path LIMIT {limit}"
        
        # Pattern 5: All functions/methods/types
        if "all function" in question_lower or "list function" in question_lower or "show function" in question_lower:
            return f"MATCH (n:Entity {{type: 'function'}}) RETURN n.name, n.file_path, n.type ORDER BY n.name LIMIT {limit}"
        
        if "all method" in question_lower or "list method" in question_lower or "show method" in question_lower:
            return f"MATCH (n:Entity {{type: 'method'}}) RETURN n.name, n.file_path, n.type ORDER BY n.name LIMIT {limit}"
        
        if "struct" in question_lower or "type" in question_lower:
            return f"MATCH (n:Entity) WHERE n.type IN ['struct', 'type', 'interface'] RETURN n.name, n.type, n.file_path ORDER BY n.name LIMIT {limit}"
        
        # Pattern 6: General search - look for any capitalized words as potential entity names
        words = question.split()
        entity_candidates = [w for w in words if w[0].isupper() and len(w) > 1]
        if entity_candidates:
            entity_name = entity_candidates[0]
            return f"MATCH (n:Entity) WHERE n.name CONTAINS '{entity_name}' RETURN n.name, n.type, n.file_path LIMIT {limit}"
        
        # Default fallback: search for any keyword in entity names
        search_terms = [w for w in question.split() if len(w) > 3 and w.lower() not in ['what', 'where', 'how', 'does', 'function', 'method', 'class']]
        if search_terms:
            search_term = search_terms[0]
            return f"MATCH (n:Entity) WHERE toLower(n.name) CONTAINS toLower('{search_term}') RETURN n.name, n.type, n.file_path LIMIT {limit}"
        
        # Ultimate fallback
        return f"MATCH (n:Entity) RETURN n.name, n.type, n.file_path ORDER BY n.name LIMIT {limit}"
    
    def close(self):
        """Close the visualization server and connections."""
        if self.visualizer:
            self.visualizer.close()
        if self.neo4j_client:
            self.neo4j_client.close()