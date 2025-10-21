# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Infrahub demo repository showcasing data center fabric management with VxLAN/EVPN and firewalls. It demonstrates Infrahub integration with Arista AVD, where Infrahub generates configurations that AVD deploys.

Infrahub is an infrastructure data management platform built on three pillars:

- **Flexible Schema**: Extensible data models defining infrastructure and relationships
- **Version Control**: Native branching, diffing, and merging in the graph database
- **Unified Storage**: Combined graph database and git for data and code

## Development Commands

### Environment Setup

```bash
# Install dependencies
poetry install

# Install with dev dependencies
poetry install --with dev
```

### Running the Demo

```bash
# Start Infrahub (uses docker compose)
invoke start

# Load schema into Infrahub
invoke load-schema

# Load demo data
invoke load-data

# Stop services
invoke stop

# Destroy services and volumes
invoke destroy
```

### Testing

```bash
# Run all tests
pytest

# Run integration tests only
pytest tests/integration/

# Run specific test
pytest tests/integration/test_workflow.py
```

### Code Quality

```bash
# Format code with ruff
invoke format

# Run all linters
invoke lint

# Run individual linters
invoke lint-yaml    # yamllint
invoke lint-ruff    # ruff check
invoke lint-mypy    # mypy type checking
```

### Documentation

The documentation is built with Docusaurus and lives in the `docs/` directory.

```bash
# Build documentation (requires Node.js >= 20.0)
cd docs
npm install
npm run build

# Serve documentation locally
npm run start
```

**Requirements:**
- Node.js >= 20.0 (specified in `.node-version` and `docs/package.json`)
- The `.node-version` file ensures Cloudflare Pages uses the correct Node.js version

## Architecture

### Schema Models (schemas/)

YAML schema files define the Infrahub data model:

- `dcim.yml` - Device, interface, platform definitions (GenericDevice, InfraInterface, etc.)
- `ipam.yml` - IP addressing and network objects
- `locations.yml` - Sites and physical locations
- `organizations.yml` - Organizations, tenants, providers
- `routing.yml` - Routing protocols and BGP configuration
- `security.yml` - Security policies and firewall rules
- `topology.yml` - Network topology definitions
- `circuit.yml` - Circuit and connectivity definitions

Schemas are loaded with: `infrahubctl schema load schemas/*.yml --wait 30`

### Bootstrap Scripts (bootstrap/)

Python scripts that populate initial data using the Infrahub SDK. Executed in order:

1. `create_basic.py` - Accounts, tags, organizations, device types
2. `create_location.py` - Locations and sites
3. `create_topology.py` - Topology definitions and device creation
4. `create_security_nodes.py` - Security policies and firewall configurations

Each uses `infrahub_sdk.InfrahubClient` and batch operations for efficient data creation.

### Generators (generators/)

Python generators create derived data based on existing objects:

- `network_services.py` - Generates VLANs, prefixes, and IP allocations for network services
- Uses `infrahub_sdk.generator.InfrahubGenerator` base class
- Triggered via: `infrahubctl generator generate_network_services network_service_name="<name>"`

### Checks (checks/)

Data validation checks enforcing business rules:

- `check_device_topology.py` - Validates topology definitions match actual device deployments
- Uses `infrahub_sdk.checks.InfrahubCheck` base class
- Queries graph database to validate relationships and quantities

### Transforms (transforms/)

Data transformation modules:

- `openconfig.py` - Converts Infrahub interface data to OpenConfig JSON format
- Uses `infrahub_sdk.transforms.InfrahubTransform` base class

### Templates (templates/)

Jinja2 templates for configuration generation:

- `device_arista_config.tpl.j2` - Arista device startup configs
- `device_cisco_config.tpl.j2` - Cisco device startup configs
- `juniper_srx_config.j2` - Juniper SRX firewall configs
- `*.gql` files - GraphQL queries used by templates and transforms

### Configuration (.infrahub.yml)

Central configuration file defining:

- `jinja2_transforms` - Template-based transformations
- `artifact_definitions` - Generated configuration artifacts (startup-config, openconfig-interfaces, etc.)
- `check_definitions` - Data validation checks
- `python_transforms` - Python-based transformations
- `generator_definitions` - Data generators
- `queries` - GraphQL query definitions

## Working with Infrahub

### Common Patterns

**Creating objects with the SDK:**

```python
from infrahub_sdk import InfrahubClient
client = await InfrahubClient()
obj = await client.create(kind="InfraDevice", data={...})
await obj.save()
```

**Using batch operations (recommended for bulk creation):**

```python
from infrahub_sdk.batch import InfrahubBatch
batch = await client.create_batch()
await batch.add(task=client.create, ...)
async for result in batch.execute():
    # process result
```

