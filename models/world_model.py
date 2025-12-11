"""World Model module for AgentMove.

This module provides:
- SpatialWorld: Geographic knowledge generator using LLM reasoning
- SocialWorld: Collective knowledge extractor using mobility graphs
"""

from __future__ import annotations

import glob
import itertools
import os
from collections import Counter
from typing import TYPE_CHECKING, Any

import networkx as nx
import pandas as pd

from .llm_api import LLMWrapper

if TYPE_CHECKING:
    from processing.data import Dataset


class SpatialWorld:
    """World Knowledge Generator using LLM reasoning.
    
    Analyzes trajectory data to predict likely subdistricts and POIs
    based on spatial patterns.
    
    Attributes:
        city_name: Name of the city.
        max_lens: Maximum length for world info prompt.
        max_history: Maximum historical addresses to consider.
        llm: LLM wrapper for generating predictions.
        world_model: Generated world knowledge dictionary.
    """

    def __init__(
        self,
        platform: str,
        model_name: str,
        city_name: str,
        traj_seqs: dict[str, Any],
        explore_num: int = 5
    ) -> None:
        """Initialize Spatial World model.
        
        Args:
            platform: LLM platform name.
            model_name: LLM model name.
            city_name: Name of the city.
            traj_seqs: Trajectory sequence data.
            explore_num: Number of places to predict.
        """
        self.city_name = city_name
        self.max_lens = 1000
        self.max_history = 50
        
        self.llm = LLMWrapper(model_name, platform)

        # Process trajectory data
        his_addresses_len = min(len(traj_seqs['historical_addr']), self.max_history)
        historical = [
            [his[0], his[1], his[3], his[2]]
            for his in traj_seqs['historical_addr'][-his_addresses_len:]
        ]
        context = [
            [his[0], his[1], his[3], his[2]]
            for his in traj_seqs['context_addr']
        ]
        traj_pos = historical + context
        
        self.administrative_area: list[str] = list(set(addr[0] for addr in traj_pos))
        self.subdistrict: list[str] = [addr[1] for addr in traj_pos]
        self.poi: list[tuple[str, str]] = [(addr[3], addr[2]) for addr in traj_pos]
        self.explore_num = explore_num

        # Build the world model
        self.world_model = self.build_inner_world_model()

    def get_world_info(self) -> str:
        """Get formatted world information for prompt.
        
        Returns:
            World information prompt string.
        """
        world_info_prompt = f"""
### Names of subdistricts that are relatively likely to be visited:
{self.world_model.get("subdistrict", "")}
### Names of POIs that are relatively likely to be visited:
{self.world_model.get("poi", "")}
        """
        if len(world_info_prompt) <= self.max_lens:
            return world_info_prompt
        return world_info_prompt[-self.max_lens:]

    def build_inner_world_model(self) -> dict[str, str | None]:
        """Build the inner world model using LLM.
        
        Returns:
            Dictionary with subdistrict and POI predictions.
        """
        world_info: dict[str, str | None] = {}

        subdistrict_pre = (
            f"This trajectory moves within following administrative areas:\n"
            f"{self.administrative_area}\n"
            f"This trajectory sequentially visited following subdistricts, "
            f"with the last subdistrict being the most recently visited:\n"
            + ";".join(str(item) for item in self.subdistrict)
        )
        
        poi_pre = (
            "This trajectory sequentially visited following POIs"
            "(Each POI is represented by 'POI name, the feeder road or access road it is on'), "
            "with the last POI being the most recently visited:\n"
            + ";".join(str(item) for item in self.poi)
        )
        
        subdistrict_post = (
            "Consider about following two aspects:\n"
            "1.The frequency each subdistrict is visited.\n"
            "2.Transition probability between two administrative areas.\n"
            f"Please predict the next subdistrict in the trajectory. "
            f"Give {self.explore_num} subdistricts that are relatively likely to be visited. "
            "Do not output other content."
        )
        
        poi_post = (
            "Consider about following two aspects:\n"
            "1.The frequency each subdistrict is visited\n"
            "2.The frequency each poi is visited\n"
            "3.Transition probability between two subdistricts.\n"
            "4.Transition probability between two pois."
            "Please predict the next poi in the trajectory."
            f"Give {self.explore_num} POIs that are relatively likely to be visited. "
            "Do not output other content."
        )

        world_info["subdistrict"] = self.llm.get_response(
            prompt_text=subdistrict_pre + subdistrict_post
        )
        world_info["poi"] = self.llm.get_response(
            prompt_text=poi_pre + poi_post
        )
        return world_info

    def build_inner_world_model_v2(self) -> dict[str, Any]:
        """Build the world model using training data (placeholder).
        
        Returns:
            Empty dictionary (not implemented).
        """
        return {}
    
    def update_world_with_outter(self) -> dict[str, Any]:
        """Update world model with external resources (placeholder).
        
        Returns:
            Empty dictionary (not implemented).
        """
        return {}


