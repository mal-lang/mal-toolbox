use tree_sitter::{Language, Parser};

/// Build a fresh tree-sitter `Parser` configured for the MAL grammar.
pub fn new_parser() -> Parser {
    let language = Language::new(tree_sitter_mal::LANGUAGE);
    let mut parser = Parser::new();
    parser
        .set_language(&language)
        .expect("tree-sitter-mal grammar failed to load");
    parser
}
