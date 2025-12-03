def is_prime(num):
    """Check if a number is prime."""
    if num <= 1:
        return False
    if num <= 3:
        return True
    if num % 2 == 0 or num % 3 == 0:
        return False
    i = 5
    while i * i <= num:
        if num % i == 0 or num % (i + 2) == 0:
            return False
        i += 6
    return True

def generate_primes(limit):
    """
    Generate a list of prime numbers up to a given limit.
    
    Args:
    limit (int): The upper bound for generating prime numbers.
    
    Returns:
    list: A list of prime numbers up to the specified limit.
    """
    if limit < 2:
        return []
    primes = [2]
    for num in range(3, limit + 1, 2):
        if is_prime(num):
            primes.append(num)
    return primes

if __name__ == "__main__":
    # Example usage
    limit = 50
    primes_up_to_limit = generate_primes(limit)
    print(f"Prime numbers up to {limit}: {primes_up_to_limit}")
```

This code defines a function `generate_primes` that calculates all prime numbers up to a specified limit. It includes a helper function `is_prime` to check the primality of individual numbers. The main block demonstrates how to use these functions.