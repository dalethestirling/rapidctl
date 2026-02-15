import re
from typing import Any, Dict, List, Optional, Union

class VersionParser:
    """
    Utility class for parsing and comparing version strings.
    Supports semantic versioning (v1.2.3), timestamps (1746190043), 
    and custom tags (latest, stable).
    """

    @staticmethod
    def is_semver(version: str) -> bool:
        """Check if a version string follows semantic versioning."""
        # Simple semver regex: optional 'v' prefix, 3 numbers separated by dots
        return bool(re.match(r'^v?\d+\.\d+\.\d+', version))

    @staticmethod
    def is_timestamp(version: str) -> bool:
        """Check if a version string is a numeric timestamp."""
        return version.isdigit()

    @classmethod
    def parse(cls, version: str) -> Dict[str, Any]:
        """
        Parse a version string into a comparable format.
        
        Returns a dict with:
            - type: 'semver', 'timestamp', or 'custom'
            - components: list of integers (for semver) or a single integer (for timestamp)
            - value: the original string
        """
        if cls.is_semver(version):
            # Strip 'v' prefix and split by '.'
            clean_v = version.lstrip('v')
            # Extract only the numeric version parts (ignore suffixes for now)
            matches = re.match(r'^(\d+)\.(\d+)\.(\d+)', clean_v)
            if matches:
                components = [int(p) for p in matches.groups()]
                return {
                    "type": "semver",
                    "components": components,
                    "value": version
                }
        
        if cls.is_timestamp(version):
            return {
                "type": "timestamp",
                "components": [int(version)],
                "value": version
            }
            
        return {
            "type": "custom",
            "components": [],
            "value": version
        }

    @classmethod
    def compare(cls, version1: str, version2: str) -> int:
        """
        Compare two versions.
        
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1_data = cls.parse(version1)
        v2_data = cls.parse(version2)

        # Exact match
        if version1 == version2:
            return 0

        # Handle 'latest' tag - it's always considered newer than anything else
        if version2 == "latest":
            return -1 if version1 != "latest" else 0
        if version1 == "latest":
            return 1 if version2 != "latest" else 0

        # Different types: generally incomparable, but we'll try to keep some order
        # Timestamp vs Semver: let's treat timestamp as newer if compared directly
        if v1_data["type"] != v2_data["type"]:
            # If one is semver and other is timestamp, timestamp is newer (following examplectl pattern)
            if v1_data["type"] == "semver" and v2_data["type"] == "timestamp":
                return -1
            if v1_data["type"] == "timestamp" and v2_data["type"] == "semver":
                return 1
            # Fallback to string comparison for completely mismatched types
            return (version1 > version2) - (version1 < version2)

        # Same type: perform numeric comparison
        for v1_comp, v2_comp in zip(v1_data["components"], v2_data["components"]):
            if v1_comp < v2_comp:
                return -1
            if v1_comp > v2_comp:
                return 1

        # If components match but lengths differ (like 1.2 vs 1.2.3, though our parse enforces 3)
        if len(v1_data["components"]) < len(v2_data["components"]):
            return -1
        if len(v1_data["components"]) > len(v2_data["components"]):
            return 1

        return 0
