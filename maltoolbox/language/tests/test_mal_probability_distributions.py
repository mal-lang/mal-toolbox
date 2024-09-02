from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

def test_probability_distributions_1() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            # defense [Enabled]
            | havePassword
                -> login
            | findPassword [Exponential(0.1)]
                -> login
            & login
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_2() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            & login [Enabled]
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_3() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Enabled]
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_4() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Disabled]
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_5() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            & login [Disabled]
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_6() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [0.9]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_7() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Bernoulli(0.5) * Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_8() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Exponential(0.5) * Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_9() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Exponential(0.5) / Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_10() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Exponential(0.5) ^ Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_11() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Exponential(0.5) + Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_12() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Exponential(0.5) - Exponential(0.1)]
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_13() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {
            | login [Bernoulli(0.5) ^ Exponential(0.1)]
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )