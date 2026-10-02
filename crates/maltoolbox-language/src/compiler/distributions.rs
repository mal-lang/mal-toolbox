//! Port of `maltoolbox/language/compiler/distributions.py`.
//!
//! Per-TTC-distribution parameter arity/range validation, used by the
//! semantic analyzer ([`super::semantic`]) when checking attack step TTC
//! expressions.

#[derive(Debug, thiserror::Error)]
#[error("{0}")]
pub struct DistributionsError(pub String);

fn err(msg: impl Into<String>) -> DistributionsError {
    DistributionsError(msg.into())
}

pub fn validate(distribution_name: &str, params: &[f64]) -> Result<(), DistributionsError> {
    match distribution_name {
        "Bernoulli" => validate_bernoulli(params),
        "Binomial" => validate_binomial(params),
        "Exponential" => validate_exponential(params),
        "Gamma" => validate_gamma(params),
        "LogNormal" => validate_log_normal(params),
        "Pareto" => validate_pareto(params),
        "TruncatedNormal" => validate_truncated_normal(params),
        "Uniform" => validate_uniform(params),
        "Enabled" | "Disabled" | "Zero" | "Infinity" | "EasyAndCertain" | "EasyAndUncertain"
        | "HardAndCertain" | "HardAndUncertain" | "VeryHardAndCertain"
        | "VeryHardAndUncertain" => validate_combination(params),
        other => Err(err(format!("Distribution {other} is not supported"))),
    }
}

fn validate_bernoulli(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 1 {
        return Err(err(
            "Expected exactly one parameter (probability), for Bernoulli distribution",
        ));
    }
    if !(0.0..=1.0).contains(&params[0]) {
        return Err(err(format!(
            "{} is not in valid range '0 <= probability <= 1', for Bernoulli distribution",
            params[0]
        )));
    }
    Ok(())
}

fn validate_binomial(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (trials, probability), for Binomial distribution",
        ));
    }
    if !(0.0..=1.0).contains(&params[1]) {
        return Err(err(format!(
            "{} is not in valid range '0 <= probability <= 1', for Binomial distribution",
            params[1]
        )));
    }
    Ok(())
}

fn validate_exponential(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 1 {
        return Err(err(
            "Expected exactly one parameter (lambda), for Exponential distribution",
        ));
    }
    if params[0] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'lambda > 0', for Exponential distribution",
            params[0]
        )));
    }
    Ok(())
}

fn validate_gamma(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (shape, scale), for Gamma distribution",
        ));
    }
    if params[0] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'shape > 0', for Gamma distribution",
            params[0]
        )));
    }
    if params[1] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'scale > 0', for Gamma distribution",
            params[1]
        )));
    }
    Ok(())
}

fn validate_log_normal(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (mean, standardDeviation), for LogNormal distribution",
        ));
    }
    if params[1] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'standardDeviation > 0', for LogNormal distribution",
            params[1]
        )));
    }
    Ok(())
}

fn validate_pareto(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (min, shape), for Pareto distribution",
        ));
    }
    if params[0] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'min > 0', for Pareto distribution",
            params[0]
        )));
    }
    if params[1] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'shape > 0', for Pareto distribution",
            params[1]
        )));
    }
    Ok(())
}

fn validate_truncated_normal(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (mean, standardDeviation), for TruncatedNormal distribution",
        ));
    }
    if params[1] <= 0.0 {
        return Err(err(format!(
            "{} is not in valid range 'standardDeviation > 0', for TruncatedNormal distribution",
            params[1]
        )));
    }
    Ok(())
}

fn validate_uniform(params: &[f64]) -> Result<(), DistributionsError> {
    if params.len() != 2 {
        return Err(err(
            "Expected exactly two parameters (min, max), for Uniform distribution",
        ));
    }
    if params[0] > params[1] {
        return Err(err(format!(
            "({}, {}) does not meet requirement 'min <= max', for Uniform distribution",
            params[0], params[1]
        )));
    }
    Ok(())
}

fn validate_combination(params: &[f64]) -> Result<(), DistributionsError> {
    if !params.is_empty() {
        return Err(err(
            "Expected exactly zero parameters, for combination distributions",
        ));
    }
    Ok(())
}
