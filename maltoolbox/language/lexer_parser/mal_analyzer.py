from .mal_parser import malParser

import logging
import re

from typing import Any, Tuple, List

class malAnalyzerInterface:
    def checkMal(self, ctx: malParser.MalContext) -> None:
        pass
    def checkDefine(self, ctx: malParser.DefineContext, data: Tuple[str, dict]) -> None:
        pass
    def checkInclude(self, ctx: malParser.IncludeContext, data: Tuple[str, str]) -> None:
        pass
    def checkCategory(self, ctx: malParser.CategoryContext, data: Tuple[str, Tuple[List, Any]]) -> None:
        pass
    def checkAsset(self, ctx: malParser.AssetContext, asset: dict) -> None:
        pass
    def checkMeta(self, ctx: malParser.MetaContext, data: Tuple[Tuple[str, str],]) -> None:
        pass
    def checkStep(self, ctx: malParser.StepContext, step: dict) -> None:
        pass
    def checkVariable(self, ctx: malParser.VariableContext, var: dict) -> None:
        pass
    def checkAssociation(self, ctx: malParser.AssociationContext, association: dict) -> None:
        pass
    def checkReaches(self, ctx: malParser.ReachesContext, data: dict) -> None:
        pass

class malAnalyzerException(Exception):
    def __init__(self, error_message):
        self._error_message = error_message
        super().__init__(self._error_message)

