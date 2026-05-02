# Source Inventory — Super Browser Analysis

## Category 1: Direct Browser/Web Automation (Highest Relevance)

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 1 | SRC-001 | browser-harness-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-001 | Canonical | Included | CDP-first, coordinate clicks, skill system, daemon |
| 2 | SRC-002 | browser-use-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-002 | Canonical | Included | Full framework, 14 watchdogs, event-driven, cdp-use |
| 3 | SRC-003 | stagehand-main | TypeScript | `package.json` | Yes | `git:HEAD` | DG-003 | Canonical | Included | Custom CDP layer, 14+ LLM providers, CUA agents |
| 4 | SRC-004 | skyvern-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-004 | Canonical | Included | Vision-first, workflow engine, Playwright-based |
| 5 | SRC-005 | LaVague-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-005 | Canonical | Included | RAG action generation, World Model + Action Engine |
| 6 | SRC-006 | agent-browser-main | TypeScript | `package.json` | Yes | `git:HEAD` | DG-006 | Canonical | Included | Rust CLI/daemon, accessibility-tree snapshots, ref-based |
| 7 | SRC-007 | python-sdk-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-002 | Related | Excluded | Browser Use Python SDK, subset of SRC-002 |
| 8 | SRC-008 | hermes-agent-browser-bridge | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-007 | Related | Included | Browser bridge fork with Patchright, Bedrock, Gemini |
| 9 | SRC-009 | firecrawl-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Web scraping/crawling API |
| 10 | SRC-010 | crawbot-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Web crawling bot |
| 11 | SRC-011 | adblocker | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Browser ad blocking engine |

## Category 2: Agent Frameworks with Browser Integration

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 12 | SRC-012 | hermes-agent-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-007 | Canonical | Included | Self-improving agent, 60+ tools, skill system |
| 13 | SRC-013 | hermes-agent-self-evolution-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-007 | Related | Included | Self-evolution fork of hermes-agent |
| 14 | SRC-014 | openclaw-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-008 | Canonical | Included | Plugin-first, 90+ plugins, ACP protocol, browser ext |
| 15 | SRC-015 | OpenHands | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Autonomous coding agent with browser |
| 16 | SRC-016 | autogen-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Multi-agent framework (Microsoft) |
| 17 | SRC-017 | crewAI | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Multi-agent orchestration |
| 18 | SRC-018 | langgraph | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Graph-based agent orchestration |
| 19 | SRC-019 | agentscope-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-009 | Canonical | Included | Multi-agent platform (Alibaba) |
| 20 | SRC-020 | agentscope-runtime-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-009 | Related | Excluded | Runtime subset of SRC-019 |
| 21 | SRC-021 | MetaGPT-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Multi-agent framework with role-based design |
| 22 | SRC-022 | AgentVerse-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Multi-agent universe |
| 23 | SRC-023 | Agent-S-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agent framework |
| 24 | SRC-024 | MIRIX-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agent framework |
| 25 | SRC-025 | openai-agents-python-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | OpenAI Agents SDK |

## Category 3: Tool Use / MCP Integration

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 26 | SRC-026 | ToolBench-master | Unknown | — | Yes | `git:HEAD` | DG-010 | Canonical | Included | Tool use benchmark |
| 27 | SRC-027 | ToolLLM-master | Unknown | — | Yes | `git:HEAD` | DG-010 | Related | Included | Tool use for LLMs |
| 28 | SRC-028 | ToolEVO-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool evolution |
| 29 | SRC-029 | Tool-N1-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool use research |
| 30 | SRC-030 | Tool-Planner-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool planning |
| 31 | SRC-031 | Tool-Star-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool use research |
| 32 | SRC-032 | ToolRL-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Tool use RL |
| 33 | SRC-033 | MCP-Zero-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | MCP integration |
| 34 | SRC-034 | mcp-agent-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | MCP agent framework |
| 35 | SRC-035 | mcp-skillset-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | MCP skill definitions |
| 36 | SRC-036 | agentic-tools-mcp-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Agentic tools via MCP |
| 37 | SRC-037 | GPT4Tools-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool use for GPT-4 |
| 38 | SRC-038 | CLOVA-tool-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool use research |

## Category 4: Provider Management / LLM Integration

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 39 | SRC-039 | cherry-studio-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Multi-provider AI desktop app |
| 40 | SRC-040 | litellm | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Universal LLM proxy (100+ providers) |
| 41 | SRC-041 | langchain-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | LLM framework |
| 42 | SRC-042 | llama_index-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | LLM framework |
| 43 | SRC-043 | dspy-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | LLM programming framework |
| 44 | SRC-044 | deepchat-dev | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Multi-provider chat app |
| 45 | SRC-045 | lobehub-canary | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | AI chat framework |
| 46 | SRC-046 | semantic-kernel-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Microsoft semantic kernel |

## Category 5: Memory / Knowledge

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 47 | SRC-047 | mem0-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | AI memory layer |
| 48 | SRC-048 | letta-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | LLM with memory (MemGPT) |
| 49 | SRC-049 | memorix-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Memory system |
| 50 | SRC-050 | khoj-master | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | AI personal assistant with memory |
| 51 | SRC-051 | claude-mem-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Claude memory |
| 52 | SRC-052 | Memento-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Memory for agents |

## Category 6: Skill / Self-Improvement Systems

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 53 | SRC-053 | EvoSkill-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Automated skill discovery |
| 54 | SRC-054 | skyll-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Skill learning |
| 55 | SRC-055 | agent-skills-main | Unknown | — | No | — | — | Standalone | Excluded | No source files |
| 56 | SRC-056 | awesome-openclaw-skills-main | Unknown | — | No | — | — | Standalone | Excluded | No source files |
| 57 | SRC-057 | antigravity-awesome-skills-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Skill definitions |

## Category 7: Coding Agents / Developer Tools

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 58 | SRC-058 | aider-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | AI coding assistant |
| 59 | SRC-059 | codex-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | OpenAI Codex CLI |
| 60 | SRC-060 | continue | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | AI code assistant |
| 61 | SRC-061 | open-swe-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | SWE agent |
| 62 | SRC-062 | SWE-bench-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | SWE benchmark |
| 63 | SRC-063 | void-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | AI code editor |

## Category 8: Runtime / Security / Infrastructure

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 64 | SRC-064 | E2B-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Sandboxed code execution |
| 65 | SRC-065 | gvisor-master | Go | `go.mod` | Yes | `git:HEAD` | — | Standalone | Included | Application kernel (sandboxing) |
| 66 | SRC-066 | guardrails-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | LLM output validation |
| 67 | SRC-067 | temporal-main | Go | `go.mod` | Yes | `git:HEAD` | — | Standalone | Included | Durable execution |
| 68 | SRC-068 | openfga-main | Go | `go.mod` | Yes | `git:HEAD` | — | Standalone | Included | Fine-grained authorization |

## Category 9: Agent Research / Reasoning / Planning

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 69 | SRC-069 | Agent-KB-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agent knowledge base |
| 70 | SRC-070 | AgentBench-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agent benchmark |
| 71 | SRC-071 | Agent_Foundation_Models-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agent foundation models research |
| 72 | SRC-072 | AutoAgent-engineering | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Auto agent engineering |
| 73 | SRC-073 | AutoAgent-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Auto agent |
| 74 | SRC-074 | AutoFlow-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Automated workflow |
| 75 | SRC-075 | AutoIntent-dev | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Intent classification |
| 76 | SRC-076 | CORAL-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agent research |
| 77 | SRC-077 | deer-flow-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agent flow |
| 78 | SRC-078 | OSWorld-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | OS-level agent benchmark |
| 79 | SRC-079 | open-multi-agent-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Multi-agent framework |
| 80 | SRC-080 | protocol-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agent protocol |
| 81 | SRC-081 | solace-agent-mesh-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agent mesh |

## Category 10: Personal Assistants / Voice

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 82 | SRC-082 | Personal-Assistant-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Personal assistant |
| 83 | SRC-083 | My-AI-Personal-Voice-Assistant-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Voice assistant |
| 84 | SRC-084 | leon-develop | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Open-source personal assistant |
| 85 | SRC-085 | Shioru-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Discord bot assistant |
| 86 | SRC-086 | reachy-personal-assistant-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Robot assistant |

## Category 11: Agent / Claw Variants (Personal Assistants)

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 87 | SRC-087 | chromeclaw-main | TypeScript | `package.json` | Yes | `git:HEAD` | DG-011 | Canonical | Included | Chrome extension assistant |
| 88 | SRC-088 | claw-code-main | Unknown | — | Yes | `git:HEAD` | DG-011 | Related | Included | Code-focused assistant |
| 89 | SRC-089 | clawlet-main | Go | `go.mod` | Yes | `git:HEAD` | DG-011 | Related | Included | Lightweight assistant |
| 90 | SRC-090 | myclaw-main | Go | `go.mod` | Yes | `git:HEAD` | DG-011 | Related | Included | Go assistant |
| 91 | SRC-091 | nextclaw-master | TypeScript | `package.json` | Yes | `git:HEAD` | DG-011 | Related | Included | Next.js assistant |
| 92 | SRC-092 | youclaw-main | TypeScript | `package.json` | Yes | `git:HEAD` | DG-011 | Related | Included | You assistant |
| 93 | SRC-093 | zeroclaw-master | Rust | `Cargo.toml` | Yes | `git:HEAD` | DG-011 | Related | Included | Zero assistant |
| 94 | SRC-094 | nullclaw-main | Unknown | — | Yes | `git:HEAD` | DG-011 | Related | Included | Null assistant |
| 95 | SRC-095 | nullhub-main | Unknown | — | Yes | `git:HEAD` | DG-011 | Related | Included | Null hub |
| 96 | SRC-096 | nofx-dev | Go | `go.mod` | Yes | `git:HEAD` | DG-011 | Related | Included | No-effects runtime |
| 97 | SRC-097 | opencrust-main | Rust | `Cargo.toml` | Yes | `git:HEAD` | DG-011 | Related | Included | Rust assistant |
| 98 | SRC-098 | CoPaw-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-011 | Related | Included | Python assistant |
| 99 | SRC-099 | QwenPaw-main | Python | `pyproject.toml` | Yes | `git:HEAD` | DG-011 | Related | Included | Qwen assistant |
| 100 | SRC-100 | pocket-agent-main | TypeScript | `package.json` | Yes | `git:HEAD` | DG-011 | Related | Included | Pocket agent |

