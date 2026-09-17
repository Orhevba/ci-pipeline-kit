"""Minimal example app proving the Python reusable workflow works end to end."""


def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("world"))
