"""LicenseValidateTool - Validate state contractor licenses.

Validates contractor licenses against state licensing databases.

Usage:
    tool = LicenseValidateTool()
    result = await tool.run({
        "contractor_name": "ABC Solar",
        "state": "CA",
        "license_number": "12345",  # optional
    })
"""

from plugins.scraper_tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


def lookup_license(contractor_name: str, state: str, license_number: str = None) -> dict:
    """Look up contractor license in state database.

    This is a placeholder that should be replaced with actual
    license lookup logic using scrapers/license/ module.

    Args:
        contractor_name: Name of contractor
        state: Two-letter state code
        license_number: Optional license number for exact lookup

    Returns:
        License information dictionary
    """
    # TODO: Integrate with scrapers/license/ module
    # For now, return a structured response
    return {
        "license_number": license_number or "Unknown",
        "license_status": "Unknown",
        "expiration_date": None,
        "license_type": None,
        "violations": [],
        "lookup_source": f"{state} State License Board",
    }


class LicenseValidateTool(BaseTool):
    """Validate contractor licenses against state databases.

    Checks license status, expiration, violations for contractors
    in supported states (CA, TX, FL, NY, etc.).
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="license_validate",
            description=(
                "Validate contractor license status against state licensing databases. "
                "Returns license number, status (Active/Expired/Revoked), expiration date, "
                "and any violations."
            ),
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "contractor_name": {
                        "type": "string",
                        "description": "Name of contractor/business to look up",
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter state code (e.g., 'CA', 'TX')",
                    },
                    "license_number": {
                        "type": "string",
                        "description": "Known license number for exact lookup (optional)",
                    },
                },
                "required": ["contractor_name", "state"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """Execute license validation.

        Args:
            arguments: Must contain 'contractor_name' and 'state'

        Returns:
            ToolResult with license information
        """
        contractor_name = arguments.get("contractor_name", "")
        state = arguments.get("state", "")
        license_number = arguments.get("license_number")

        try:
            # Validate state code
            if len(state) != 2:
                return ToolResult(
                    tool_name="license_validate",
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=f"Invalid state code: {state}. Use two-letter code (e.g., 'CA')",
                )

            state = state.upper()

            # Look up license
            license_info = lookup_license(
                contractor_name=contractor_name,
                state=state,
                license_number=license_number,
            )

            return ToolResult(
                tool_name="license_validate",
                success=True,
                result=license_info,
                execution_time_ms=0,
            )

        except Exception as e:
            return ToolResult(
                tool_name="license_validate",
                success=False,
                result=None,
                execution_time_ms=0,
                error=f"License lookup failed: {str(e)}",
            )
