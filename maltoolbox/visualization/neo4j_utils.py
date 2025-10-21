"""MAL-Toolbox Neo4j Ingestor Module
"""
# mypy: ignore-errors

import logging
from typing import Any

from py2neo import Graph, Node, Relationship, Subgraph

logger = logging.getLogger(__name__)


def ingest_attack_graph_neo4j(
        graph,
        neo4j_config: dict[str, Any],
        delete: bool = True
    ) -> None:
    """Ingest an attack graph into a neo4j database

    Arguments:
    ---------
    graph                - the attackgraph provided by the atkgraph.py module.
    uri                  - the URI to a running neo4j instance
    username             - the username to login on Neo4J
    password             - the password to login on Neo4J
    dbname               - the selected database
    delete               - if True, the previous content of the database is deleted
                           before ingesting the new attack graph

    """
    uri = neo4j_config.get('uri')
    username = neo4j_config.get('username')
    password = neo4j_config.get('password')
    dbname = neo4j_config.get('dbname')

    g = Graph(uri=uri, user=username, password=password, name=dbname)
    if delete:
        g.delete_all()

    nodes = {}
    rels = []
    for node in graph.nodes.values():
        node_dict = node.to_dict()
        nodes[node.id] = Node(
            node_dict['asset'] if 'asset' in node_dict else node_dict['id'],
            name=node_dict['name'],
            full_name=node.full_name,
            type=node_dict['type'],
            ttc=str(node_dict['ttc']),
        )

    for node in graph.nodes.values():
        for child in node.children:
            rels.append(Relationship(nodes[node.id], nodes[child.id]))

    subgraph = Subgraph(list(nodes.values()), rels)

    tx = g.begin()
    tx.create(subgraph)
    g.commit(tx)


def ingest_model_neo4j(
        model,
        neo4j_config: dict[str, Any],
        delete: bool = True
    ) -> None:
    """Ingest an instance model graph into a Neo4J database

    Arguments:
    ---------
    model                - the instance model dictionary as provided by the model.py module
    uri                  - the URI to a running neo4j instance
    username             - the username to login on Neo4J
    password             - the password to login on Neo4J
    dbname               - the selected database
    delete               - if True, the previous content of the database is deleted
                           before ingesting the new attack graph

    """
    uri = neo4j_config.get('uri')
    username = neo4j_config.get('username')
    password = neo4j_config.get('password')
    dbname = neo4j_config.get('dbname')

    g = Graph(uri=uri, user=username, password=password, name=dbname)
    if delete:
        g.delete_all()

    nodes = {}
    rels = []

    for asset in model.assets.values():
        nodes[str(asset.id)] = Node(
            str(asset.type),
            name=str(asset.name),
            asset_id=str(asset.id),
            type=str(asset.type)
        )

    for asset in model.assets.values():
        for fieldname, other_assets in asset.associated_assets.items():
            for other_asset in other_assets:
                rels.append(
                    Relationship(
                        nodes[str(asset.id)],
                        str(fieldname),
                        nodes[str(other_asset.id)]
                    )
                )

    subgraph = Subgraph(list(nodes.values()), rels)

    tx = g.begin()
    tx.create(subgraph)
    g.commit(tx)
