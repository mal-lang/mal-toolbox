"""Unit tests for AttackGraph.partially_regenerate_graph"""

import pytest

from maltoolbox.attackgraph import AttackGraph, AttackGraphNode
from maltoolbox.attackgraph.partially_generate import (
    affected_root_assets,
    assoc_affected_expr_chain,
    correct_node_children_on_modified_assoc,
    nodes_to_be_removed,
    switch_fieldname,
)
from maltoolbox.exceptions import AttackGraphException
from maltoolbox.language import LanguageGraph
from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language.expression_chain import ExpressionsChain, ExprType
from maltoolbox.model import Model


def check_graph_equivalence(true: AttackGraph, other: AttackGraph) -> None:
    """Helper function to check that two graphs are equivalent in terms of nodes and their relationships."""
    assert len(true.nodes) == len(other.nodes), (
        f'Number of nodes differ: True AttackGraph {len(true.nodes)} != Other: {len(other.nodes)}'
    )

    true_full_names = set(true.full_name_to_node.keys())
    other_full_names = set(other.full_name_to_node.keys())
    assert true_full_names == other_full_names, (
        f'Node full_names differ: '
        f'only in true: {true_full_names - other_full_names}; '
        f'only in other: {other_full_names - true_full_names}'
    )

    true_node_id_to_full_name = {node.id: node.full_name for node in true.nodes.values()}
    other_node_id_to_full_name = {node.id: node.full_name for node in other.nodes.values()}

    for true_node_full_name, true_node in true.full_name_to_node.items():
        try:
            part_node = other.full_name_to_node[true_node_full_name]
        except LookupError:
            pytest.fail(
                reason=f'{true_node.full_name} not in partially regenerated graph.'
            )
        true_node_child_names = {true_node_id_to_full_name[node.id] for node in true_node.children}
        part_node_child_names = {other_node_id_to_full_name[node.id] for node in part_node.children}
        assert true_node_child_names == part_node_child_names, (
            f'Different children between true and partially regenerated graphs for {true_node.full_name}'
        )
        true_node_parent_names = {true_node_id_to_full_name[node.id] for node in true_node.parents}
        part_node_parent_names = {other_node_id_to_full_name[node.id] for node in part_node.parents}
        assert true_node_parent_names == part_node_parent_names, (
            f'Different parents between true and partially regenerated graphs for {true_node.full_name}'
        )


