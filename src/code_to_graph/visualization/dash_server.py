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
    
    def close(self):
        """Close the visualization server and connections."""
        if self.visualizer:
            self.visualizer.close()
        if self.neo4j_client:
            self.neo4j_client.close()