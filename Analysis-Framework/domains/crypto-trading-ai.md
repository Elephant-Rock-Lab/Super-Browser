# Domain Pack: AI-Powered Cryptocurrency Trading

> **Version**: v1.0
> **Taxonomy Coverage**: All 10 categories
> **Pillar Count**: 18
> **Derived from**: Generic taxonomy v1.0, specialized for AI-powered crypto trading platforms combining quantitative finance with LLM-driven strategy generation, causal inference, and autonomous execution

## Overview

Specializes the generic taxonomy for AI-powered cryptocurrency trading platforms — systems that combine exchange connectivity, market data processing, strategy authoring, backtesting, and live execution with AI capabilities including natural language strategy generation, multi-agent coordination, causal inference, LLM-based reasoning, and graduated autonomous trading. Covers platforms that extend existing trading bot frameworks (e.g., Freqtrade) with NL→DSL→code pipelines, vectorized backtesting, regime-aware strategy adaptation, triple-barrier risk methods, and RAG-grounded knowledge systems.

## Pillar Definitions

### 1. Market Data Pipeline

**Generic category**: Data & Storage + Perception & Input
**Types**: OHLCV candle data, tick/trade data, order book snapshots, funding rates, liquidation data, alternative data (sentiment, on-chain, social), real-time streaming, batch historical
**Look for**:
- Data provider abstractions — Fetcher/Transform/Extract patterns, provider factory with multi-source support
- Historical data fetching — paginated API calls, automatic rate-limit handling, gap detection and backfill
- Data caching — parquet/arrow columnar storage, cache key schemes (exchange/symbol/timeframe), incremental merge with existing cache, date-range partitioning
- Real-time streaming — WebSocket price feeds, order book streaming, trade aggregation into candles
- Time-series storage — time-series databases (QuestDB, TimescaleDB), compression, retention policies
- Data normalization — timezone handling, missing bar interpolation, split/dividend adjustment (equities), ticker remapping
- Alternative data ingestion — sentiment feeds, on-chain metrics, social signals, news NLP pipelines
- Data validation — OHLCV sanity checks (high ≥ open/close, low ≤ open/close, volume ≥ 0), timestamp monotonicity
**Extract**: Data provider interfaces, cache key schemas, pagination logic, WebSocket message parsers, normalization formulas, validation rules
**Intrinsic value indicators**: Zero-gap historical data with automatic backfill, multi-source fusion with conflict resolution, sub-second streaming with tick-to-candle aggregation, adaptive caching based on data staleness

### 2. Indicator & Feature Engineering

**Generic category**: Processing & Logic
**Types**: Technical indicators (trend, momentum, volatility, volume), statistical features, cross-asset features, time features, custom composite indicators
**Look for**:
- Indicator computation engines — TA-Lib bindings, pandas-ta, vectorbt indicator factories, custom NumPy/Numba implementations
- Indicator registration — `self.I()` decorator patterns, lazy evaluation, indicator dependency graphs
- Feature engineering pipelines — rolling windows, multi-timeframe features, lag features, interaction features
- Normalization methods — z-score, min-max, percentile rank, cross-sectional normalization
- Vectorized computation — NumPy broadcasting, Numba JIT, pandas vectorized ops vs. row-wise loops
- Indicator parameter spaces — IntParameter/DecimalParameter with optimization ranges, categorical parameter support
- Feature selection — importance-based filtering, correlation pruning, mutual information scoring
- Multi-timeframe alignment — resampling higher-timeframe indicators to lower-timeframe bars, forward-fill vs. interpolation
**Extract**: Indicator computation code (formulas, window sizes, normalization), parameter range definitions, feature pipeline DAGs, multi-timeframe alignment logic
**Intrinsic value indicators**: Numba-JIT vectorized indicator computation, automatic feature selection with importance ranking, multi-timeframe feature fusion with proper lookahead prevention

### 3. Strategy Framework

