import pytest

from reflector.db.user_tokens import user_tokens_controller


@pytest.mark.asyncio
async def test_token_creation_and_verification():
    """Basic token flow"""
    token_model, plaintext = await user_tokens_controller.create_token(
        user_id="test_user",
        name="Test Token",
    )

    # Verify token works
    verified = await user_tokens_controller.verify_token(plaintext)
    assert verified is not None
    assert verified.user_id == "test_user"
    assert verified.name == "Test Token"

    # Invalid token fails
    invalid = await user_tokens_controller.verify_token("fake_token")
    assert invalid is None


@pytest.mark.asyncio
async def test_token_hashing():
    """Ensure tokens are hashed, not stored plaintext"""
    _, plaintext = await user_tokens_controller.create_token(
        user_id="test_user_2",
    )

    # Get from DB
    tokens = await user_tokens_controller.get_by_user_id("test_user_2")
    assert len(tokens) == 1
    # Hash should not equal plaintext
    assert tokens[0].token_hash != plaintext


@pytest.mark.asyncio
async def test_generate_token_uniqueness():
    """Ensure generated tokens are unique"""
    token1 = user_tokens_controller.generate_token()
    token2 = user_tokens_controller.generate_token()
    assert token1 != token2


@pytest.mark.asyncio
async def test_hash_token_deterministic():
    """Ensure hashing is deterministic"""
    token = "test_token_123"
    hash1 = user_tokens_controller.hash_token(token)
    hash2 = user_tokens_controller.hash_token(token)
    assert hash1 == hash2


@pytest.mark.asyncio
async def test_get_by_user_id_empty():
    """Get tokens for user with no tokens"""
    tokens = await user_tokens_controller.get_by_user_id("nonexistent_user")
    assert tokens == []


@pytest.mark.asyncio
async def test_get_by_user_id_multiple():
    """Get multiple tokens for a user"""
    user_id = "multi_token_user"

    # Create multiple tokens
    _, plaintext1 = await user_tokens_controller.create_token(
        user_id=user_id,
        name="Token 1",
    )
    _, plaintext2 = await user_tokens_controller.create_token(
        user_id=user_id,
        name="Token 2",
    )

    # Get all tokens
    tokens = await user_tokens_controller.get_by_user_id(user_id)
    assert len(tokens) == 2
    names = {t.name for t in tokens}
    assert names == {"Token 1", "Token 2"}


@pytest.mark.asyncio
async def test_delete_token_wrong_user():
    """Trying to delete another user's token raises ValueError"""
    # User 1 creates a token
    token1, _ = await user_tokens_controller.create_token(
        user_id="user1",
        name="User1 Token",
    )

    # User 2 tries to delete it - should raise
    with pytest.raises(ValueError, match="belongs to another user"):
        await user_tokens_controller.delete_token(token1.id, "user2")
