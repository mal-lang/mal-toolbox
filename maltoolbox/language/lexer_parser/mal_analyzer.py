from .mal_parser import malParser
from .mal_visitor import malVisitor

import logging
import re
    
class malAnalyzer(malVisitor):
    '''
    A class to preform syntax-checks for MAL.
    '''
        
    def __init__(self, *args, **kwargs) -> None:
        self._error:   bool = False
        self._defines: dict = {}
        self._assets: dict = {}
        self._category: dict = {}
        self._metas: dict = {}
        self._steps: dict = {}
        super().__init__(*args, **kwargs)

    def is_valid(self) -> bool:
        return self._error

    def __post_analysis(self) -> None:
        '''
        Perform a post-analysis to confirm that the 
        mandatory fields and relations are met.
        '''
        self.__analyse_defines()
        self.__analyse_extends()
        self.__analyse_abstract()
        self.__analyse_parents()
    
    def __analyse_defines(self) -> None:
        '''
        Check for mandatory defines: ID & Version
        '''

        if 'id' in  self._defines.keys():
            define_value: str = self._defines['id']['obj']['id']
            if(len(define_value) == 0):
                logging.error('Define \'id\' cannot be empty')
                self._error = True
        else:
            logging.error('Missing required define \'#id: ""\'')
            self._error = True

        if 'version' in self._defines:
            version: str = self._defines['version']['obj']['version']
            if not re.match(r"\d+\.\d+\.\d+", version):
                logging.error(f'Define \'version\' must be valid semantic versioning without pre-release identifier and build metadata')
                self._error = True
        else:
            logging.error('Missing required define \'#version: ""\'')
            self._error = True

    def __analyse_extends(self) -> None:
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

    def __analyse_abstract(self) -> None:
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
    
    def __analyse_parents(self) -> None:
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
                parent_ctx = self.__get_assets_extendee(parent_ctx)
        if error:
            self._error = True
            raise
    
    def __get_assets_extendee(self, ctx: malParser.AssetContext) -> malParser.AssetContext:
        if (ctx.EXTENDS()):
            return self._assets[ctx.ID()[1].getText()]['ctx']
        return None
    
    def visitMal(self, ctx: malParser.MalContext) -> None:
        result = super().visitMal(ctx)
        self.__post_analysis()
        return result

    def visitDefine(self, ctx: malParser.DefineContext) -> None:
        result = super().visitDefine(ctx)
        [_, obj] = result

        if(len(obj.keys()) != 1):
            raise 
        
        define_id = next(iter(obj))
        if(define_id in self._defines.keys()):
            prev_define_line = self._defines[define_id]['ctx'].start.line
            logging.error(f'Define \'{define_id}\' previously defined at line {prev_define_line}')
            self._error = True
            return result
        
        self._defines[define_id] = {'ctx': ctx, 'obj': obj}
        return result
    
    def visitCategory(self, ctx: malParser.CategoryContext) -> None:
        result = super().visitCategory(ctx)

        category = result[1][0][0]
        if(category['name'] == '<missing <INVALID>>'):
            category_line = ctx.start.line
            logging.error(f'Category has no name at line {category_line}')
            self._error = True
            return result

        if len(category['meta']) == 0 and len(result[1][1]) == 0:
            logging.warning(f'Category \'{category["name"]}\' contains no assets or metadata')
            self._error = True
            return result
        
        self._category[category['name']] = {'ctx': ctx, 'obj': result}
        
        return result
        
    def visitAsset(self, ctx: malParser.AssetContext) -> None:
        result = super().visitAsset(ctx)
        asset_name = result['name']
        category_name = ctx.parentCtx.ID()

        # Check if asset was previously defined in same category.
        if asset_name in self._assets.keys() and self._assets[asset_name]['parent']['name'] == category_name:
            prev_asset_line = self._assets[asset_name]['ctx'].start.line
            logging.error(f"Asset '{asset_name}' previously defined at {prev_asset_line}")
            self._error = True
            return result
        else:
            self._assets[asset_name] = {'ctx': ctx, 'obj': result, 'parent': {'name': ctx.parentCtx.ID() ,'ctx': ctx.parentCtx}}
        return result

    def visitMeta(self, ctx: malParser.MetaContext) -> None:
        result = super().visitMeta(ctx)
        meta_name = result[0][0]
        parent_name = ''
        location_name = ''

        # Finding metadata type
        if isinstance(ctx.parentCtx, malParser.CategoryContext):
            parent_name = ctx.parentCtx.ID()
            location_name = 'category'
        elif isinstance(ctx.parentCtx, malParser.AssetContext):
            parent_name = ctx.parentCtx.ID()[0]
            location_name = 'asset'
        elif isinstance(ctx.parentCtx, malParser.StepContext):
            parent_name = ctx.parentCtx.ID()
            location_name = 'step'
        
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

        # TODO: check for Associations
            
        return result


    def visitStep(self, ctx: malParser.StepContext):
        step = super().visitStep(ctx)
        step_name = step['name']

        if isinstance(ctx.parentCtx, malParser.AssetContext):
            asset_name = ctx.parentCtx.ID()[0]   

            # TODO: Validate step
            # if (not asset_name in self._steps.keys()):
            #     self._steps[asset_name] = {step_name: ctx}
            self._validate_CIA(ctx, step)
            self._validate_TTC(ctx, step)

        return step
    
    def _validate_TTC(self, ctx: malParser.StepContext, step):
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

    def visitTtcexpr(self, ctx: malParser.TtcexprContext):
       pass

    def _validate_CIA(self, ctx: malParser.StepContext, step):
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