**Generic category**: Processing & Logic
**Types**: Signal-based strategies, state-machine strategies, ML-predictor strategies, rule-based strategies, composite/ensemble strategies
**Look for**:
- Strategy base class — `init()`/`next()` interface pattern, data accessor with `[0]`/`[-1]` indexing
- Signal type systems — long/short/exit taxonomy, crossover operators, logical composition (AND/OR/NOT), signal strength
- Parameter definitions — typed parameters (IntParameter, DecimalParameter, BoolParameter) with optimization ranges
- Strategy DSL/JSON schema — intermediate representation between NL and code, validation rules, schema versioning
- Strategy templates — template library with Jinja2 code generation, template selection heuristics
- Order creation API — `buy()`, `sell()`, `close_position()` with stop-loss/take-profit, order tagging
- Strategy context — data access, indicator registration, order flow management, position tracking
- Strategy lifecycle — creation → validation → backtesting → approval → deployment → monitoring → retirement
- Strategy composition — combining multiple sub-strategies, priority-based signal resolution, conflict handling
**Extract**: Strategy base class interface, signal type enums, parameter schemas, DSL JSON schema, template Jinja2 patterns, order creation API signatures
**Intrinsic value indicators**: LLM-friendly two-method interface (simpler than 3-method Freqtrade pattern), typed parameter system with optimization support, JSON DSL with validation before code generation

### 4. NL Strategy Generation

**Generic category**: Processing & Logic (specialized)
**Types**: NL→DSL translation, DSL→code generation, strategy validation, strategy repair, strategy refinement
**Look for**:
- NL parsing pipeline — intent extraction, entity recognition (indicators, timeframes, conditions, actions)
- DSL generation — NL→JSON structured representation, schema validation, semantic correctness checking
- Code generation — DSL→Python strategy class, Jinja2 templates, type-annotated output, import management
- Generation validation — syntax checking, type checking, backtest smoke test, edge-case coverage
- Strategy repair — error-message-driven code repair, iterative fix-and-validate loops
- Strategy refinement — NL critique of generated strategy, improvement suggestions, parameter tuning recommendations
- Prompt engineering — few-shot examples, chain-of-thought decomposition, structured output parsing
- Template matching — mapping NL descriptions to strategy templates, template customization with parameters
- Safety checks — preventing dangerous operations (unlimited positions, missing stop-loss, look-ahead bias)
**Extract**: NL→DSL translation prompts, DSL JSON schema, code generation templates, validation pipeline stages, repair loop logic, safety constraint definitions
**Intrinsic value indicators**: Multi-stage NL→DSL→code pipeline with validation at each stage, automated repair loops with error-message feedback, safety constraints preventing dangerous strategy patterns

### 5. Backtesting Engine

**Generic category**: Processing & Logic
**Types**: Event-driven backtesting, vectorized backtesting, walk-forward analysis, Monte Carlo simulation, stress testing
**Look for**:
- Event-driven engines — bar-by-bar iteration, `init()` then `next()` per bar, realistic fill simulation
- Vectorized engines — whole-dataframe computation, vectorbt-style 100x speedup over event-driven, broadcasting operations
- Fill simulation — next-bar-open fills, slippage models (fixed, percentage, volume-based), commission structures
- Position tracking — long/short positions, stop-loss/take-profit execution, trailing stop implementation
- Performance metrics — equity curve, total return, Sharpe ratio (annualized), Sortino ratio, max drawdown, win rate, profit factor, Calmar ratio
- Walk-forward analysis — rolling in-sample/out-of-sample windows, anchored vs. rolling, fold management
- Multi-strategy backtesting — strategy portfolio simulation, cross-strategy correlation, capital allocation simulation
- Backtest result types — trade-level detail (entry/exit prices, PnL, close type, duration, fees, slippage)
- Data quality — handling missing bars, survivorship bias awareness, split/dividend adjustment
**Extract**: Backtest loop implementation, fill simulation logic, position tracking state machine, metric calculation formulas, walk-forward fold generation, result data models
**Intrinsic value indicators**: Dual-mode engine (event-driven + vectorized) with same strategy interface, walk-forward with anchored/rolling modes, realistic slippage models with market impact

### 6. Order Execution

**Generic category**: Coordination
**Types**: Market orders, limit orders, stop orders, stop-limit orders, trailing stop orders, iceburg/hidden orders, smart order routing
**Look for**:
- Order type abstractions — unified order interface across exchanges, type mapping (exchange-specific order types)
- Fill simulation — partial fill handling, fill-or-kill vs. immediate-or-cancel, fill price estimation
- Slippage models — fixed slippage, percentage-based, volume-weighted, market-impact models
- Order lifecycle — pending → open → partially_filled → filled / canceled / rejected, state transitions
- Smart order routing — multi-exchange best-price execution, latency-aware routing, liquidity detection
- Position management — concurrent position limits, position sizing (fixed, percentage, Kelly criterion), leverage handling
- Order batching — coalescing multiple signals into single orders, priority ordering
- Execution quality — implementation shortfall tracking, slippage analytics, fill rate monitoring
- Emergency handling — kill switches, position liquidation, circuit breakers on execution errors
**Extract**: Order type enums, fill simulation algorithms, slippage formulas, order state machines, smart routing decision trees, emergency shutdown sequences
**Intrinsic value indicators**: Smart order routing with multi-exchange liquidity aggregation, volume-weighted slippage with market impact modeling, circuit breaker with automatic position liquidation

### 7. Multi-Agent Coordination

**Generic category**: Coordination
**Types**: SOP (Sequential Orchestration Pipeline), parallel agent execution, hierarchical agent trees, consensus/voting agents
**Look for**:
- Agent roles — MarketAnalyst, SignalGenerator, RiskValidator, BacktestRunner, StrategyApprover, ExecutionManager
- Pipeline composition — sequential handoffs, conditional branching, parallel fan-out/fan-in, error handling between stages
- Agent communication — structured message passing, shared state protocols, context handoff formats
- Agent prompt engineering — role-specific system prompts, few-shot examples per role, output format specifications
- Consensus mechanisms — voting on signals, quality-weighted aggregation, confidence thresholds
- Agent failure handling — timeout handling, fallback agents, retry strategies, graceful degradation
- Agent orchestration — DSPy chain-of-thought composition, LangGraph-style state graphs, custom orchestrators
- Human-in-the-loop — approval gates, confirmation prompts, escalation to human decision
**Extract**: Agent role definitions, pipeline orchestration code, message schemas, consensus algorithms, failure handling state machines, approval gate interfaces
**Intrinsic value indicators**: Multi-role SOP pipeline with structured handoffs, confidence-weighted consensus across agent opinions, human approval gates at critical decision points

### 8. Portfolio Management

**Generic category**: Goal & Planning
**Types**: Capital allocation, multi-strategy portfolios, rebalancing, correlation-aware allocation, drawdown budgeting
**Look for**:
- Capital allocation models — equal-weight, risk-parity, Kelly criterion, mean-variance optimization, budget-constrained allocation
- Multi-strategy coordination — strategy signal aggregation, conflict resolution when strategies disagree, strategy weighting
- Correlation analysis — cross-strategy return correlation, rolling correlation, correlation-break detection
- Drawdown budgeting — maximum portfolio drawdown, per-strategy drawdown allocation, circuit breakers
- Rebalancing logic — time-based rebalancing, threshold-based rebalancing, drift-triggered rebalancing
- Exposure management — net exposure calculation, sector/asset concentration limits, leverage limits
- Portfolio metrics — portfolio Sharpe/Sortino, diversification ratio, marginal risk contribution, tail risk metrics
- Cash management — reserve allocation, opportunity cost, cash drag optimization
**Extract**: Allocation formulas, correlation calculation code, rebalancing trigger logic, exposure limit schemas, portfolio metric calculations
**Intrinsic value indicators**: Risk-parity allocation with dynamic correlation updating, multi-strategy conflict resolution with portfolio-level optimization, drawdown budget with automatic de-risking

### 9. Autonomous Trading

**Generic category**: Autonomy & Scheduling
**Types**: Manual mode, semi-autonomous (human approval), fully autonomous (no human intervention), confidence-based mode selection
**Look for**:
- Autonomy levels — manual (human confirms every trade), semi-autonomous (human approves above threshold), fully autonomous (system trades independently)
- Confidence scoring — strategy confidence, market regime confidence, execution confidence, composite confidence
- Mode selection logic — rule-based vs. ML-based mode selection, mode transition triggers, cooldown periods
- Scheduled operations — periodic strategy re-optimization, scheduled backtesting, regular risk review
- Trigger-based execution — price alerts, volume spikes, regime changes, news events triggering action
- Approval gates — trade size thresholds, new strategy approval, drawdown-triggered pause
- Graduated autonomy — earning trust over time, increasing autonomy after N successful trades, reducing autonomy after failures
- Emergency protocols — automatic pause on drawdown, kill switch, forced position closure, notification escalation
**Extract**: Autonomy level enum, confidence scoring formulas, mode transition state machine, approval gate configurations, emergency protocol sequences
**Intrinsic value indicators**: Graduated autonomy with trust-earning mechanism, composite confidence scoring from multiple dimensions, automatic de-escalation with human notification on anomalies

### 10. Causal Inference & Regime Detection

**Generic category**: Knowledge & Representation
**Types**: Causal discovery, causal effect estimation, treatment effect heterogeneity, regime classification, regime transition detection
**Look for**:
- Causal discovery — PC/FCI/GES algorithms (CausalLearn), constraint-based vs. score-based, variable selection
- Causal inference — DoWhy framework (model→identify→estimate→refute), treatment effect estimation, counterfactual analysis
- Heterogeneous treatment effects — EconML double-ML, causal forests, instrument variables, conditional average treatment effects
- Refutation testing — placebo tests, random common cause, data subset validation, unobserved confounder sensitivity
- Regime detection — Hidden Markov Models, change-point detection, clustering-based regime identification
- Regime features — volatility regime, trend regime, correlation regime, liquidity regime, macro regime
- Regime-aware strategy — switching strategies per regime, regime-conditional parameters, regime transition signals
- Market microstructure — order flow imbalance, bid-ask spread dynamics, trade intensity patterns
**Extract**: Causal graph structures, treatment effect estimation code, refutation test implementations, HMM state definitions, regime classification features, regime-switching logic
**Intrinsic value indicators**: Full causal pipeline (discover→estimate→refute) with automated refutation testing, HMM-based regime detection with real-time transition probability, regime-conditional strategy switching

### 11. Explanation & Diagnostics

**Generic category**: Knowledge & Representation (specialized)
**Types**: Strategy explanation, trade rationale, failure diagnosis, improvement recommendations, NL report generation
**Look for**:
- Strategy explanation — NL synthesis of strategy logic, indicator contribution analysis, decision boundary visualization
- Trade rationale — per-trade explanation of why a signal was generated, what indicators triggered, market context at trade time
- Failure diagnosis — root cause analysis of losing trades, systematic error detection, regime mismatch identification
- Improvement recommendations — TextGrad-style textual gradient descent, Reflexion-style self-critique, actionable improvement suggestions
- Backtest report generation — NL summary of backtest results, key metrics interpretation, strategy strengths/weaknesses
- Model interpretability — SHAP values for ML strategies, feature importance ranking, sensitivity analysis
- Audit trail — decision logging, signal provenance, execution rationale for compliance
**Extract**: Explanation generation prompts, failure diagnosis algorithms, improvement recommendation templates, audit log schemas, SHAP integration code
**Intrinsic value indicators**: TextGrad-style textual gradient descent for strategy improvement, per-trade NL rationale with indicator contribution, automated failure pattern detection across trade history

### 12. Strategy Optimization

