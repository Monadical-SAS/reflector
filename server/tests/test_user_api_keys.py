import pytest

from reflector.db.user_api_keys import user_api_keys_controller


@pytest.mark.asyncio
async def test_api_key_creation_and_verification():
    api_key_model, plaintext = await user_api_keys_controller.create_key(
        user_id="test_user",
        name="Test API Key",
    )

    verified = await user_api_keys_controller.verify_key(plaintext)
    assert verified is not None
    assert verified.user_id == "test_user"
    assert verified.name == "Test API Key"

    invalid = await user_api_keys_controller.verify_key("fake_key")
    assert invalid is None


@pytest.mark.asyncio
async def test_api_key_hashing():
    _, plaintext = await user_api_keys_controller.create_key(
        user_id="test_user_2",
    )

    api_keys = await user_api_keys_controller.list_by_user_id("test_user_2")
    assert len(api_keys) == 1
    assert api_keys[0].key_hash != plaintext


@pytest.mark.asyncio
async def test_generate_api_key_uniqueness():
    key1 = user_api_keys_controller.generate_key()
    key2 = user_api_keys_controller.generate_key()
    assert key1 != key2


@pytest.mark.asyncio
async def test_hash_api_key_deterministic():
    key = "test_key_123"
    hash1 = user_api_keys_controller.hash_key(key)
    hash2 = user_api_keys_controller.hash_key(key)
    assert hash1 == hash2


@pytest.mark.asyncio
async def test_get_by_user_id_empty():
    api_keys = await user_api_keys_controller.list_by_user_id("nonexistent_user")
    assert api_keys == []


@pytest.mark.asyncio
async def test_get_by_user_id_multiple():
    user_id = "multi_key_user"

    _, plaintext1 = await user_api_keys_controller.create_key(
        user_id=user_id,
        name="API Key 1",
    )
    _, plaintext2 = await user_api_keys_controller.create_key(
        user_id=user_id,
        name="API Key 2",
    )

    api_keys = await user_api_keys_controller.list_by_user_id(user_id)
    assert len(api_keys) == 2
    names = {k.name for k in api_keys}
    assert names == {"API Key 1", "API Key 2"}
