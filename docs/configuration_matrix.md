# Security Configuration Matrix

**Date:** 2026-10-14  
**Project:** Security and Reliability of MCP-Based Multi-Agent Systems

## Configuration Comparison

| Control | Config A (No Security) | Config B (Basic Security) | Config C (Hardened) |
|---------|----------------------|--------------------------|---------------------|
| **Authentication** | Disabled | Enabled (API Token) | Enabled (API Token) |
| **Tool Permission Scoping** | Disabled | Enabled | Enabled |
| **Input Validation** | Disabled | Disabled | Enabled (Keywords + Length) |
| **Output Validation** | Disabled | Enabled (Length: 5000) | Enabled (Length: 2000 + Content Scan) |
| **Security Event Logging** | Basic (INFO) | Standard (INFO) | Verbose (DEBUG) |
| **Allowed Tools (Research)** | * (all) | read_file, web_search | read_file, web_search |
| **Allowed Tools (Planner)** | * (all) | none | none |
| **Allowed Tools (Execution)** | * (all) | none | none |
| **Allowed Tools (Evaluation)** | * (all) | none | none |
| **Max Input Length** | N/A | N/A | 500 characters |
| **Blocked Keywords** | N/A | N/A | ignore previous, disregard, override, forget instructions, new instruction |
| **Max Output Length** | N/A | 5000 characters | 2000 characters |

## Detailed Control Status

### Authentication

**Config A:** Disabled
- YAML: `authentication: false`
- Enforcement: Not enforced
- Implementation: `check_authentication()` returns `(True, None)` immediately without requiring credentials.
- Tests: Auth disabled allows access without credentials.

**Config B:** Enabled
- YAML: `authentication: true`
- Expected Secret: `expected_auth_secret: "$AUTH_SECRET"`
- Enforcement: Enforced at pipeline entry point (`pipeline/graph.py` inside `run_pipeline()`). If authentication fails, the pipeline aborts immediately before any agent node is constructed or executed.
- Implementation: Resolves expected secret from `AUTH_SECRET` environment variable and compares against presented credential using `hmac.compare_digest`. Rejects missing credentials, empty credentials, mismatched credentials, and self-referential configuration (`$AUTH_TOKEN`).
- Tests: Missing secret, missing token, empty token, incorrect token, correct token, rejection of arbitrary strings, rejection of `$AUTH_TOKEN` self-reference.
- Location: `security/auth.py`, `pipeline/graph.py`

**Config C:** Enabled
- YAML: `authentication: true`
- Expected Secret: `expected_auth_secret: "$AUTH_SECRET"`
- Enforcement: Enforced at pipeline entry point (`pipeline/graph.py` inside `run_pipeline()`). Identical authentication enforcement to Config B.
- Implementation: Same as Config B.
- Tests: Same comprehensive test coverage as Config B.
- Location: `security/auth.py`, `pipeline/graph.py`

**What It Protects:**
- Protects the pipeline entry point against unauthorized invocations.
- Prevents unauthenticated users/callers from triggering multi-agent graph flows, consuming LLM API credits, or invoking MCP tool servers.
- Protects credential integrity via timing-attack safe comparison (`hmac.compare_digest`).
- Prevents secret leakage in error logs or test reporting.

**Limitations:**
- Single shared secret (symmetric authentication); lacks per-user identity or role-based access control.
- No automatic token expiration (TTL) or rotation mechanism.
- No rate limiting or IP-based lockout to defend against brute-force guessing.
- Credentials and secrets stored in environment variables.

### Tool Permission Scoping

**Config A:** Disabled
- YAML: `tool_permission_scoping: false`
- Enforcement: Not enforced
- Implementation: Permission check skipped
- Tests: All tools allowed

**Config B:** Enabled
- YAML: `tool_permission_scoping: true`
- Enforcement: Enforced before MCP invocation (agents/research_agent.py lines 148-156)
- Implementation: Checks tool name against `allowed_tools.research` list
- Tests: Allowed tools succeed, unknown tools rejected
- Location: agents/research_agent.py

**Config C:** Enabled
- YAML: `tool_permission_scoping: true`
- Enforcement: Enforced before MCP invocation (agents/research_agent.py lines 148-156)
- Implementation: Same as Config B
- Tests: Same as Config B
- Location: agents/research_agent.py

**Limitations:**
- Only applies to Research Agent (only agent that invokes MCP tools)
- Config B and Config C have identical tool permissions
- No wildcard expansion beyond "*"
- Permission check is case-sensitive

### Input Validation

**Config A:** Disabled
- YAML: `input_validation: false`
- Enforcement: Not enforced
- Implementation: Validation checks skipped
- Tests: No keyword or length blocking

**Config B:** Disabled
- YAML: `input_validation: false`
- Enforcement: Not enforced
- Implementation: Validation checks skipped
- Tests: No keyword or length blocking

**Config C:** Enabled
- YAML: `input_validation: true`
- Enforcement: Enforced at planner entry point (agents/planner_agent.py lines 82-101)
- Implementation: 
  - Keyword blocking (case-insensitive substring match)
  - Length limit (max_input_length: 500 characters)
- Tests: Blocked keywords rejected, long input rejected
- Location: agents/planner_agent.py

**Additional Validation (All Configs):**
- Tool parameter validation in research_agent.py (lines 110-145):
  - Empty query check
  - Filename validation (path traversal prevention)
  - Query length limit (1000 characters)

**Limitations:**
- Keyword matching is substring-based (may have false positives)
- Does not claim to prevent all prompt injection attacks
- Only validates user_task in planner_agent
- Tool parameters validated separately in research_agent

### Output Validation

**Config A:** Disabled
- YAML: `output_validation: false`
- Enforcement: Not enforced
- Implementation: No truncation or content scanning
- Tests: Output passes through unchanged

**Config B:** Enabled (Length Only)
- YAML: `output_validation: true`
- Enforcement: Enforced after MCP invocation (agents/research_agent.py lines 150-155)
- Implementation: Length truncation to 5000 characters (configurable via max_output_length)
- Tests: Long output truncated
- Location: agents/research_agent.py

**Config C:** Enabled (Length + Content Scan)
- YAML: `output_validation: true`
- Enforcement: 
  - Length truncation (agents/research_agent.py lines 150-155)
  - Content scanning (agents/execution_agent.py lines 126-148)
- Implementation:
  - Length truncation to 2000 characters (configurable via max_output_length)
  - Content scanning for unsafe patterns (configurable via block_keywords)
- Tests: Long output truncated, unsafe content blocked
- Location: agents/research_agent.py, agents/execution_agent.py

**Limitations:**
- Length truncation does not remove malicious content, just shortens it
- Content scanning uses simple substring matching
- May have false positives/negatives
- Does not provide comprehensive prompt-injection detection
- Truncation may obscure attack indicators

### Security Event Logging

**Config A:** Basic
- YAML: `logging: basic`
- Enforcement: INFO level logging
- Implementation: Python logging.basicConfig(level=INFO)
- Events logged: Standard operational events
- Location: security/logging_config.py, pipeline/graph.py

**Config B:** Standard
- YAML: `logging: standard`
- Enforcement: INFO level logging
- Implementation: Python logging.basicConfig(level=INFO)
- Events logged: Standard operational events + security events
- Location: security/logging_config.py, pipeline/graph.py

**Config C:** Verbose
- YAML: `logging: verbose`
- Enforcement: DEBUG level logging
- Implementation: Python logging.basicConfig(level=DEBUG)
- Events logged: All operational events + detailed security events
- Location: security/logging_config.py, pipeline/graph.py

**Security Events Logged:**
- Authentication failures
- Permission denials
- Input validation failures
- Output validation failures (truncation, blocking)
- MCP invocation failures

**Limitations:**
- No dedicated security event log file
- Security events mixed with operational logs
- No structured event format for analysis
- Basic and Standard both use INFO level (currently identical)

## Configuration Distinguishability

**Config A vs Config B:**
- Authentication: Disabled vs Enabled ✓
- Tool Permission Scoping: Disabled vs Enabled ✓
- Input Validation: Both Disabled ✗
- Output Validation: Disabled vs Enabled ✓
- Logging: Basic vs Standard (currently identical level) ✗

**Config B vs Config C:**
- Authentication: Both Enabled ✗
- Tool Permission Scoping: Both Enabled ✗
- Input Validation: Disabled vs Enabled ✓
- Output Validation: Both Enabled (different limits) ✓
- Logging: Standard vs Verbose ✓

**Summary:**
- Config A is clearly distinguishable from Config B and C
- Config B and C are distinguishable by input validation and output validation limits
- Authentication is identical between Config B and C (both enabled)
- Tool permissions are identical between Config B and C