class malAnalyzer(malAnalyzerInterface):
    '''
    A class to preform syntax-checks for MAL.
    '''
        
    def __init__(self, *args, **kwargs) -> None:
        self._error: bool = False
        self._error_msg: str = ""
        self._warn: bool = False
        self._preform_post_analysis = 0 

        self._defines: dict      = {}
        self._assets: dict       = {}
        self._category: dict     = {}
        self._metas: dict        = {}
        self._steps: dict        = {}
        self._vars: dict         = {}
        self._associations: dict = {}

        self._all_associations   = []
        self._current_vars       = []
        self._include_stack      = []

        super().__init__(*args, **kwargs)
        
    def has_error(self) -> bool:
        return self._error
    
    def has_warning(self) -> bool:
        return self._warn

    def _post_analysis(self) -> None:
        '''
        Perform a post-analysis to confirm that the 
        mandatory fields and relations are met.
        '''
        self._analyse_defines()
        self._analyse_extends()
        self._analyse_abstract()
        self._analyse_parents()
        self._analyse_association()
        self._analyse_steps()
        self._analyse_fields()
        self._analyse_variables()
        self._analyse_reaches()
    
    def _analyse_defines(self) -> None:
        '''
        Check for mandatory defines: ID & Version
        '''
        if 'id' in self._defines.keys():
            define_value: str = self._defines['id']['value']
            if (len(define_value) == 0):
                error_msg = 'Define \'id\' cannot be empty'
                logging.error(error_msg)
                self._error = True
        else:
            error_msg = 'Missing required define \'#id: ""\''
            logging.error(error_msg)
            self._error = True
            raise malAnalyzerException(error_msg)

        if 'version' in self._defines.keys():
            version: str = self._defines['version']['value']
            if not re.match(r"\d+\.\d+\.\d+", version):
                error_msg = 'Define \'version\' must be valid semantic versioning without pre-release identifier and build metadata'
                logging.error(error_msg)
                self._error = True
                raise malAnalyzerException(error_msg)
        else:
            error_msg = 'Missing required define \'#version: ""\''
            logging.error(error_msg)
            self._error = True
            raise malAnalyzerException(error_msg)

    def _analyse_extends(self) -> None:
        '''
        For all assets which extend another, verify if the extended asset exists
        '''
        raise_error: bool = False
        extend_asset_name: str = ''
        for asset in self._assets:
            asset_context: malParser.AssetContext = self._assets[asset]['ctx']
            if(asset_context.EXTENDS()):
                extend_asset_name = asset_context.ID()[1].getText()
                if(not extend_asset_name in self._assets):
                    '''
                    Do we need to check if the extended asset is 
                    in the same category? If so we can load the asset
                    and check it's parent
                    '''
                    error_msg = f'Asset \'{extend_asset_name}\' not defined'
                    logging.error(error_msg)
                    raise malAnalyzerException(error_msg)

    def _analyse_abstract(self) -> None:
        '''
        For every abstract asset, verify if it is extended by another asset
        '''
        for parent in self._assets:
            parent_ctx: malParser.AssetContext = self._assets[parent]['ctx']
            if(parent_ctx.ABSTRACT()):
                found: bool = False
                for extendee in self._assets:
                    extendee_ctx: malParser.AssetContext = self._assets[extendee]['ctx']
                    if(extendee_ctx.EXTENDS() and extendee_ctx.ID()[1].getText() == parent_ctx.ID()[0].getText()):
                        found = True
                        break
                if not found:
                    self._warn = True
                    logging.warn(f'Asset \'{parent_ctx.ID()[0].getText()}\' is abstract but never extended to')
    
    def _analyse_parents(self) -> None:
        '''
        Verify if there are circular extend relations
        '''
        error: bool = False
        for asset in self._assets:
            parents: list[str] = []
            parent_ctx: malParser.AssetContext  = self._assets[asset]['ctx']
            while (isinstance(parent_ctx, malParser.AssetContext)):
                parent_name: str = parent_ctx.ID()[0].getText()
                if (parent_name in parents):
                    error_msg: str = ' -> '.join(parents)
                    error_msg += f' -> {parent_name}' 
                    error_msg = f'Asset \'{parent_name}\' extends in loop \'{error_msg}\''
                    logging.error(error_msg)
                    raise malAnalyzerException(error_msg)
                parents.append(parent_name)
                parent_ctx = self._get_assets_extendee(parent_ctx)

    def _analyse_reaches(self) -> None:
        '''
        For every attackStep in every asset, verify if the prerequisites point to assets and that the reaches point to 
        attack steps
        '''
        for asset in self._assets.keys():
            attack_steps = self._assets[asset]['obj']['attackSteps']
            for attack_step in attack_steps:
                if (attack_step['type'] in ['exist', 'notExist']):
                    if (attack_step['ttc']):
                        logging.error(f'Attack step of type \'{attack_step["type"]}\' must not have TTC')
                        self._error = True
                        continue
                    if (attack_step['requires']):
                        # Verify if every requires expression returns an asset
                        for expr in attack_step['requires']['stepExpressions']:
                            self._check_to_asset(asset, expr)
                    else:
                        logging.error(f'Attack step of type \'{attack_step["type"]}\' must have require \'<-\'')
                        self._error = True
                        continue  
                elif (attack_step['requires']):
                        logging.error('Require \'<-\' may only be defined for attack step type exist \'E\' or not-exist \'!E\'')
                        self._error = True
                        continue 
                
                if (attack_step['reaches']):
                    # Verify if every reaches expresion returns an attack step
                    for expr in attack_step['reaches']['stepExpressions']:
                        self._check_to_step(asset, expr)
        
    def _check_to_step(self, asset, expr) -> None:
        '''
        Given a reaches, verify if the expression resolves to a valid AttackStep for an existing Asset 
        '''
        match (expr['type']):
            # Returns an attackStep if it exists for this asset
            case 'attackStep':
                if (asset in self._assets.keys()):
                    for attackStep in self._steps[asset].keys():
                        if (attackStep == expr['name']):
                            return self._steps[asset][attackStep]['step']
                        
                logging.error(f'Attack step \'{expr["name"]}\' not defined for asset \'{asset}\'')
                self._error = True
                return None
            # Returns an attackStep if it exists for the asset returned by the lhs expression 
            case 'collect':
                if (left_target := self._check_to_asset(asset, expr['lhs'])):
                    return self._check_to_step(left_target, expr['rhs'])
                self._error = True
                return None
            case _:
                logging.error('Last step is not attack step')
                self._error = True
                return None
                
    def _check_to_asset(self, asset, expr) -> None:
        '''
        Verify if the expression resolves to an existing Asset
        '''
        match (expr['type']):
            # field - verify if asset exists via associations
            case 'field': 
                return self._check_field_expr(asset, expr)
            # variable - verify if there is a variable with this name
            case 'variable':
                return self._check_variable_expr(asset, expr)
            # collect - return asset pointed by all the parts in the expression
            case 'collect':
                return self._check_collect_expr(asset, expr)
            # set - verify if the assets in the operation have an common ancestor
            case 'union' | 'intersection' | 'difference':
                return self._check_set_expr(asset, expr)
            # transitive - verify if the asset before * (STAR) exists
            case 'transitive':
                return self._check_transitive_expr(asset, expr)
            # subtype - verifies if the asset inside [] is a child from the asset preceding it
            case 'subType':
                return self._check_sub_type_expr(asset, expr)
            case _:
                logging.error(f'Unexpected expression \'{expr["type"]}\'')
                self._error = True
                return None
    
    def _check_field_expr(self, asset, expr):
        '''
        Check if an asset exists by checking the associations for the current asset
        '''
        if asset in self._associations.keys():
            for association in self._associations[asset].keys():
                association = self._associations[asset][association]['association']
                if (expr['name'] == association['leftField']):
                    if (self._get_asset_name(association['leftAsset'])):
                        return association['leftAsset']
                if (expr['name'] == association['rightField']):
                    if (self._get_asset_name(association['rightAsset'])):
                        return association['rightAsset']

        # Verify if there is a variable defined with the same name; possible the user forgot to call it
        extra=""
        if (asset in self._vars.keys() and expr['name'] in self._vars[asset].keys()):
            extra=f', did you mean the variable \'{expr['name']}()\'?'
            self._warn = True
    
        logging.error(f'Field \'{expr["name"]}\' not defined for asset \'{asset}\''+extra)
        self._error = True

    def _check_variable_expr(self, asset, expr):
        '''
        Check if there is a variable reference in this asset with the user identifier.
        '''        
        if (asset in self._vars.keys() and expr['name'] in self._vars[asset].keys()):
            return self._variable_to_asset(asset, expr['name']) 

        logging.error(f'Variable \'{expr["name"]}\' is not defined')
        self._error = True
        return None
    
    def _check_collect_expr(self, asset, expr):
        '''
        Iteratively, retrieve the asset pointed by the leftmost expression and, recursively, check the rhs associated
        with each lhs.
        '''
        if (left_target := self._check_to_asset(asset, expr['lhs'])):
            return self._check_to_asset(left_target, expr['rhs'])
        return None
    
    def _check_set_expr(self, asset, expr) -> None:
        '''
        Obtains the assets pointed by boths hs's and verifies if they have a common ancestor
        '''
        lhs_target = self._check_to_asset(asset, expr['lhs'])
        rhs_target = self._check_to_asset(asset, expr['rhs'])
        if (not lhs_target or not rhs_target):
            return None

        if (target := self._get_LCA(lhs_target, rhs_target)):
            return target
        
        logging.error(f'Types \'{lhs_target}\' and \'{rhs_target}\' have no common ancestor')
        self._error = True
        return None

    def _get_LCA(self, lhs_target, rhs_target):
        '''
        Receives two assets and verifies if they have an ancestor in common
        '''
        if (self._is_child(lhs_target, rhs_target)):
            return lhs_target
        elif (self._is_child(rhs_target, lhs_target)):
            return rhs_target
        else:
            lhs_ctx = self._assets[lhs_target]['ctx']
            rhs_ctx = self._assets[rhs_target]['ctx']
            lhs_parent_ctx = self._get_assets_extendee(lhs_ctx)
            rhs_parent_ctx = self._get_assets_extendee(rhs_ctx)
            if (not lhs_parent_ctx or not rhs_parent_ctx):
                return None
            return self._get_LCA(lhs_parent_ctx.ID()[0].getText(), rhs_parent_ctx.ID()[0].getText())

    def _check_sub_type_expr(self, asset, expr) -> None:
        '''
        Given expr[ID], obtains the assets given by expr and ID and verifies if ID is 
        a child of expr
        '''
        target = self._check_to_asset(asset, expr['stepExpression'])
        if (not target):
            return None

        if (asset_type := self._get_asset_name(expr['subType'])):
            if (self._is_child(target, asset_type)):
                return asset_type

            logging.error(f'Asset \'{target}\' cannot be of type \'{asset_type}\'')
            self._error = True
        return None

    def _check_transitive_expr(self, asset, expr) -> None:
        '''
        Given expr*, obtain the asset given by expr and verify if it is a child of the current asset
        '''
        if (res := self._check_to_asset(asset, expr['stepExpression'])):
            if (self._is_child(asset,res)):
                return res
   
            logging.error(f'Previous asset \'{asset}\' is not of type \'{res}\'')
            self._error = True
        return None
    
    def _is_child(self, parent_name, child_name):
        '''
        Receives two assets and verifies if one extends the other
        '''
        if (parent_name == child_name):
            return True
        
        if (valid_asset := self._get_asset_name(child_name)):
            asset_context: malParser.AssetContext = self._assets[valid_asset]['ctx']
            if (parent_ctx := self._get_assets_extendee(asset_context)):
                child_parent_name = self._get_asset_name(parent_ctx.ID()[0].getText())
                return self._is_child(parent_name, child_parent_name)
            
        return False

    def _get_asset_name(self, name):
        if (name in self._assets.keys()):
            return name

        logging.error(f'Asset \'{name}\' not defined')
        self._error = True
        return None

    def _analyse_association(self) -> None:
        '''
        For every association, verify if the assets exist
        '''
        for association in self._all_associations:
            leftAsset = association['association']['leftAsset']
            rightAsset= association['association']['rightAsset']

            if (not leftAsset in self._assets.keys()):
                logging.error(f'Left asset \'{leftAsset}\' is not defined')
                self._error = True
            if (not rightAsset in self._assets.keys()):
                logging.error(f'Right asset \'{leftAsset}\' is not defined')
                self._error = True

    def _analyse_fields(self) -> None:
        '''
        Update a variable's fields (associations) to include its parents associations. 
        Also checks if an association has been defined more than once in a hierarchy
        '''
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['ctx'])
            for parent in parents:
                for association in self._all_associations:
                    leftAsset = association['association']['leftAsset']
                    rightAsset= association['association']['rightAsset']
                    if leftAsset==parent:
                        rightField = association['association']['rightField']
                        self._add_field(parent, asset, rightField, association)
                    if rightAsset==parent:
                        leftField = association['association']['leftField']
                        self._add_field(parent, asset, leftField, association)
    
    def _add_field(self, parent: str, asset: str, field: str, association: dict):
        # Check that this asset does not have an assoication with the same name
        if asset not in self._associations or field not in self._associations[asset]:
            # Check if there isn't a step with the same name
            step_ctx = self._has_step(asset, field)
            if not step_ctx:
                if not asset in self._associations.keys():
                    self._associations[asset] = {field: {k: association[k] for k in ["association", "ctx"]}}
                else:
                    self._associations[asset][field] = {k: association[k] for k in ["association", "ctx"]}
            # Otherwise, this will be an error
            else:
                self._error = True
                logging.error(f'Field {field} previously defined as an attack step at {step_ctx.start.line}')
        # Association field was already defined for this asset
        else:
            logging.error(f'Field {parent}.{field} previously defined at {self._associations[asset][field]['ctx'].start.line}')
            self._error = True

    def _has_step(self, asset, field):
        if asset in self._steps.keys() and field in self._steps[asset]:
            return self._steps[asset][field]['ctx']
        return None

    def _get_assets_extendee(self, ctx: malParser.AssetContext) -> malParser.AssetContext:
        '''
        Verifies if the current asset extends another and, if so, return the parent's context
        '''
        if (ctx.EXTENDS()):
            return self._assets[ctx.ID()[1].getText()]['ctx']
        return None
    
    def _variable_to_asset(self, asset: str, var: str):
        '''
        Checks if there is no cycle in the variables and verifies that it points to 
        an existing asset
        '''
        if var not in self._current_vars:
            self._current_vars.append(var)
            res = self._check_to_asset(asset, self._vars[asset][var]['var']['stepExpression'])
            self._current_vars.pop()
            return res

        cycle = '->'.join(self._current_vars)+'->'+var
        error_msg = f'Variable \'{var}\' contains cycle {cycle}'
        logging.error(error_msg)
        raise malAnalyzerException(error_msg)

    def _analyse_variables(self):
        '''
        This function will verify if an asset which extends another does not redefine a variable.
        It also updates the list of variables for an asset to includes its parent's variables

        Once that is done, we need to guarantee that the variable points to an asset and that 
        there are no loops in the variables, i.e. a variable does not somehow reference itself
        '''
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['ctx'])
            parents.pop() # The last element is the asset itself, no need to check again if variable is defined twice
            for parent in parents:
                if parent not in self._vars.keys():
                    continue # If parent has no variables, we don't need to do anything
                if asset not in self._vars.keys():
                    self._vars[asset] = self._vars[parent] # If asset has no variables, just inherit its parents variables
                    continue
                # Otherwise, we do need to check if variables are defined more than once
                for var in self._vars[asset].keys():
                    if parent in self._vars.keys() and var in self._vars[parent].keys() and self._vars[asset][var]['ctx']!=self._vars[parent][var]['ctx']:
                        error_msg = f'Variable \'{var}\' previously defined at {self._vars[parent][var]['ctx'].start.line}'
                        logging.error(error_msg)
                        raise malAnalyzerException(error_msg)
                self._vars[asset].update(self._vars[parent])
        
            # If the current asset has variables, we want to check they point to an asset
            if asset in self._vars.keys():
                for var in self._vars[asset].keys():
                    if self._variable_to_asset(asset, var)==None:
                        error_msg = f'Variable \'{var}\' defined at {self._vars[asset][var]['ctx'].start.line} does not point to an asset'
                        logging.error(error_msg)
                        raise malAnalyzerException(error_msg)
                        

    def checkMal(self, ctx: malParser.MalContext) -> None:
        '''
        We only want to preform _post_analysis as the very last step.
        '''
        if (self._preform_post_analysis==0):
            self._post_analysis()
        else:
            self._include_stack.pop()
            self._preform_post_analysis -= 1 

    def checkInclude(self, ctx: malParser.MalContext, data: Tuple[str, str]) -> None:       
        '''
        When an include is found, it triggers the analysis of a new MAL file. To prevent
        checkMal from being performed before all files have been analysed, we increment
        the variable and, every time the file is finished being analysed, it is decreased 
        again (in checkMal()). This prevents out-of-order analysis.
        '''
        self._preform_post_analysis += 1 

        include_file = ctx.STRING().getText()
        if include_file in self._include_stack:
            logging.error(self._error)
            self._error = True
        self._include_stack.append(ctx.STRING().getText())

    def checkDefine(self, ctx: malParser.DefineContext, data: Tuple[str, dict]) -> None:
        '''
        Given a new define, verify if it has been previously defined
        '''
        _, obj = data
        key, value = list(obj.items())[0]
        
        # ID and version can be defined multiple times
        if(key!='id' and key!='version' and key in self._defines.keys()):
            prev_define_line = self._defines[key]['ctx'].start.line
            logging.error(f'Define \'{key}\' previously defined at line {prev_define_line}')
            self._error = True
            return 
        
        self._defines[key] = {'ctx': ctx, 'value': value}
    
    def checkCategory(self, ctx: malParser.CategoryContext, data: Tuple[str, Tuple[List, Any]]) -> None:
        '''
        Given a category, verify if it has a name and if contains metadata or assets
        '''
        _, [[category], assets] = data

        # TODO: is this really needed? doesn't the grammar prevent this?
        if(str(category['name']) == '<missing <INVALID>>'):
            category_line = ctx.start.line
            logging.error(f'Category has no name at line {category_line}')
            self._error = True
            return 

        if len(category['meta']) == 0 and len(assets) == 0:
            logging.warning(f'Category \'{category["name"]}\' contains no assets or metadata')
        
        self._category[category['name']] = {'ctx': ctx, 'obj': {'category': category, 'assets': assets}}

    def checkAsset(self, ctx: malParser.AssetContext, asset: dict) -> None:
        '''
        Given an asset, verify if it has been previously defined in the same category
        '''
        asset_name = asset['name']
        category_name = ctx.parentCtx.ID().getText()

        if (not asset_name or asset_name == '<missing <INVALID>>'):
            logging.error(f"Asset was defined without a name at line {ctx.start.line}")
            self._error = True
            return

        # Check if asset was previously defined // in same category.
        if asset_name in self._assets.keys(): # and str(self._assets[asset_name]['parent']['name']) == str(category_name):
            prev_asset_line = self._assets[asset_name]['ctx'].start.line
            error_msg = f"Asset '{asset_name}' previously defined at {prev_asset_line}"
            logging.error(error_msg)
            self._error = True
            raise(malAnalyzerException(error_msg))
            return
        else:
            self._assets[asset_name] = {'ctx': ctx, 'obj': asset, 'parent': {'name': ctx.parentCtx.ID().getText() ,'ctx': ctx.parentCtx}}

    def checkMeta(self, ctx: malParser.MetaContext, data: Tuple[Tuple[str, str],]) -> None:
        '''
        Given a meta, verify if it was previously defined for the same type (category, asset, step or association)
        '''
        ((meta_name, _),) = data

        # Check if we don't have the metas for this parent (category, asset, step or association)
        if ctx.parentCtx not in self._metas.keys():
            self._metas[ctx.parentCtx] = {meta_name:ctx}
        # Check if the new meta is not already defined
        elif ctx.parentCtx in self._metas.keys() and meta_name not in self._metas[ctx.parentCtx]:
            self._metas[ctx.parentCtx][meta_name] = ctx
        # Otherwise, throw error
        else:
            prev_ctx = self._metas[ctx.parentCtx][meta_name]
            error_msg = f'Metadata {meta_name} previously defined at {prev_ctx.start.line}'
            logging.error(error_msg)
            raise malAnalyzerException(error_msg)

    def _get_parents(self, ctx: malParser.AssetContext) -> List[dict[str, malParser.AssetContext]]:
        '''
        Given an asset, obtain its parents in inverse order.
        I.e., A->B->C returns [C,B,A] for asset A
        '''
        parents = [ctx.ID()[0].getText()]
        while ctx.EXTENDS():
            parent_name = ctx.ID()[1].getText()
            if parent_name in parents:
                break
            parents.insert(0, parent_name) 
            ctx = self._assets[parent_name]['ctx']
        return parents

    def _analyse_steps(self) -> None:
        '''
        For each asset, obtain its parents and analyse each step
        '''
        for asset in self._assets.keys():
            parents = self._get_parents(self._assets[asset]['ctx'])
            self._read_steps(asset, parents)
    
    def _attackStep_seen_in_parent(self, attackStep: str, seen_steps: List) -> str:
        '''
        Given a list of parent scopes, verify if the attackStep has been defined
        '''
        for parent, parent_scope in seen_steps:
            if attackStep in parent_scope:
                return parent
        return None 

    def _read_steps(self, asset: str, parents: List) -> None:
        '''
        For an asset, check if every step is properly defined in accordance to its hierarchy, i.e. if any of the asset's parents 
        also defines this step
        '''

        seen_steps = []
        for parent in parents:
            # If this parent has no steps, skip it
            if parent not in self._steps.keys():
                continue

            current_steps = []
            for attackStep in self._steps[parent].keys():
                # Verify if attackStep has not been defined in the current asset
                if attackStep not in current_steps:
                    # Verify if attackStep has not been defined in any parent asset
                    prevDef_parent = self._attackStep_seen_in_parent(attackStep, seen_steps)
                    if not prevDef_parent:
                        # Since this attackStep has never been defined, it must either not reach or reach with '->'
                        attackStep_ctx = self._steps[parent][attackStep]['ctx']
                        if (not attackStep_ctx.reaches() or attackStep_ctx.reaches().getChild(0).getText()=='->'):
                            # Valid step
                            current_steps.append(attackStep)
                        else:
                            # Step was defined using '+>', but there is nothing to inherit from
                            logging.error(f'Cannot inherit attack step \'{attackStep}\' without previous definition')
                            self._error = True
                    else:
                        # Step was previously defined in a parent
                        # So it must be of the same type (&, |, #, E, !E)
                        attackStep_ctx = self._steps[parent][attackStep]['ctx']
                        parent_attackStep_ctx = self._steps[prevDef_parent][attackStep]['ctx']
                        if attackStep_ctx.steptype().getText()==parent_attackStep_ctx.steptype().getText():
                            # Valid step
                            current_steps.append(attackStep)
                        else:
                            # Invalid, type mismatches that of parent
                            logging.error((f"Cannot override attack step \'{attackStep}\' previously defined "
                                f"at {parent_attackStep_ctx.start.line} with different type \'{attackStep_ctx.steptype().getText()}\' "
                                f"=/= \'{parent_attackStep_ctx.steptype().getText()}\'"))
                            self._error = True
                else:
                    # Step already defined in this asset
                    logging.error(f'Attack step \'{attackStep}\' previously defined at {self._steps[parent][attackStep]['ctx'].start.line}')
                    self._error = True

            seen_steps.append((parent,current_steps))

        for parent, steps in seen_steps:
            for step in steps:
                if asset not in self._steps.keys():
                    self._steps[asset] = {step: self._steps[parent][step]}
                else:
                    self._steps[asset][step] = self._steps[parent][step]
                
    def checkStep(self, ctx: malParser.StepContext, step: dict) -> None:
        '''
        Given a step, check if it is already defined in the current asset. Otherwise, add it to the list of 
        steps related to this asset
        '''
        step_name = step['name']
        asset_name = ctx.parentCtx.ID()[0].getText()   

        # Check if asset has no steps
        if not asset_name in self._steps.keys():
            self._steps[asset_name] = {step_name: {'ctx': ctx, 'step': step}}
        # If so, check if the there is no step with this name in the current asset
        elif not step_name in self._steps[asset_name].keys():
            self._steps[asset_name][step_name] = {'ctx': ctx, 'step': step}
        # Otherwise, log error
        else:
            prev_ctx = self._steps[asset_name][step_name]['ctx']
            logging.error(f'Attack step \'{step_name}\' previously defined at {prev_ctx.start.line}')
            self._error = True

        self._validate_CIA(ctx, step)
        self._validate_TTC(ctx, asset_name, step)

    def checkReaches(self, ctx: malParser.ReachesContext, data: dict) -> None:
        pass

    def _validate_TTC(self, ctx: malParser.StepContext, asset_name, step: dict) -> None:
        if not step['ttc']:
            return
        match step['type']:
            case  'defense':
                if (step['ttc']['type'] != 'function'):
                    logging.error(f'Defense {asset_name}.{step["name"]} may not have advanced TTC expressions')
                    self._error = True
                    return
                
                match step['ttc']['name']:
                    case 'Enabled' | 'Disabled' | 'Bernoulli':
                        #   try/catch Distributions.validate(name, params)
                        return
                    case _:
                        logging.error(f'Defense {asset_name}.{step["name"]} may only have \'Enabled\', \'Disabled\', or \'Bernoulli(p)\' as TTC')
                        self._error = True
                        return
            case 'exist' | 'notExist':
                pass
            case _:
                self._check_TTC_expr(step['ttc'])
        
    def _check_TTC_expr(self, expr, isSubDivExp = False):
        match expr['type']:
            case 'function':
                if (expr['name'] == 'Enabled' or expr['name'] == 'Disabled'):
                    logging.error('Distributions \'Enabled\' or \'Disabled\' may not be used as TTC values in \'&\' and \'|\' attack steps')
                    self._error = True
                    return
                if (isSubDivExp and expr['name'] in ['Bernoulli', 'EasyAndUncertain']):
                    logging.error(f'TTC distribution \'{expr["name"]}\' is not available in subtraction, division or exponential expressions.')
                    self._error = True
                    return
                # try/catch  Distributions.validate(name, params)
            case  'subtraction' | 'exponentiation' | 'division':
                self._check_TTC_expr(expr['lhs'], True)
                self._check_TTC_expr(expr['rhs'], True)
            case 'multiplication' | 'addition':
                self._check_TTC_expr(expr['lhs'], False)
                self._check_TTC_expr(expr['rhs'], False)
            case 'number':
                pass
            case _:
                logging.error(f'Unexpected expression {expr}')
                self._error = True
                # exit(1)


    def _validate_CIA(self, ctx: malParser.StepContext, step: dict) -> None:
        '''
        Given a step, check if it has CIAs. In that case, verify if the step is not of type
        defense and that it does not have repeated CIAs.
        '''
        if not ctx.cias():
            return
        
        step_name = step['name']
        asset_name = ctx.parentCtx.ID()[0].getText() 

        if (step['type'] == 'defense' or step['type'] == 'exist' or step['type'] == 'notExist'):
            logging.error(f'{step_name}: Defenses cannot have CIA classifications')
            self._error = True
            return

        index = 0
        cias = []
        while (cia := ctx.cias().getChild(index)):
            if(isinstance(cia, malParser.CiaContext)):
                letter = ''
                letter = 'C' if cia.C() else letter
                letter = 'I' if cia.I() else letter
                letter = 'A' if cia.A() else letter
                
                if (letter in cias):
                    logging.warning(f'Attack step {asset_name}.{step_name} contains duplicate classification {letter}')
                    self._warn = True
                    return
                cias.append(letter)
            index += 1

    def checkVariable(self, ctx: malParser.VariableContext, var: dict) -> None:
        '''
        This checks if the variable has been defined in the current asset.

        self._vars = {
            <asset-name>: {
                <var-name>: {'ctx': <var-ctx>, 'var' <var-dict>}
            }
        }
        '''
        parent = ctx.parentCtx
        if (isinstance(parent, malParser.AssetContext)):
            asset_name: str = str(parent.ID()[0].getText())
            var_name: str = var['name']
            if (asset_name not in self._vars.keys()):
                self._vars[asset_name] = {var_name: {'ctx': ctx, 'var': var}} 
            elif (var_name not in self._vars[asset_name]):
                self._vars[asset_name][var_name] = {'ctx': ctx, 'var': var}
            else: 
                prev_define_line = self._vars[asset_name][var_name]['ctx'].start.line
                error_msg = f'Variable \'{var_name}\' previously defined at line {prev_define_line}'
                logging.error(error_msg)
                raise malAnalyzerException(error_msg)

    def checkAssociation(self, ctx: malParser.AssociationContext, association: dict):
        self._all_associations.append({'name': association['name'], 'association': association,'ctx':ctx})