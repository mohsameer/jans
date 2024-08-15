## cedarling ⚙️

The `cedarling` is an embeddable Webassembly Component that runs a local Cedar Engine, enabling fine grained and responsive Policy Management on the Web (or any JS environment). The `cedarling` allows for dynamic updates to it's internal Policy Store via Server Sent events, enabling sub-second Access Management.

### Setup 1️⃣

> Follow the cedar tutorial [`here`](https://www.cedarpolicy.com/en/tutorial), before running the cedarling.

Make sure you have [the Rust Toolchain](https://rustup.rs/), [`wasm-bindgen`](https://rustwasm.github.io/wasm-bindgen/reference/cli.html), [`clang`](https://clang.llvm.org/) and the `wasm32-unknown-unknown` Rust target triple installed. General setup follows the following flow:

```bash
# clang installation differs by OS and distribution

rustup default stable # Install Rust stable
rustup target add wasm32-unknown-unknown # Install wasm target

cargo install -f wasm-bindgen-cli # Install wasm-bindgen CLI
```

### Building ⚒️

To build the `cedarling`, run the following commands, the appropriate Javascript bindings will be generated in the `out` directory.


```bash
cargo build --release --target wasm32-unknown-unknown

# For use in Node, Deno or the Edge
wasm-bindgen --out-dir out ./target/wasm32-unknown-unknown/release/cedarling.wasm

ls out
	out
	├── cedarling_bg.js
	├── cedarling_bg.wasm
	├── cedarling_bg.wasm.d.ts
	├── cedarling.d.ts
	└── cedarling.js
```

To run the `cedarling`, you'll need to include the `cedarling.js`, `cedarling_bg.js` and `cedarling.wasm`. The other files in `out` are Typescript type definitions.

### Special Instructions for the Web 🌍

The Web requires the WASM binary to be loaded from the network, and thus requires some manual initialization. Luckily, it's not a complicated process. To build:

```bash
wasm-bindgen --out-dir out ./target/wasm32-unknown-unknown/release/cedarling.wasm --target web
```

To instantiate:

```js
import setup, { authz, init } from "cedarling.js";

// The default export is the initialization function, here renamed to `setup`
await setup();

// ... use cedarling functions here
```

### Special Instructions for the NodeJS 🟩

There is no prelude required at runtime for NodeJS, but the `cedarling` must be built with the correct flags set.

```bash
# `--features direct_startup_strategy` enables sending in the policy store directly from JS, useful for testing
cargo build --release --target wasm32-unknown-unknown --features direct_startup_strategy

# Note --target nodejs
wasm-bindgen --target nodejs --out-dir out ./target/wasm32-unknown-unknown/release/cedarling.wasm
```

The cedarling can now be used directly, via:

```js
// CommonJS import
const { init, authz } = require("../out/cedarling.js");

// As an ES6 Module
import { init, authz } from "../out/cedarling.js"
```

### Testing 🧪

To test, you'll need Node.js installed. First, build the cedarling by running:

```sh
# `--features direct_startup_strategy` enables sending in the policy store directly from JS, useful for testing
cargo build --release --target wasm32-unknown-unknown --features direct_startup_strategy

# Note --target nodejs
wasm-bindgen --target nodejs --out-dir out ./target/wasm32-unknown-unknown/release/cedarling.wasm

# Execute tests, "local" "remote" or "lock-master" for alternate startup strategies
node tests/main.mjs local
```

### Policy Store Format 📐

The `remote` and `lock-master` startup strategies share a similar format, documented below:

```jsonc
{
	// policies is a dictionary that maps PolicyIDs to base64 encoded cedar policies
	"policies": {
		"b34fce229be0629e1e17baca42fbfe3621b70540598c": "pb25QaG90bzk0LmpwZyIKKTs=",
		"kaushd787aosd90aspd908i123j1238okjl1iop245up": "cGVybWl0KAogICAgcHJpbmNpcGFsIGluIFVzZXI6OiJhbGljZSIsIAogICAgYWN0aW90X2lwID09ICIyMjIuMjIyLjIyMi4yMjIiCn07",
	},
	// trustedIssuers is also an array of IDPs known by the cedarling
	"trustedIssuers": [
		{
			"name": "<IDP_NAME>",
			"description": "<DESCRIPTION>",
			"openidConfigurationEndpoint": "https://accounts.google.com/.well-known/openid-configuration",

			// Configures if this IDP can issue a specific token type, and how the token is handled by the cedarling during `authz`
			"accessTokens": {
				"trusted": true
			},
			"idTokens": {
				"trusted": true,
				"principalIdentifier": "email"
			},
			"userinfoTokens": {
				"trusted": true,
				"roleMapping": "role"
			}
		}
	],
	// schema is a base64 encoded cedar schema, in human readable format
	"schema": "h23GV5ybWl0KAogICAgcHJpbmNpcGFsIGluIFVzZXI6OiJhbGljZSIsIAogICAgYWN0aW90X2lwID09ICIyMjIuMjIyLjIyMi4yMjIiCn07==",
}
```

The `local` startup format is slightly different, as it stores multiple entries to be chosen from at runtime. It's a simple dictionary, mapping a PolicyStore ID to a `PolicyStoreEntry`, documented above. You can edit this file, under `policy-store/local.json` and it will be statically embedded into the `cedarling` at compile time:

```jsonc
{
	"<POLICY_STORE_ID#1>": {
		// PolicyStoreEntry
	},
	"<POLICY_STORE_ID#2>": {
		// PolicyStoreEntry
	},
}
```

### Usage 🔧

From within your JS project, you'll need to import the exported `cedarling` functions from the `cedarling.js` file.

```js
// cedarling initialization flow
// INFO: The cedarling must be initialized only once, any further attempts will throw errors

import { init } from "cedarling.js"

const config = {
	// [REQUIRED] name that cedarling will use for DCR
	applicationName: "test#docs",
	// [DEFAULT = false] Controls if cedarling will discard id_token without an access token with the corresponding client_id.
	requireAudValidation: false,
	// [DEFAULT = true] If any token claims are checked, set to false with caution
	jwtValidation: true,
	// Configure how the cedarling acquires it's Policy Store during startup
	policyStore: {
		// can be "local", "remote" or "lock-server",
		// each strategy requires different parameters, see below
		strategy: "local",
		id: "fc2fee0253af46f3dce320484c42444ae0b24f7ec84a",
	},
	// if policy-store.json is compressed using deflate-zlib
	decompressPolicyStore: false,
	// [OPTIONAL] How often, in milliseconds, will the cedarling refresh it's TrustStore. The trust store won't refresh if omitted
	trustStoreRefreshRate: 2000,
	// Set of jwt algorithms that the cedarling will allow
	supportedAlgorithms: ["HS256", "HS384", "RS256"]
};

/// > config.policyStore options <

// the "local" strategy is a fallback option. the cedarling will use a statically embedded policy store, located in `/policy-store/local.json`. This policy store contains several entries, and one will have to be picked using `id`
const local = {
	strategy: "local",
	id: "fc2fee0253af46f3dce320484c42444ae0b24f7ec84a",
};

// the "remote" strategy is only slightly more complex than "local", with the only difference being you provide a http `url` from which a simple GET request is used to acquire the Policy Store
const remote = {
	strategy: "remote",
	url: "https://raw.githubusercontent.com/JanssenProject/jans/main/jans-lock/cedarling/policy-store/remote.json"
}

// the "lock-server" strategy is a more complicated, authenticated strategy employing OAuth.
const lockMaster = {
	strategy: "lock-server",
	// `url` a http URL to a Jans Lock Master instance
	url: "https://lock.master.gluu.cloud",
	// `policyStoreId` acquire a specific Policy Store from the Lock Master
	policyStoreId: "#83J5KF9U2KAKtO2J",
	// `enableDynamicConfiguration` if the cedarling should subscribe to Policy Updates via the Lock Master's SSE endpoint
	enableDynamicConfiguration: true,
	// `ssaJwt`: Software Statement used by the cedarling during OAuth Dynamic Client registration
	ssaJwt: "..."
}

/// END > config.policyStore options <

// To initialize the cedarling, run init(config)
init(config);
```

### `authz` Usage

The `authz` export is how you send requests to the cedarling. `authz` runs a `cedar` decision under the hood, a `cedar` decision has 4 parts:
 - The `principal`: The entity requesting access.
 - The `action`: The action being requested.
 - The `resource`: The resource being accessed.
 - The `context`: Extra information provided to the cedar engine used by policies to facilitate decisions.

`authz` generates several entities as described by the `schema` from it's input, runs the cedar-engine for these entities and aggregates the results into a single decision, using a lightweight DSL.

The input of authz is described below:

```js
// the data provided below is for demonstration purposes only

let input = {
	// `statement`: a lightweight DSL used to aggregate decisions
	statement: "&(User, Application)",
	// `idToken`: an id_token JWT used to extract the `idTokenEntity` entity defined in the core cedarling schema
	idToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
	// `userinfoToken`: used together with the `idToken` to generate the `User` and `userinfoTokenEntity` entities
	userinfoToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
	// `accessToken`: used to generate the `Client` and `Application` entities
	accessToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
	// `action`: Maps 1:1 to the `action` parameter in a cedar request, is expected to be an EntityUid
	action: 'Delete::"Cache"',
	// `resource`: An entity definition that is appended as is to the Entities list. The `resource` should respect the schema, and once appended it's UID is used as the `resource` parameter for any subsequent Cedar requests.
	// The format follows 1:1 the JSON format for defining entities in cedar
	resource: {
		uid: { type: "User", id: "alice" },
		attrs: {
			age: 19,
			ip_addr: { "__extn": { fn: "ip", arg: "10.0.1.101" } }
		},
		parents: [{ type: "Group", id: "admin" }]
	},
	// `context` An object used to pass additional information to the policy engine, maps 1:1 to the `context` parameter in a Cedar request
	context: { type: "Context", id: "12345678" }
}
```

### Lock Master SSE Interface 🚧

> Status List updates are in incubation