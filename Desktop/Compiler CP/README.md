# Multi-Cloud Deployment Compiler

MCDC is a compiler-design project for a provider-neutral deployment DSL. It implements lexical analysis, parsing, typed AST construction, symbol table creation, semantic analysis, IR lowering, IR transformations, provider capability checks, and Terraform/OpenTofu HCL generation for AWS, GCP, and Azure.

## CLI

```bash
python3 -m mcdc.cli check examples/static_web_server.mcd
python3 -m mcdc.cli compile examples/static_web_server.mcd --target all --out build
python3 -m mcdc.cli ast examples/static_web_server.mcd --dot ast.dot
python3 -m mcdc.cli ir examples/static_web_server.mcd --dot ir.dot
python3 -m mcdc.cli evaluate
```

## Web App

Run the API:

```bash
uvicorn api.main:app --reload --port 8000
```

Run the React frontend:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`.

The web app shows two featured examples in the dropdown:

- `static_web_server` demonstrates a successful deployment with network, subnet, firewall, and compute resources.
- `negative_unsupported_resource` demonstrates compiler diagnostics for an unsupported provider capability.

Or run both services with Docker:

```bash
docker-compose up --build
```

## Tests

```bash
python3 -m pytest -q
```

## DSL

Top-level programs are `cloud app "Name" { ... }`. Supported portable resources are `network`, `subnet`, `compute`, `storage`, and `firewall`. Variables use `var name = literal;` and references use `${name}`.
