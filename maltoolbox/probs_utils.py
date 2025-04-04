"""Utility functions for handling probabilities"""

import logging
import math
import random
from enum import Enum

logger = logging.getLogger(__name__)

class TTCCalculation(Enum):
    SAMPLE = 1
    EXPECTED = 2

def sample_ttc(probs_dict):
    """Calculate the sampled value from a ttc distribution function
    Arguments:
    probs_dict      - a dictionary containing the probability distribution
                      function that is part of a TTC

    Return:
    The float value obtained from calculating the sampled value corresponding
    to the function provided.
    """
    if probs_dict['type'] != 'function':
        raise ValueError('Sample TTC function requires a function '
            f'probability distribution, but got "{probs_dict["type"]}"')

    match(probs_dict['name']):
        case 'Bernoulli':
            value = random.random()
            threshold = 1.0 - float(probs_dict['arguments'][0])
            return math.inf if value < threshold else 0.0

        case 'Exponential':
            lambd = float(probs_dict['arguments'][0])
            return random.expovariate(lambd)

        case 'Binomial':
            n = int(probs_dict['arguments'][0])
            p = float(probs_dict['arguments'][1])
            # TODO: Someone with basic probabilities competences should
            # actually check if this is correct.
            return random.binomialvariate(n, p)

        case 'Gamma':
            alpha = float(probs_dict['arguments'][0])
            beta = float(probs_dict['arguments'][1])
            return random.gammavariate(alpha, beta)

        case 'LogNormal':
            mu = float(probs_dict['arguments'][0])
            sigma = float(probs_dict['arguments'][1])
            return random.lognormvariate(mu, sigma)

        case 'Uniform':
            a = float(probs_dict['arguments'][0])
            b = float(probs_dict['arguments'][1])
            return random.uniform(a, b)

        case 'Pareto' | 'Truncated Normal':
            raise NotImplementedError('f{probs_dict["name"]} '
                'probability distribution is not currently '
                'supported!')

        case _:
            raise ValueError('Unknown probability distribution '
                f'function encountered {probs_dict["name"]}!')


def expected_ttc(probs_dict):
    """Calculate the expected value from a ttc distribution function
    Arguments:
    probs_dict      - a dictionary containing the probability distribution
                      function that is part of a TTC

    Return:
    The float value obtained from calculating the expected value corresponding
    to the function provided.
    """
    if probs_dict['type'] != 'function':
        raise ValueError('Expected value TTC function requires a function '
            f'probability distribution, but got "{probs_dict["type"]}"')

    match(probs_dict['name']):
        case 'Bernoulli':
            threshold = 1 - float(probs_dict['arguments'][0])
            return threshold

        case 'Exponential':
            lambd = float(probs_dict['arguments'][0])
            return 1/lambd

        case 'Binomial':
            n = int(probs_dict['arguments'][0])
            p = float(probs_dict['arguments'][1])
            # TODO: Someone with basic probabilities competences should
            # actually check if this is correct.
            return n * p

        case 'Gamma':
            alpha = float(probs_dict['arguments'][0])
            beta = float(probs_dict['arguments'][1])
            return alpha * beta

        case 'LogNormal':
            mu = float(probs_dict['arguments'][0])
            sigma = float(probs_dict['arguments'][1])
            return pow(math.e, (mu + (pow(sigma, 2)/2)))

        case 'Uniform':
            a = float(probs_dict['arguments'][0])
            b = float(probs_dict['arguments'][1])
            return (a + b)/2

        case 'Pareto' | 'Truncated Normal':
            raise NotImplementedError('f{probs_dict["name"]} '
                'probability distribution is not currently '
                'supported!')

        case _:
            raise ValueError('Unknown probability distribution '
                f'function encountered {probs_dict["name"]}!')


def calculate_ttc(probs_dict: dict, method: TTCCalculation) -> float:
    """Calculate the value from a ttc distribution
    Arguments:
    probs_dict      - a dictionary containing the probability distribution
                      corresponding to the TTC
    method          - the method to use in calculating the TTC
                      values(currently supporting sampled or expected values)

    Return:
    The float value obtained from calculating the TTC probability distribution.

    TTC Distributions in MAL:
    https://mal-lang.org/mal-langspec/apidocs/org.mal_lang.langspec/org/mal_lang/langspec/ttc/TtcDistribution.html
    """
    if probs_dict is None:
        return math.nan

    match(probs_dict['type']):
        case 'addition' | 'subtraction' | 'multiplication' | \
                'division' | 'exponentiation':
            lv = calculate_ttc(probs_dict['lhs'], method)
            rv = calculate_ttc(probs_dict['rhs'], method)
            match(probs_dict['type']):
                case 'addition':
                    return lv + rv
                case 'subtraction':
                    return lv - rv
                case 'multiplication':
                    return lv * rv
                case 'division':
                    return lv / rv
                case 'exponentiation':
                    return pow(lv, rv)
                case _:
                    raise ValueError('Unknown probability distribution type '
                    f'encountered {probs_dict["type"]}!')

        case 'function':
            match(method):
                case TTCCalculation.SAMPLE:
                    return sample_ttc(probs_dict)
                case TTCCalculation.EXPECTED:
                    return expected_ttc(probs_dict)
                case _:
                    raise ValueError('Unknown TTC Calculation method '
                    f'encountered {method}!')

        case _:
            raise ValueError('Unknown probability distribution type '
            f'encountered {probs_dict["type"]}!')
