# B. de Medeiros' Claude Skills Collection

Custom Claude skills for enhanced reasoning, bioinformatics, and natural history museum workflows. Each skill is a self-contained module bundled into installable plugins.

## Available Plugins and Skills

### general-skills

| Skill | Description |
|-------|-------------|
| **think-deeply** | Enforces multi-perspective analysis instead of automatic agreement/disagreement. Activates on confirmation-seeking questions, leading statements, and binary choices. [Docs →](./think_deeply/README.md) |
| **extract-from-pdfs** | 8-step pipeline for extracting structured data from scientific PDFs using Claude's vision. Supports abstract filtering (Ollama/Haiku/Sonnet), external validation (GBIF, WFO, GeoNames, PubChem, NCBI), and export to multiple formats. [Docs →](./extract_from_pdfs/README.md) |

### bioinfo-skills

| Skill | Description |
|-------|-------------|
| **phylo-from-buscos** | Generates phylogenomic workflows from genome assemblies using BUSCO/compleasm single-copy orthologs. Supports NCBI accessions, multiple schedulers (SLURM, PBS, local), concatenated and coalescent phylogenies. [Docs →](./phylo_from_buscos/README.md) |
| **biogeobears** | Sets up BioGeoBEARS biogeographic analyses in R. Validates inputs, generates RMarkdown scripts, compares DEC/DIVALIKE/BAYAREALIKE models, and produces publication-ready ancestral range visualizations. [Docs →](./biogeobears/README.md) |

### museum-skills

| Skill | Description |
|-------|-------------|
| **emu-bulk-upload** | Helps FMNH entomology curators bulk upload specimen data to the Emu database. Matches localities to existing records, creates new site records, and generates formatted upload tables. [Docs →](./Emu_bulk_upload_FMNH/SKILL.md) |
| **entomological-labels** | Generates print-ready entomological specimen labels (.docx) from any tabular data. Interactively maps data to Darwin Core, assists with abbreviation, and produces label sheets. [Docs →](./entomological_labels/SKILL.md) |

### Anthropic Official Skills (submodule)

The `anthropic-skills/` directory contains Anthropic's official example skills as a git submodule, including **skill-creator**, document tools, and more.

## Installation

### Claude Code — CLI, VS Code, or JetBrains (Recommended)

These instructions work the same way in:
- **Claude Code CLI** — type commands directly in the terminal
- **VS Code** — type commands in the Claude Code chat panel (or use `/plugins` to open the visual manager)
- **JetBrains IDEs** — type commands in the Claude Code panel

#### Step 1: Add the marketplace

You only need to do this once:

```
/plugin marketplace add brunoasm/my_claude_skills
```

#### Step 2: Install the plugins you need

Install all plugins:
```
/plugin install general-skills@brunoasm/my_claude_skills
/plugin install bioinfo-skills@brunoasm/my_claude_skills
/plugin install museum-skills@brunoasm/my_claude_skills
```

Or install only the ones you want — each plugin is independent.

#### Install from a local clone

```bash
git clone --recurse-submodules https://github.com/brunoasm/my_claude_skills.git
cd my_claude_skills
```
Then in Claude Code:
```
/plugin marketplace add .
/plugin install general-skills@.
```

#### Scope options

When installing, Claude Code will ask you to choose a scope:
- **User** — available in all your projects
- **Project** — shared with collaborators via `.claude/settings.json`
- **Local** — only you, only this repo

### Claude.ai (Web)

1. Download the zip file for the desired skill from [releases](https://github.com/brunoasm/my_claude_skills/releases)
2. Go to Claude.ai **Settings > Capabilities > Skills**
3. Click **Upload Skill** and select the ZIP file
4. Enable the skill

### Clone with submodule

To get the Anthropic example skills submodule:
```bash
git clone --recurse-submodules https://github.com/brunoasm/my_claude_skills.git
```

If you already cloned without it:
```bash
git submodule update --init --recursive
```

## Resources

- [Claude Code Plugins Documentation](https://code.claude.com/docs/en/plugins.md)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills.md)
- [Claude.ai](https://claude.ai)
