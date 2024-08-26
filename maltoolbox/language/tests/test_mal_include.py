from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

import os

'''
A file to test different cases of the `include` instruction in MAL.
'''

def test_include_1() -> None:
    '''
    Missing keys ID and version.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('')
    AnalyzerTestWrapper(f'''
    include "{path}"                     
    ''').test(
        error=True
    )

    if os.path.exists(path):
        os.remove(path)

def test_include_2() -> None:
    '''
    Including file with ID and version.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #id: "org.mal-lang.testAnalyzer"
        #version:"0.0.0"
        ''')
    AnalyzerTestWrapper(f'''
    include "{path}"                     
    ''').test(
        defines=['id', 'version']
    )

    if os.path.exists(path):
        os.remove(path)

def test_include_3() -> None:
    '''
    Including file with ID and version.
    Defining ID and version both files.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #id: "org.mal-lang.testAnalyzer"
        #version:"0.0.0"
        ''')
    AnalyzerTestWrapper(f'''
    include "{path}" 
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"                    
    ''').test(
        error=True,
        defines=['id', 'version']
    )

    if os.path.exists(path):
        os.remove(path)
        
def test_include_4() -> None:
    '''
    Including file with ID and version.
    Defining key with value.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #id: "org.mal-lang.testAnalyzer"
        #version:"0.0.0"
        ''')
    AnalyzerTestWrapper(f'''
    include "{path}" 
    #key: "test"
    ''').test(
        defines=['id', 'version', 'key']
    )

    if os.path.exists(path):
        os.remove(path)

def test_include_5() -> None:
    '''
    Including one file with ID and another with version.
    Defining key with value.
    '''
    path_1 = "./generated_test_mal_1.mal"
    path_2 = "./generated_test_mal_2.mal"
    with open(path_1, 'w') as file:
        file.write('''
        #version:"0.0.0"
        ''')
    with open(path_2, 'w') as file:
        file.write('''
        #id: "org.mal-lang.testAnalyzer"
        ''')
    AnalyzerTestWrapper(f'''
    include "{path_1}" 
    include "{path_2}" 
    #key: "test"
    ''').test(
        defines=['id', 'version', 'key']
    )

    if os.path.exists(path_1):
        os.remove(path_1)
    if os.path.exists(path_2):
        os.remove(path_2)

def test_include_6() -> None:
    '''
    Include same file twice.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('')
    AnalyzerTestWrapper(f'''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
                        
    include "{path}"                     
    include "{path}"                     
    ''').test(    
        defines=['id', 'version']
    )

    if os.path.exists(path):
        os.remove(path)

def test_include_7() -> None:
    '''
    Defining keys ID and version after include.
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('')
    AnalyzerTestWrapper(f'''
    include "{path}"   

    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"                  
    ''').test(    
        defines=['id', 'version']
    )

    if os.path.exists(path):
        os.remove(path)