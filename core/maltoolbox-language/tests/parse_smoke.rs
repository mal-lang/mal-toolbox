use maltoolbox_language::new_parser;

#[test]
fn parses_wiper_lang_without_errors() {
    let source = include_str!("fixtures/wiperLang.mal");
    let mut parser = new_parser();
    let tree = parser.parse(source, None).expect("parser did not run");
    assert!(
        !tree.root_node().has_error(),
        "parse tree contains errors:\n{}",
        tree.root_node().to_sexp()
    );
}
