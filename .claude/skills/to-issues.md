# Skill: To Issues

## Purpose
Decompose PRD.md into atomic, sequentially ordered technical tickets (ISSUES.md) ready for execution.

## Rules for Issues
1. Each ticket must represent a single vertical slice of functionality (e.g., Issue 01: Health check routes, Issue 02: Twilio webhook signature validation).
2. Every ticket must explicitly define:
   - **Pre-requisites**: Which issue must be merged first.
   - **Target Files**: Exact files to create or modify.
   - **Acceptance Criteria**: Concrete pass/fail assertions.
   - **Test Requirement**: The specific test file and scenarios that must pass.
