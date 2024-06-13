"""
MAL-Toolbox Neo4j Ingestor Module
"""
# mypy: ignore-errors

import logging

from py2neo import Graph, Node, Relationship, Subgraph # type: ignore

from ..model import AttackerAttachment, Model
from ..language import specification

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
            full_name = node_dict['id'],
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


def get_model(
        uri: str,
        username: str,
        password: str,
        dbname: str,
        lang_spec: dict,
        lang_classes_factory: LanguageClassesFactory
    ) -> Model:
    """Load a model from Neo4j"""

    g = Graph(uri=uri, user=username, password=password, name=dbname)

    instance_model = Model('Neo4j imported model', lang_spec,
        lang_classes_factory)
    # Get all assets
    assets_results = g.run('MATCH (a) WHERE a.type IS NOT NULL RETURN DISTINCT a').data()
    for asset in assets_results:
        asset_data = dict(asset['a'])
        logger.debug('Loading asset from Neo4j instance:\n' \
            + str(asset_data))
        if asset_data['type'] == 'Attacker':
            attacker_id = int(asset_data['asset_id'])
            attacker = AttackerAttachment()
            attacker.entry_points = []
            instance_model.add_attacker(attacker, attacker_id = attacker_id)
            continue

        if not hasattr(lang_classes_factory.ns, asset_data['type']):
            msg = (f'Failed to find {asset_data["type"]} '
                    'asset in language specification!')
            logger.error(msg)
            raise LookupError(msg)

        asset_obj = getattr(lang_classes_factory.ns,
            asset_data['type'])(name = asset_data['name'])
        asset_id = int(asset_data['asset_id'])

        #TODO Process defense values when they are included in Neo4j

        instance_model.add_asset(asset_obj, asset_id)

    # Get all relationships
    assocs_results = g.run('MATCH (a)-[r1]->(b),(a)<-[r2]-(b) WHERE a.type IS NOT NULL RETURN DISTINCT a, r1, r2, b').data()

    for assoc in assocs_results:
        left_field = list(assoc['r1'].types())[0]
        right_field = list(assoc['r2'].types())[0]
        left_asset = dict(assoc['a'])
        right_asset = dict(assoc['b'])

        logger.debug(f'Load association '
            f'(\"{left_field}\",'
            f'\"{right_field}\",'
            f'\"{left_asset["type"]}\",'
            f'\"{right_asset["type"]}\") '
            f'from Neo4j instance.')

        left_id = int(left_asset['asset_id'])
        right_id = int(right_asset['asset_id'])
        attacker_id = None
        if left_field == 'firstSteps':
            attacker_id = right_id
            target_id = left_id
            target_prop = right_field
        elif right_field == 'firstSteps':
            attacker_id = left_id
            target_id = right_id
            target_prop = left_field

        if attacker_id:
            attacker = instance_model.get_attacker_by_id(attacker_id)
            if not attacker:
                msg = (f'Failed to find attacker with id {attacker_id} '
                        'in model!')
                logger.error(msg)
                raise LookupError(msg)
            target_asset = instance_model.get_asset_by_id(target_id)
            if not target_asset:
                msg = (f'Failed to find asset with id {target_id} '
                        'in model!')
                logger.error(msg)
                raise LookupError(msg)
            attacker.entry_points.append((target_asset,
                [target_prop]))
            continue

        left_asset = instance_model.get_asset_by_id(left_id)
        if not left_asset:
            msg = f'Failed to find asset with id {left_id} in model!'
            logger.error(msg)
            raise LookupError(msg)
        right_asset = instance_model.get_asset_by_id(right_id)
        if not right_asset:
            msg = f'Failed to find asset with id {right_id} in model!'
            logger.error(msg)
            raise LookupError(msg)

        assoc_name = specification.get_association_by_fields_and_assets(
            lang_spec,
            left_field,
            right_field,
            left_asset.type,
            right_asset.type)
        logger.debug(f'Found \"{assoc_name}\" association.')

        if not assoc_name:
            logger.error(f'Failed to find '
                f'(\"{left_asset.type}\",'
                f'\"{right_asset.type}\",'
                f'\"{left_field}\",'
                f'\"{right_field}\") '
                'association in language specification!')
            return None

        if not hasattr(lang_classes_factory.ns,
            assoc_name):
            msg = (f'Failed to find {assoc_name}'
                    'association in language specification!')
            logger.error(msg)
            raise LookupError(msg)

        assoc = getattr(lang_classes_factory.ns, assoc_name)()
        setattr(assoc, left_field, [left_asset])
        setattr(assoc, right_field, [right_asset])
        instance_model.add_association(assoc)

    return instance_model

