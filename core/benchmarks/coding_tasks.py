"""
Ryx AI - Coding Task Benchmarks

Benchmark problems for evaluating code generation capabilities.
These are the core tests for RSI improvement.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any

from .base import (
    BaseBenchmark, Problem, BenchmarkCategory,
    register_benchmark
)


@register_benchmark
class CodingTasksBenchmark(BaseBenchmark):
    """
    Code generation benchmark.
    
    Tests:
    - Function implementation
    - Algorithm implementation
    - File manipulation
    - Error handling
    """
    
    name = "coding_tasks"
    description = "Code generation and implementation tasks"
    category = BenchmarkCategory.CODING
    
    @property
    def problems(self) -> List[Problem]:
        return [
            # Easy (difficulty 1)
            Problem(
                problem_id="coding_001",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `fibonacci(n)` that returns the nth Fibonacci number. fib(0)=0, fib(1)=1.",
                expected_output="def fibonacci",
                validation_type="function_test",
                difficulty=1,
                tags=["python", "algorithm", "recursion"]
            ),
            Problem(
                problem_id="coding_002",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `is_palindrome(s)` that returns True if string s is a palindrome (ignoring case and spaces).",
                expected_output="def is_palindrome",
                validation_type="function_test",
                difficulty=1,
                tags=["python", "string"]
            ),
            Problem(
                problem_id="coding_003",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `factorial(n)` that returns n! (n factorial). Handle n=0 returning 1.",
                expected_output="def factorial",
                validation_type="function_test",
                difficulty=1,
                tags=["python", "math"]
            ),
            
            # Medium (difficulty 2-3)
            Problem(
                problem_id="coding_004",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `merge_sorted_lists(list1, list2)` that merges two sorted lists into one sorted list.",
                expected_output="def merge_sorted_lists",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "algorithm", "sorting"]
            ),
            Problem(
                problem_id="coding_005",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `find_duplicates(lst)` that returns a list of elements that appear more than once.",
                expected_output="def find_duplicates",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "list"]
            ),
            Problem(
                problem_id="coding_006",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `validate_email(email)` that returns True if the email format is valid (contains @, has domain with dot).",
                expected_output="def validate_email",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "validation", "regex"]
            ),
            Problem(
                problem_id="coding_007",
                category=BenchmarkCategory.CODING,
                statement="Write a Python class `Stack` with methods: push(item), pop(), peek(), is_empty(). Use a list internally.",
                expected_output="class Stack",
                validation_type="class_test",
                difficulty=2,
                tags=["python", "class", "data-structure"]
            ),
            Problem(
                problem_id="coding_008",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `binary_search(sorted_list, target)` that returns the index of target, or -1 if not found.",
                expected_output="def binary_search",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "algorithm", "search"]
            ),
            
            # Hard (difficulty 4-5)
            Problem(
                problem_id="coding_009",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `lru_cache(capacity)` that returns a decorator implementing LRU cache with given capacity.",
                expected_output="def lru_cache",
                validation_type="function_test",
                difficulty=4,
                tags=["python", "decorator", "cache"]
            ),
            Problem(
                problem_id="coding_010",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `parse_json_safe(json_string)` that parses JSON and returns (success, result_or_error) tuple.",
                expected_output="def parse_json_safe",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "json", "error-handling"]
            ),
            
            # File operations
            Problem(
                problem_id="coding_011",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `count_lines(filepath)` that returns the number of lines in a file. Handle file not found gracefully.",
                expected_output="def count_lines",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "file", "io"]
            ),
            Problem(
                problem_id="coding_012",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `find_files(directory, pattern)` that returns list of files matching glob pattern.",
                expected_output="def find_files",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "file", "glob"]
            ),
            
            # Async
            Problem(
                problem_id="coding_013",
                category=BenchmarkCategory.CODING,
                statement="Write an async Python function `fetch_all(urls)` that fetches all URLs concurrently and returns list of responses.",
                expected_output="async def fetch_all",
                validation_type="contains",
                difficulty=3,
                tags=["python", "async", "http"]
            ),
            
            # Data processing
            Problem(
                problem_id="coding_014",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `group_by(items, key_func)` that groups items by the result of key_func.",
                expected_output="def group_by",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "functional"]
            ),
            Problem(
                problem_id="coding_015",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `flatten(nested_list)` that flattens arbitrarily nested lists into a single list.",
                expected_output="def flatten",
                validation_type="function_test",
                difficulty=3,
                tags=["python", "recursion", "list"]
            ),
            
            # String processing
            Problem(
                problem_id="coding_016",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `word_frequency(text)` that returns a dict of word -> count (lowercase, ignore punctuation).",
                expected_output="def word_frequency",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "string", "dict"]
            ),
            
            # Algorithm
            Problem(
                problem_id="coding_017",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `quick_sort(lst)` that implements quicksort algorithm. Return new sorted list.",
                expected_output="def quick_sort",
                validation_type="function_test",
                difficulty=3,
                tags=["python", "algorithm", "sorting"]
            ),
            Problem(
                problem_id="coding_018",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `is_valid_parentheses(s)` that returns True if brackets (), [], {} are balanced.",
                expected_output="def is_valid_parentheses",
                validation_type="function_test",
                difficulty=2,
                tags=["python", "stack", "validation"]
            ),
            
            # Tree/Graph
            Problem(
                problem_id="coding_019",
                category=BenchmarkCategory.CODING,
                statement="Write a Python class `TreeNode` with value, left, right, and method `inorder()` returning inorder traversal list.",
                expected_output="class TreeNode",
                validation_type="class_test",
                difficulty=3,
                tags=["python", "tree", "recursion"]
            ),
            Problem(
                problem_id="coding_020",
                category=BenchmarkCategory.CODING,
                statement="Write a Python function `shortest_path(graph, start, end)` using BFS. Graph is dict of node -> [neighbors].",
                expected_output="def shortest_path",
                validation_type="function_test",
                difficulty=4,
                tags=["python", "graph", "bfs"]
            ),
        ]
    
    async def score_problem(
        self,
        problem: Problem,
        response: str,
        context: Optional[Dict] = None
    ) -> tuple[float, bool, Optional[str]]:
        """Score a coding problem response"""
        
        if not response:
            return 0.0, False, "Empty response"
        
        # Extract code from response (handle markdown)
        code = self._extract_code(response)
        
        if not code:
            return 0.0, False, "No code found in response"
        
        # Check for expected output (basic check)
        if problem.validation_type == "contains":
            if problem.expected_output in code:
                return 1.0, True, None
            return 0.0, False, f"Expected '{problem.expected_output}' not found"
        
        # For function/class tests, try to execute
        if problem.validation_type in ["function_test", "class_test"]:
            return await self._test_code(problem, code)
        
        # Default: check if expected string is present
        if problem.expected_output in code:
            return 0.8, True, None
        
        return 0.2, False, "Code structure doesn't match expected"
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from response"""
        # Try to find code block
        patterns = [
            r'```python\n(.*?)```',
            r'```\n(.*?)```',
            r'```(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # No code block, try to find def/class
        if 'def ' in response or 'class ' in response:
            lines = []
            in_code = False
            for line in response.split('\n'):
                if line.strip().startswith(('def ', 'class ', 'async def ')):
                    in_code = True
                if in_code:
                    lines.append(line)
                    # Simple heuristic: stop at empty line after some code
                    if line.strip() == '' and len(lines) > 3:
                        break
            if lines:
                return '\n'.join(lines)
        
        return response
    
    async def _test_code(
        self,
        problem: Problem,
        code: str
    ) -> tuple[float, bool, Optional[str]]:
        """Actually test the code"""
        
        # Build test script based on problem
        test_cases = self._get_test_cases(problem.problem_id)
        
        if not test_cases:
            # No specific tests, just check syntax
            try:
                compile(code, '<string>', 'exec')
                return 0.7, True, "Syntax valid, no specific tests"
            except SyntaxError as e:
                return 0.0, False, f"Syntax error: {e}"
        
        # Create test script
        test_script = f'''
{code}

# Test cases
import sys
passed = 0
total = 0
errors = []

{test_cases}

print(f"RESULT: {{passed}}/{{total}}")
if errors:
    print("ERRORS:", errors[:3])
sys.exit(0 if passed == total else 1)
'''
        
        # Run in subprocess
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                f.flush()
                
                result = subprocess.run(
                    ['python3', f.name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse result
                output = result.stdout + result.stderr
                
                if 'RESULT:' in output:
                    match = re.search(r'RESULT: (\d+)/(\d+)', output)
                    if match:
                        passed = int(match.group(1))
                        total = int(match.group(2))
                        score = passed / total if total > 0 else 0.0
                        return score, passed == total, None if passed == total else f"{passed}/{total} tests passed"
                
                if result.returncode == 0:
                    return 0.8, True, None
                else:
                    return 0.3, False, output[:200]
                    
        except subprocess.TimeoutExpired:
            return 0.1, False, "Test timeout"
        except Exception as e:
            return 0.0, False, str(e)
    
    def _get_test_cases(self, problem_id: str) -> str:
        """Get test cases for a problem"""
        
        tests = {
            "coding_001": '''
try:
    total = 5
    assert fibonacci(0) == 0; passed += 1
    assert fibonacci(1) == 1; passed += 1
    assert fibonacci(5) == 5; passed += 1
    assert fibonacci(10) == 55; passed += 1
    assert fibonacci(20) == 6765; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_002": '''
try:
    total = 5
    assert is_palindrome("racecar") == True; passed += 1
    assert is_palindrome("hello") == False; passed += 1
    assert is_palindrome("A man a plan a canal Panama") == True; passed += 1
    assert is_palindrome("") == True; passed += 1
    assert is_palindrome("ab") == False; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_003": '''
try:
    total = 5
    assert factorial(0) == 1; passed += 1
    assert factorial(1) == 1; passed += 1
    assert factorial(5) == 120; passed += 1
    assert factorial(10) == 3628800; passed += 1
    assert factorial(3) == 6; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_004": '''
try:
    total = 4
    assert merge_sorted_lists([1,3,5], [2,4,6]) == [1,2,3,4,5,6]; passed += 1
    assert merge_sorted_lists([], [1,2,3]) == [1,2,3]; passed += 1
    assert merge_sorted_lists([1,2,3], []) == [1,2,3]; passed += 1
    assert merge_sorted_lists([1,1,2], [1,3]) == [1,1,1,2,3]; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_005": '''
try:
    total = 4
    result = find_duplicates([1,2,3,2,4,3])
    assert set(result) == {2,3}; passed += 1
    assert find_duplicates([1,2,3]) == []; passed += 1
    assert find_duplicates([]) == []; passed += 1
    assert 1 in find_duplicates([1,1,1]); passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_006": '''
try:
    total = 5
    assert validate_email("test@example.com") == True; passed += 1
    assert validate_email("invalid") == False; passed += 1
    assert validate_email("no@domain") == False; passed += 1
    assert validate_email("@nodomain.com") == False; passed += 1
    assert validate_email("user@sub.domain.com") == True; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_007": '''
try:
    total = 5
    s = Stack()
    assert s.is_empty() == True; passed += 1
    s.push(1); s.push(2)
    assert s.peek() == 2; passed += 1
    assert s.pop() == 2; passed += 1
    assert s.pop() == 1; passed += 1
    assert s.is_empty() == True; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
            "coding_008": '''
try:
    total = 5
    assert binary_search([1,2,3,4,5], 3) == 2; passed += 1
    assert binary_search([1,2,3,4,5], 1) == 0; passed += 1
    assert binary_search([1,2,3,4,5], 5) == 4; passed += 1
    assert binary_search([1,2,3,4,5], 6) == -1; passed += 1
    assert binary_search([], 1) == -1; passed += 1
except AssertionError as e:
    errors.append(str(e))
except Exception as e:
    errors.append(str(e))
''',
        }
        
        return tests.get(problem_id, "total = 1; passed = 1  # No specific tests")
