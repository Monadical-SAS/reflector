"""Platform type definitions.

This module exists solely to define the Platform literal type without any imports,
preventing circular import issues when used across the codebase.
"""

from typing import Literal

Platform = Literal["whereby", "daily"]