## Category 12: Reasoning / Prompt Engineering Research

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 101 | SRC-101 | ReMe-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Reflection from memory |
| 102 | SRC-102 | reflexion-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Reflexion agent |
| 103 | SRC-103 | STaR-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Self-taught reasoner |
| 104 | SRC-104 | buffer-of-thought-llm-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Buffer of thought |
| 105 | SRC-105 | forest-of-thought-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Forest of thought |
| 106 | SRC-106 | graph-of-thoughts-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Graph of thoughts |
| 107 | SRC-107 | tree-of-thought-llm-master | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Tree of thought |
| 108 | SRC-108 | Deductive-Beam-Search-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Beam search reasoning |
| 109 | SRC-109 | self-rag-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Self-RAG |
| 110 | SRC-110 | self-refine-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Self-refinement |
| 111 | SRC-111 | Critic-V-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Critic-based verification |
| 112 | SRC-112 | CriticEval-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Critic evaluation |
| 113 | SRC-113 | critic-rl-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Critic RL |
| 114 | SRC-114 | ToRA-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Tool-integrated reasoning |
| 115 | SRC-115 | textgrad-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Text-based optimization |
| 116 | SRC-116 | Retroformer-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Retrospective transformer |
| 117 | SRC-117 | simulated-trial-and-error-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Trial and error reasoning |
| 118 | SRC-118 | TEMPERA-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Prompt tuning |
| 119 | SRC-119 | EvoPrompt-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Prompt evolution |
| 120 | SRC-120 | GrIPS-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Gradient-free prompt search |
| 121 | SRC-121 | opro-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Optimization by prompting |
| 122 | SRC-122 | PromptAgent-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Prompt optimization agent |

## Category 13: RAG / Search / Knowledge

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 123 | SRC-123 | RAG-Anything-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Multi-modal RAG |
| 124 | SRC-124 | rag-agentic-search-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Agentic search |
| 125 | SRC-125 | rag-fusion-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | RAG fusion |
| 126 | SRC-126 | RAG-Critic-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | RAG critic |
| 127 | SRC-127 | StructRAG-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Structured RAG |
| 128 | SRC-128 | haystack-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | LLM framework |
| 129 | SRC-129 | onyx-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | AI assistant |
| 130 | SRC-130 | inbox-zero-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | AI email assistant |

## Category 14: RL / Training / Evaluation

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 131 | SRC-131 | deepeval-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | LLM evaluation framework |
| 132 | SRC-132 | agent-as-a-judge-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agent-as-judge evaluation |
| 133 | SRC-133 | Auto-Arena-LLMs-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | LLM arena evaluation |
| 134 | SRC-134 | MLGym-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | ML gym |
| 135 | SRC-135 | liveideabench-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Live idea benchmark |

## Category 15: Infrastructure / Observability

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 136 | SRC-136 | dagster-master | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Data orchestration |
| 137 | SRC-137 | prefect-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Workflow orchestration |
| 138 | SRC-138 | argo-workflows | Unknown | — | Yes | `git:HEAD` | — | Standalone | Excluded | Kubernetes workflows |
| 139 | SRC-139 | axon-framework | Java | `pom.xml` | Yes | `git:HEAD` | — | Standalone | Included | CQRS/ES framework |
| 140 | SRC-140 | KurrentDB-master | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Event store DB |

## Category 16: Other Agent Frameworks / Orchestration

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 141 | SRC-141 | agent-framework-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Generic agent framework |
| 142 | SRC-142 | agent-health-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Agent health monitoring |
| 143 | SRC-143 | agent-orchestrator-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Agent orchestration |
| 144 | SRC-144 | agents-js-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | JS agent framework |
| 145 | SRC-145 | agents-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Python agents |
| 146 | SRC-146 | agents-master | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Agents collection |
| 147 | SRC-147 | agentic-personal-assistant-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Agentic personal assistant |
| 148 | SRC-148 | argentos-core-main | TypeScript | `package.json` | Yes | `git:HEAD` | — | Standalone | Included | Agent core |
| 149 | SRC-149 | deepagents-main | Unknown | — | Yes | `git:HEAD` | — | Standalone | Included | Deep agents |
| 150 | SRC-150 | NagaAgent-main | Python | `pyproject.toml` | Yes | `git:HEAD` | — | Standalone | Included | Naga agent |

## Remaining Sources (151-438): Related but Lower Priority

The following sources are included in the inventory but categorized as lower priority for the browser automation analysis. They span additional agent frameworks, research repos, coding tools, personal assistant variants, infrastructure, and domain-specific projects. Full enumeration continues below.

