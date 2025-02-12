from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different if steps respect the hierarchy of the assets, namely when using '+>'
'''

import os

def test_steps_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | guessPassword
            +> authenticate
            | stealPassword
            -> authenticate
        } 
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_steps_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines a step with '+>' when there isn't parent asset with that step
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Linux
        {
        | spyware
            +> readBashHistory
        & readBashHistory
        }
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux']
    )

def test_steps_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines a step with '+>' when there is another asset with that step but it isn't extended
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
            -> logKeystrokes
        | logKeystrokes
        }

        asset Linux
        {
        | spyware
            +> readBashHistory
        & readBashHistory
        }
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_4() -> None:
    '''
    Define two assets which do not extend a parent and have steps without '+>'
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
        }

        asset Linux
        {
        & logIn
          -> access
        & access
        }
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_5() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (&)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        & spyware
        }

        asset Linux extends OperatingSystem
        {
        | spyware
        }
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_6() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (|)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
        }

        asset Linux extends OperatingSystem
        {
        & spyware
        }
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_7() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (E)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        E compromiseCamera
         <- camera 
        }

        asset ThinkPad extends Computer
        {
        !E compromiseCamera
          <- camera
        }

        asset Camera {
        | turnOn
        }
    } 

    Computer [computer] 1 <-- CameraUsage --> 1 [camera] Camera
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'ThinkPad','Camera']
    )

def test_steps_8() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (!E)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
        !E noCamera
         <- camera 
        }

        asset ThinkPad extends Computer
        {
        E noCamera
          <- camera
        }

        asset Camera {
        | turnOn
        }
    } 

    Computer [computer] 1 <-- CameraUsage --> 1 [camera] Camera
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'ThinkPad','Camera']
    )

def test_steps_9() -> None:
    '''
    Test '+>' in a longer hierarchy
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
      asset Machine {
        | compromise
      }
      
      asset Computer extends Machine {
        | stealCredentials
      }

      asset Thinkpad extends Computer {
        | compromise
          +> shutDown
        & shutDown
      }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_10() -> None:
    '''
    Test wrong type of extend step in a longer hierarchy
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
      asset Machine {
        | compromise
      }
      
      asset Computer extends Machine {
        | stealCredentials
      }

      asset Thinkpad extends Computer {
        & compromise
          +> shutDown
        & shutDown
      }
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_11() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Tests if two steps with the same names in different assets with different types does not throw error
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
        }

        asset Linux
        {
        & spyware
        }
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_12() -> None:
    '''
    Test if '+>' works if the extended asset is in another file
    '''
    path1 = "./generated_test_mal1.mal"
    with open(path1, 'w') as file:
        file.write('''
        category System {
            asset Machine {
            | compromise
            }
        } 
        ''')

    path2 = "./generated_test_mal2.mal"
    with open(path2, 'w') as file:
        file.write('''
        include "'''+path1+'''"
        category System {
            asset Computer extends Machine {
            & logKeyStrokes
            }
        } 
        ''')

    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    include "'''+path2+'''"
                        
    category System {
        asset Thinkpad extends Computer {
        | compromise
          +> logIn
        & logIn
        }
    } 
                           
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

    if os.path.exists(path1):
        os.remove(path1)
    if os.path.exists(path2):
        os.remove(path2)

def test_steps_13() -> None:
    '''
    Test if mismatched step types works if the extended asset is in another file
    '''
    path1 = "./generated_test_mal1.mal"
    with open(path1, 'w') as file:
        file.write('''
        category System {
            asset Machine {
            | compromise
            }
        } 
        ''')

    path2 = "./generated_test_mal2.mal"
    with open(path2, 'w') as file:
        file.write('''
        include "'''+path1+'''"
        category System {
            asset Computer extends Machine {
            & logKeyStrokes
            }
        } 
        ''')

    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    include "'''+path2+'''"
                        
    category System {
        asset Thinkpad extends Computer {
        & compromise
          +> logIn
        & logIn
        }
    } 
                           
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

    if os.path.exists(path1):
        os.remove(path1)
    if os.path.exists(path2):
        os.remove(path2)

def test_steps_14() -> None:
    '''
    Test inherit parent steps
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    

    category System {          
        asset Asset1 {
            | step1
        }

        asset Asset2 extends Asset1 {
            | step2
        }

        asset Asset3 extends Asset2 {
            | step3
        }

        asset Asset4 extends Asset3 {
            | step4
        }
    } 
                        
    associations 
    {
    }  
                           
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1', 'Asset2', 'Asset3', 'Asset4'],
        steps = [('Asset1',['step1']), ('Asset2',['step1','step2']), (
            'Asset3', ['step1','step2','step3']), ('Asset4',['step1','step2','step3','step4'])]
    )

def test_steps_15() -> None:
    '''
    A complex example which should work
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    

    category System {          
        asset Linux {
            E hasCamera
            <- hardware[Camera]
            -> hijackCamera
            | hijackCamera
        }
        asset Camera {
            | photo
        }
    } 
                        
    associations 
    {
        Linux [linux] * <-- L --> * [hardware] Camera
    }  
                           
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'Camera']
    )