**Generic category**: Adaptation & Learning
**Types**: Hyperparameter optimization, evolutionary optimization, population-based training, multi-objective optimization
**Look for**:
- Hyperopt frameworks — Optuna (TPESampler, NSGAIISampler), Hyperopt (TPE), scikit-optimize (Bayesian)
- Search spaces — parameter ranges from IntParameter/DecimalParameter, conditional search spaces, categorical choices
- Objective functions — Sharpe ratio, profit factor, Calmar ratio, custom multi-objective (return vs. drawdown)
- Pruning strategies — median stopping rule, hyperband, successive halving, early termination of poor trials
- Multi-objective optimization — Pareto front of return vs. risk, NSGA-II, weighted sum scalarization
- Parameter importance — Optuna importance analysis, ablation studies, sensitivity analysis
- Evolutionary optimization — genetic algorithms, differential evolution, covariance matrix adaptation (CMA-ES)
- Overfitting prevention — in-sample/out-of-sample split, walk-forward during optimization, complexity penalties
- Population-based training — maintaining strategy populations, fitness-proportionate selection, mutation/crossover operators
**Extract**: Optuna study configurations, objective function implementations, pruning callback code, multi-objective Pareto logic, parameter importance calculation, evolutionary operators
**Intrinsic value indicators**: Multi-objective optimization with Pareto front tracking, walk-forward-aware hyperopt preventing overfitting, population-based training with fitness-proportionate selection

### 13. Monitoring & Drift Detection

**Generic category**: Autonomy & Scheduling + Adaptation & Learning
**Types**: Data drift detection, model drift detection, live performance monitoring, anomaly detection, alerting
**Look for**:
- Data drift detection — Evidently AI profiles, KS test, PSI (Population Stability Index), feature distribution monitoring
- Concept drift detection — performance degradation tracking, statistical process control, CUSUM, Page-Hinkley
- Live performance monitoring — real-time equity curve, drawdown tracking, trade frequency, slippage tracking
- Anomaly detection — unusual trade patterns, abnormal execution latency, unexpected position sizes
- Alerting systems — threshold-based alerts, trend-based alerts, escalation policies, notification channels (Slack, email, webhook)
- Experiment tracking — MLflow integration, run comparison, parameter logging, metric history
- Dashboard/visualization — equity curves, drawdown charts, regime overlays, trade scatter plots
- Health checks — exchange connectivity monitoring, LLM API health, database connectivity, memory usage
**Extract**: Drift detection algorithm implementations, monitoring metric definitions, alert threshold configurations, MLflow experiment schemas, dashboard visualization code
**Intrinsic value indicators**: Multi-signal drift detection (data + concept + performance) with automated strategy pausing, MLflow-integrated experiment tracking with run comparison, real-time anomaly detection with automated escalation

### 14. Risk Management

**Generic category**: Governance & Quality
**Types**: Position-level risk, portfolio-level risk, triple-barrier method, stop-loss systems, exposure limits, drawdown limits
**Look for**:
- Triple-barrier method — profit-taking barrier, stop-loss barrier, time barrier, first-touch resolution
- Stop-loss systems — fixed stop, trailing stop, ATR-based stop, chandelier exit, time-based stop
- Position sizing — fixed size, percentage of equity, Kelly criterion, risk parity, volatility-adjusted sizing
- Drawdown limits — max drawdown per strategy, max drawdown per portfolio, drawdown speed limits (drawdown/time)
- Exposure limits — maximum concurrent positions, maximum sector/asset exposure, leverage limits, margin requirements
- Correlation risk — cross-position correlation limits, diversification requirements
- Risk budgeting — risk allocation per strategy, marginal risk contribution, risk contribution parity
- Circuit breakers — per-strategy pause, portfolio-wide halt, exchange connectivity pause, daily loss limit
- Tail risk management — maximum position loss, gap risk handling, black swan protection
**Extract**: Triple-barrier implementation, stop-loss formulas, position sizing algorithms, drawdown tracking code, exposure limit schemas, circuit breaker state machines
**Intrinsic value indicators**: Triple-barrier method with all three barriers configurable, volatility-adjusted Kelly criterion position sizing, multi-level circuit breakers (strategy→portfolio→system)

### 15. Validation & Robustness

