class DistributionsException(Exception):
    def __init__(self, error_message):
        self._error_message = error_message
        super().__init__(self._error_message)

class Distributions:
    def validate(distribution_name: str, params: list) -> None:
        match distribution_name:
            case 'Bernoulli':
                Bernoulli.validate(params)
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