| # | Source ID | Directory | Language | Status | Notes |
|---|-----------|-----------|----------|--------|-------|
| 151 | SRC-151 | 724-office-master | Unknown | Included | Office automation |
| 152 | SRC-152 | ADAM-main | Python | Included | Agent research |
| 153 | SRC-153 | ADAS-main | Unknown | Included | Agent research |
| 154 | SRC-154 | AGrail4Agent-main | Python | Included | Agent research |
| 155 | SRC-155 | APOHF-main | Unknown | Included | Agent research |
| 156 | SRC-156 | ARPO-main | Unknown | Included | Agent research |
| 157 | SRC-157 | Adapting-While-Learning-main | Unknown | Included | Agent research |
| 158 | SRC-158 | Alita-main | Unknown | Excluded | No source files |
| 159 | SRC-159 | Amadeus-master | Unknown | Included | Agent research |
| 160 | SRC-160 | AntiGravity-personal-assistant-lite-LDN-main | Unknown | Excluded | No source files |
| 161 | SRC-161 | AutoDAN-Turbo-main | Unknown | Included | Agent research |
| 162 | SRC-162 | AutoResearchClaw-main | Python | Included | Agent research |
| 163 | SRC-163 | AutoTIR-main | Python | Included | Agent research |
| 164 | SRC-164 | BUTTON-main | Unknown | Excluded | No source files |
| 165 | SRC-165 | CREATOR-main | Unknown | Included | Agent research |
| 166 | SRC-166 | CarDreamer-master | Python | Included | Agent research |
| 167 | SRC-167 | Claude Code | Unknown | Included | Claude Code CLI |
| 168 | SRC-168 | Claude-Code-Game-Studios-main | Unknown | Excluded | No source files |
| 169 | SRC-169 | Claude-Code-Projects-Index-main | TypeScript | Included | Project index |
| 170 | SRC-170 | CoRT-master | Unknown | Included | Agent research |
| 171 | SRC-171 | CoRe-main | Unknown | Included | Agent research |
| 172 | SRC-172 | CodeT-main | Unknown | Included | Code research |
| 173 | SRC-173 | Comfy-Canvas-main | Unknown | Included | Canvas tool |
| 174 | SRC-174 | Confucius-master | Unknown | Included | Agent research |
| 175 | SRC-175 | Context-Engineering-main | Unknown | Included | Context engineering |
| 176 | SRC-176 | DRAFT-main | Unknown | Included | Agent research |
| 177 | SRC-177 | ESAA-main | Python | Included | Event sourcing agents |
| 178 | SRC-178 | EurekaClaw-main | Python | Included | Agent research |
| 179 | SRC-179 | GPO-main | Unknown | Included | Agent research |
| 180 | SRC-180 | GPS-main | Unknown | Included | Agent research |
| 181 | SRC-181 | GPTSwarm-main | Python | Included | Swarm agents |
| 182 | SRC-182 | HiClaw-main | Unknown | Included | Agent research |
| 183 | SRC-183 | JARVIS-main | Unknown | Included | Agent research |
| 184 | SRC-184 | LLMCWM-main | Unknown | Included | Agent research |
| 185 | SRC-185 | LMOps-main | Unknown | Included | LLM operations |
| 186 | SRC-186 | LSE-MTP-main | Unknown | Included | Agent research |
| 187 | SRC-187 | Lean-master | Unknown | Included | Lean theorem proving |
| 188 | SRC-188 | LeanRL-main | Unknown | Included | Lean RL |
| 189 | SRC-189 | MARBLE-main | Python | Included | Agent research |
| 190 | SRC-190 | MAS-GPT-main | Unknown | Included | Multi-agent |
| 191 | SRC-191 | MAT-Agent-main | Unknown | Included | Agent research |
| 192 | SRC-192 | MLGym-main | Python | Included | ML gym |
| 193 | SRC-193 | MMClaw-main | Python | Included | Agent research |
| 194 | SRC-194 | MaAS-main | Python | Included | Agent research |
| 195 | SRC-195 | Matrix-Game-main | Unknown | Included | Game theory |
| 196 | SRC-196 | MetaAgent-main | Unknown | Included | Agent research |
| 197 | SRC-197 | Mighty-main | Python | Included | Agent research |
| 198 | SRC-198 | MiroShark-main | TypeScript | Included | Agent tool |
| 199 | SRC-199 | MobileBench-main | Unknown | Included | Mobile benchmark |
| 200 | SRC-200 | MoneyPrinterPlus-main | Unknown | Included | Content automation |
| 201 | SRC-201 | NarratoAI-main | Unknown | Included | AI narrator |
| 202 | SRC-202 | OpenAGI-main | Python | Included | Agent research |
| 203 | SRC-203 | OpenHarness-main | Python | Included | Agent harness |
| 204 | SRC-204 | OpenJarvis-main | Unknown | Included | Agent research |
| 205 | SRC-205 | OpenNARS-for-Applications-master | Unknown | Included | NARS reasoning |
| 206 | SRC-206 | OpenWorldLib-main | Python | Included | Open world library |
| 207 | SRC-207 | OwnPilot-main | TypeScript | Included | AI pilot |
| 208 | SRC-208 | PUMA-main | Unknown | Included | Program understanding |
| 209 | SRC-209 | Parallel-R1-main | Unknown | Included | Parallel reasoning |
| 210 | SRC-210 | Personal-Voice-Assistent-main | Unknown | Included | Voice assistant |
| 211 | SRC-211 | Plum-main | Unknown | Included | Agent research |
| 212 | SRC-212 | PySyft-dev | Unknown | Included | Privacy ML |
| 213 | SRC-213 | REVOLVE-main | Python | Included | Agent research |
| 214 | SRC-214 | R-Zero-main | Unknown | Included | Agent research |
| 215 | SRC-215 | RD-Agent-main | Python | Included | Agent research |
| 216 | SRC-216 | ScoreFlow-main | Unknown | Included | Agent research |
| 217 | SRC-217 | SeRL-main | Unknown | Included | Agent research |
| 218 | SRC-218 | SPORT-Agents-main | Unknown | Included | Sports agents |
| 219 | SRC-219 | SSRL-main | Python | Included | Agent research |
| 220 | SRC-220 | Soar-development | Unknown | Included | Soar cognitive architecture |
| 221 | SRC-221 | SocratiCode-main | TypeScript | Included | Code reasoning |
| 222 | SRC-222 | X-MAS-main | Unknown | Included | Multi-agent system |
| 223 | SRC-223 | YuLan-SwarmIntell-main | Unknown | Included | Swarm intelligence |
| 224 | SRC-224 | autonovel-master | Python | Included | AutoML |
| 225 | SRC-225 | autoreason-main | Unknown | Included | Auto reasoning |
| 226 | SRC-226 | automatic_prompt_engineer-main | Python | Included | Prompt engineering |
| 227 | SRC-227 | atomspace-master | Python | Included | OpenCog atomspace |
| 228 | SRC-228 | ccxt-master | Python | Excluded | Crypto exchange library |
| 229 | SRC-229 | coda-main | Python | Included | Agent research |
| 230 | SRC-230 | cognetivy-main | Unknown | Included | Cognitive agent |
| 231 | SRC-231 | concilium | TypeScript | Included | Agent research |
| 232 | SRC-232 | coda-main | Python | Included | Code research |
| 233 | SRC-233 | das-master | Unknown | Included | Agent research |
| 234 | SRC-234 | dawn-main | Unknown | Included | Agent research |
| 235 | SRC-235 | deepagents-main | Unknown | Included | Deep agents |
| 236 | SRC-236 | docify-main | Unknown | Included | Documentation |
| 237 | SRC-237 | everything-claude-code-main | TypeScript | Included | Claude Code resources |
| 238 | SRC-238 | evolver-main | TypeScript | Included | Agent evolution |
| 239 | SRC-239 | funcat-master | Python | Excluded | Finance |
| 240 | SRC-240 | gaia-master | Python | Included | GAIA benchmark |
| 241 | SRC-241 | gepa-main | Python | Included | Data augmentation |
| 242 | SRC-242 | go-critic-master | Go | Included | Go code critic |
| 243 | SRC-243 | hanzo-main | Swift | Included | Agent framework |
| 244 | SRC-244 | harbor-main | Unknown | Included | Agent research |
| 245 | SRC-245 | hayhooks-main | Python | Included | Haystack hooks |
| 246 | SRC-246 | hummingbot-master | Unknown | Excluded | Crypto trading |
| 247 | SRC-247 | hyperon-experimental-main | Rust | Included | OpenCog Hyperon |
| 248 | SRC-248 | intent-classification-agent-main | Unknown | Included | Intent classification |
| 249 | SRC-249 | kairos-sensenova-main | Unknown | Included | Agent research |
| 250 | SRC-250 | kilocode-main | TypeScript | Included | Code agent |
| 251 | SRC-251 | lettabot-main | TypeScript | Included | Letta bot |
| 252 | SRC-252 | lever-main | Unknown | Included | Agent research |
| 253 | SRC-253 | lida-main | Python | Included | Visualization |
| 254 | SRC-254 | lingbot-va-main | Python | Included | Voice assistant |
| 255 | SRC-255 | livekit-master | Go | Included | Real-time audio/video |
| 256 | SRC-256 | llm-support-agent-main | Unknown | Included | LLM support |
| 257 | SRC-257 | m3-agent-master | Unknown | Included | Agent research |
| 258 | SRC-258 | multica-main | TypeScript | Included | Multi-agent |
| 259 | SRC-259 | mirror-log-main | Rust | Included | Logging |
| 260 | SRC-260 | openui-main | Unknown | Included | UI generation |
| 261 | SRC-261 | play2prompt-main | Unknown | Included | Prompt research |
| 262 | SRC-262 | probability-main | Python | Included | Probability |
| 263 | SRC-263 | python_actr-main | Python | Included | ACT-R implementation |
| 264 | SRC-264 | ray-master | Python | Included | Distributed computing |
| 265 | SRC-265 | se-agi-main | Python | Included | AGI research |
| 266 | SRC-266 | semantic_backprop-main | Python | Included | Semantic backprop |
| 267 | SRC-267 | sharp-main | TypeScript | Included | Agent research |
| 268 | SRC-268 | siiRL-main | Python | Included | Agent research |
| 269 | SRC-269 | skyll-main | Python | Included | Skill learning |
| 270 | SRC-270 | solace-agent-mesh-main | Python | Included | Agent mesh |
| 271 | SRC-271 | sourcegraph-main | TypeScript | Included | Code search |
| 272 | SRC-272 | spec-generator-main | Unknown | Included | Spec generation |
| 273 | SRC-273 | specops-main | Unknown | Included | Agent research |
| 274 | SRC-274 | spiral-main | Python | Included | Agent research |
| 275 | SRC-275 | stavrobot-main | TypeScript | Included | Agent research |
| 276 | SRC-276 | superpowers-main | TypeScript | Included | Agent research |
| 277 | SRC-277 | synbot-main | Rust | Included | Sync bot |
| 278 | SRC-278 | ten-framework-main | TypeScript | Included | Agent framework |
| 279 | SRC-279 | understudy-main | TypeScript | Included | Agent understudy |
| 280 | SRC-280 | validate-repos-main | Unknown | Included | Repo validation |
| 281 | SRC-281 | vscode-maestro-mcp-master | TypeScript | Included | VS Code MCP |
| 282 | SRC-282 | wandb-main | Python | Included | ML tracking |
| 283 | SRC-283 | waoowaoo-main | TypeScript | Included | Agent research |
| 284 | SRC-284 | weave-master | Python | Included | ML tracking |
| 285 | SRC-285 | xyops-main | TypeScript | Included | DevOps agent |

