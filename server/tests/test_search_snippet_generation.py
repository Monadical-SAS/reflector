from reflector.db.search import SnippetGenerator


class TestSnippetGeneration:
    def test_multi_word_query_snippet_behavior(self):
        """
        Test that multi-word queries generate snippets based on exact phrase matching.

        This test documents the current simplistic behavior:
        - When searching for "user jordan", it looks for that exact phrase
        - If found, it returns only snippets around the exact phrase
        - Individual occurrences of "user" or "jordan" are ignored
        """
        # Sample text with multiple occurrences of "user" and "jordan"
        sample_text = """This is a sample transcript where user Alice is talking.
        Later in the conversation, jordan mentions something important.
        The user jordan collaboration was successful.
        Another user named Bob joins the discussion."""

        # Test 1: Single word "user" returns multiple snippets
        user_snippets = SnippetGenerator.generate(sample_text, "user")
        assert len(user_snippets) == 2, "Should find 2 snippets for 'user'"

        # Test 2: Single word "jordan" returns snippet(s)
        jordan_snippets = SnippetGenerator.generate(sample_text, "jordan")
        assert len(jordan_snippets) >= 1, "Should find at least 1 snippet for 'jordan'"

        # Test 3: Multi-word "user jordan" returns only 1 snippet (the exact phrase match)
        multi_word_snippets = SnippetGenerator.generate(sample_text, "user jordan")
        assert len(multi_word_snippets) == 1, (
            "Should return exactly 1 snippet for 'user jordan' "
            "(only the exact phrase match, not individual word occurrences)"
        )

        # Test 4: The single snippet should contain the exact phrase "user jordan"
        snippet = multi_word_snippets[0]
        assert (
            "user jordan" in snippet.lower()
        ), "The snippet should contain the exact phrase 'user jordan'"

        # Test 5: Verify the snippet doesn't include the first standalone "user" occurrence
        # The first "user" appears with "Alice", which should not be in our snippet
        assert (
            "alice" not in snippet.lower()
        ), "The snippet should not include the first standalone 'user' with Alice"

    def test_multi_word_query_without_exact_match(self):
        """
        Test snippet generation when exact phrase is not found.
        In this case, it falls back to searching for the first word only.
        """
        sample_text = """User Alice is here. Bob and jordan are talking.
        Later jordan mentions something. The user is happy."""

        # Search for "user jordan" - no exact phrase match exists
        snippets = SnippetGenerator.generate(sample_text, "user jordan")

        # Should fall back to first word "user"
        assert (
            len(snippets) >= 1
        ), "Should find at least 1 snippet when falling back to first word"

        # The snippets should contain "user" but not necessarily "jordan"
        all_snippets_text = " ".join(snippets).lower()
        assert (
            "user" in all_snippets_text
        ), "Snippets should contain 'user' (the first word)"

    def test_exact_phrase_at_text_boundaries(self):
        """Test snippet generation when exact phrase appears at text boundaries."""

        # Exact phrase at the beginning
        text_start = "user jordan started the meeting. Other content here."
        snippets = SnippetGenerator.generate(text_start, "user jordan")
        assert len(snippets) == 1
        assert "user jordan" in snippets[0].lower()

        # Exact phrase at the end
        text_end = "Other content here. The meeting ended with user jordan"
        snippets = SnippetGenerator.generate(text_end, "user jordan")
        assert len(snippets) == 1
        assert "user jordan" in snippets[0].lower()

    def test_snippet_max_count_limit(self):
        """Test that snippet generation respects the max_snippets limit."""

        text_many = "user " * 20  # 20 occurrences

        snippets = SnippetGenerator.generate(text_many, "user", max_snippets=3)

        assert len(snippets) <= 3, "Should respect max_snippets limit"

    def test_multi_word_query_matches_words_appearing_separately_and_together(self):
        """
        Test that multi-word queries prioritize exact phrase matches over individual word occurrences.

        When searching for two words that appear both separately AND together in the text:
        1. Only the exact phrase match generates a snippet
        2. Individual word occurrences are ignored
        3. The snippet includes context around the exact phrase

        This documents the current design: exact phrase matching takes precedence.
        """
        # Text where two words appear separately first, then together as an exact phrase
        sample_text = """This is a sample transcript where user Alice is talking.
        Later in the conversation, jordan mentions something important.
        The user jordan collaboration was successful.
        Another user named Bob joins the discussion."""

        # Search for the two-word query
        search_query = "user jordan"
        snippets = SnippetGenerator.generate(sample_text, search_query)

        # Verify only 1 snippet is returned (ignoring separate occurrences)
        assert len(snippets) == 1, (
            f"Expected exactly 1 snippet for '{search_query}' when exact phrase exists, "
            f"got {len(snippets)}. Should ignore individual word occurrences."
        )

        snippet = snippets[0]

        # Verify the snippet contains the exact phrase match
        assert (
            search_query in snippet.lower()
        ), f"Snippet should contain the exact phrase '{search_query}'. Got: {snippet}"

        # Verify the snippet includes context from around the exact match
        # The second word appears alone before the exact phrase, so it should be in context
        assert (
            "jordan mentions" in snippet.lower()
        ), f"Snippet should include context before the exact phrase match. Got: {snippet}"

        # Verify individual occurrences are not included
        # The first word appears with "Alice" earlier, which should NOT be in the snippet
        assert (
            "alice" not in snippet.lower()
        ), f"Snippet should not include separate occurrences of individual words. Got: {snippet}"

        # Additional test with different words to ensure behavior is consistent
        text_2 = """The alpha version was released.
        Beta testing started yesterday.
        The alpha beta integration is complete."""

        snippets_2 = SnippetGenerator.generate(text_2, "alpha beta")
        assert len(snippets_2) == 1, "Should return 1 snippet for exact phrase match"
        assert "alpha beta" in snippets_2[0].lower(), "Should contain exact phrase"
        assert (
            "version" not in snippets_2[0].lower()
        ), "Should not include first separate occurrence"
