from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
File to test set operations (/\\ and \\/ and -)
'''

# TESTS FOR /\
def test_operation_1() -> None:
    '''
    Test /\\ correctly (used in variable)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = operatingSystems[Windows] /\\ operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets().attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_2() -> None:
    '''
    Test /\\ correctly (used directly in step)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        | findWindowsAndLinux
        -> (operatingSystems[Windows] /\\ operatingSystems[Linux]).attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_3() -> None:
    '''
    Test /\\ directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] /\\ computers.operatingSystems[Linux])
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_4() -> None:
    '''
    Test /\\ directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] /\\ computers.operatingSystems[Linux]).foundWindows
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_5() -> None:
    '''
    Test /\\ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let targets = windows /\\ linux
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows 
        {
            | attack
        }
        asset Linux 
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        error=True,
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )


def test_operation_6() -> None:
    '''
    Test /\\ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network
        {
            let allComputers = computers[ThinkPad] \\/ computers[Asus]
            | access
            -> allComputers().compromise
        }

        asset Machine {
            | compromise
        }

        asset Computer extends Machine {
        }

        asset ThinkPad extends Computer {
        }

        asset Asus extends Computer {
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [computers] Computer
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_7() -> None:
    '''
    Test /\\ directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | do
            -> (windows /\\ linux).softwareStep
        }

        abstract asset Software {
            | softwareStep
        }

        abstract asset OperatingSystem extends Software
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | attack
        }
        asset Linux extends OperatingSystem
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )






# Tests for \/
def test_operation_8() -> None:
    '''
    Test \\/ correctly (used in variable)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = operatingSystems[Windows] \\/ operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets().attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_9() -> None:
    '''
    Test \\/ correctly (used directly in step)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        | findWindowsAndLinux
        -> (operatingSystems[Windows] \\/ operatingSystems[Linux]).attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_10() -> None:
    '''
    Test \\/ directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] \\/ computers.operatingSystems[Linux])
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_11() -> None:
    '''
    Test \\/ directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] \\/ computers.operatingSystems[Linux]).foundWindows
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_12() -> None:
    '''
    Test \\/ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let targets = windows \\/ linux
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows 
        {
            | attack
        }
        asset Linux 
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        error=True,
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )


def test_operation_13() -> None:
    '''
    Test \\/ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network
        {
            let allComputers = computers[ThinkPad] \\/ computers[Asus]
            | access
            -> allComputers().compromise
        }

        asset Machine {
            | compromise
        }

        asset Computer extends Machine {
        }

        asset ThinkPad extends Computer {
        }

        asset Asus extends Computer {
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [computers] Computer
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_14() -> None:
    '''
    Test \\/ directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | do
            -> (windows \\/ linux).softwareStep
        }

        abstract asset Software {
            | softwareStep
        }

        abstract asset OperatingSystem extends Software
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | attack
        }
        asset Linux extends OperatingSystem
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )





# TESTS FOR -
def test_operation_15() -> None:
    '''
    Test - correctly (used in variable)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = operatingSystems[Windows] - operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets().attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_16() -> None:
    '''
    Test - correctly (used directly in step)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        | findWindowsAndLinux
        -> (operatingSystems[Windows] - operatingSystems[Linux]).attack
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_17() -> None:
    '''
    Test - directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] - computers.operatingSystems[Linux])
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_18() -> None:
    '''
    Test - directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | findWindowsAndLinux
            -> (computers.operatingSystems[Windows] - computers.operatingSystems[Linux]).foundWindows
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux 
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_19() -> None:
    '''
    Test - directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let targets = windows - linux
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows 
        {
            | attack
        }
        asset Linux 
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        error=True,
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )


def test_operation_20() -> None:
    '''
    Test - directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Network
        {
            let allComputers = computers[ThinkPad] - computers[Asus]
            | access
            -> allComputers().compromise
        }

        asset Machine {
            | compromise
        }

        asset Computer extends Machine {
        }

        asset ThinkPad extends Computer {
        }

        asset Asus extends Computer {
        }
    }
                        
    associations 
    {
        Network [network] 1 <-- L --> * [computers] Computer
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_21() -> None:
    '''
    Test - directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | do
            -> (windows - linux).softwareStep
        }

        abstract asset Software {
            | softwareStep
        }

        abstract asset OperatingSystem extends Software
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | attack
        }
        asset Linux extends OperatingSystem
        {
            | attack
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [linux] Linux
        Computer [computers] * <-- L --> 0..1 [windows] Windows
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )




# General functionality test
def test_operation_22() -> None:
    '''
    Test complex operation
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Main
        {
            | do
            -> (((grandchild \\/ child) /\\ parent) - grandparent).bigAttack
        }

        asset Generator {
            | bigAttack
        }

        asset Grandparent extends Generator {
            | attack
        }

        asset Parent extends Grandparent
        {
            | attack
        }
        asset Child extends Parent
        {
            | attack
        }
        asset Grandchild extends Child
        {
            | attack
        }
    }
                        
    associations 
    {
        Main [host] * <-- L --> 0..1 [grandparent]  Grandparent
        Main [host1] * <-- L --> 0..1 [parent]      Parent
        Main [host2] * <-- L --> 0..1 [child]       Child 
        Main [host3] * <-- L --> 0..1 [grandchild]  Grandchild
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Main','Generator','Grandparent','Parent','Child','Grandchild']
    )