# AsyncIO Event Loop Analysis for test_attendee_parsing_bug.py

## Problem Summary
The test passes but encounters an error during teardown where asyncpg tries to use a different/closed event loop, resulting in:
- `RuntimeError: Task got Future attached to a different loop`
- `RuntimeError: Event loop is closed`

## Root Cause Analysis

### 1. Multiple Event Loop Creation Points

The test environment creates event loops at different scopes:

1. **Session-scoped loop** (conftest.py:27-34):
   - Created once per test session
   - Used by session-scoped fixtures
   - Closed after all tests complete

2. **Function-scoped loop** (pytest-asyncio default):
   - Created for each async test function
   - This is the loop that runs the actual test
   - Closed immediately after test completes

3. **AsyncPG internal loop**:
   - AsyncPG connections store a reference to the loop they were created with
   - Used for connection lifecycle management

### 2. Event Loop Lifecycle Mismatch

The issue occurs because:

1. **Session fixture creates database connection** on session-scoped loop
2. **Test runs** on function-scoped loop (different from session loop)
3. **During teardown**, the session fixture tries to rollback/close using the original session loop
4. **AsyncPG connection** still references the function-scoped loop which is now closed
5. **Conflict**: SQLAlchemy tries to use session loop, but asyncpg Future is attached to the closed function loop

### 3. Configuration Issues

Current pytest configuration:
- `asyncio_mode = "auto"` in pyproject.toml
- `asyncio_default_fixture_loop_scope=session` (shown in test output)
- `asyncio_default_test_loop_scope=function` (shown in test output)

This mismatch between fixture loop scope (session) and test loop scope (function) causes the problem.

## Solutions

### Option 1: Align Loop Scopes (Recommended)
Change pytest-asyncio configuration to use consistent loop scopes:

```python
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"  # Change from session to function
```

### Option 2: Use Function-Scoped Database Fixture
Change the `session` fixture scope from session to function:

```python
@pytest_asyncio.fixture  # Remove scope="session"
async def session(setup_database):
    # ... existing code ...
```

### Option 3: Explicit Loop Management
Ensure all async operations use the same loop:

```python
@pytest_asyncio.fixture
async def session(setup_database, event_loop):
    # Force using the current event loop
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={"loop": event_loop}  # Pass explicit loop
    )
    # ... rest of fixture ...
```

### Option 4: Upgrade pytest-asyncio
The current version (1.1.0) has known issues with loop management. Consider upgrading to the latest version which has better loop scope handling.

## Immediate Workaround

For the test to run cleanly without the teardown error, you can:

1. Add explicit cleanup in the test:
```python
@pytest.mark.asyncio
async def test_attendee_parsing_bug(session):
    # ... existing test code ...

    # Explicit cleanup before fixture teardown
    await session.commit()  # or await session.close()
```

2. Or suppress the teardown error (not recommended for production):
```python
@pytest.fixture
async def session(setup_database):
    # ... existing setup ...
    try:
        yield session
        await session.rollback()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise
    finally:
        await session.close()
```

## Recommendation

The cleanest solution is to align the loop scopes by setting both fixture and test loop scopes to "function" scope. This ensures each test gets its own clean event loop and avoids cross-contamination between tests.