**Generic category**: Governance & Quality
**Types**: Walk-forward validation, cross-validation, overfitting detection, stress testing, robustness scoring
**Look for**:
- Walk-forward validation — anchored vs. rolling windows, in-sample/train vs. out-of-sample/test splits, fold generation
- Cross-validation — time-series cross-validation (expanding window, sliding window), purged cross-validation (embargo)
- Overfitting detection — deflated Sharpe ratio, combinatorial purged cross-validation, performance degradation ratio (in-sample vs. out-of-sample)
- Stress testing — worst-case scenarios, flash crash simulation, liquidity crisis, gap risk scenarios
- Robustness metrics — Sharpe ratio consistency across folds, maximum performance degradation, parameter sensitivity maps
- Multiple testing correction — Bonferroni correction, false discovery rate (Benjamini-Hochberg) for multiple strategy comparisons
- Strategy complexity penalty — parameter count penalty, indicator count penalty, overfitting risk score
- Reproducibility — deterministic seeds, versioned data, deterministic backtesting, reproducible experiment configurations
**Extract**: Walk-forward fold generation code, purged cross-validation logic, deflated Sharpe ratio calculation, stress test scenarios, robustness scoring formulas, multiple testing correction implementations
**Intrinsic value indicators**: Purged cross-validation with embargo preventing information leakage, deflated Sharpe ratio accounting for multiple testing, comprehensive robustness score from multiple validation methods

### 16. Exchange Connectivity

**Generic category**: Integration & Extension
**Types**: Centralized exchange (CEX) APIs, decentralized exchange (DEX) contracts, multi-exchange abstraction, exchange capability detection
**Look for**:
- Exchange abstraction — unified interface wrapping CCXT async API, typed request/response models
- Multi-exchange management — exchange registry, simultaneous multi-exchange connections, exchange-specific feature detection
- API integration — REST API clients, WebSocket connections, authentication (HMAC, API key/secret), rate limiting
- Error mapping — CCXT error taxonomy mapping to domain exceptions (Auth, RateLimit, InsufficientFunds, Network, etc.)
- Testnet/sandbox support — testnet endpoints, paper trading, simulated order execution
- Market metadata — symbol precision, tick size, lot size, min/max order size, leverage limits, fee schedules
- Capability detection — `has()` checks for createOrder, fetchOHLCV, fetchTrades, marginTrading, etc.
- Connection resilience — auto-reconnect, exponential backoff, circuit breaker on exchange errors
**Extract**: Exchange base class interfaces, error mapping tables, rate limiter implementations, WebSocket reconnection logic, market metadata schemas
**Intrinsic value indicators**: Clean exchange abstraction supporting 100+ exchanges via CCXT with typed responses, comprehensive error taxonomy with automatic retry strategies, capability-aware feature degradation

### 17. LLM Integration

**Generic category**: Integration & Extension
**Types**: Multi-model routing, structured output parsing, declarative LLM programming, cost management, prompt management
**Look for**:
- Model routing — LiteLLM-based multi-provider routing, model selection by task type, cost-based routing, latency-based routing
- Structured output — Pydantic schema enforcement, JSON mode, function calling, output validation and retry
- Declarative programming — DSPy signatures, chain-of-thought modules, module composition, typed input/output
- Cost management — per-request cost tracking, daily budget limits, cost alerts, provider cost comparison
- Complexity routing — simple tasks → fast/cheap models, complex tasks → capable/expensive models, automatic classification
- Fallback chains — primary → secondary → tertiary provider, graceful degradation on provider failure
- Prompt management — template versioning, few-shot example libraries, prompt A/B testing
- Streaming — streaming responses for UI, token-by-token generation, partial result handling
- Caching — response caching for identical prompts, semantic caching for similar prompts
**Extract**: LiteLLM router configurations, DSPy signature definitions, cost tracking schemas, complexity classification logic, fallback chain configurations, prompt template libraries
**Intrinsic value indicators**: DSPy-based declarative LLM programming with typed signatures, complexity-aware routing optimizing cost vs. quality, daily budget enforcement with automatic model downgrading

### 18. Memory & RAG

**Generic category**: Data & Storage
**Types**: Core memory (identity/preferences), recall memory (recent context), archival memory (historical knowledge), RAG over external knowledge, strategy memory
**Look for**:
- Memory tiers — core (user preferences, risk tolerance), recall (recent trades, current market state), archival (historical patterns, strategy performance)
- Memory storage backends — SQLite, PostgreSQL, Redis, vector databases (ChromaDB, Qdrant), graph databases
- RAG systems — Freqtrade documentation retrieval, strategy pattern retrieval, trading knowledge retrieval
- Embedding pipelines — document chunking, embedding model selection, chunk size optimization, retrieval scoring
- Hallucination prevention — grounding LLM outputs in retrieved documentation, citation tracking, factual verification
- Strategy memory — remembering past strategies, their performance, failure modes, and improvement history
- Session continuity — maintaining context across trading sessions, resuming interrupted analysis
- Memory consolidation — compressing old memories, extracting patterns, forgetting irrelevant details
- Cross-session learning — learning from past mistakes, improving strategy generation over time
**Extract**: Memory tier schemas, RAG pipeline configurations, embedding model settings, retrieval scoring formulas, hallucination prevention checks, strategy memory data models
**Intrinsic value indicators**: Three-tier memory architecture (core/recall/archival) with automatic consolidation, RAG-grounded strategy generation preventing hallucination, cross-session learning from past strategy performance

## Category-to-Pillar Mapping

| Generic Category | Pillar(s) |
|-----------------|-----------|
| 1. Data & Storage | 1. Market Data Pipeline, 18. Memory & RAG |
| 2. Processing & Logic | 2. Indicator & Feature Engineering, 3. Strategy Framework, 4. NL Strategy Generation, 5. Backtesting Engine |
| 3. Coordination | 6. Order Execution, 7. Multi-Agent Coordination |
| 4. Perception & Input | 1. Market Data Pipeline (data ingestion, streaming feeds) |
| 5. Goal & Planning | 8. Portfolio Management |
| 6. Autonomy & Scheduling | 9. Autonomous Trading, 13. Monitoring & Drift Detection |
| 7. Knowledge & Representation | 10. Causal Inference & Regime Detection, 11. Explanation & Diagnostics |
| 8. Adaptation & Learning | 12. Strategy Optimization, 13. Monitoring & Drift Detection (drift adaptation) |
| 9. Integration & Extension | 16. Exchange Connectivity, 17. LLM Integration |
| 10. Governance & Quality | 14. Risk Management, 15. Validation & Robustness |

## Common Gaps in AI-Powered Crypto Trading Platforms

Typical architectural gaps found in AI-powered crypto trading projects:

- No NL-to-strategy pipeline (strategies must be hand-coded in Python)
- No strategy DSL or intermediate representation (direct code execution with no validation layer)
- No multi-model LLM routing (single provider dependency, no fallback)
- No RAG system for knowledge grounding (LLM hallucination risk in strategy generation)
- No structured output enforcement (unreliable LLM response parsing)
- No causal inference (correlation-only analysis, no causal claims)
- No market regime detection (static strategies across all market conditions)
- No vectorized backtesting (slow event-driven-only backtesting)
- No walk-forward validation (in-sample overfitting goes undetected)
- No overfitting detection or deflated Sharpe ratio correction
- No triple-barrier risk method (simple stop-loss only)
- No portfolio-level risk management (position-level risk only)
- No cross-strategy correlation analysis
- No multi-agent coordination (monolithic strategy execution pipeline)
- No evolutionary strategy optimization (grid search or manual tuning only)
- No data drift detection in production (strategy degrades silently)
- No graduated autonomy (fully manual or fully autonomous, no middle ground)
- No confidence scoring for strategy or trading decisions
- No NL explanation of trading decisions (black-box signals)
- No memory across trading sessions (stateless execution each session)
- No strategy lifecycle management (no creation→validation→deployment→retirement pipeline)
- No multi-exchange support (hardcoded to single exchange)
- No smart order routing (single exchange execution only)
- No cost-aware LLM usage (unbounded API costs possible)
- No strategy template library (generation from scratch every time)
- No alternative data integration beyond OHLCV candles
- No real-time streaming data pipeline (batch-only historical data)
- No audit trail for compliance (no decision provenance logging)
- No automated failure diagnosis (manual investigation required)
- No prompt versioning or A/B testing for LLM prompts
