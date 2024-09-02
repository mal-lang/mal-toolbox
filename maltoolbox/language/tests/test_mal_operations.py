from .mal_analyzer_test_wrapper import AnalyzerTestWrapper



def test_operation_1() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] /\\ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windows].foundWindows
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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
    This test might be invalid.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] /\\ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windows].foundLinux
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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

def test_operation_3() -> None:
    '''
    This test might be invalid.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] /\\ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windowss].foundWindows
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
                        
    category Test {
        asset Policy {
        & satisfy @trace
        | calledByUser
            -> satisfy
        | calledByHost
            -> satisfy
        }

        asset User {
        let effectivePolicies = policies
        let policyReachableHosts = policies.hosts

        | compromise
            -> effectivePolicies.calledByUser,
            policyReachableHosts.connect
        }

        asset Host {
        let effectivePolicies = policies
        | connect
            -> effectivePolicies.calledByHost

        }
    }
    associations 
    {
        User [user] * <-- L --> * [policies] Policy
        Policy [policies] * <-- L --> * [hosts] Host
    }  
    ''').test(
        defines=['id', 'version'],
        categories=['Test'],
        assets=['Policy', 'User', 'Host']
    )

def test_operation_5() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] \\/ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windows].foundWindows
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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

def test_operation_6() -> None:
    '''
    This test might be invalid.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] \\/ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windows].foundLinux
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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

def test_operation_7() -> None:
    '''
    This test might be invalid.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        let allTargets = computers.operatingSystems[Windows] \\/ computers.operatingSystems[Linux]
        | findWindowsAndLinux
        -> allTargets[Windowss].foundWindows
        }

        abstract asset OperatingSystem 
        {}
        asset Windows extends OperatingSystem
        {
            | foundWindows @debug
        }
        asset Linux extends OperatingSystem
        {
            | foundLinux @debug
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
