# core/ai_engine_v2.py

class AIEngineV2:
    """
    AIEngineV2 is the main class for handling AI operations.
    """

    @staticmethod
    def reverse_string(input_string: str) -> str:
        """
        Reverses the given string.

        Args:
            input_string (str): The string to be reversed.

        Returns:
            str: The reversed string.
        """
        return input_string[::-1]

# Example usage
if __name__ == "__main__":
    engine = AIEngineV2()
    original_string = "Hello, World!"
    reversed_string = engine.reverse_string(original_string)
    print(f"Original: {original_string}")
    print(f"Reversed: {reversed_string}")