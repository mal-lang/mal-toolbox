from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

# This file aims to test the call/substitution operator (A.X()) in MAL

def test_substitution_1() -> None:
    '''
    Test substitution correctly 
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network {
            let hostsOperatingSystems = hosts.operatingSystems
            | access
            -> hostsOperatingSystems().attack
        }

        asset Computer
        {
            | shutDown
        }

        asset OperatingSystem 
        {
            | attack
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [hosts] Computer
        Computer [computer] 1 <-- L --> * [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_2() -> None:
    '''
    Test substitution with a non existing variable 
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network {
            //                       COMMENTED
            //                           |
            //                           v
            // let hostsOperatingSystems = hosts.operatingSystems
            | access
            -> hostsOperatingSystems().attack
        }

        asset Computer
        {
            | shutDown
        }

        asset OperatingSystem 
        {
            | attack
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [hosts] Computer
        Computer [computer] 1 <-- L --> * [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_3() -> None:
    '''
    Test substitution with an existing variable, but forget to call it, i.e. do not use parenthesis
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network {
            let hostsOperatingSystems = hosts.operatingSystems
            | access
            -> hostsOperatingSystems.attack
        }

        asset Computer
        {
            | shutDown
        }

        asset OperatingSystem 
        {
            | attack
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [hosts] Computer
        Computer [computer] 1 <-- L --> * [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_4() -> None:
    '''
    Try to call a variable defined in the parent
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network {
            let hostsOperatingSystems = hosts.operatingSystems
            | access
        }

        asset SubNet extends Network {
            | accessParent
            -> hostsOperatingSystems().attack
        }

        asset Computer
        {
            | shutDown
        }

        asset OperatingSystem 
        {
            | attack
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [hosts] Computer
        Computer [computer] 1 <-- L --> * [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'SubNet', 'Computer', 'OperatingSystem']
    )

def test_substitution_5() -> None:
    '''
    Try to call a variable defined in a parent in a complex hierarchy
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Hardware {
            | overHeat
        }
        asset Machine {
            let hardwareComponents = components
            | access
        }

        asset Computer extends Machine {
            | turnOff
        }

        asset Lenovo extends Computer 
        {
            | shutDown
        }

        asset LenovoThinkPad extends Lenovo 
        {
            | attack
            -> hardwareComponents().overHeat
        }
    }
                        
    associations 
    {
        Machine [host] 1 <-- L --> * [components] Hardware
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Hardware', 'Machine', 'Computer', 'Lenovo', 'LenovoThinkPad']
    )

def test_substitution_5() -> None:
    '''
    Try to call a variable defined in another asset 
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Hardware {
            let physicalComponents = components
            | overHeat
        }
        
        asset PhysicalComponent {
            | destroy
        }

        asset Computer {
            | attack
            -> physicalComponents().destroy
        }
    }
                        
    associations 
    {
        Hardware [host] 1 <-- L --> * [components] PhysicalComponent
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Hardware', 'PhysicalComponent', 'Computer']
    )

def test_substitution_6() -> None:
    '''
    Try to call a variable defined in the child
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network {
            | accessChild
            -> hostsOperatingSystems().attack
        }

        asset SubNet extends Network {
            let hostsOperatingSystems = hosts.operatingSystems
            | acces
            -> hostsOperatingSystems(),attack 
        }

        asset Computer
        {
            | shutDown
        }

        asset OperatingSystem 
        {
            | attack
        }
    }
                        
    associations 
    {
        SubNet [network] 1 <-- L --> * [hosts] Computer
        Computer [computer] 1 <-- L --> * [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'SubNet', 'Computer', 'OperatingSystem']
    )