def test_partial_regeneration(trainingLang_lang_graph: LanguageGraph) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)

    host0 = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host0})
    AG.partially_regenerate_graph(
        new_assets={host0}, new_associations={(network, 'hosts', host0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    user0 = model.add_asset(asset_type='User', name='User0')
    host0.add_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        new_assets={user0}, new_associations={(host0, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Data [data] * <-- DataOnHosts --> * [hosts] Host
    data0 = model.add_asset(asset_type='Data', name='Data0')
    host0.add_associated_assets(fieldname='data', assets={data0})
    AG.partially_regenerate_graph(
        new_assets={data0}, new_associations={(host0, 'data', data0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Add a second host to the already existing network, this requires
    # relinking of the pre-existing Network:LAN:access node's children.
    host1 = model.add_asset(asset_type='Host', name='Host1')
    network.add_associated_assets('hosts', {host1})
    AG.partially_regenerate_graph(
        new_assets={host1}, new_associations={(network, 'hosts', host1)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Associate the same user with the second host as well, exercising
    # relinking of an existing node (User0:compromise) to a new child.
    host1.add_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        new_associations={(host1, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # A second Data asset, this time on Host1, and a second piece of Data
    # added onto Host0 (which already has Data0 associated), covering both
    # a fresh host/data pairing and a host gaining an additional Data child.
    data1 = model.add_asset(asset_type='Data', name='Data1')
    data2 = model.add_asset(asset_type='Data', name='Data2')
    host1.add_associated_assets(fieldname='data', assets={data1})
    host0.add_associated_assets(fieldname='data', assets={data2})
    AG.partially_regenerate_graph(
        new_assets={data1, data2},
        new_associations={(host1, 'data', data1), (host0, 'data', data2)},
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Network [fromNetworks] * <-- InterNetworkConnectivity --> * [toNetworks] Network
    network2 = model.add_asset(asset_type='Network', name='WAN')
    AG.partially_regenerate_graph(new_assets={network2})
    network.add_associated_assets(fieldname='toNetworks', assets={network2})
    AG.partially_regenerate_graph(
        new_associations={(network, 'toNetworks', network2)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Now tear everything back down and check that the partially regenerated graph is equivalent to the newly generated graph.
    network.remove_associated_assets(fieldname='toNetworks', assets={network2})
    AG.partially_regenerate_graph(
        removed_associations={(network, 'toNetworks', network2)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(network2)
    AG.partially_regenerate_graph(removed_assets={network2})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data1)
    AG.partially_regenerate_graph(removed_assets={data1}, removed_associations={(host1, 'data', data1)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data2)
    AG.partially_regenerate_graph(removed_assets={data2}, removed_associations={(host0, 'data', data2)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    host1.remove_associated_assets(fieldname='users', assets={user0})
    AG.partially_regenerate_graph(
        removed_associations={(host1, 'users', user0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(host1)
    AG.partially_regenerate_graph(removed_assets={host1}, removed_associations={(network, 'hosts', host1)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    host0.remove_associated_assets(fieldname='data', assets={data0})
    AG.partially_regenerate_graph(
        removed_associations={(host0, 'data', data0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(data0)
    AG.partially_regenerate_graph(removed_assets={data0})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(user0)
    AG.partially_regenerate_graph(removed_assets={user0}, removed_associations={(host0, 'users', user0)})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    network.remove_associated_assets(fieldname='hosts', assets={host0})
    AG.partially_regenerate_graph(
        removed_associations={(network, 'hosts', host0)}
    )
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    model.remove_asset(host0)
    AG.partially_regenerate_graph(removed_assets={host0})
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Back down to only the original Network asset.
    assert set(model.assets.values()) == {network}


def test_partial_regeneration_change_model_completely(trainingLang_lang_graph: LanguageGraph) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)

    new_assets = set()
    new_associations = set()

    host0 = model.add_asset(asset_type='Host', name='Host0')
    new_assets.add(host0)
    network.add_associated_assets('hosts', {host0})
    new_associations.add((network, 'hosts', host0))

    user0 = model.add_asset(asset_type='User', name='User0')
    new_assets.add(user0)
    host0.add_associated_assets(fieldname='users', assets={user0})
    new_associations.add((host0, 'users', user0))

    data0 = model.add_asset(asset_type='Data', name='Data0')
    new_assets.add(data0)
    host0.add_associated_assets(fieldname='data', assets={data0})
    new_associations.add((host0, 'data', data0))

    host1 = model.add_asset(asset_type='Host', name='Host1')
    new_assets.add(host1)
    network.add_associated_assets('hosts', {host1})
    new_associations.add((network, 'hosts', host1))

    host1.add_associated_assets(fieldname='users', assets={user0})
    new_associations.add((host1, 'users', user0))

    data1 = model.add_asset(asset_type='Data', name='Data1')
    data2 = model.add_asset(asset_type='Data', name='Data2')
    new_assets.update({data1, data2})
    host1.add_associated_assets(fieldname='data', assets={data1})
    host0.add_associated_assets(fieldname='data', assets={data2})
    new_associations.update({(host1, 'data', data1), (host0, 'data', data2)})

    network2 = model.add_asset(asset_type='Network', name='WAN')
    new_assets.add(network2)
    network.add_associated_assets(fieldname='toNetworks', assets={network2})
    new_associations.add((network, 'toNetworks', network2))

    AG.partially_regenerate_graph(new_assets=new_assets, new_associations=new_associations)
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    removed_assets = set()
    removed_associations = set()
    new_assets.clear()
    new_associations.clear()

    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != network:
            removed_assets.add(asset)
            model.remove_asset(asset)

    network1 = model.add_asset(asset_type='Network', name='Network1')
    network2 = model.add_asset(asset_type='Network', name='Network2')
    network3 = model.add_asset(asset_type='Network', name='Network3')
    new_assets.update({network1, network2, network3})
    network1.add_associated_assets(fieldname='toNetworks', assets={network2, network3})
    new_associations.update({(network1, 'toNetworks', network2), (network1, 'toNetworks', network3)})
    network.add_associated_assets(fieldname='toNetworks', assets={network1})
    new_associations.add((network, 'toNetworks', network1))

    hostInNetwork = model.add_asset(asset_type='Host', name='HostInNetwork')
    hostInNetwork1 = model.add_asset(asset_type='Host', name='HostInNetwork1')
    hostInNetwork2 = model.add_asset(asset_type='Host', name='HostInNetwork2')
    hostInNetwork3 = model.add_asset(asset_type='Host', name='HostInNetwork3')
    new_assets.update({hostInNetwork, hostInNetwork1, hostInNetwork2, hostInNetwork3})
    network.add_associated_assets(fieldname='hosts', assets={hostInNetwork})
    network1.add_associated_assets(fieldname='hosts', assets={hostInNetwork1})
    network2.add_associated_assets(fieldname='hosts', assets={hostInNetwork2})
    network3.add_associated_assets(fieldname='hosts', assets={hostInNetwork3})
    new_associations.update({(network, 'hosts', hostInNetwork), (network1, 'hosts', hostInNetwork1),
        (network2, 'hosts', hostInNetwork2), (network3, 'hosts', hostInNetwork3)
    })

    dataConnectedToAllHosts = model.add_asset(asset_type='Data', name='DataConnectedToAllHosts')
    new_assets.add(dataConnectedToAllHosts)
    dataConnectedToAllHosts.add_associated_assets(fieldname='hosts', assets={hostInNetwork, hostInNetwork1, hostInNetwork2, hostInNetwork3})

    userFornet0and2 = model.add_asset(asset_type='User', name='UserForNet0and2')
    userFornet1and3 = model.add_asset(asset_type='User', name='UserForNet1and3')
    new_assets.update({userFornet0and2, userFornet1and3})
    userFornet0and2.add_associated_assets(fieldname='hosts', assets={hostInNetwork, hostInNetwork2})
    userFornet1and3.add_associated_assets(fieldname='hosts', assets={hostInNetwork1, hostInNetwork3})
    new_associations.update({(userFornet0and2, 'hosts', hostInNetwork), (userFornet0and2, 'hosts', hostInNetwork2),
        (userFornet1and3, 'hosts', hostInNetwork1), (userFornet1and3, 'hosts', hostInNetwork3)
    })

    AG.partially_regenerate_graph(new_assets=new_assets, new_associations=new_associations, removed_assets=removed_assets, removed_associations=removed_associations)
    regenerated_AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)


def test_partial_regeneration_corelang(corelang_lang_graph: LanguageGraph) -> None:
    """Tests partial regeneration of the attack graph for a model in coreLang."""
    model = Model('Test Model', corelang_lang_graph)
    corpnet = model.add_asset(asset_type='Network', name='CorpNet')
    AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)

    # --- Phase 1: incremental build ---

    webapp = model.add_asset(asset_type='Application', name='WebApp')
    corpnet.add_associated_assets('applications', {webapp})
    AG.partially_regenerate_graph(
        new_assets={webapp}, new_associations={(corpnet, 'applications', webapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    webhw = model.add_asset(asset_type='Hardware', name='WebServer')
    webhw.add_associated_assets('sysExecutedApps', {webapp})
    AG.partially_regenerate_graph(
        new_assets={webhw}, new_associations={(webhw, 'sysExecutedApps', webapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    webdata = model.add_asset(asset_type='Data', name='WebAppData')
    webapp.add_associated_assets('containedData', {webdata})
    AG.partially_regenerate_graph(
        new_assets={webdata}, new_associations={(webapp, 'containedData', webdata)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Add a second application to the already existing network, this requires
    # relinking of the pre-existing Network:CorpNet:access node's children.
    dbapp = model.add_asset(asset_type='Application', name='DBApp')
    corpnet.add_associated_assets('applications', {dbapp})
    AG.partially_regenerate_graph(
        new_assets={dbapp}, new_associations={(corpnet, 'applications', dbapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # WebApp executes DBApp (self-referential AppExecution association),
    # exercising relinking of an existing node's (WebApp) children.
    webapp.add_associated_assets('appExecutedApps', {dbapp})
    AG.partially_regenerate_graph(
        new_associations={(webapp, 'appExecutedApps', dbapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Two new assets and three new associations in a single call: DBApp gets
    # its own hardware, which also hosts a second, hardware-only Data asset.
    dbhw = model.add_asset(asset_type='Hardware', name='DBServer')
    dbdata = model.add_asset(asset_type='Data', name='DBData')
    dbhw.add_associated_assets('sysExecutedApps', {dbapp})
    dbhw.add_associated_assets('hostedData', {dbdata})
    dbapp.add_associated_assets('containedData', {dbdata})
    AG.partially_regenerate_graph(
        new_assets={dbhw, dbdata},
        new_associations={
            (dbhw, 'sysExecutedApps', dbapp),
            (dbhw, 'hostedData', dbdata),
            (dbapp, 'containedData', dbdata),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # IDPS protecting two existing applications at once, i.e. a multi-target
    # association added in a single call.
    netidps = model.add_asset(asset_type='IDPS', name='NetIDPS')
    netidps.add_associated_assets('protectedApps', {webapp, dbapp})
    AG.partially_regenerate_graph(
        new_assets={netidps},
        new_associations={
            (netidps, 'protectedApps', webapp),
            (netidps, 'protectedApps', dbapp),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Identity/Credentials/User chain plus an IAM read privilege, all new at once.
    svcidentity = model.add_asset(asset_type='Identity', name='SvcIdentity')
    svccreds = model.add_asset(asset_type='Credentials', name='SvcCreds')
    alice = model.add_asset(asset_type='User', name='Alice')
    svcidentity.add_associated_assets('credentials', {svccreds})
    alice.add_associated_assets('userIds', {svcidentity})
    svcidentity.add_associated_assets('readPrivData', {webdata})
    AG.partially_regenerate_graph(
        new_assets={svcidentity, svccreds, alice},
        new_associations={
            (svcidentity, 'credentials', svccreds),
            (alice, 'userIds', svcidentity),
            (svcidentity, 'readPrivData', webdata),
        },
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # --- Phase 2: change model (almost) completely ---
    # Tear everything down except CorpNet, then rebuild a bigger topology:
    # three networks linked pairwise via ConnectionRule assets, each with its
    # own application/hardware/data, plus a second IAM chain and an IDPS
    # protecting two apps at once. CorpNet's 'applications' field is both
    # relieved of WebApp/DBApp and given a new ProxyApp in the same call,
    # which is exactly the "same fieldname sees both an addition and a
    # removal in one partial_regenerate_graph call" case that previously
    # broke partial regeneration for trainingLang.

    removed_assets = set()
    removed_associations = set()
    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != corpnet:
            removed_assets.add(asset)
            model.remove_asset(asset)

    new_assets = set()
    new_associations = set()

    dmz = model.add_asset(asset_type='Network', name='DMZ')
    backup = model.add_asset(asset_type='Network', name='BackupNet')
    new_assets.update({dmz, backup})

    cr1 = model.add_asset(asset_type='ConnectionRule', name='CR-CorpNet-DMZ')
    cr2 = model.add_asset(asset_type='ConnectionRule', name='CR-DMZ-Backup')
    new_assets.update({cr1, cr2})
    cr1.add_associated_assets('networks', {corpnet, dmz})
    cr2.add_associated_assets('networks', {dmz, backup})
    new_associations.update({
        (cr1, 'networks', corpnet), (cr1, 'networks', dmz),
        (cr2, 'networks', dmz), (cr2, 'networks', backup),
    })

    proxyapp = model.add_asset(asset_type='Application', name='ProxyApp')
    dmzapp = model.add_asset(asset_type='Application', name='DmzApp')
    backupapp = model.add_asset(asset_type='Application', name='BackupApp')
    new_assets.update({proxyapp, dmzapp, backupapp})
    # Same fieldname ('applications') on CorpNet as the associations just removed.
    corpnet.add_associated_assets('applications', {proxyapp})
    dmz.add_associated_assets('applications', {dmzapp})
    backup.add_associated_assets('applications', {backupapp})
    new_associations.update({
        (corpnet, 'applications', proxyapp),
        (dmz, 'applications', dmzapp),
        (backup, 'applications', backupapp),
    })

    proxyhw = model.add_asset(asset_type='Hardware', name='ProxyServer')
    new_assets.add(proxyhw)
    proxyhw.add_associated_assets('sysExecutedApps', {proxyapp})
    new_associations.add((proxyhw, 'sysExecutedApps', proxyapp))

    shareddata = model.add_asset(asset_type='Data', name='SharedData')
    new_assets.add(shareddata)
    proxyapp.add_associated_assets('containedData', {shareddata})
    # SharedData is reachable both through ProxyApp's containment and
    # directly through the hardware it's hosted on.
    shareddata.add_associated_assets('hardware', {proxyhw})
    new_associations.update({
        (proxyapp, 'containedData', shareddata),
        (shareddata, 'hardware', proxyhw),
    })

    svcidentity2 = model.add_asset(asset_type='Identity', name='SvcIdentity2')
    svccreds2 = model.add_asset(asset_type='Credentials', name='SvcCreds2')
    bob = model.add_asset(asset_type='User', name='Bob')
    new_assets.update({svcidentity2, svccreds2, bob})
    svcidentity2.add_associated_assets('credentials', {svccreds2})
    bob.add_associated_assets('userIds', {svcidentity2})
    svcidentity2.add_associated_assets('readPrivData', {shareddata})
    new_associations.update({
        (svcidentity2, 'credentials', svccreds2),
        (bob, 'userIds', svcidentity2),
        (svcidentity2, 'readPrivData', shareddata),
    })

    edgeidps = model.add_asset(asset_type='IDPS', name='EdgeIDPS')
    new_assets.add(edgeidps)
    edgeidps.add_associated_assets('protectedApps', {proxyapp, dmzapp})
    new_associations.update({
        (edgeidps, 'protectedApps', proxyapp),
        (edgeidps, 'protectedApps', dmzapp),
    })

    AG.partially_regenerate_graph(
        new_assets=new_assets, new_associations=new_associations,
        removed_assets=removed_assets, removed_associations=removed_associations,
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # --- Phase 3: teardown ---

    # Partial removal from a multi-target association (EdgeIDPS keeps
    # protecting ProxyApp but stops protecting DmzApp).
    edgeidps.remove_associated_assets('protectedApps', {dmzapp})
    AG.partially_regenerate_graph(
        removed_associations={(edgeidps, 'protectedApps', dmzapp)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    svcidentity2.remove_associated_assets('readPrivData', {shareddata})
    AG.partially_regenerate_graph(
        removed_associations={(svcidentity2, 'readPrivData', shareddata)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    shareddata.remove_associated_assets('hardware', {proxyhw})
    AG.partially_regenerate_graph(
        removed_associations={(shareddata, 'hardware', proxyhw)}
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Cascading removal of several interlinked assets (a network, its
    # application and their connecting rule) in one call.
    removed_assets = set()
    removed_associations = set()
    for asset in (backup, backupapp, cr2):
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in (backup, backupapp, cr2):
        removed_assets.add(asset)
        model.remove_asset(asset)
    AG.partially_regenerate_graph(
        removed_assets=removed_assets, removed_associations=removed_associations
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Final bulk teardown back to only the original Network asset.
    removed_assets = set()
    removed_associations = set()
    for asset in model.assets.values():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                removed_associations.add((asset, fieldname, associated_asset))
    for asset in list(model.assets.values()):
        if asset != corpnet:
            removed_assets.add(asset)
            model.remove_asset(asset)
    AG.partially_regenerate_graph(
        removed_assets=removed_assets, removed_associations=removed_associations
    )
    regenerated_AG = AttackGraph(lang_graph=corelang_lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    assert set(model.assets.values()) == {corpnet}

def test_partial_regeneration_with_assocChainLang(assocChainLang_lang_graph: LanguageGraph) -> None:
    """Tests partial regeneration of the attack graph for a model in assocChainLang."""
    model = Model('Test Model', assocChainLang_lang_graph)
    parent = model.add_asset(asset_type='A', name='A:0')
    for asset_type in ["B", "C", "D", "E", "F", "G", "H", "I"]:
        child = model.add_asset(asset_type=asset_type, name=f"{asset_type}:0")
        parent.add_associated_assets(asset_type.lower(), {child})
        parent = child
    AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)

    for asset_type, fieldname in [("A", "b"), ("B", "c"), ("C", "d"), ("D", "e"), ("E", "f"), ("F", "g"), ("G", "h"), ("H", "i")]:
        parent = model.get_asset_by_name(f"{asset_type}:0")
        assert parent, f"Could not find asset {asset_type}:0"
        child = model.get_asset_by_name(f"{fieldname.upper()}:0")
        assert child, f"Could not find asset {fieldname.upper()}:0"
        parent.remove_associated_assets(fieldname, {child})
        generated_AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)
        AG.partially_regenerate_graph(removed_associations={(parent, fieldname, child)})
        check_graph_equivalence(AG, generated_AG)

        parent.add_associated_assets(fieldname, {child})
        generated_AG = AttackGraph(lang_graph=assocChainLang_lang_graph, model=model)
        AG.partially_regenerate_graph(new_associations={(parent, fieldname, child)})
        check_graph_equivalence(AG, generated_AG)


def test_partial_regeneration_transitive() -> None:
    """Tests partial regeneration for a step reached via a transitive
    closure (field2*.test_step)."""
    lang_graph = LanguageGraph(MalCompiler().compile('tests/testdata/transitive.mal'))
    model = Model('Test Model', lang_graph)

    root_a = model.add_asset(asset_type='TestAsset', name='RootTestAsset')
    AG = AttackGraph(lang_graph=lang_graph, model=model)

    for i in range(20):
        next_a = model.add_asset(asset_type='TestAsset', name=f'TestAsset:{i}')
        root_a.add_associated_assets('field2', {next_a})
        AG.partially_regenerate_graph(new_assets={next_a}, new_associations={(root_a, 'field2', next_a)})
        regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
        check_graph_equivalence(regenerated_AG, AG)
        root_a = next_a

    for i in reversed(range(0, 20, 2)):
        child_a = model.get_asset_by_name(f'TestAsset:{i}')
        assert child_a, f"Could not find asset TestAsset:{i}"
        parent_a = next(iter(child_a.associated_assets['field1']))
        parent_a.remove_associated_assets('field2', {child_a})
        AG.partially_regenerate_graph(removed_associations={(parent_a, 'field2', child_a)})
        regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
        check_graph_equivalence(regenerated_AG, AG)

def test_partial_regeneration_set_ops_adv() -> None:
    """Tests partial regeneration for steps whose chain nests an
    intersection inside a collect (innerIntersection/outerIntersection)."""
    lang_graph = LanguageGraph(MalCompiler().compile('tests/testdata/set_ops_adv.mal'))
    model = Model('Test Model', lang_graph)

    hub1 = model.add_asset(asset_type='Hub', name='Hub 1')
    hub2 = model.add_asset(asset_type='Hub', name='Hub 2')
    hub3 = model.add_asset(asset_type='Hub', name='Hub 3')
    target1 = model.add_asset(asset_type='Target', name='Target 1')
    target2 = model.add_asset(asset_type='Target', name='Target 2')
    target3 = model.add_asset(asset_type='Target', name='Target 3')

    hub2.add_associated_assets('setA', {target1, target2})
    hub3.add_associated_assets('setB', {target2, target3})
    hub1.add_associated_assets('siblings', {hub2, hub3})

    AG = AttackGraph(lang_graph=lang_graph, model=model)

    # target2 is the only asset reachable via both setA and setB.
    hub3.remove_associated_assets('setB', {target2})
    AG.partially_regenerate_graph(removed_associations={(hub3, 'setB', target2)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    hub3.add_associated_assets('setB', {target2})
    AG.partially_regenerate_graph(new_associations={(hub3, 'setB', target2)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    # Removing the sibling link removes both chains' path to Hub 3's targets.
    hub1.remove_associated_assets('siblings', {hub3})
    AG.partially_regenerate_graph(removed_associations={(hub1, 'siblings', hub3)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    hub1.add_associated_assets('siblings', {hub3})
    AG.partially_regenerate_graph(new_associations={(hub1, 'siblings', hub3)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)


def test_partial_regeneration_set_ops_collect_left() -> None:
    """Tests partial regeneration for a step whose chain has a difference
    nested on the left side of a collect ((setA - setB).next.reach), a
    position where the reverse walk in affected_root_assets is unsafe if
    more than one association changes in the same call."""
    lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/set_ops_collect_left.mal')
    )
    model = Model('Test Model', lang_graph)

    origin = model.add_asset(asset_type='Origin', name='Origin')
    node1 = model.add_asset(asset_type='Node', name='Node 1')
    node2 = model.add_asset(asset_type='Node', name='Node 2')
    target1 = model.add_asset(asset_type='Target', name='Target 1')
    target2 = model.add_asset(asset_type='Target', name='Target 2')

    # Origin's (setA - setB) is {Node 1, Node 2} - {Node 2} = {Node 1}.
    origin.add_associated_assets('setA', {node1, node2})
    origin.add_associated_assets('setB', {node2})
    node1.add_associated_assets('next', {target1})
    node2.add_associated_assets('next', {target2})

    AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_node = AG.get_node_by_full_name('Origin:check')
    assert AG.get_node_by_full_name('Target 1:reach') in check_node.children
    assert AG.get_node_by_full_name('Target 2:reach') not in check_node.children

    # Change both Node 1's and Node 2's next in the same call.
    node1.remove_associated_assets('next', {target1})
    node2.remove_associated_assets('next', {target2})
    AG.partially_regenerate_graph(
        removed_associations={(node1, 'next', target1), (node2, 'next', target2)}
    )
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    node1.add_associated_assets('next', {target1})
    node2.add_associated_assets('next', {target2})
    AG.partially_regenerate_graph(
        new_associations={(node1, 'next', target1), (node2, 'next', target2)}
    )
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)


def test_partial_regeneration_shared_assoc_sibling() -> None:
    """Tests partial regeneration when two sibling subtypes share an
    inherited association but only one of them defines the attack step
    that uses it."""
    lang_graph = LanguageGraph(
        MalCompiler().compile('tests/testdata/shared_assoc_sibling.mal')
    )
    model = Model('Test Model', lang_graph)

    a = model.add_asset(asset_type='SiblingA', name='A1')
    b = model.add_asset(asset_type='SiblingB', name='B1')
    t1 = model.add_asset(asset_type='Target', name='T1')

    b.add_associated_assets('target', {t1})
    AG = AttackGraph(lang_graph=lang_graph, model=model)

    b.remove_associated_assets('target', {t1})
    AG.partially_regenerate_graph(removed_associations={(b, 'target', t1)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    b.add_associated_assets('target', {t1})
    AG.partially_regenerate_graph(new_associations={(b, 'target', t1)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)

    a.add_associated_assets('target', {t1})
    AG.partially_regenerate_graph(new_associations={(a, 'target', t1)})
    regenerated_AG = AttackGraph(lang_graph=lang_graph, model=model)
    check_graph_equivalence(regenerated_AG, AG)


def test_switch_fieldname_unknown_fieldname_raises(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    with pytest.raises(AttackGraphException, match='not found in associations'):
        switch_fieldname(network, 'doesNotExist')


def test_correct_node_children_on_modified_assoc_missing_asset_link_raises(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    lg_attack_step = trainingLang_lang_graph.assets['Network'].attack_steps['access']
    node = AttackGraphNode(node_id=0, lg_attack_step=lg_attack_step, model_asset=None)
    with pytest.raises(AttackGraphException, match='missing asset link'):
        correct_node_children_on_modified_assoc(model, node, {})


def test_correct_node_children_on_modified_assoc_missing_target_node_raises(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    host = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host})
    AG = AttackGraph(lang_graph=trainingLang_lang_graph, model=model)
    access_node = AG.get_node_by_full_name('LAN:access')
    assert access_node is not None

    # An intentionally incomplete full_name_to_node map: Host0:connect (a
    # child reachable from LAN:access) is missing from it.
    with pytest.raises(AttackGraphException, match='Failed to find target node'):
        correct_node_children_on_modified_assoc(model, access_node, {})


def test_nodes_to_be_removed_missing_node_raises(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    with pytest.raises(AttackGraphException, match='Failed to find'):
        nodes_to_be_removed({network}, {})


def test_assoc_affected_expr_chain_default_modified_fieldnames(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    """When modified_fieldnames isn't passed in, it should be derived from
    affected_assoc_dict."""
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    host = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host})

    hosts_assoc = trainingLang_lang_graph.assets['Network'].associations['hosts']
    field_chain = ExpressionsChain(
        type=ExprType.FIELD, association=hosts_assoc, fieldname='hosts'
    )
    affected_assoc_dict = {network: {'hosts': {host}}}

    assert assoc_affected_expr_chain(model, {network}, affected_assoc_dict, field_chain)


def test_assoc_affected_expr_chain_subtype(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    host = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host})

    hosts_assoc = trainingLang_lang_graph.assets['Network'].associations['hosts']
    field_chain = ExpressionsChain(
        type=ExprType.FIELD, association=hosts_assoc, fieldname='hosts'
    )
    subtype_chain = ExpressionsChain(
        type=ExprType.SUBTYPE,
        sub_link=field_chain,
        subtype=trainingLang_lang_graph.assets['Host'],
    )
    affected_assoc_dict = {network: {'hosts': {host}}}
    modified_fieldnames = frozenset({'hosts'})

    assert assoc_affected_expr_chain(
        model, {network}, affected_assoc_dict, subtype_chain, modified_fieldnames
    )


def test_assoc_affected_expr_chain_transitive(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network1 = model.add_asset(asset_type='Network', name='Network1')
    network2 = model.add_asset(asset_type='Network', name='Network2')
    network3 = model.add_asset(asset_type='Network', name='Network3')
    network1.add_associated_assets('toNetworks', {network2})
    network2.add_associated_assets('toNetworks', {network3})

    to_networks_assoc = trainingLang_lang_graph.assets['Network'].associations['toNetworks']
    field_chain = ExpressionsChain(
        type=ExprType.FIELD, association=to_networks_assoc, fieldname='toNetworks'
    )
    transitive_chain = ExpressionsChain(type=ExprType.TRANSITIVE, sub_link=field_chain)
    modified_fieldnames = frozenset({'toNetworks'})

    # Network2's outgoing toNetworks association changed; reachable from
    # Network1 two hops deep into the transitive closure.
    affected_assoc_dict = {network2: {'toNetworks': {network3}}}
    assert assoc_affected_expr_chain(
        model, {network1}, affected_assoc_dict, transitive_chain, modified_fieldnames
    )

    # Network3 is a leaf: nothing changed on any Network reachable from it.
    assert not assoc_affected_expr_chain(
        model, {network3}, affected_assoc_dict, transitive_chain, modified_fieldnames
    )


def test_affected_root_assets_subtype(
    trainingLang_lang_graph: LanguageGraph,
) -> None:
    model = Model('Test Model', trainingLang_lang_graph)
    network = model.add_asset(asset_type='Network', name='LAN')
    host = model.add_asset(asset_type='Host', name='Host0')
    network.add_associated_assets('hosts', {host})

    hosts_assoc = trainingLang_lang_graph.assets['Network'].associations['hosts']
    field_chain = ExpressionsChain(
        type=ExprType.FIELD, association=hosts_assoc, fieldname='hosts'
    )
    subtype_chain = ExpressionsChain(
        type=ExprType.SUBTYPE,
        sub_link=field_chain,
        subtype=trainingLang_lang_graph.assets['Host'],
    )
    affected_assoc_dict = {network: {'hosts': {host}}}
    modified_fieldnames = frozenset({'hosts'})

    assert affected_root_assets(
        model, affected_assoc_dict, subtype_chain, modified_fieldnames
    ) == {network}
