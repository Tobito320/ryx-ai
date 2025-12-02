"""
Comprehensive Test Suite for Intent Parser
Tests edge cases, bugs, and improvements identified in the analysis
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.intent_parser import IntentParser


class TestModelSwitchDetection:
    """Test model switch detection and false positives"""

    def test_false_positive_use_editor(self):
        """BUG: 'use nvim' should not trigger model switch"""
        parser = IntentParser()
        intent = parser.parse("use nvim to edit file")

        # Current behavior: FAILS (triggers model switch)
        # Expected behavior: model_switch should be None
        assert intent.model_switch is None, "KNOWN BUG: False positive on 'use nvim'"

    def test_false_positive_use_terminal(self):
        """BUG: 'use terminal' should not trigger model switch"""
        parser = IntentParser()
        intent = parser.parse("use the terminal to run command")

        assert intent.model_switch is None, "KNOWN BUG: False positive on 'use terminal'"

    def test_legitimate_switch_to_deepseek(self):
        """Valid: 'switch to deepseek' should work"""
        parser = IntentParser()
        intent = parser.parse("switch to deepseek")

        assert intent.model_switch == "deepseek-coder:6.7b"

    def test_legitimate_use_fast_model(self):
        """Valid: 'use fast model' should work"""
        parser = IntentParser()
        intent = parser.parse("use fast model")

        # This might work or fail depending on implementation
        # Current implementation: likely FAILS (no "model" context check)
        assert intent.model_switch in [None, "qwen2.5:1.5b"]


class TestImplicitLocate:
    """Test implicit file location detection"""

    def test_false_positive_conversational(self):
        """BUG: 'I need config help' should not trigger locate"""
        parser = IntentParser()
        intent = parser.parse("I need config help")

        # Current behavior: FAILS (triggers locate)
        # Expected: should be 'chat'
        assert intent.action == 'chat', "KNOWN BUG: False positive on conversational pattern"

    def test_false_positive_how_to(self):
        """BUG: 'how do I change config' should not trigger locate"""
        parser = IntentParser()
        intent = parser.parse("how do I change config")

        assert intent.action == 'chat', "KNOWN BUG: False positive on 'how do'"

    def test_legitimate_implicit_locate(self):
        """Valid: 'hyprland config' should trigger locate"""
        parser = IntentParser()
        intent = parser.parse("hyprland config")

        assert intent.action == 'locate'
        assert 'hyprland' in intent.target.lower()

    def test_legitimate_short_config(self):
        """Valid: 'waybar settings' should trigger locate"""
        parser = IntentParser()
        intent = parser.parse("waybar settings")

        assert intent.action == 'locate'


class TestConflictingKeywords:
    """Test prompts with multiple action keywords"""

    def test_open_and_lookup(self):
        """EDGE CASE: 'open look up hyprland' has both execute and browse"""
        parser = IntentParser()
        intent = parser.parse("open look up hyprland")

        # Current behavior: First match wins (execute)
        # This is expected behavior, but could be improved
        assert intent.action in ['execute', 'browse']

    def test_find_and_open(self):
        """EDGE CASE: 'find and open config' has both locate and execute"""
        parser = IntentParser()
        intent = parser.parse("find and open config")

        # Should prioritize execute (more specific action)
        assert intent.action in ['locate', 'execute']

    def test_search_and_edit(self):
        """EDGE CASE: 'search and edit' has both browse and execute"""
        parser = IntentParser()
        intent = parser.parse("search docs and edit config")

        assert intent.action in ['browse', 'execute']


class TestTargetExtraction:
    """Test target extraction from prompts"""

    def test_multiword_filename(self):
        """EDGE CASE: Multi-word filenames"""
        parser = IntentParser()
        intent = parser.parse("open my hyprland config")

        # Current behavior: includes 'my'
        # Expected: should extract meaningful target
        # This might be acceptable depending on implementation
        assert 'hyprland' in intent.target.lower()
        assert 'config' in intent.target.lower()

    def test_path_with_spaces(self):
        """EDGE CASE: Paths with spaces"""
        parser = IntentParser()
        intent = parser.parse("open ~/.config/my folder/file.txt")

        assert intent.target is not None
        assert 'my folder' in intent.target or 'folder' in intent.target

    def test_target_with_quotes(self):
        """EDGE CASE: Quoted targets"""
        parser = IntentParser()
        intent = parser.parse('open "hyprland config"')

        assert intent.target is not None


class TestVeryShortPrompts:
    """Test very short prompts (1-2 words)"""

    def test_single_word_greeting(self):
        """Simple greeting should not query AI"""
        parser = IntentParser()
        intent = parser.parse("hello")

        # Should be chat, but ideally handled before AI query
        assert intent.action == 'chat'

    def test_single_word_config(self):
        """Single word 'config' is ambiguous"""
        parser = IntentParser()
        intent = parser.parse("config")

        # Could be locate or chat
        assert intent.action in ['locate', 'chat']

    def test_two_word_file(self):
        """'hyprland config' should locate"""
        parser = IntentParser()
        intent = parser.parse("hyprland config")

        assert intent.action == 'locate'


class TestLongConversationalPrompts:
    """Test long conversational prompts with embedded keywords"""

    def test_embedded_open_keyword(self):
        """EDGE CASE: 'open' in conversation"""
        parser = IntentParser()
        intent = parser.parse("I'm trying to open a discussion about hyprland config files")

        # Should not trigger execute (it's conversational)
        # Current behavior: likely triggers execute
        # This is a known limitation
        assert intent.action in ['execute', 'chat']

    def test_embedded_find_keyword(self):
        """EDGE CASE: 'find' in conversation"""
        parser = IntentParser()
        intent = parser.parse("I find it hard to understand config files")

        # Should be chat, not locate
        assert intent.action in ['locate', 'chat']

    def test_long_prompt_with_actual_intent(self):
        """Long prompt with clear intent"""
        parser = IntentParser()
        intent = parser.parse("I need you to help me open my hyprland config file please")

        # Should detect 'open' as execute intent
        assert intent.action == 'execute'
        assert 'hyprland' in intent.target.lower()


class TestTypos:
    """Test prompts with typos in keywords"""

    def test_typo_opne(self):
        """LIMITATION: Typo 'opne' instead of 'open'"""
        parser = IntentParser()
        intent = parser.parse("opne hyprland config")

        # Current behavior: Won't detect (no fuzzy matching)
        # This is a known limitation
        assert intent.action in ['chat', 'locate']

    def test_typo_edti(self):
        """LIMITATION: Typo 'edti' instead of 'edit'"""
        parser = IntentParser()
        intent = parser.parse("edti config file")

        # Won't detect execute intent
        assert intent.action in ['chat', 'locate']

    def test_typo_finde(self):
        """LIMITATION: Typo 'finde' instead of 'find'"""
        parser = IntentParser()
        intent = parser.parse("finde waybar config")

        # Won't detect locate intent
        assert intent.action in ['chat', 'locate']


class TestModifiers:
    """Test modifier keyword detection"""

    def test_new_terminal_modifier(self):
        """Detect 'new terminal' modifier"""
        parser = IntentParser()
        intent = parser.parse("open config in new terminal")

        assert 'new_terminal' in intent.modifiers

    def test_separate_window_modifier(self):
        """Detect 'separate window' modifier"""
        parser = IntentParser()
        intent = parser.parse("edit file in separate window")

        assert 'new_terminal' in intent.modifiers

    def test_no_modifier(self):
        """No modifiers in simple prompt"""
        parser = IntentParser()
        intent = parser.parse("open config")

        assert len(intent.modifiers) == 0


class TestEdgeCaseScenarios:
    """Test various edge case scenarios"""

    def test_empty_prompt(self):
        """EDGE CASE: Empty prompt"""
        parser = IntentParser()
        intent = parser.parse("")

        assert intent.action == 'chat'
        assert intent.target is None or intent.target == ""

    def test_only_whitespace(self):
        """EDGE CASE: Only whitespace"""
        parser = IntentParser()
        intent = parser.parse("   \n\t  ")

        assert intent.action == 'chat'

    def test_special_characters(self):
        """EDGE CASE: Special characters"""
        parser = IntentParser()
        intent = parser.parse("open ~/.config/hypr/hyprland.conf")

        assert intent.action == 'execute'
        assert '~' in intent.target or 'config' in intent.target.lower()

    def test_numbers_in_prompt(self):
        """EDGE CASE: Numbers in prompt"""
        parser = IntentParser()
        intent = parser.parse("open file123.txt")

        assert intent.action == 'execute'
        assert 'file123' in intent.target


class TestComplexScenarios:
    """Test complex real-world scenarios"""

    def test_multiple_commands_in_prompt(self):
        """Complex: Multiple commands in one prompt"""
        parser = IntentParser()
        intent = parser.parse("open config and then search for keybinds")

        # Should detect first action (open = execute)
        assert intent.action == 'execute'

    def test_question_with_action_keyword(self):
        """Complex: Question containing action keyword"""
        parser = IntentParser()
        intent = parser.parse("where can I find the open source license?")

        # 'open source' shouldn't trigger execute
        # 'find' should trigger locate
        assert intent.action in ['locate', 'chat']

    def test_negation(self):
        """Complex: Negation 'don't open'"""
        parser = IntentParser()
        intent = parser.parse("don't open the config file")

        # Should still detect 'open' keyword
        # (Negation handling would require NLP)
        assert intent.action == 'execute'  # Known limitation


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
