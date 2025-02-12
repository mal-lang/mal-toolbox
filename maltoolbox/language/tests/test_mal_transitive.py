from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
File to test the transitive step (X*.A) in MAL
'''

def test_transitive_1() -> None:
    '''
    Correctly define a transitive expression (in a step)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            | openAllSubFolders
            -> folders.subFolder*.access
        }

        asset Folder
        {
        }

        asset SubFolder extends Folder
        {
            | access
        }
    }
                        
    associations 
    {
        Computer [host] * <-- L --> 0..1 [folders] Folder
        Folder [parent] 1 <-- L --> 0..* [subFolder] SubFolder
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_2() -> None:
    '''
    Correctly define a transitive expression (in a variable)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let recursive_subfolders = folders.subFolder*
            | openAllSubFolders
            -> recursive_subfolders().access
        }

        asset Folder
        {
        }

        asset SubFolder extends Folder
        {
            | access
        }
    }
                        
    associations 
    {
        Computer [host] * <-- L --> 0..1 [folders] Folder
        Folder [parent] 1 <-- L --> 0..* [subFolder] SubFolder
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_3() -> None:
    '''
    Create a transitive expression when there is no inheritance 
    relationship between X and A (A is not a child of X, given X.A*)
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let recursive_subfolders = folders.subFolder*
            | openAllSubFolders
            -> recursive_subfolders().access
        }

        asset Folder
        {
        }

        //          COMMENTED
        //              |
        //              v
        asset SubFolder // extends Folder
        {
            | access
        }
    }
                        
    associations 
    {
        Computer [host] * <-- L --> 0..1 [folders] Folder
        Folder [parent] 1 <-- L --> 0..* [subFolder] SubFolder
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_4() -> None:
    '''
    Test transitive step in a long hierarchy
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let recursive_subfolders = fileSystem.fileSystemEntries.folders.subFolder*
            | openAllSubFolders
            -> recursive_subfolders().access
        }

        asset FileSystem {
        }

        asset FileSystemEntries {
        }

        asset Folder
        {
        }

        asset SubFolder extends Folder
        {
            | access
        }
    }
                        
    associations 
    {
        Computer [host] * <-- L --> 0..1 [fileSystem] FileSystem
        FileSystem [host] * <-- L --> 0..1 [fileSystemEntries] FileSystemEntries
        Folder [folders] * <-- L --> 0..1 [holder] FileSystemEntries
        Folder [parent] 1 <-- L --> 0..* [subFolder] SubFolder
    }  
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'FileSystem', 'FileSystemEntries', 'Folder', 'SubFolder']
    )

def test_transitive_5() -> None:
    '''
    Define a transitive expression, but call it without a step belonging to the asset
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer
        {
            let recursive_subfolders = folders.subFolder*
            | openAllSubFolders
            -> recursive_subfolders().wrongStep
        }

        asset Folder
        {
        }

        asset SubFolder extends Folder
        {
            | access
        }
    }
                        
    associations 
    {
        Computer [host] * <-- L --> 0..1 [folders] Folder
        Folder [parent] 1 <-- L --> 0..* [subFolder] SubFolder
    }  
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )