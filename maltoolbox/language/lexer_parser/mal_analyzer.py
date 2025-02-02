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

class malAnalyzer(malAnalyzerInterface):
    '''
    A class to preform syntax-checks for MAL.
    '''
        
    def __init__(self, *args, **kwargs) -> None:
        self._error: bool = False
        self._preform_post_analysis = True

        self._defines: dict     = {}
        self._assets: dict      = {}
        self._category: dict    = {}
        self._metas: dict       = {}
        self._steps: dict       = {}
        self._vars: dict        = {}

        self._associations      = []

        super().__init__(*args, **kwargs)
        
    def has_error(self) -> bool:
        return self._error

    def _post_analysis(self) -> None:
        '''
        Perform a post-analysis to confirm that the 
        mandatory fields and relations are met.
        '''
        self._analyse_defines()
        self._analyse_extends()
        self._analyse_abstract()
        self._analyse_parents()
        self._analyse_reaches()
        self._analyse_association()
    
    def _analyse_defines(self) -> None:
        '''
        Check for mandatory defines: ID & Version
        Verify no repeated defines
        '''
        seen = []
        for define in self._defines.keys():
            if define in seen:
                logging.error("Define '%s' previously defined", define)
                self._error = True
            seen.append(define)

        if 'id' in self._defines.keys():
            define_value: str = self._defines['id']['value']
            if (len(define_value) == 0):
                logging.error('Define \'id\' cannot be empty')
                self._error = True
        else:
            logging.error('Missing required define \'#id: ""\'')
            self._error = True

        if 'version' in self._defines.keys():
            version: str = self._defines['version']['value']
            if not re.match(r"\d+\.\d+\.\d+", version):
                logging.error(f'Define \'version\' must be valid semantic versioning without pre-release identifier and build metadata')
                self._error = True
        else:
            logging.error('Missing required define \'#version: ""\'')
            self._error = True

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
                    logging.error(f'Asset \'{extend_asset_name}\' not defined')
                    raise_error = True
        if raise_error:
            self._error = True   # Maybe unnecessary if we raise
            raise SyntaxError(f'Asset \'{extend_asset_name}\' not defined')

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
                    err_msg: str = ' -> '.join(parents)
                    err_msg += f' -> {parent_name}' 
                    logging.error(f'Asset \'{parent_name}\' extends in loop \'{err_msg}\'')
                    self._error = True
                    break
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
                    for attackStep in self._assets[asset]['obj']['attackSteps']:
                        if (attackStep['name'] == expr['name']):
                            return attackStep
                        
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
        for association in self._associations:
            if (expr['name'] == association['leftField']):
                if (self._get_asset_name(association['leftAsset'])):
                    return association['leftAsset']
            if (expr['name'] == association['rightField']):
                if (self._get_asset_name(association['rightAsset'])):
                    return association['rightAsset']

        # Verify if there is a variable defined with the same name; possible the user forgot to call it
        extra=""
        if (asset in self._vars.keys() and expr['name'] in self._vars[asset].keys()):
            extra=f', did you mean the variable \'{expr[name]}()\'?'
    
        logging.error(f'Field \'{expr["name"]}\' not defined for asset \'{asset}\'')
        return None
   
    def _check_variable_expr(self, asset, expr):
        '''
        Check if there is a variable reference in this asset with the used identifier.
        '''        
        if (asset in self._vars.keys() and expr['name'] in self._vars[asset].keys()):
            return self._check_to_asset(asset, self._vars[asset][expr['name']]['var']['stepExpression']) 

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
        
        logging.error(f'Types \'{lhs_target["name"]}\' and \'{rhs_target["name"]}\' have no common ancestor')
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
            if (self._is_child(res, asset)):
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
        for association in self._associations:
            leftAsset = association['leftAsset']
            rightAsset = association['rightAsset']

            if (not leftAsset in self._assets.keys()):
                logging.error(f'Left asset \'{leftAsset}\' is not defined')
                self._error = True
            if (not rightAsset in self._assets.keys()):
                logging.error(f'Right asset \'{leftAsset}\' is not defined')
                self._error = True

    def _get_assets_extendee(self, ctx: malParser.AssetContext) -> malParser.AssetContext:
        '''
        Verifies if the current asset extends another and, if so, return the parent's context
        '''
        if (ctx.EXTENDS()):
            return self._assets[ctx.ID()[1].getText()]['ctx']
        return None
    
    def checkMal(self, ctx: malParser.MalContext) -> None:
        '''
        We only want to preform _post_analysis as the very last step.
        '''
        if (self._preform_post_analysis):
            self._post_analysis()
        self._preform_post_analysis = True

    def checkInclude(self, ctx: malParser.MalContext, data: Tuple[str, str]) -> None:
        '''
        When an include is found, it triggers the analysis of a new MAL file. To prevent
        checkMal from being performed before all files have been analysed, we set the 
        variable to false and, every time the file is finished being analysed, it is set
        to True again (in checkMal()). This prevents out-of-order analysis.
        '''
        self._preform_post_analysis = False

    def checkDefine(self, ctx: malParser.DefineContext, data: Tuple[str, dict]) -> None:
        '''
        Given a new define, verify if it has been previously defined
        '''
        _, obj = data
        key, value = list(obj.items())[0]
        
        if(key in self._defines.keys()):
            prev_define_line = self._defines[key]['ctx'].start.line
            logging.error(f'Define \'{key}\' previously defined at line {prev_define_line}')
            self._error = True
            return 
        
        self._defines[key] = {'ctx': ctx, 'value': value}
    
    def checkCategory(self, ctx: malParser.CategoryContext, data: Tuple[str, Tuple[List, Any]]) -> None:
        _, [[category], assets] = data

        if(str(category['name']) == '<missing <INVALID>>'):
            category_line = ctx.start.line
            logging.error(f'Category has no name at line {category_line}')
            self._error = True
            return 

        if len(category['meta']) == 0 and len(assets) == 0:
            logging.warning(f'Category \'{category["name"]}\' contains no assets or metadata')
        
        self._category[category['name']] = {'ctx': ctx, 'obj': {'category': category, 'assets': assets}}

    def checkAsset(self, ctx: malParser.AssetContext, asset: dict) -> None:
        asset_name = asset['name']
        category_name = ctx.parentCtx.ID().getText()
        
        if (not asset_name or asset_name == '<missing <INVALID>>'):
            logging.error(f"Asset was defined without a name at line {ctx.start.line}")
            self._error = True
            return
        # Check if asset was previously defined in same category.
        if asset_name in self._assets.keys() and str(self._assets[asset_name]['parent']['name']) == str(category_name):
            prev_asset_line = self._assets[asset_name]['ctx'].start.line
            logging.error(f"Asset '{asset_name}' previously defined at {prev_asset_line}")
            self._error = True
            return
        else:
            self._assets[asset_name] = {'ctx': ctx, 'obj': asset, 'parent': {'name': ctx.parentCtx.ID().getText() ,'ctx': ctx.parentCtx}}

    def checkMeta(self, ctx: malParser.MetaContext, data: Tuple[Tuple[str, str],]) -> None:
        ((meta_name, _),) = data
        parent_name: str = ''
        location_name: str = ''

        # Finding metadata type
        if isinstance(ctx.parentCtx, malParser.CategoryContext):
            parent_name = str(ctx.parentCtx.ID().getText())
            location_name = 'category'
        elif isinstance(ctx.parentCtx, malParser.AssetContext):
            parent_name = str(ctx.parentCtx.ID()[0].getText())
            location_name = 'asset'
        elif isinstance(ctx.parentCtx, malParser.StepContext):
            parent_name = str(ctx.parentCtx.ID().getText())
            location_name = 'step'
        elif isinstance(ctx.parentCtx, malParser.AssociationContext):
            parent_name = str(ctx.parentCtx.ID()[0].getText())
            location_name = 'association'

        # Validate that the metadata is unique
        if not location_name in self._metas.keys():
            self._metas[location_name] = {parent_name: {meta_name: ctx}}
        elif not parent_name in self._metas[location_name].keys():
            self._metas[location_name][parent_name] = {meta_name: ctx}
        elif not meta_name in self._metas[location_name][parent_name].keys():
            self._metas[location_name][parent_name][meta_name] = ctx
        else:
            prev_ctx = self._metas[location_name][parent_name][meta_name]
            logging.error(f'Metadata {meta_name} previously defined at {prev_ctx.start.line}')
            self._error = True

    def checkStep(self, ctx: malParser.StepContext, step: dict) -> None:
        step_name = step['name']

        if isinstance(ctx.parentCtx, malParser.AssetContext):        
            asset_name = ctx.parentCtx.ID()[0].getText()   
            # Check if the step is defined in other assets.
            for other_asset_name in self._steps.keys():
                if (asset_name == other_asset_name):
                    continue
                if not (self._steps[other_asset_name] and step_name in self._steps[other_asset_name].keys()):
                    continue
                
                other_step = self._steps[other_asset_name][step_name]
                other_type = other_step['step']['type']
                current_type = step['type']
                if (other_type == current_type):
                    self._steps[asset_name] = {step_name: {'ctx': ctx, 'step': step}}
                    return
                
                prev_ctx = other_step['ctx']
                logging.error(f'Cannot override attack step \'{step_name}\' previously defined at {prev_ctx.start.line} with different type \'{current_type}\' =/= \'{other_type}\'')
                self._error = True
                return
            
            if ((step['reaches'] and not step['reaches']['overrides'])):
                logging.error(f'Cannot inherit attack step \'{step_name}\' without previous definition')
                self._error = True
                return

            # Check if the step is already defined in the parent asset.
            if not asset_name in self._steps.keys():
                self._steps[asset_name] = {step_name: {'ctx': ctx, 'step': step}}
            elif not step_name in self._steps[asset_name].keys():
                self._steps[asset_name][step_name] = {'ctx': ctx, 'step': step}
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
        while cia := ctx.cias().getChild(index):
            if(isinstance(cia, malParser.CiaContext)):
                letter = ''
                letter = 'C' if cia.C() else letter
                letter = 'I' if cia.I() else letter
                letter = 'A' if cia.A() else letter
                
                if (letter in cias):
                    logging.error(f'Attack step {asset_name}.{step_name} contains duplicate classification {letter}')
                    self._error = True
                    return
                cias.append(letter)
            index += 1

    def check(self, ctx: malParser.VariableContext, var: dict) -> None:
        '''
        self._vars = {
            <asset-name>: {
                <var-name>: <var-ctx>
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
                logging.error(f'Variable \'{var_name}\' previously defined at line {prev_define_line}')
                self._error = True
        else:
            # TODO
            raise 

    def checkAssociation(self, ctx: malParser.AssociationContext, association: dict):
        self._associations.append(association)