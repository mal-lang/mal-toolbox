"""
MAL-Toolbox securiCAD Translator Module
"""

import zipfile
import json
import logging
import xml.etree.ElementTree as ET

from typing import Optional

from ..model import AttackerAttachment, Model
from ..language import LanguageGraph, LanguageClassesFactory

logger = logging.getLogger(__name__)

def load_model_from_scad_archive(
        scad_archive: str,
        lang_graph: LanguageGraph,
        lang_classes_factory: LanguageClassesFactory
    ) -> Optional[Model]:
    """
    Reads a '.sCAD' archive generated by securiCAD representing an instance
    model and loads the information into a maltoobox.model.Model object.

    Arguments:
    scad_archive            - the path to a '.sCAD' archive
    lang_graph              - a language graph representing the MAL
                              language specification
    lang_classes_factory    - a language classes factory that contains
                              the classes defined by the
                              language specification

    Return:
    A maltoobox.model.Model object containing the instance model.
    """
    with zipfile.ZipFile(scad_archive, 'r') as archive:
        filelist = archive.namelist()
        model_file = next(filter(lambda x: ( x[-4:] == '.eom'), filelist))
        scad_model = archive.read(model_file)
        root = ET.fromstring(scad_model)

    instance_model = Model(scad_archive,
        lang_classes_factory)

    for child in root.iter('objects'):

        if logger.isEnabledFor(logging.DEBUG):
            # Avoid running json.dumps when not in debug
            logger.debug(
                'Loading asset from "%s": \n%s',
                scad_archive, json.dumps(child.attrib, indent=2)
            )

        if child.attrib['metaConcept'] == 'Attacker':
            attacker_obj_id = int(child.attrib['id'])
            attacker_at = AttackerAttachment()
            attacker_at.entry_points = []
            instance_model.add_attacker(
                attacker_at,
                attacker_id = attacker_obj_id
            )
            continue

        if not hasattr(lang_classes_factory.ns,
            child.attrib['metaConcept']):
            logger.error(
                'Failed to find %s asset in language specification!',
                child.attrib["metaConcept"]
            )
            return None
        asset = getattr(lang_classes_factory.ns,
            child.attrib['metaConcept'])(name = child.attrib['name'])
        asset_id = int(child.attrib['id'])
        for subchild in child.iter('evidenceAttributes'):
            defense_name = subchild.attrib['metaConcept']
            defense_name = defense_name[0].lower() + defense_name[1:]
            for distrib in subchild.iter('evidenceDistribution'):
                for d in distrib.iter('parameters'):
                    if 'value' in d.attrib:
                        dist_value = d.attrib['value']
                        setattr(asset, defense_name, float(dist_value))
        instance_model.add_asset(asset, asset_id)

    for child in root.iter('associations'):
        logger.debug(
            'Load association ("%s", "%s", "%s", "%s") from %s',
            child.attrib["sourceObject"], child.attrib["targetObject"],
            child.attrib["targetProperty"], child.attrib["sourceProperty"],
            scad_archive
        )
        # Note: This is not a bug in the code. The fields and assets are
        # listed incorrectly in the securiCAD format where the source asset
        # matches the target field and vice versa.
        left_id = int(child.attrib['targetObject'])
        right_id = int(child.attrib['sourceObject'])
        attacker_id = None
        if child.attrib['sourceProperty'] == 'firstSteps':
            attacker_id = right_id
            target_id = left_id
            target_prop = child.attrib['targetProperty']
        elif child.attrib['targetProperty'] == 'firstSteps':
            attacker_id = left_id
            target_id = right_id
            target_prop = child.attrib['sourceProperty']

        if  attacker_id is not None:
            attacker = instance_model.get_attacker_by_id(attacker_id)
            if not attacker:
                logger.error(
                    'Failed to find attacker with id %s in model!',
                    attacker_id
                )
                return None
            target_asset = instance_model.get_asset_by_id(target_id)
            if not target_asset:
                logger.error(
                    'Failed to find asset with id %s in model!',
                    target_id
                )
                return None
            attacker.entry_points.append((target_asset,
                [target_prop.split('.')[0]]))
            continue

        left_asset = instance_model.get_asset_by_id(left_id)
        if not left_asset:
            logger.error(
                'Failed to find asset with id %s in model!', left_id
            )
            return None
        right_asset = instance_model.get_asset_by_id(right_id)
        if not right_asset:
            logger.error(
                'Failed to find asset with id %s in model!', right_id
            )
            return None

        # Note: This is not a bug in the code. The fields and assets are
        # listed incorrectly in the securiCAD format where the source asset
        # matches the target field and vice versa.
        left_field = child.attrib['sourceProperty']
        right_field = child.attrib['targetProperty']
        lang_graph_assoc = lang_graph.get_association_by_fields_and_assets(
            left_field,
            right_field,
            left_asset.type,
            right_asset.type)

        if not lang_graph_assoc:
            raise LookupError(
                'Failed to find ("%s", "%s", "%s", "%s")'
                'association in lang specification.' %
                (left_asset.type, right_asset.type,
                left_field, right_field)
            )
            return None

        logger.debug('Found "%s" association.', lang_graph_assoc.name)
        assoc_name = lang_classes_factory.get_association_by_signature(
            lang_graph_assoc.name,
            left_asset.type,
            right_asset.type
        )

        if assoc_name is None:
            logger.error(
                'Failed to find association with name \"%s\" in model!',
                lang_graph_assoc.name
            )
            return None

        assoc = getattr(lang_classes_factory.ns, assoc_name)()
        setattr(assoc, left_field, [left_asset])
        setattr(assoc, right_field, [right_asset])
        instance_model.add_association(assoc)

    return instance_model