class SocialWorld:
    """Collective Knowledge Extractor using mobility graphs.
    
    Builds and queries a knowledge graph from collective mobility patterns
    to find similar user behaviors.
    
    Attributes:
        save_dir: Directory to save/load graph.
        city_name: Name of the city.
        graph: NetworkX graph of venue transitions.
        khop: Number of hops for neighbor search.
        max_neighbors: Maximum neighbors to return.
    """

    def __init__(
        self,
        traj_dataset: Dataset,
        save_dir: str,
        city_name: str,
        khop: int = 1,
        max_neighbors: int = 10
    ) -> None:
        """Initialize Social World model.
        
        Args:
            traj_dataset: Dataset instance with trajectory data.
            save_dir: Directory to save/load graph.
            city_name: Name of the city.
            khop: Number of hops for neighbor search.
            max_neighbors: Maximum neighbors to return.
        """
        self.save_dir = save_dir
        self.city_name = city_name
        self.save_name = f"{city_name}_graph.gml"
        self.graph_file_path = os.path.join(self.save_dir, self.save_name)

        self.khop = khop
        self.max_neighbors = max_neighbors
        self.graph: nx.Graph

        test_dataset, _ = traj_dataset.get_generated_datasets()
        self.get_processed_graph(test_dataset)

    def build_graph(self, traj_dataset: dict[str, Any]) -> None:
        """Build knowledge graph from trajectory data.
        
        Args:
            traj_dataset: Dictionary of user trajectory data.
        """
        edges_list: list[list[tuple[Any, Any]]] = []
        nodes_list: list[list[list[Any]]] = []
        
        for uid in traj_dataset.keys():
            traj_ids = list(traj_dataset[uid].keys())
            if len(traj_ids) == 0:
                continue
            traj_id = traj_ids[0]
            train_instance = traj_dataset[uid][traj_id]["historical_stays_long"]
            venue_ids = [x[3] for x in train_instance]
            # ['hour', 'weekday', 'venue_category_name', venue_id_type, "admin", "subdistrict", "poi", "street"]
            nodes_list.append([
                [x[3], x[2], x[4], x[5], x[6], x[7]]
                for x in train_instance
            ])
            traj_edges = list(zip(venue_ids[:-1], venue_ids[1:]))
            edges_list.append(traj_edges)

        edges = list(itertools.chain.from_iterable(edges_list))
        nodes = list(itertools.chain.from_iterable(nodes_list))
        nodes_df = pd.DataFrame(
            data=nodes,
            columns=["venue_id", "venue_category_name", "admin", "subdistrict", "poi", "street"]
        )

        edges_weights = list(Counter(edges).items())
        edges_final = [
            [edge[0][0], edge[0][1], edge[1]]
            for edge in edges_weights
        ]
        edges_df = pd.DataFrame(edges_final, columns=["src", "dst", "weight"])
        self.graph = nx.from_pandas_edgelist(
            df=edges_df,
            source="src",
            target="dst",
            edge_attr=["weight"]
        )
        
        for _, row in nodes_df.iterrows():
            node = row['venue_id']
            self.graph.nodes[node]['category'] = row['venue_category_name']
            self.graph.nodes[node]['admin'] = row['admin']
            self.graph.nodes[node]['subdistrict'] = row['subdistrict']
            self.graph.nodes[node]["street"] = row["street"]
            self.graph.nodes[node]['poi'] = row['poi']
        
        nx.write_gml(self.graph, self.graph_file_path)

    def get_processed_graph(self, traj_dataset: dict[str, Any]) -> None:
        """Load existing graph or build new one.
        
        Args:
            traj_dataset: Dictionary of user trajectory data.
        """
        for file in glob.glob(os.path.join(self.save_dir, "*")):
            if self.save_name in file:
                print(f"Loading existing graph from: {file}")
                self.graph = nx.read_gml(self.graph_file_path)
                break
        else:
            print(f"Building new graph in: {self.graph_file_path}")
            self.build_graph(traj_dataset)

    def retrival_neighbors(
        self,
        venue_id: Any,
        context_trajs: list[Any]
    ) -> list[tuple[Any, int]]:
        """Retrieve neighbor venues from graph.
        
        Args:
            venue_id: Source venue ID.
            context_trajs: Context trajectory venue IDs to exclude.
            
        Returns:
            List of (neighbor_id, hop_distance) tuples.
        """
        try:
            if venue_id not in self.graph.nodes():
                return []
            
            if self.khop == 1:
                neighbors = list(self.graph.neighbors(venue_id))
                sorted_neighbors_freq = [
                    (n, 1) for n in neighbors
                    if n not in context_trajs
                ]
            else:
                lengths = nx.single_source_shortest_path_length(
                    self.graph,
                    venue_id,
                    cutoff=self.khop
                )
                neighbors = [
                    (neighbor, length)
                    for neighbor, length in lengths.items()
                    if (1 <= length <= self.khop) and (neighbor not in context_trajs)
                ]
                sorted_neighbors_freq = sorted(neighbors, key=lambda x: x[1])

            return sorted_neighbors_freq
        except (KeyError, nx.NetworkXError):
            return []

    def get_world_info(
        self,
        venue_id: Any,
        context_traj: list[Any],
        type: str = "all"
    ) -> str:
        """Get social world information for a venue.
        
        Args:
            venue_id: Source venue ID.
            context_traj: Context trajectory venue IDs.
            type: Information type ('all', 'category', 'address', or 'id').
            
        Returns:
            Formatted social world information string.
        """
        neighbors_sorted = self.retrival_neighbors(venue_id, context_traj)
        neighbors_info: dict[int, list[str]] = {}
        count = 0
        
        for n, f in neighbors_sorted:
            category = self.graph.nodes[n]["category"]
            street = self.graph.nodes[n]["street"]
            poi = self.graph.nodes[n]["poi"]
            
            if type == "all":
                info = ",".join([str(n), category, street, poi])
            elif type == "category":
                info = category
            elif type == "address":
                info = ",".join([street, poi])
            elif type == "id":
                info = str(n)
            else:
                info = ",".join([str(n), category, street, poi])
            
            if f in neighbors_info:
                neighbors_info[f].append(info)
            else:
                neighbors_info[f] = [info]
            
            if count >= self.max_neighbors:
                break
            count += 1
        
        prompts = [
            f"{f}-hop neighbor places in the social world:\n {chr(10).join(neighbors_info[f])}"
            for f in neighbors_info
        ]
        return "\n".join(prompts)
