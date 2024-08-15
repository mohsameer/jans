use std::{borrow::Cow, collections::BTreeSet};

use crate::startup;
use wasm_bindgen::{throw_str, JsValue, UnwrapThrowExt};
use web_sys::*;

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub enum Binding {
	Client,
	Application,
	User,
}

#[derive(Debug, Clone)]
pub enum Statement {
	Binding(Binding),
	Operation(fn(&[cedar_policy::Decision]) -> cedar_policy::Decision, Cow<'static, [Statement]>),
}

// supported tokens: Client, Application, User, !, |, &, (, )
pub fn parse(tokens: &str) -> Statement {
	let mut start = 0;
	let mut o_stack: Vec<fn(&[cedar_policy::Decision]) -> cedar_policy::Decision> = vec![];

	// stores arguments
	let mut a_stack = vec![];
	let mut statements = vec![];

	for (index, _) in tokens.char_indices() {
		let slice = tokens.get(start..=index).expect_throw("Overflow encountered during string slice");

		// TODO: enable !Client pattern
		match slice {
			// ! is a unary operation
			"User" | "Application" | "Client" if o_stack.last().map(|f| *f as usize) == Some(operators::not as usize) => match slice {
				"User" => statements.push(Statement::Operation(operators::not, Cow::Borrowed(&[Statement::Binding(Binding::User)]))),
				"Application" => statements.push(Statement::Operation(operators::not, Cow::Borrowed(&[Statement::Binding(Binding::Application)]))),
				"Client" => statements.push(Statement::Operation(operators::not, Cow::Borrowed(&[Statement::Binding(Binding::Client)]))),
				_ => unreachable!(),
			},
			"User" | "Application" | "Client" => match slice {
				"User" => statements.push(Statement::Binding(Binding::User)),
				"Application" => statements.push(Statement::Binding(Binding::Application)),
				"Client" => statements.push(Statement::Binding(Binding::Client)),
				_ => unreachable!(),
			},

			"!" => o_stack.push(operators::not),
			"|" => o_stack.push(operators::any),
			"&" => o_stack.push(operators::all),
			"(" => a_stack.push(statements.len()),
			")" => {
				let Some(start) = a_stack.pop() else { throw_str(&format!("Unmatched `)` at index: {}", index)) };
				let Some(operator) = o_stack.pop() else { throw_str("Operator call without function name") };

				let statement = Statement::Operation(operator, statements.drain(start..).collect());
				statements.push(statement);
			}
			"\n" | " " | "," => {
				// ignored inputs
			}
			// End of input, with unknown syntax
			_ if index == tokens.len() => match tokens.get(index..index + 1) {
				Some(s) => {
					let msg = format!("Unknown syntax: {}", s);
					throw_str(&msg)
				}
				None => throw_str("Syntax Error, encountered unknown tokens in boolean combine string"),
			},
			// expand window
			_ => continue,
		}

		start = index + 1;
	}

	// statements should have length of 1, since it's either an operation or a simple binding
	if statements.len() != 1 {
		throw_str("multiple statements found, possible syntax error")
	}

	statements.swap_remove(0)
}

mod operators {
	use wasm_bindgen::UnwrapThrowExt;

	// !
	pub fn not(input: &[cedar_policy::Decision]) -> cedar_policy::Decision {
		match input.first().expect_throw("`!` operation takes one input") {
			cedar_policy::Decision::Allow => cedar_policy::Decision::Deny,
			cedar_policy::Decision::Deny => cedar_policy::Decision::Allow,
		}
	}

	// |
	pub fn any(input: &[cedar_policy::Decision]) -> cedar_policy::Decision {
		match input.iter().any(|i| *i == cedar_policy::Decision::Allow) {
			true => cedar_policy::Decision::Allow,
			false => cedar_policy::Decision::Deny,
		}
	}

	// &
	pub fn all(input: &[cedar_policy::Decision]) -> cedar_policy::Decision {
		match input.iter().all(|i| *i == cedar_policy::Decision::Allow) {
			true => cedar_policy::Decision::Allow,
			false => cedar_policy::Decision::Deny,
		}
	}
}

#[derive(Debug, Default)]
pub struct ExecCtx {
	client: Option<cedar_policy::Decision>,
	user: Option<cedar_policy::Decision>,
	application: Option<cedar_policy::Decision>,
	pub(crate) policies: BTreeSet<String>,
}

pub fn evaluate(
	// Lord have mercy on the number of parameters this takes
	statement: &Statement,
	uids: &super::types::EntityUids,
	entities: &cedar_policy::Entities,
	input: &(cedar_policy::EntityUid, cedar_policy::EntityUid, cedar_policy::Context),
	ctx: &mut ExecCtx,
) -> cedar_policy::Decision {
	let schema = startup::SCHEMA.get();
	let policies = startup::POLICY_SET.get().expect_throw("POLICY_SET not initialized");

	match statement {
		Statement::Binding(s) => {
			let decision = match s {
				Binding::Client => &mut ctx.client,
				Binding::Application => &mut ctx.application,
				Binding::User => &mut ctx.user,
			};

			// check cache
			decision
				.get_or_insert_with(|| {
					// calculate result
					let (action, resource, context) = input;
					let principal = match s {
						Binding::Client => Some(uids.user.clone()),
						Binding::Application => uids.application.clone(),
						Binding::User => Some(uids.user.clone()),
					};

					let decision = cedar_policy::Request::new(principal, Some(action.clone()), Some(resource.clone()), context.clone(), schema).unwrap_throw();

					// create authorizer
					let authorizer = cedar_policy::Authorizer::new();
					let response = authorizer.is_authorized(&decision, policies, entities);

					// log errors
					for err in response.diagnostics().errors() {
						let msg = format!("[Principal={:?}] Encountered Error during Policy Evaluation: {:?}", s, err);
						let msg = JsValue::from_str(&msg);

						console::error_1(&msg)
					}

					// insert affecting policies
					let iter = response.diagnostics().reason().map(ToString::to_string);
					ctx.policies.extend(iter);

					response.decision()
				})
				.clone()
		}
		Statement::Operation(function, arguments) => {
			let cb = |s| evaluate(s, uids, entities, input, ctx);
			let arguments: Vec<_> = arguments.into_iter().map(cb).collect();
			function(&arguments)
		}
	}
}
