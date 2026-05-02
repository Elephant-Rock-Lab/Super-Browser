# Generic Analysis Taxonomy

> **Taxonomy Version**: v1.0

10 universal software categories. Every software project can be mapped to these categories regardless of domain. Domain packs (in `domains/`) specialize each category with domain-specific types, look-for criteria, and extract targets.

## How to Use

During Phase -1 (Domain Discovery), map the target project's source tree to these categories:

1. Walk directories and files
2. Assign each directory/module to the best-fitting category
3. Score each category by what percentage of the source tree it covers
4. High-scoring categories indicate the project's primary concerns
5. Select or create a domain pack that covers the high-scoring categories

During Phase 2A (Gap-Blind Deep Read), use these categories to ensure subsystem inventory completeness — check that every major subsystem maps to at least one category.

## The 10 Categories

### 1. Data & Storage

- **What it covers**: How data is stored, retrieved, indexed, cached, compressed, and managed. Persistence, schemas, migrations, query engines.
- **Generic look-for**: Storage backends (files, databases, caches), data models/schemas, query languages, indexing strategies, compression, partitioning, replication, backup/recovery, garbage collection, TTL/eviction
- **Intrinsic value indicators**: Novel storage format, efficient indexing algorithm, sophisticated caching strategy, schema evolution patterns
- **Domain examples**: AI Agents → Memory systems (episodic, semantic, procedural); GIS → Tile caches, spatial databases, GeoJSON storage

### 2. Processing & Logic

- **What it covers**: Core algorithms, computation pipelines, transformation logic, business rules, decision-making.
- **Generic look-for**: Processing pipelines, algorithm implementations, loop structures, state machines, rule engines, optimization routines, validation logic, transformation chains
- **Intrinsic value indicators**: Novel algorithm, optimized processing pipeline, sophisticated state machine, complex decision tree with fallbacks
- **Domain examples**: AI Agents → Reasoning (ReAct, CoT, planning); GIS → Spatial analysis, map rendering, coordinate transforms

### 3. Coordination

- **What it covers**: Multi-component interaction, concurrency, orchestration, task distribution, result aggregation.
- **Generic look-for**: Worker pools, task queues, pub/sub systems, orchestration engines, concurrency patterns (locks, semaphores, actors), inter-process communication, service meshes, leader election
- **Intrinsic value indicators**: Novel coordination topology, efficient work distribution, sophisticated conflict resolution, elegant result aggregation
- **Domain examples**: AI Agents → Multi-agent coordination; GIS → Distributed map rendering, parallel spatial queries

### 4. Perception & Input

- **What it covers**: How the system receives and interprets external input. Sensors, parsers, capture pipelines, signal processing.
- **Generic look-for**: Input parsers, capture pipelines, signal processing, format converters, protocol handlers, streaming consumers, webhook receivers, file watchers
- **Intrinsic value indicators**: Multi-format parsing, real-time streaming, sophisticated preprocessing, adaptive capture
- **Domain examples**: AI Agents → Vision, voice, document parsing; GIS → Satellite imagery ingestion, sensor data processing, GPS input

### 5. Goal & Planning

- **What it covers**: Goal definition, prioritization, decomposition, progress tracking, resource allocation.
- **Generic look-for**: Goal/task models, priority queues, decomposition logic, progress tracking, resource budgeting, scheduling algorithms, dependency graphs, critical path analysis
- **Intrinsic value indicators**: Multi-criteria prioritization, dynamic re-planning, conflict detection between goals
- **Domain examples**: AI Agents → Goal management; GIS → Route planning, resource optimization, delivery scheduling

### 6. Autonomy & Scheduling

- **What it covers**: Self-initiated actions, scheduled tasks, event-driven triggers, background processing.
- **Generic look-for**: Cron systems, event listeners, trigger mechanisms, idle-time processing, self-monitoring, health checks, auto-scaling, periodic maintenance, heartbeat systems
- **Intrinsic value indicators**: Sophisticated trigger composition, adaptive scheduling, self-healing mechanisms
- **Domain examples**: AI Agents → Autonomous cycle, curiosity-driven exploration; GIS → Auto-update tile caches, scheduled data refresh

### 7. Knowledge & Representation

- **What it covers**: How domain knowledge is structured, stored, and queried. Models, graphs, ontologies, embeddings.
- **Generic look-for**: Knowledge graphs, ontologies, vector databases, embedding pipelines, entity resolution, fact verification, schema definition languages, catalog systems
- **Intrinsic value indicators**: Novel representation format, efficient query engine, sophisticated entity resolution, multi-modal knowledge
- **Domain examples**: AI Agents → Knowledge graph, world model; GIS → Geospatial feature model, terrain representation

### 8. Adaptation & Learning

- **What it covers**: How the system changes behavior based on experience. Skill creation, parameter tuning, behavioral modification.
- **Generic look-for**: Learning loops, skill/capability definitions, performance metrics, lesson extraction, parameter optimization, A/B testing, feedback incorporation, evolutionary systems
- **Intrinsic value indicators**: Novel learning algorithm, multi-dimensional fitness scoring, safe rollback mechanisms
- **Domain examples**: AI Agents → Self-improvement, skill lifecycle; GIS → Adaptive rendering, quality-based cache tuning

### 9. Integration & Extension

- **What it covers**: How the system connects to external services and how it allows extension. APIs, plugins, protocols, adapters.
- **Generic look-for**: Plugin systems, extension registries, API clients, protocol adapters, middleware chains, provider factories, health checks, connection pooling, capability advertisement
- **Intrinsic value indicators**: Clean plugin interface, capability-based routing, sophisticated middleware pipeline, multi-protocol support
- **Domain examples**: AI Agents → Provider registry, MCP, tool use; GIS → WMS/WFS protocols, format adapters (GeoJSON, Shapefile, GeoTIFF)

### 10. Governance & Quality

- **What it covers**: Validation, security, compliance, audit trails, output verification, access control.
- **Generic look-for**: Validation pipelines, audit logging, access control, content filtering, output verification, compliance checks, rate limiting, sandboxing, permission systems
- **Intrinsic value indicators**: Multi-layer validation, comprehensive audit trail, constitutional constraints, human-in-the-loop
- **Domain examples**: AI Agents → Value alignment, output validation; GIS → Data quality checks, coordinate validation, compliance (GDPR, etc.)

## Category Coverage Scoring

When mapping a target project's source tree:

| Score | Meaning |
|-------|---------|
| High (≥30% of source files) | Core concern of the project |
| Medium (10-29%) | Supporting concern |
| Low (<10%) | Peripheral or absent |

Categories with High or Medium scores should have corresponding pillars in the domain pack. If a category has no matching pillar, the domain discovery step should propose one.

## Creating a New Domain Pack

A domain pack file (in `domains/`) defines:

1. **Pillar definitions**: One or more pillars per generic category, with domain-specific types, look-for criteria, and extract targets
2. **Category specialization**: How each generic category maps to domain-specific concepts
3. **Cross-pillar relationships**: Which pillars commonly interact
4. **Common gaps**: Typical architectural gaps in this domain

See `domains/ai-agents.md` for a complete example.
