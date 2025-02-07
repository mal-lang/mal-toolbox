from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `info` instruction in MAL.
'''

def test_asset_info_1() -> None:
    '''
    Defines asset with name.
    Defines random info. (this should be allowed as to not break previous custom metas)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
        random info: "Hello"
        {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_2() -> None:
    '''
    Defines asset with name.
    Defines random info twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
        random info: "Hello"
        random info: "Hello once more!"
        {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )


def test_asset_info_3() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_3() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
            random info: "Hello from the attack step once more"
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_4() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
            another_random info: "Hello from the attack step once more"
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_5() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
            another_random info: "Hello from the attack step once more"
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_6() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
      random info: "This is a repetition"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
            another_random info: "Hello from the attack step once more"
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_7() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
      another_random info: "This is more"
    {
        asset Foo
          random info: "Hello"
          another_random info: "Hello again"
        {
          | compromise
            random info: "Hello from the attack step"
            another_random info: "Hello from the attack step once more"
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_8() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category for two different categories.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }
    }
                                        
    category AnotherSystem 
      random info: "This is another category"
    {
        asset Bar
          random info: "Hello from another category"
        {
          | compromise
            random info: "Hello from another attack step"
        }
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_9() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and association
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }
    }
                                        
    category AnotherSystem 
      random info: "This is another category"
    {
        asset Bar
          random info: "Hello from another category"
        {
          | compromise
            random info: "Hello from another attack step"
        }
    }

    associations {
      Foo [foo] 1 <-- RandomAssociation --> 0 [bar] Bar 
        random info: "This is an association"
    }

    ''').test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_10() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and twice in the association
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }
    }
                                        
    category AnotherSystem 
      random info: "This is another category"
    {
        asset Bar
          random info: "Hello from another category"
        {
          | compromise
            random info: "Hello from another attack step"
        }
    }

    associations {
      Foo [foo] 1 <-- RandomAssociation --> 0 [bar] Bar 
        random info: "This is an association"
        random info: "This is another comment on association"
    }

    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_11() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and association
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }
    }
                                        
    category AnotherSystem 
      random info: "This is another category"
    {
        asset Bar
          random info: "Hello from another category"
        {
          | compromise
            random info: "Hello from another attack step"
        }
    }

    associations {
      Foo [foo] 1 <-- RandomAssociation --> 0 [bar] Bar 
        random info: "This is an association"
      Foo [foos] * <-- AnotherRandomAssociation --> * [bars] Bar 
        random info: "This is another association"
    }

    ''').test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_12() -> None:
    '''
    Defines asset with name.
    Defines random info in two assets in the same category.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          | compromise
            random info: "Hello from the attack step"
        }

        asset Bar
          random info: "Hello from Bar!"
        {
          | compromise
            random info: "Hello from Bar's attack step"
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo','Bar']
    )


def test_asset_info_12() -> None:
    '''
    Defines asset with name.
    Defines random info in two steps in the same asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
    {
        asset Foo
          random info: "Hello"
        {
          & compromise
            random info: "Hello from the attack step"
          | beforeCompromise
            random info: "Stepping stone to compromise"
            -> compromise
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_13() -> None:
    '''
    Defines asset with name.
    Defines random info in asset twice but with a different meta between them
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      random info: "This is a category"
      modeler info: "This is to trick"
      random info: "This is the same category"
    {
        asset Foo
          random info: "Hello"
        {
          & compromise
            random info: "Hello from the attack step"
          | beforeCompromise
            random info: "Stepping stone to compromise"
            -> compromise
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )