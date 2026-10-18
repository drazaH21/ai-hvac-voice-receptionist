# Skill: Test-Driven Development (TDD)

## Purpose
Enforce disciplined, automated test-first implementation for every ticket.

## Execution Discipline
1. **Red**: Write a minimal failing test that specifies the expected behavior according to the issue criteria. Execute the test suite and confirm it fails for the expected reason.
2. **Green**: Write the minimal implementation code necessary to make the test pass. No premature abstractions.
3. **Refactor**: Clean up the implementation, optimize imports, ensure typing compliance (Pydantic / type hints), and verify all tests remain green.
4. Never modify application logic without an accompanying test case.