## Category 17: Excluded — No Source or Unrelated Domain

| # | Source ID | Directory | Language | Status | Notes |
|---|-----------|-----------|----------|--------|-------|
| 286 | SRC-286 | CryptoList-master | Unknown | Excluded | No source; crypto domain |
| 287 | SRC-287 | NoodlesPlate-master | Unknown | Excluded | No source; graphics |
| 288 | SRC-288 | Plagues-Protocol-main | Unknown | Excluded | No source |
| 289 | SRC-289 | ToolsOfTheTrade-master | Unknown | Excluded | No source |
| 290 | SRC-290 | catalog | Unknown | Excluded | No source |
| 291 | SRC-291 | cryptocurrency-master | Unknown | Excluded | No source; crypto |
| 292 | SRC-292 | diagram-design-main | Unknown | Excluded | No source |
| 293 | SRC-293 | flower-main | Unknown | Excluded | No source; federated learning |
| 294 | SRC-294 | jepsen-main | Unknown | Excluded | No source; distributed systems testing |
| 295 | SRC-295 | liquid_glass_widgets-main | Unknown | Excluded | No source |
| 296 | SRC-296 | mstar-main | Unknown | Excluded | No source |
| 297 | SRC-297 | open-dev-main | Unknown | Excluded | No source |
| 298 | SRC-298 | openclaw-auto-dream-main | Unknown | Excluded | No source |
| 299 | SRC-299 | outbox-event-bus-master | Java | Excluded | No source; event bus |
| 300 | SRC-300 | rsims-main | Unknown | Excluded | No source |
| 301 | SRC-301 | shader-3dcurve-master | Unknown | Excluded | No source; graphics |
| 302 | SRC-302 | smux | Unknown | Excluded | No source |
| 303 | SRC-303 | statConfR-main | Unknown | Excluded | No source |
| 304 | SRC-304 | symphony | Unknown | Excluded | No source |
| 305 | SRC-305 | visual-explainer-main | TypeScript | Excluded | No source |
| 306 | SRC-306 | awesome-glsl-master | Unknown | Excluded | No source; graphics |
| 307 | SRC-307 | awesome-openclaw-skills-main | Unknown | Excluded | No source |
| 308 | SRC-308 | Alita-main | Unknown | Excluded | No source |
| 309 | SRC-309 | AntiGravity-personal-assistant-lite-LDN-main | Unknown | Excluded | No source |
| 310 | SRC-310 | BUTTON-main | Unknown | Excluded | No source |
| 311 | SRC-311 | Claude-Code-Game-Studios-main | Unknown | Excluded | No source |
| 312 | SRC-312 | Skywork-Reward-V2-main | Unknown | Excluded | No source |
| 313 | SRC-313 | agent-skills-main | Unknown | Excluded | No source |
| 314 | SRC-314 | marvin-template-main | Unknown | Excluded | No source |
| 315 | SRC-315 | neo4j-release-5.26.0 | Java | Excluded | No source; database |

