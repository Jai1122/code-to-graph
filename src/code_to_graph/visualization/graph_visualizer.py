"""Graph visualization utilities for CodeToGraph."""

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger
import math

from ..storage.neo4j_client import Neo4jClient


class GraphVisualizer:
    """Creates interactive graph visualizations from Neo4j data."""
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None):
        """Initialize the graph visualizer.
        
        Args:
            neo4j_client: Neo4j client instance (creates new one if not provided)
        """
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.color_map = {
            'function': '#1f77b4',  # Blue
            'method': '#ff7f0e',    # Orange  
            'type': '#2ca02c',      # Green
            'variable': '#d62728',  # Red
            'package': '#9467bd',   # Purple
            'file': '#8c564b',      # Brown
            'class': '#e377c2',     # Pink
        }
        
    def fetch_graph_data(self, limit: int = 100, filter_query: str = "") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch nodes and relationships from Neo4j.
        
        Args:
            limit: Maximum number of relationships to fetch
            filter_query: Optional filter for entity names
            
        Returns:
            Tuple of (nodes_df, relationships_df)
        """
        try:
            # Fetch nodes
            if filter_query:
                nodes_query = f"""
                MATCH (n:Entity) 
                WHERE n.name CONTAINS '{filter_query}' OR n.file_path CONTAINS '{filter_query}'
                RETURN n.id as id, n.name as name, n.type as type, 
                       n.file_path as file_path, 1.0 as confidence
                LIMIT {limit}
                """
            else:
                nodes_query = f"""
                MATCH (n:Entity) 
                RETURN n.id as id, n.name as name, n.type as type, 
                       n.file_path as file_path, 1.0 as confidence
                LIMIT {limit}
                """
            
            nodes_result = self.neo4j_client.execute_query(nodes_query)
            nodes_df = pd.DataFrame([dict(record) for record in nodes_result])
            
            if nodes_df.empty:
                logger.warning("No nodes found with the given filter")
                return pd.DataFrame(), pd.DataFrame()
            
            # Get node IDs for relationship filtering
            node_ids = nodes_df['id'].tolist()
            
            # Fetch relationships between these nodes
            rel_query = f"""
            MATCH (source:Entity)-[r:RELATES]->(target:Entity)
            WHERE source.id IN {node_ids} AND target.id IN {node_ids}
            RETURN source.id as source, target.id as target, r.relation_type as relation,
                   1.0 as confidence, r.line_number as line_number
            LIMIT {limit}
            """
            
            rel_result = self.neo4j_client.execute_query(rel_query)
            rel_df = pd.DataFrame([dict(record) for record in rel_result])
            
            logger.info(f"Fetched {len(nodes_df)} nodes and {len(rel_df)} relationships")
            return nodes_df, rel_df
            
        except Exception as e:
            logger.error(f"Failed to fetch graph data: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def create_network_graph(self, nodes_df: pd.DataFrame, rel_df: pd.DataFrame, 
                           layout: str = "spring") -> go.Figure:
        """Create an interactive network graph using Plotly.
        
        Args:
            nodes_df: DataFrame with node data
            rel_df: DataFrame with relationship data
            layout: Layout algorithm ('spring', 'circular', 'random')
            
        Returns:
            Plotly figure object
        """
        if nodes_df.empty:
            return self._create_empty_graph()
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for _, node in nodes_df.iterrows():
            G.add_node(
                node['id'], 
                name=node['name'], 
                type=node['type'],
                file_path=node.get('file_path', ''),
                confidence=node.get('confidence', 1.0)
            )
        
        # Add edges
        for _, rel in rel_df.iterrows():
            if rel['source'] in G.nodes and rel['target'] in G.nodes:
                G.add_edge(
                    rel['source'], 
                    rel['target'], 
                    relation=rel['relation'],
                    confidence=rel.get('confidence', 1.0),
                    line_number=rel.get('line_number', 0)
                )
        
        # Calculate layout
        if layout == "spring":
            pos = nx.spring_layout(G, k=3, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        else:
            pos = nx.random_layout(G)
        
        # Extract node positions and attributes
        node_trace = self._create_node_trace(G, pos, nodes_df)
        edge_trace = self._create_edge_trace(G, pos)
        
        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(
                    text=f"Code Graph Visualization ({len(G.nodes)} nodes, {len(G.edges)} edges)",
                    x=0.5,
                    font_size=16
                ),
                showlegend=True,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                annotations=[ dict(
                    text="Click and drag nodes to explore the graph",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor='left', yanchor='bottom',
                    font=dict(color="#999", size=12)
                )],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
        )
        
        return fig
    
    def _create_node_trace(self, G: nx.Graph, pos: Dict, nodes_df: pd.DataFrame) -> go.Scatter:
        """Create node trace for Plotly graph."""
        node_x = []
        node_y = []
        node_text = []
        node_info = []
        node_colors = []
        node_sizes = []
        
        for node_id in G.nodes():
            x, y = pos[node_id]
            node_x.append(x)
            node_y.append(y)
            
            node_data = G.nodes[node_id]
            node_type = node_data.get('type', 'unknown')
            node_name = node_data.get('name', node_id)
            file_path = node_data.get('file_path', '')
            confidence = node_data.get('confidence', 1.0) or 1.0  # Ensure not None
            
            # Shorten file path for display
            short_path = file_path.split('/')[-1] if file_path else ''
            
            node_text.append(f"{node_name}<br>{node_type}")
            node_info.append(f"<b>{node_name}</b><br>" +
                           f"Type: {node_type}<br>" +
                           f"File: {short_path}<br>" +
                           f"Confidence: {confidence:.2f}<br>" +
                           f"Connections: {len(G[node_id])}")
            
            # Color by type
            node_colors.append(self.color_map.get(node_type, '#cccccc'))
            
            # Size by number of connections
            connections = len(G[node_id])
            node_sizes.append(max(10, min(30, 8 + connections * 2)))
        
        return go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="middle center",
            textfont=dict(size=8, color="white"),
            hoverinfo='text',
            hovertext=node_info,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=1, color='white'),
                opacity=0.8
            ),
            name="Entities"
        )
    
    def _create_edge_trace(self, G: nx.Graph, pos: Dict) -> go.Scatter:
        """Create edge trace for Plotly graph."""
        edge_x = []
        edge_y = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        return go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888888', dash='solid'),
            hoverinfo='none',
            mode='lines',
            name="Relationships",
            opacity=0.6
        )
    
    def _create_empty_graph(self) -> go.Figure:
        """Create an empty graph with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text="No data to display<br>Try adjusting your filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title="Code Graph Visualization",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )
        return fig
    
    def create_statistics_charts(self) -> Dict[str, go.Figure]:
        """Create various statistics charts.
        
        Returns:
            Dictionary of chart names to Plotly figures
        """
        charts = {}
        
        try:
            # Entity type distribution
            type_query = """
            MATCH (n:Entity) 
            RETURN n.entity_type as type, count(*) as count 
            ORDER BY count DESC
            """
            type_result = self.neo4j_client.execute_query(type_query)
            type_df = pd.DataFrame([dict(record) for record in type_result])
            
            if not type_df.empty:
                charts['entity_types'] = px.pie(
                    type_df, 
                    values='count', 
                    names='type',
                    title="Entity Types Distribution",
                    color='type',
                    color_discrete_map=self.color_map
                )
            
            # File complexity (entities per file)
            complexity_query = """
            MATCH (n:Entity) 
            WITH split(n.file_path, '/')[-1] as filename, count(*) as entity_count
            RETURN filename, entity_count
            ORDER BY entity_count DESC
            LIMIT 20
            """
            complexity_result = self.neo4j_client.execute_query(complexity_query)
            complexity_df = pd.DataFrame([dict(record) for record in complexity_result])
            
            if not complexity_df.empty:
                charts['file_complexity'] = px.bar(
                    complexity_df,
                    x='filename',
                    y='entity_count',
                    title="Entities per File (Top 20)",
                    labels={'entity_count': 'Number of Entities', 'filename': 'File Name'}
                )
                charts['file_complexity'].update_xaxes(tickangle=45)
            
            # Relationship types
            rel_query = """
            MATCH ()-[r:RELATES]->() 
            RETURN r.relation_type as relation, count(*) as count 
            ORDER BY count DESC
            """
            rel_result = self.neo4j_client.execute_query(rel_query)
            rel_df = pd.DataFrame([dict(record) for record in rel_result])
            
            if not rel_df.empty:
                charts['relationship_types'] = px.bar(
                    rel_df,
                    x='relation',
                    y='count',
                    title="Relationship Types",
                    labels={'count': 'Number of Relationships', 'relation': 'Relation Type'}
                )
            
        except Exception as e:
            logger.error(f"Failed to create statistics charts: {e}")
        
        return charts
    
    def close(self):
        """Close the Neo4j connection."""
        if self.neo4j_client:
            self.neo4j_client.close()