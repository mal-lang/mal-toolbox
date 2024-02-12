from antlr4 import ParseTreeVisitor
from .mal_parser import malParser

from dataclasses import dataclass
import logging
import re
    
class malAnalyzer(ParseTreeVisitor):
    '''
    A class to preform syntax-checks for MAL.
    '''

    class Analyze:
        '''
        A decoration to insert `super().<visit-method>(...)` in child.
        If `malAnalyzer` haven't implemented that method an error message
        will occur and a raise.
        '''
        def __init__(self, func):
            self.func = func

        def __get__(self, instance, owner):
            def wrapper(*args, **kwargs):
                super_method = getattr(super(owner, instance), self.func.__name__, None)
                # Check if method is implemented.
                if super_method:
                    super_method(*args, **kwargs)
                else:
                    logging.error(f'There is no analyzer implemented for \'{self.func.__name__}\'')
                    raise

                return self.func(instance, *args, **kwargs)
            return wrapper
        
    @dataclass
    class ContextWrapper():
        '''
        A wrapper to store context 
        for post-analysis.
        '''
        name: str
        ctx: any
        def __str__(self) -> str:
            return self.name
    
    @dataclass
    class AssetWrapper(ContextWrapper):
        '''
        A wrapper to store assets.
        '''
        attack_steps: [malParser.StepContext]
        
    def __init__(self, *args, **kwargs) -> None:
        self._error:   bool = False
        self._defines: dict[str, self.ContextWrapper] = {}
        self._assets:  dict[str, self.AssetWrapper  ] = {}
        self._metas:   dict[str, self.ContextWrapper] = {}

        super().__init__(*args, **kwargs)

    def visit(self, ctx: malParser.MalContext) -> any:
        '''
        Override ParseTreeVisitor `visit` to be able
        to preform `__post_analysis` as last step.
        '''
        result: any = super().visit(ctx)
        if ctx.depth() == 1:
            self.__post_analysis()
        return result

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
        self.__analyse_steps()

    
    def __analyse_defines(self) -> None:
        '''
        Check for mandatory defines: ID & Version
        '''

        if 'id' in  self._defines:
            value: str = self._defines['id'].ctx.STRING().getText()[1:-1]
            if(len(value.strip()) == 0):
                logging.error('Define \'id\' cannot be empty')
                self._error = True
        else:
            logging.error('Missing required define \'#id: ""\'')
            self._error = True

        if 'version' in self._defines:
            version: str = self._defines['version'].ctx.STRING().getText()[1:-1]
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
            asset_context: malParser.AssetContext = self._assets[asset].ctx
            if(asset_context.EXTENDS()):
                extend_asset_name = asset_context.getChild(3).getText()
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
            parent_ctx: malParser.AssetContext = self._assets[parent].ctx
            print(parent_ctx.ID()[0].getText())
            if(parent_ctx.ABSTRACT()):
                found: bool = False
                for extendee in self._assets:
                    '''
                    Add same parent check?
                    '''
                    extendee_ctx: malParser.AssetContext = self._assets[extendee].ctx
                    if(extendee_ctx.EXTENDS() and extendee_ctx.ID()[1].getText() == parent_ctx.ID()[0].getText()):
                        found = True
                        break
                if not found:
                    logging.warn(f'Asset \'{parent_ctx.ID()[0].getText()}\' is abstract but never extended to')
    
    def __analyse_parents(self) -> None:
        error: bool = False
        for asset in self._assets:
            parents: list[str] = []
            parent_ctx: malParser.AssetContext  = self._assets[asset].ctx
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
    
    def __analyse_steps(self):
        logging.warning('__analyse_steps not implemented.')
        # for asset in self._assets:
        #     pass

    def __get_assets_extendee(self, ctx: malParser.AssetContext) -> malParser.AssetContext:
        if (ctx.EXTENDS()):
            return self._assets[ctx.ID()[1].getText()].ctx
        return None

    def visitDefine(self, ctx: malParser.DefineContext) -> None:
        define_id: str = ctx.ID().getText()

        # Check if define was previously defined.
        if define_id in self._defines:
            prevDef = self._defines[define_id].ctx.start.line
            logging.error(f'Define \'{define_id}\' previously defined at {prevDef}')
            self._error = True
            return
        
        self._defines[define_id] = self.ContextWrapper(ctx=ctx, name=define_id)  

    def visitCategory(self, ctx: malParser.CategoryContext) -> None:
        category_name: str = ctx.ID().getText()
        if (len(ctx.asset()) == 0 and len(ctx.meta()) == 0):
            logging.error(f'Category \'{category_name}\' contains no assets or metadata')
            self._error = True
            return
        
    def visitAsset(self, ctx: malParser.AssetContext) -> None:
        asset_id: str = ctx.ID()[0].getText()

        '''
        # Is this possible to check?
        category: malParser.CategoryContext = ctx.parentCtx
        if not category: 
            logging.error(f'Asset \'{asset_id}\' is outside an category')
        '''

        # Check if asset was previously defined.
        if asset_id in self._assets:
            prevDef = self._assets[asset_id].ctx.start.line
            logging.error(f"Asset '{asset_id}' previously defined at {prevDef}")
            self._error = True
            return
        else:
            self._assets[asset_id] = self.AssetWrapper(ctx=ctx, name=asset_id, attack_steps=[]) 

    def visitMeta(self, ctx: malParser.MetaContext) -> None:
        meta_id: str = ctx.ID().getText()
      
        # Check if meta was previously defined.
        if meta_id in self._metas:
            prevDef = self._metas[meta_id].ctx.start.line
            logging.error(f"Metadata '{meta_id}' previously defined at {prevDef}")
            self._error = True
            return
        else:
            self._metas[meta_id] = self.ContextWrapper(ctx=ctx, name=meta_id) 

    def visitStep(self, ctx: malParser.StepContext) -> None:
        logging.warn('visitStep not implemented.')
        # step_id: str = ctx.ID().getText()
        # parent_asset_name = ctx.parentCtx.ID()[0].getText()
        # if  parent_asset_name in self._assets:
        #     logging.error(f'Asset \'{parent_asset_name}\' was not found.')
        #     self._error = True
        #     return
        
        # parent_asset: self.AssetWrapper = self._assets[parent_asset_name]
        # Can a step be define twice?
        # parent_asset.attack_steps.append(ctx)  
