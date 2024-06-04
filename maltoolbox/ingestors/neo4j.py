"""
MAL-Toolbox Neo4j Ingestor Module
"""
# mypy: ignore-errors

import logging

from py2neo import Graph, Node, Relationship, Subgraph

from ..model import AttackerAttachment, Model
from ..language import specification, LanguageClassesFactory

logger = logging.getLogger(__name__)

def ingest_attack_graph(graph,
        uri: str,
        username: str,
        password: str,
        dbname: str,
        delete: bool = False
    ) -> None:
    """
    Ingest an attack graph into a neo4j database

    Arguments:
    graph                - the attackgraph provided by the atkgraph.py module.
    uri                  - the URI to a running neo4j instance
    username             - the username to login on Neo4J
    password             - the password to login on Neo4J
    dbname               - the selected database
    delete               - if True, the previous content of the database is deleted
                           before ingesting the new attack graph
    """

    g = Graph(uri=uri, user=username, password=password, name=dbname)
    if delete:
        g.delete_all()

    nodes = {}
    rels = []
    for node in graph.nodes:
        node_dict = node.to_dict()
        nodes[node.id] = Node(
            node_dict['asset'] if 'asset' in node_dict else node_dict['id'],
            name = node_dict['name'],
            full_name = node.full_name,
            type = node_dict['type'],
            ttc = str(node_dict['ttc']),
            is_necessary = str(node.is_necessary),
            is_viable = str(node.is_viable),
            compromised_by = str(node_dict['compromised_by']),
            defense_status = node_dict['defense_status'] if 'defense_status'
                in node_dict else 'N/A')


    for node in graph.nodes:
        for child in node.children:
            rels.append(Relationship(nodes[node.id], nodes[child.id]))

    subgraph = Subgraph(list(nodes.values()), rels)

    tx = g.begin()
    tx.create(subgraph)
    g.commit(tx)


def ingest_model(model,
        uri: str,
        username: str,
        password: str,
        dbname: str,
        delete: bool = False
    ) -> None:
    """
    Ingest an instance model graph into a Neo4J database

    Arguments:
    model                - the instance model dictionary as provided by the model.py module
    uri                  - the URI to a running neo4j instance
    username             - the username to login on Neo4J
    password             - the password to login on Neo4J
    dbname               - the selected database
    delete               - if True, the previous content of the database is deleted
                           before ingesting the new attack graph
    """
    g = Graph(uri=uri, user=username, password=password, name=dbname)
    if delete:
        g.delete_all()

    nodes = {}
    rels = []

    for asset in model.assets:

        nodes[str(asset.id)] = Node(str(asset.type),
                name=str(asset.name),
                asset_id=str(asset.id),
                type=str(asset.type))

    for assoc in model.associations:
        firstElementName, secondElementName = assoc._properties.keys()
        firstElements = getattr(assoc, firstElementName)
        secondElements = getattr(assoc, secondElementName)
        for first_asset in firstElements:
            for second_asset in secondElements:
                rels.append(Relationship(nodes[str(first_asset.id)],
                    str(firstElementName),
                    nodes[str(second_asset.id)]))
                rels.append(Relationship(nodes[str(second_asset.id)],
                    str(secondElementName),
                    nodes[str(first_asset.id)]))


    subgraph = Subgraph(list(nodes.values()), rels)

    tx = g.begin()
    tx.create(subgraph)
    g.commit(tx)