**Querying with GraphQL:**

```python
query = await client.execute_graphql(query="...", variables={...})
```

**Running scripts:**

```bash
infrahubctl run bootstrap/create_basic.py
```

### Testing with Testcontainers

Integration tests use `infrahub-testcontainers` to spin up ephemeral Infrahub instances:

- Tests inherit from `TestInfrahubDockerWithClient`
- Provides `client_main` fixture for main branch operations
- Use `execute_command()` method for running `infrahubctl` commands

## Important Notes

- Python version: 3.10 - 3.12 (not 3.13+)
- Ansible version varies by Python version (see pyproject.toml)
- The demo requires Docker for running Infrahub services
- Integration tests require significant resources (run on "huge-runners" in CI)
- Always use batch operations for creating multiple objects to avoid performance issues
- GraphQL queries are stored separately from code in `.gql` files and referenced by name in `.infrahub.yml`

## Documentation Quality

### Linting and Formatting

When working on documentation files (`.mdx`), always run markdownlint to ensure consistent formatting:

```bash
# Check all documentation files
markdownlint docs/docs/**/*.mdx

# Fix auto-fixable issues
markdownlint docs/docs/**/*.mdx --fix
```

### Common Markdownlint Rules

- **MD032**: Lists must be surrounded by blank lines
- **MD022**: Headings must be surrounded by blank lines
- **MD007**: Use consistent list indentation (4 spaces for nested items)
- **MD009**: No trailing spaces
- **MD031**: Fenced code blocks must be surrounded by blank lines
- **MD040**: Fenced code blocks should specify a language

### Documentation Standards

- Follow the Diataxis framework for content structure
- Use clear, actionable headings for guides
- Include code snippets with language specifications
- Add explanatory callouts (:::tip, :::info, :::warning) for important concepts
- Ensure all lists and code blocks have proper spacing

### Vale Style Guide

When working on documentation, run Vale to ensure consistent style:

```bash
# Run Vale on documentation files (as used in CI)
vale $(find ./docs/docs -type f \( -name "*.mdx" -o -name "*.md" \) )

```

#### Common Vale Issues to Fix

1. **Sentence Case for Headings**
   - Use sentence case for all headings (lowercase except first word and proper nouns)
   - Example: "Understanding the workflow" not "Understanding the Workflow"
   - Exception: Proper nouns like "Infrahub", "GitHub", "Streamlit"

2. **Spelling Exceptions**
   - Add technical terms to `.vale/styles/spelling-exceptions.txt`
   - Common additions: `IPs`, `Gbps`, `Mbps`, `UIs`, `configs`, `auditable`, `idempotently`
   - Keep terms alphabetically sorted in the file

