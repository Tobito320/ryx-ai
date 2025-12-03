"""
Ryx AI - Bug Fixing Benchmark

Tests the ability to:
1. Understand broken code
2. Identify the bug
3. Generate a correct fix
4. Explain the fix

These are critical for the self-healing RSI capabilities.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

from .base import (
    BaseBenchmark, Problem, BenchmarkCategory,
    register_benchmark
)


@register_benchmark
class BugFixingBenchmark(BaseBenchmark):
    """
    Bug fixing benchmark.
    
    Each problem presents broken code and asks for a fix.
    Tests diagnostic and repair capabilities.
    """
    
    name = "bug_fixing"
    description = "Bug detection and fixing tasks"
    category = BenchmarkCategory.FIXING
    
    @property
    def problems(self) -> List[Problem]:
        return [
            # Off-by-one errors
            Problem(
                problem_id="fix_001",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It should return the sum of numbers from 1 to n (inclusive).
Currently it's off by one.

```python
def sum_to_n(n):
    total = 0
    for i in range(n):  # Bug here
        total += i
    return total
```

Expected: sum_to_n(5) = 15 (1+2+3+4+5)""",
                expected_output="range(1, n + 1)",
                validation_type="function_test",
                difficulty=1,
                tags=["off-by-one", "loop"]
            ),
            
            # Null/None handling
            Problem(
                problem_id="fix_002",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It crashes when the input list is None.

```python
def get_first(items):
    return items[0]  # Crashes on None
```

Expected: get_first(None) should return None, get_first([1,2,3]) returns 1""",
                expected_output="if not items",
                validation_type="function_test",
                difficulty=1,
                tags=["null-check", "defensive"]
            ),
            
            # Infinite loop
            Problem(
                problem_id="fix_003",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It causes an infinite loop.

```python
def countdown(n):
    result = []
    while n > 0:
        result.append(n)
        # Missing: n -= 1
    return result
```

Expected: countdown(3) = [3, 2, 1]""",
                expected_output="n -= 1",
                validation_type="contains",
                difficulty=1,
                tags=["infinite-loop", "while"]
            ),
            
            # Wrong operator
            Problem(
                problem_id="fix_004",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It uses the wrong comparison operator.

```python
def is_adult(age):
    return age > 18  # Should be >= for exactly 18
```

Expected: is_adult(18) = True""",
                expected_output=">=",
                validation_type="function_test",
                difficulty=1,
                tags=["operator", "comparison"]
            ),
            
            # Missing return
            Problem(
                problem_id="fix_005",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It doesn't return anything in one branch.

```python
def absolute(n):
    if n < 0:
        return -n
    # Missing return for positive case
```

Expected: absolute(5) = 5, absolute(-5) = 5""",
                expected_output="return n",
                validation_type="function_test",
                difficulty=1,
                tags=["return", "branch"]
            ),
            
            # String vs int
            Problem(
                problem_id="fix_006",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It fails when parsing user input.

```python
def add_numbers(a, b):
    # User input is strings, need to convert
    return a + b  # Concatenates instead of adding
```

Expected: add_numbers("5", "3") = 8""",
                expected_output="int(",
                validation_type="function_test",
                difficulty=2,
                tags=["type-conversion", "string"]
            ),
            
            # List mutation during iteration
            Problem(
                problem_id="fix_007",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It modifies a list while iterating.

```python
def remove_evens(numbers):
    for n in numbers:
        if n % 2 == 0:
            numbers.remove(n)  # Dangerous!
    return numbers
```

Expected: remove_evens([1,2,3,4,5,6]) = [1,3,5]""",
                expected_output="[n for n in numbers if",
                validation_type="function_test",
                difficulty=2,
                tags=["list-mutation", "iteration"]
            ),
            
            # Key error
            Problem(
                problem_id="fix_008",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It raises KeyError for missing keys.

```python
def get_value(data, key):
    return data[key]  # Crashes if key missing
```

Expected: get_value({}, 'a') = None, get_value({'a': 1}, 'a') = 1""",
                expected_output=".get(",
                validation_type="function_test",
                difficulty=1,
                tags=["dict", "key-error"]
            ),
            
            # Wrong recursion base case
            Problem(
                problem_id="fix_009",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this recursive function. It has the wrong base case.

```python
def factorial(n):
    if n == 1:  # Wrong: doesn't handle 0
        return 1
    return n * factorial(n - 1)
```

Expected: factorial(0) = 1, factorial(5) = 120""",
                expected_output="n <= 1",
                validation_type="function_test",
                difficulty=2,
                tags=["recursion", "base-case"]
            ),
            
            # Variable scope
            Problem(
                problem_id="fix_010",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It has a variable scope issue.

```python
def counter():
    count = 0
    def increment():
        count += 1  # UnboundLocalError
        return count
    return increment
```

Expected: c = counter(); c() = 1; c() = 2""",
                expected_output="nonlocal count",
                validation_type="contains",
                difficulty=2,
                tags=["scope", "closure"]
            ),
            
            # Exception handling
            Problem(
                problem_id="fix_011",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It swallows all exceptions badly.

```python
def safe_divide(a, b):
    try:
        return a / b
    except:  # Too broad, catches everything
        return 0
```

Should specifically catch ZeroDivisionError and re-raise others.""",
                expected_output="except ZeroDivisionError",
                validation_type="contains",
                difficulty=2,
                tags=["exception", "error-handling"]
            ),
            
            # Mutable default argument
            Problem(
                problem_id="fix_012",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It has a mutable default argument bug.

```python
def append_to(item, lst=[]):  # Bug: shared list
    lst.append(item)
    return lst
```

Expected: append_to(1) = [1], append_to(2) = [2] (not [1,2])""",
                expected_output="lst=None",
                validation_type="function_test",
                difficulty=2,
                tags=["mutable-default", "python-gotcha"]
            ),
            
            # Float comparison
            Problem(
                problem_id="fix_013",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. It fails due to float precision.

```python
def is_equal(a, b):
    return a == b  # Fails for 0.1 + 0.2 == 0.3
```

Should use approximate comparison for floats.""",
                expected_output="abs(",
                validation_type="contains",
                difficulty=2,
                tags=["float", "precision"]
            ),
            
            # String formatting
            Problem(
                problem_id="fix_014",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this function. The string formatting is broken.

```python
def greet(name, age):
    return "Hello {name}, you are {age}"  # Missing f-string
```

Expected: greet("Alice", 30) = "Hello Alice, you are 30\"""",
                expected_output='f"',
                validation_type="function_test",
                difficulty=1,
                tags=["string", "f-string"]
            ),
            
            # Import error
            Problem(
                problem_id="fix_015",
                category=BenchmarkCategory.FIXING,
                statement="""Fix this code. It has an import that might not be available.

```python
import special_module  # Might not exist

def process():
    return special_module.do_thing()
```

Should handle the case when special_module is not installed.""",
                expected_output="try:",
                validation_type="contains",
                difficulty=2,
                tags=["import", "optional-dependency"]
            ),
        ]
    
    async def score_problem(
        self,
        problem: Problem,
        response: str,
        context: Optional[Dict] = None
    ) -> tuple[float, bool, Optional[str]]:
        """Score a bug fixing response"""
        
        if not response:
            return 0.0, False, "Empty response"
        
        # Extract code
        code = self._extract_code(response)
        
        if not code:
            return 0.0, False, "No code found"
        
        # Check for expected fix pattern
        if problem.validation_type == "contains":
            if problem.expected_output in code:
                return 1.0, True, None
            return 0.3, False, f"Expected pattern '{problem.expected_output}' not found"
        
        # Run actual tests for function_test
        if problem.validation_type == "function_test":
            return await self._test_fix(problem, code)
        
        return 0.5, False, "Could not validate"
    
    def _extract_code(self, response: str) -> str:
        """Extract code from response"""
        patterns = [
            r'```python\n(.*?)```',
            r'```\n(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Try to find function definition
        if 'def ' in response:
            lines = []
            in_func = False
            indent = 0
            for line in response.split('\n'):
                if line.strip().startswith('def '):
                    in_func = True
                    indent = len(line) - len(line.lstrip())
                if in_func:
                    lines.append(line)
                    # Check if we've left the function
                    if lines and line.strip() and not line.startswith(' ' * indent) and not line.strip().startswith('def'):
                        break
            if lines:
                return '\n'.join(lines)
        
        return response
    
    async def _test_fix(
        self,
        problem: Problem,
        code: str
    ) -> tuple[float, bool, Optional[str]]:
        """Test the fixed code"""
        
        test_cases = self._get_test_cases(problem.problem_id)
        
        if not test_cases:
            # Just check syntax
            try:
                compile(code, '<string>', 'exec')
                if problem.expected_output in code:
                    return 0.8, True, "Syntax valid, pattern found"
                return 0.5, False, "Syntax valid, pattern not found"
            except SyntaxError as e:
                return 0.0, False, f"Syntax error: {e}"
        
        # Create and run test
        test_script = f'''
{code}

import sys
passed = 0
total = 0
errors = []

{test_cases}

print(f"RESULT: {{passed}}/{{total}}")
sys.exit(0 if passed == total else 1)
'''
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                f.flush()
                
                result = subprocess.run(
                    ['python3', f.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                output = result.stdout + result.stderr
                
                if 'RESULT:' in output:
                    match = re.search(r'RESULT: (\d+)/(\d+)', output)
                    if match:
                        passed = int(match.group(1))
                        total = int(match.group(2))
                        score = passed / total if total > 0 else 0.0
                        return score, passed == total, None if passed == total else f"{passed}/{total}"
                
                return 0.3, False, output[:200]
                
        except subprocess.TimeoutExpired:
            return 0.0, False, "Test timeout (possible infinite loop)"
        except Exception as e:
            return 0.0, False, str(e)
    
    def _get_test_cases(self, problem_id: str) -> str:
        """Get test cases for a problem"""
        
        tests = {
            "fix_001": '''
try:
    total = 3
    assert sum_to_n(1) == 1; passed += 1
    assert sum_to_n(5) == 15; passed += 1
    assert sum_to_n(10) == 55; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_002": '''
try:
    total = 3
    assert get_first(None) is None; passed += 1
    assert get_first([]) is None; passed += 1
    assert get_first([1, 2, 3]) == 1; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_004": '''
try:
    total = 3
    assert is_adult(17) == False; passed += 1
    assert is_adult(18) == True; passed += 1
    assert is_adult(21) == True; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_005": '''
try:
    total = 3
    assert absolute(5) == 5; passed += 1
    assert absolute(-5) == 5; passed += 1
    assert absolute(0) == 0; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_006": '''
try:
    total = 3
    assert add_numbers("5", "3") == 8; passed += 1
    assert add_numbers("0", "0") == 0; passed += 1
    assert add_numbers("-1", "1") == 0; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_007": '''
try:
    total = 2
    assert remove_evens([1,2,3,4,5,6]) == [1,3,5]; passed += 1
    assert remove_evens([2,4,6]) == []; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_008": '''
try:
    total = 3
    assert get_value({}, 'a') is None; passed += 1
    assert get_value({'a': 1}, 'a') == 1; passed += 1
    assert get_value({'a': 1}, 'b') is None; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_009": '''
try:
    total = 3
    assert factorial(0) == 1; passed += 1
    assert factorial(1) == 1; passed += 1
    assert factorial(5) == 120; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_012": '''
try:
    total = 2
    result1 = append_to(1)
    result2 = append_to(2)
    assert result1 == [1]; passed += 1
    assert result2 == [2]; passed += 1
except Exception as e:
    errors.append(str(e))
''',
            "fix_014": '''
try:
    total = 2
    assert greet("Alice", 30) == "Hello Alice, you are 30"; passed += 1
    assert greet("Bob", 25) == "Hello Bob, you are 25"; passed += 1
except Exception as e:
    errors.append(str(e))
''',
        }
        
        return tests.get(problem_id, "")
