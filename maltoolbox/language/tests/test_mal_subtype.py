from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
File to test the subtype expression in MAL
'''
def test_subtype_1() -> None:
    '''
    Test subtype correctly (defined in variable)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let windowsOSes = operatingSystems[Windows]
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

def test_subtype_2() -> None:
    '''
    Test subtype correctly (defined in step)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | attack
            -> operatingSystems[Windows].foundWindows
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

def test_subtype_3() -> None:
    '''
    Test subtype without inheritance relationship (given X[A], a is not a child of X)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | attack
            -> operatingSystems[Windows].foundWindows
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        //        COMMENTED
        //            |
        //            v
        asset Windows // extends OperatingSystem
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

def test_subtype_4() -> None:
    '''
    Test subtype, but with a wrong attack step
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | attack
            -> operatingSystems[Windows].foundLinux
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

def test_subtype_5() -> None:
    '''
    Test subtype in a long hierarchy
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | attack
            -> operatingSystems[WindowsVistaProfessional].foundWindowsVistaProfessional
        }

        abstract asset OperatingSystem 
        {
            | attack
        }
        asset Windows extends OperatingSystem
        {
            | foundWindows 
        }
        asset WindowsVista extends Windows {
        }
        asset WindowsVistaProfessional extends WindowsVista {
            | foundWindowsVistaProfessional
        }
    }
                        
    associations 
    {
        Computer [computers] * <-- L --> 0..1 [operatingSystems] OperatingSystem
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'WindowsVista', 'WindowsVistaProfessional', 'OperatingSystem']
    )