//! Port of `maltoolbox/attackgraph/ttcs.py`.

use serde_json::{json, Value};

use maltoolbox_language::graph::attack_step::AttackStepType;
use maltoolbox_language::graph::LanguageGraphAttackStep;
use maltoolbox_model::ModelAsset;

/// Step TTC distribution based on the language, overridden by the
/// model's defense value when `attack_step` is a defense the model sets
/// explicitly.
pub fn get_ttc_dist(asset: &ModelAsset, attack_step: &LanguageGraphAttackStep) -> Option<Value> {
    if attack_step.step_type == AttackStepType::Defense {
        if let Some(&defense_value) = asset.defenses.get(&attack_step.name) {
            return Some(json!({
                "arguments": [defense_value],
                "name": "Bernoulli",
                "type": "function",
            }));
        }
    }
    attack_step.ttc.clone()
}