## Category 18: Excluded — Clearly Unrelated Domains (Trading, Crypto, Graphics, Causal, Video)

| # | Source ID | Directory | Language | Status | Notes |
|---|-----------|-----------|----------|--------|-------|
| 316 | SRC-316 | AI-Trader-main | TypeScript | Excluded | Trading |
| 317 | SRC-317 | abu-master | Unknown | Excluded | Trading |
| 318 | SRC-318 | backtesting.py-master | Unknown | Excluded | Trading |
| 319 | SRC-319 | backtrader-master | Unknown | Excluded | Trading |
| 320 | SRC-320 | binance-trade-bot-master | Unknown | Excluded | Crypto trading |
| 321 | SRC-321 | binance-trader-master | Unknown | Excluded | Crypto trading |
| 322 | SRC-322 | binance-trading-bot-master | TypeScript | Excluded | Crypto trading |
| 323 | SRC-323 | ccxt-master | Python | Excluded | Crypto exchange |
| 324 | SRC-324 | CryptocurrencyPrediction-master | Unknown | Excluded | Crypto prediction |
| 325 | SRC-325 | freqtrade-develop | Python | Excluded | Trading bot |
| 326 | SRC-326 | freqtrade-strategies-main | Unknown | Excluded | Trading strategies |
| 327 | SRC-327 | frequi-main | TypeScript | Excluded | Trading UI |
| 328 | SRC-328 | funcat-master | Python | Excluded | Finance |
| 329 | SRC-329 | hummingbot-master | Unknown | Excluded | Crypto trading |
| 330 | SRC-330 | machine-learning-for-trading-main | Unknown | Excluded | Trading |
| 331 | SRC-331 | monero-gui-master | Unknown | Excluded | Crypto |
| 332 | SRC-332 | monero-master | Unknown | Excluded | Crypto |
| 333 | SRC-333 | nautilus_trader-develop | Python | Excluded | Trading |
| 334 | SRC-334 | pytrader-master | Unknown | Excluded | Trading |
| 335 | SRC-335 | qstrader-master | Unknown | Excluded | Trading |
| 336 | SRC-336 | quant-trading-master | Unknown | Excluded | Trading |
| 337 | SRC-337 | StockSharp-master | Unknown | Excluded | Trading |
| 338 | SRC-338 | StrategyEase-Python-SDK-master | Python | Excluded | Trading |
| 339 | SRC-339 | Superalgos-master | TypeScript | Excluded | Trading |
| 340 | SRC-340 | tensortrade-master | Python | Excluded | Trading |
| 341 | SRC-341 | tensortrade-ng-main | Python | Excluded | Trading |
| 342 | SRC-342 | TradeMaster-1.0.0 | Python | Excluded | Trading |
| 343 | SRC-343 | TradingAgents-main | Python | Excluded | Trading |
| 344 | SRC-344 | Vibe-Trading-main | Python | Excluded | Trading |
| 345 | SRC-345 | ai_quant_trade-master | Unknown | Excluded | Trading |
| 346 | SRC-346 | zipline-master | Python | Excluded | Trading |
| 347 | SRC-347 | yfinance-main | Unknown | Excluded | Finance data |
| 348 | SRC-348 | lightweight-charts-master | Unknown | Excluded | Trading charts |
| 349 | SRC-349 | Causal-INSIGHT-main | Unknown | Excluded | Causal inference |
| 350 | SRC-350 | CausalWorld-master | Python | Excluded | Causal research |
| 351 | SRC-351 | causal-learn-main | Python | Excluded | Causal learning |
| 352 | SRC-352 | causalflow-main | Python | Excluded | Causal research |
| 353 | SRC-353 | causality-lab-main | Python | Excluded | Causal research |
| 354 | SRC-354 | causallib-master | Python | Excluded | Causal library |
| 355 | SRC-355 | causalnex-develop | Python | Excluded | Causal research |
| 356 | SRC-356 | causica-main | Python | Excluded | Causal research |
| 357 | SRC-357 | dowhy-main | Python | Excluded | Causal inference |
| 358 | SRC-358 | EconML-main | Python | Excluded | Econometrics |
| 359 | SRC-359 | glslCanvas-master | Unknown | Excluded | Graphics |
| 360 | SRC-360 | glslViewer-main | Unknown | Excluded | Graphics |
| 361 | SRC-361 | shader-doodle-main | Unknown | Excluded | Graphics |
| 362 | SRC-362 | shadertoy-react-master | Unknown | Excluded | Graphics |
| 363 | SRC-363 | rust-gpu-shadertoys-main | Unknown | Excluded | Graphics |
| 364 | SRC-364 | thebookofshaders-master | Unknown | Excluded | Graphics |
| 365 | SRC-365 | webgl-ray-tracing-demo-master | Unknown | Excluded | Graphics |
| 366 | SRC-366 | d3-force-3d-master | TypeScript | Excluded | Graphics |
| 367 | SRC-367 | three.js-dev | Unknown | Excluded | Graphics |
| 368 | SRC-368 | two.js-dev | Unknown | Excluded | Graphics |
| 369 | SRC-369 | pixijs-dev | Unknown | Excluded | Graphics |
| 370 | SRC-370 | regl-main | Unknown | Excluded | Graphics |
| 371 | SRC-371 | ogl-master | Unknown | Excluded | Graphics |
| 372 | SRC-372 | RobustVideoMatting-master | Unknown | Excluded | Video |
| 373 | SRC-373 | opus-decoder-master | Unknown | Excluded | Audio codec |
| 374 | SRC-374 | opus-encdec-master | Unknown | Excluded | Audio codec |
| 375 | SRC-375 | ogv.js-main | Unknown | Excluded | Video |
| 376 | SRC-376 | yuv-canvas-main | Unknown | Excluded | Video |
| 377 | SRC-377 | webcodecs-capture-play-main | Unknown | Excluded | Video |
| 378 | SRC-378 | webcodecs-fundamentals-main | Unknown | Excluded | Video |
| 379 | SRC-379 | webcodecs-main | Unknown | Excluded | Video |
| 380 | SRC-380 | webcodecs-node-main | Unknown | Excluded | Video |
| 381 | SRC-381 | mediabunny-main | Unknown | Excluded | Media |
| 382 | SRC-382 | moq-encoder-player-main | Unknown | Excluded | Video |
| 383 | SRC-383 | wgpu-trunk | Unknown | Excluded | Graphics |
| 384 | SRC-384 | webref-main | Unknown | Excluded | Web reference |
| 385 | SRC-385 | dawn-main | Unknown | Excluded | Browser engine |