3. **Word Choices**
   - Avoid "simple" and "easy" - use "straightforward" or "clear" instead
   - Use "for example:" instead of "e.g." or "i.e."
   - Keep "configs" as is (don't replace with "configurations")

4. **GitHub Capitalization**
   - Always capitalize as "GitHub" not "github"
   - Note: Vale's branded-terms rule may sometimes false positive on correct usage

### Documentation Writing Guidelines

**Applies to:** All MDX files (`**/*.mdx`)

**Role:** Expert Technical Writer and MDX Generator with:

- Deep understanding of Infrahub and its capabilities
- Expertise in network automation and infrastructure management
- Proficiency in writing structured MDX documents
- Awareness of developer ergonomics

**Documentation Purpose:**

- Guide users through installing, configuring, and using Infrahub in real-world workflows
- Explain concepts and system architecture clearly, including new paradigms introduced by Infrahub
- Support troubleshooting and advanced use cases with actionable, well-organized content
- Enable adoption by offering approachable examples and hands-on guides that lower the learning curve

**Structure:** Follows [Diataxis framework](https://diataxis.fr/)

- **Tutorials** (learning-oriented)
- **How-to guides** (task-oriented)
- **Explanation** (understanding-oriented)
- **Reference** (information-oriented)

**Tone and Style:**

- Professional but approachable: Avoid jargon unless well defined. Use plain language with technical precision
- Concise and direct: Prefer short, active sentences. Reduce fluff
- Informative over promotional: Focus on explaining how and why, not on marketing
- Consistent and structured: Follow a predictable pattern across sections and documents

**For Guides:**

- Use conditional imperatives: "If you want X, do Y. To achieve W, do Z."
- Focus on practical tasks and problems, not the tools themselves
- Address the user directly using imperative verbs: "Configure...", "Create...", "Deploy..."
- Maintain focus on the specific goal without digressing into explanations
- Use clear titles that state exactly what the guide shows how to accomplish

**For Topics:**

- Use a more discursive, reflective tone that invites understanding
- Include context, background, and rationale behind design decisions
- Make connections between concepts and to users' existing knowledge
- Present alternative perspectives and approaches where appropriate
- Use illustrative analogies and examples to deepen understanding

**Terminology and Naming:**

- Always define new terms when first used. Use callouts or glossary links if possible
- Prefer domain-relevant language that reflects the user's perspective (e.g., playbooks, branches, schemas, commits)
- Be consistent: follow naming conventions established by Infrahub's data model and UI

**Reference Files:**

- Documentation guidelines: `docs/docs/development/docs.mdx`
- Vale styles: `.vale/styles/`
- Markdown linting: `.markdownlint.yaml`

### Document Structure Patterns (Following Diataxis)

**How-to Guides Structure (Task-oriented, practical steps):**

```markdown
- Title and Metadata
    - Title should clearly state what problem is being solved (YAML frontmatter)
    - Begin with "How to..." to signal the guide's purpose
    - Optional: Imports for components (e.g., Tabs, TabItem, CodeBlock, VideoPlayer)
- Introduction
    - Brief statement of the specific problem or goal this guide addresses
    - Context or real-world use case that frames the guide
    - Clearly indicate what the user will achieve by following this guide
    - Optional: Links to related topics or more detailed documentation
- Prerequisites / Assumptions
    - What the user should have or know before starting
    - Environment setup or requirements
    - What prior knowledge is assumed
- Step-by-Step Instructions
    - Step 1: [Action/Goal]
        - Clear, actionable instructions focused on the task
        - Code snippets (YAML, GraphQL, shell commands, etc.)
        - Screenshots or images for visual guidance
        - Tabs for alternative methods (e.g., Web UI, GraphQL, Shell/cURL)
        - Notes, tips, or warnings as callouts
    - Step 2: [Action/Goal]
        - Repeat structure as above for each step
    - Step N: [Action/Goal]
        - Continue as needed
- Validation / Verification
    - How to check that the solution worked as expected
    - Example outputs or screenshots
    - Potential failure points and how to address them
- Advanced Usage / Variations
    - Optional: Alternative approaches for different circumstances
    - Optional: How to adapt the solution for related problems
    - Optional: Ways to extend or optimize the solution
- Related Resources
    - Links to related guides, reference materials, or explanation topics
    - Optional: Embedded videos or labs for further learning
```

**Topics Structure (Understanding-oriented, theoretical knowledge):**

```markdown
- Title and Metadata
    - Title should clearly indicate the topic being explained (YAML frontmatter)
    - Consider using "About..." or "Understanding..." in the title
    - Optional: Imports for components (e.g., Tabs, TabItem, CodeBlock, VideoPlayer)
- Introduction
    - Brief overview of what this explanation covers
    - Why this topic matters in the context of Infrahub
    - Questions this explanation will answer
- Main Content Sections
    - Concepts & Definitions
        - Clear explanations of key terms and concepts
        - How these concepts fit into the broader system
    - Background & Context
        - Historical context or evolution of the concept/feature
        - Design decisions and rationale behind implementations
        - Technical constraints or considerations
    - Architecture & Design (if applicable)
        - Diagrams, images, or explanations of structure
        - How components interact or relate to each other
    - Mental Models
        - Analogies and comparisons to help understanding
        - Different ways to think about the topic
    - Connection to Other Concepts
        - How this topic relates to other parts of Infrahub
        - Integration points and relationships
    - Alternative Approaches
        - Different perspectives or methodologies
        - Pros and cons of different approaches
- Further Reading
    - Links to related topics, guides, or reference materials
    - External resources for deeper understanding
```

### Quality and Clarity Checklist

**General Documentation:**

- Content is accurate and reflects the latest version of Infrahub
- Instructions are clear, with step-by-step guidance where needed
- Markdown formatting is correct and compliant with Infrahub's style
- Spelling and grammar are checked

**For Guides:**

- The guide addresses a specific, practical problem or task
- The title clearly indicates what will be accomplished
- Steps follow a logical sequence that maintains flow
- Each step focuses on actions, not explanations
- The guide omits unnecessary details that don't serve the goal
- Validation steps help users confirm their success
- The guide addresses real-world complexity rather than oversimplified scenarios

**For Topics:**

- The explanation is bounded to a specific topic area
- Content provides genuine understanding, not just facts
- Background and context are included to deepen understanding
- Connections are made to related concepts and the bigger picture
- Different perspectives or approaches are acknowledged where relevant
- The content remains focused on explanation without drifting into tutorial or reference material
- The explanation answers "why" questions, not just "what" or "how"
