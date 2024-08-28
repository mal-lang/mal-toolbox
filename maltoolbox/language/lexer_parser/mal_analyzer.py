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
        '''

        if 'id' in  self._defines.keys():
            define_value: str = self._defines['id']['value']
            if (len(define_value) == 0):
                logging.error('Define \'id\' cannot be empty')
                self._error = True
        else:
            logging.error('Missing required define \'#id: ""\'')
            self._error = True

        if 'version' in self._defines:
            version: str = self._defines['version']['value']
            if not re.match(r"\d+\.\d+\.\d+", version):
                logging.error(f'Define \'version\' must be valid semantic versioning without pre-release identifier and build metadata')
                self._error = True
        else:
            logging.error('Missing required define \'#version: ""\'')
            self._error = True

    def _analyse_extends(self) -> None:
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
        for parent in self._assets:
            parent_ctx: malParser.AssetContext = self._assets[parent]['ctx']
            if(parent_ctx.ABSTRACT()):
                found: bool = False
                for extendee in self._assets:
                    '''
                    Add same parent check?
                    '''
                    extendee_ctx: malParser.AssetContext = self._assets[extendee]['ctx']
                    if(extendee_ctx.EXTENDS() and extendee_ctx.ID()[1].getText() == parent_ctx.ID()[0].getText()):
                        found = True
                        break
                if not found:
                    logging.warn(f'Asset \'{parent_ctx.ID()[0].getText()}\' is abstract but never extended to')
    
    def _analyse_parents(self) -> None:
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
                    error = True
                    break
                parents.append(parent_name)
                parent_ctx = self._get_assets_extendee(parent_ctx)
        if error:
            self._error = True
            raise

    def _analyse_reaches(self) -> None:
        for asset in self._assets.keys():
            attack_steps = self._assets[asset]['obj']['attackSteps']
            for attack_step in attack_steps:
                if (attack_step['type'] in ['exist', 'notExist']):
                    if (attack_step['ttc']):
                        logging.error(f'Attack step of type \'{attack_step["type"]}\' must not have TTC')
                        self._error = True
                        continue
                    if (attack_step['requires']):
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
                    for expr in attack_step['reaches']['stepExpressions']:
                        self._check_to_step(asset, expr)
                
        if (False):
            raise ''
        
    def _check_to_step(self, asset, expr) -> None:
        pass

    def _check_to_asset(self, asset, expr) -> None:
        match (expr['type']):
            case 'StepExpr':
                raise
            case 'IDExpr':
                raise
            case 'union' | 'intersection' | 'difference':
                return self._check_set_expr(asset, expr)
            case 'transitive':
                return self._check_transitive_expr(asset, expr)
            case 'subType':
                return self._check_sub_type_expr(asset, expr)
            case 'CallExpr':
                raise
            case _:
                logging.error(f'Unexpected expression \'{expr["type"]}\'')
                self._error = True
                # exit(1)
                return None
            
    def _check_set_expr(self, asset, expr) -> None:
        pass
    def _check_sub_type_expr(self, asset, expr) -> None:
        pass
    def _check_transitive_expr(self, asset, expr) -> None:
        pass

    def _analyse_association(self) -> None:
        for association in self._associations:
            leftAsset = association['leftAsset']
            rightAsset = association['rightAsset']

            if (not leftAsset in self._assets.keys()):
                logging.error(f'Left asset \'{leftAsset}\' is not defined')
                self._error = True
            if (not rightAsset in self._assets.keys()):
                logging.error(f'Right asset \'{leftAsset}\' is not defined')
                self._error = True
        if (self._error):
            raise

    def _get_assets_extendee(self, ctx: malParser.AssetContext) -> malParser.AssetContext:
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
        self._preform_post_analysis = False

    def checkDefine(self, ctx: malParser.DefineContext, data: Tuple[str, dict]) -> None:
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
        category_name = ctx.parentCtx.ID()
        
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
            self._assets[asset_name] = {'ctx': ctx, 'obj': asset, 'parent': {'name': ctx.parentCtx.ID() ,'ctx': ctx.parentCtx}}

    def checkMeta(self, ctx: malParser.MetaContext, data: Tuple[Tuple[str, str],]) -> None:
        ((meta_name, _),) = data
        parent_name: str = ''
        location_name: str = ''

        # Finding metadata type
        if isinstance(ctx.parentCtx, malParser.CategoryContext):
            parent_name = str(ctx.parentCtx.ID())
            location_name = 'category'
        elif isinstance(ctx.parentCtx, malParser.AssetContext):
            parent_name = str(ctx.parentCtx.ID()[0])
            location_name = 'asset'
        elif isinstance(ctx.parentCtx, malParser.StepContext):
            parent_name = str(ctx.parentCtx.ID())
            location_name = 'step'
        elif isinstance(ctx.parentCtx, malParser.AssociationContext):
            parent_name = str(ctx.parentCtx.ID())
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
            asset_name = ctx.parentCtx.ID()[0]   
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
            self._validate_TTC(ctx, step)

    def checkReaches(self, ctx: malParser.ReachesContext, data: dict) -> None:
        pass

    def _validate_TTC(self, ctx: malParser.StepContext, step: dict) -> None:
        if not step['ttc']:
            return
        
        if step['type'] == 'defense':
            # TODO: TTCFuncExpr
            # if !(ttc instanceof AST.TTCFuncExpr)
            #      error
            # elif fname = Enabled, Disabled, Bernoulli
            #   Distributions.validate(fname, fparams);
            # else 
            #    ERROR   Defense %s.%s may only have 'Enabled', 'Disabled', or 'Bernoulli(p)' as TTC"
            pass

    def _validate_CIA(self, ctx: malParser.StepContext, step: dict) -> None:
        if not ctx.cias():
            return
        
        step_name = step['name']
        asset_name = ctx.parentCtx.ID()[0] 

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

    def checkVariable(self, ctx: malParser.VariableContext, var: dict) -> None:
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
                self._vars[asset_name] = {var_name: ctx} 
            elif (var_name not in self._vars[asset_name]):
                self._vars[asset_name][var_name] = ctx
            else: 
                prev_define_line = self._vars[asset_name][var_name].start.line
                logging.error(f'Variable \'{var_name}\' previously defined at line {prev_define_line}')
                self._error = True
    
    def checkAssociation(self, ctx: malParser.AssociationContext, association: dict):
        self._associations.append(association)