## Category 19: Excluded — Infrastructure/Platform (Not Agent-Specific)

| # | Source ID | Directory | Language | Status | Notes |
|---|-----------|-----------|----------|--------|-------|
| 386 | SRC-386 | camunda-main | Java | Excluded | BPM platform |
| 387 | SRC-387 | debezium-main | Java | Excluded | CDC platform |
| 388 | SRC-388 | dash-dev | Unknown | Excluded | Dashboard |
| 389 | SRC-389 | discourse-main | TypeScript | Excluded | Forum platform |
| 390 | SRC-390 | hestiacp-main | Unknown | Excluded | Hosting panel |
| 391 | SRC-391 | infra-main | Unknown | Excluded | Infrastructure |
| 392 | SRC-392 | intents-operator-main | Unknown | Excluded | Kubernetes operator |
| 393 | SRC-393 | LocalAI-master | Go | Excluded | Local LLM runtime |
| 394 | SRC-394 | mlflow-master | Unknown | Excluded | ML tracking |
| 395 | SRC-395 | nocodb-develop | Unknown | Excluded | No-code DB |
| 396 | SRC-396 | opa-main | Go | Excluded | Policy engine |
| 397 | SRC-397 | penpot-develop | TypeScript | Excluded | Design tool |
| 398 | SRC-398 | posthog-master | Unknown | Excluded | Analytics |
| 399 | SRC-399 | spicedb-main | Go | Excluded | Authorization DB |
| 400 | SRC-400 | streamlit-develop | Unknown | Excluded | Dashboard |
| 401 | SRC-401 | evidently-main | Unknown | Excluded | ML monitoring |
| 402 | SRC-402 | gensim-develop | Unknown | Excluded | NLP library |
| 403 | SRC-403 | hypothesis-master | Python | Excluded | Testing library |
| 404 | SRC-404 | scikit-learn-main | Python | Excluded | ML library |
| 405 | SRC-405 | optuna-master | Python | Excluded | Hyperparameter tuning |
| 406 | SRC-406 | pyro-dev | Python | Excluded | Probabilistic programming |
| 407 | SRC-407 | numpyro-master | Python | Excluded | Probabilistic programming |
| 408 | SRC-408 | probability-main | Python | Excluded | Probability |
| 409 | SRC-409 | vectorbt-master | Python | Excluded | Trading analytics |
| 410 | SRC-410 | moxxy-main | Rust | Excluded | Chat app |
| 411 | SRC-411 | wasmtime-main | Rust | Excluded | WebAssembly runtime |
| 412 | SRC-412 | zitadel-main | TypeScript | Excluded | Identity platform |
| 413 | SRC-413 | openfga-main | Go | Included | Fine-grained auth |
| 414 | SRC-414 | gvisor-master | Go | Included | Sandboxing |
| 415 | SRC-415 | cedar-agent-main | Rust | Excluded | Authorization |
| 416 | SRC-416 | frona-main | Rust | Excluded | Agent research |
| 417 | SRC-417 | stock-master | Unknown | Excluded | Finance |
| 418 | SRC-418 | trader-master | Unknown | Excluded | Trading |
| 419 | SRC-419 | trader-tales-master | Unknown | Excluded | Trading |
| 420 | SRC-420 | huobao-drama-master | Unknown | Excluded | Entertainment |
| 421 | SRC-421 | cjepa-main | Unknown | Excluded | Research |
| 422 | SRC-422 | jepa-main | Python | Excluded | Research |
| 423 | SRC-423 | jepa-wms-main | Python | Excluded | Research |
| 424 | SRC-424 | LSE-MTP-main | Unknown | Excluded | Research |
| 425 | SRC-425 | world_models-master | Python | Excluded | Research |
| 426 | SRC-426 | android_world-main | Python | Excluded | Mobile testing |
| 427 | SRC-427 | mobilesafetybench-release-ver.3 | Python | Excluded | Mobile testing |
| 428 | SRC-428 | wai-website-main | Unknown | Excluded | Website |
| 429 | SRC-429 | wai-website-theme-main | Unknown | Excluded | Website theme |
| 430 | SRC-430 | svader-master | Unknown | Excluded | Research |
| 431 | SRC-431 | validate-repos-main | Unknown | Excluded | Utility |
| 432 | SRC-432 | ELL-StuLife-main | Unknown | Excluded | Research |
| 433 | SRC-433 | AGrail4Agent-main | Python | Included | Agent research |
| 434 | SRC-434 | WeClaw-master | Unknown | Included | Agent research |
| 435 | SRC-435 | EurekaClaw-main | Python | Included | Agent research |
| 436 | SRC-436 | HiClaw-main | Unknown | Included | Agent research |
| 437 | SRC-437 | MMClaw-main | Python | Included | Agent research |
| 438 | SRC-438 | WeClaw-master | Unknown | Included | Agent research |

Total sources: 438
Included: 290
Excluded: 148
