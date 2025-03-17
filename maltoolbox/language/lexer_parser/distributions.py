class DistributionsException(Exception):
    def __init__(self, error_message):
        self._error_message = error_message
        super().__init__(self._error_message)

class Distributions:
    def validate(distribution_name: str, params: list) -> None:
        match distribution_name:
            case 'Bernoulli':
                Bernoulli.validate(params)
            case 'Binomial':
                Binomial.validate(params)
            case 'Exponential':
                Exponential.validate(params)
            case 'Gamma':
                Gamma.validate(params)
            case 'LogNormal':
                LogNormal.validate(params)
            case 'Pareto':
                Pareto.validate(params)
            case 'TruncatedNormal':
                TruncatedNormal.validate(params)
            case 'Uniform':
                Uniform.validate(params)
            case 'Enabled' | 'Disabled':
                pass
            case _:
                pass

class Bernoulli:
    def validate(params: list) -> None:
        if (not params or len(params)!=1):
            err_msg = "Expected exactly one parameter (probability), for Bernoulli distribution" 
            raise(DistributionsException(err_msg))
        if not 0<=params[0]<=1:
            err_msg = f"{params[0]} is not in valid range '0 <= probability <= 1', for Bernoulli distribution"
            raise(DistributionsException(err_msg))

class Binomial:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (trials, probability), for Binomial distribution" 
            raise(DistributionsException(err_msg))
        if not 0<=params[1]<=1:
            err_msg = f"{params[1]} is not in valid range '0 <= probability <= 1', for Binomial distribution"
            raise(DistributionsException(err_msg))

class Exponential:
    def validate(params: list) -> None:
        if (not params or len(params)!=1):
            err_msg = "Expected exactly one parameter (lambda), for Exponential distribution"
            raise(DistributionsException(err_msg))
        if params[0]<=0:
            err_msg = f"{params[0]} is not in valid range 'lambda > 0', for Exponential distribution"
            raise(DistributionsException(err_msg))

class Gamma:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (shape, scale), for Gamma distribution"
            raise(DistributionsException(err_msg))
        if params[0]<=0:
            err_msg = f"{params[0]} is not in valid range 'shape > 0', for Gamma distribution"
            raise(DistributionsException(err_msg))
        if params[1]<=0:
            err_msg = f"{params[1]} is not in valid range 'scale > 0', for Gamma distribution"
            raise(DistributionsException(err_msg))

class LogNormal:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (mean, standardDeviation), for LogNormal distribution"
            raise(DistributionsException(err_msg))
        if params[1]<=0:
            err_msg = f"{params[1]} is not in valid range 'standardDeviation > 0', for LogNormal distribution"
            raise(DistributionsException(err_msg))

class Pareto:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (min, shape), for Pareto distribution"
            raise(DistributionsException(err_msg))
        if params[0]<=0:
            err_msg = f"{params[0]} is not in valid range 'min > 0', for Pareto distribution"
            raise(DistributionsException(err_msg))
        if params[1]<=0:
            err_msg = f"{params[1]} is not in valid range 'shape > 0', for Pareto distribution"
            raise(DistributionsException(err_msg))

class TruncatedNormal:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (mean, standardDeviation), for TruncatedNormal distribution" 
            raise(DistributionsException(err_msg))
        if params[1]<=0:
            err_msg = f"{params[1]} is not in valid range 'standardDeviation > 0', for TruncatedNormal distribution"
            raise(DistributionsException(err_msg))

class Uniform:
    def validate(params: list) -> None:
        if (not params or len(params)!=2):
            err_msg = "Expected exactly two parameters (min, max), for Uniform distribution" 
            raise(DistributionsException(err_msg))
        if params[0] > params[1]:
            err_msg = f"({params[0]}, {params[1]}) does not meet requirement 'min <= max', for Uniform distribution"
            raise(DistributionsException(err_msg))
