from dataclasses import dataclass
from inspect import Parameter, Signature
from pathlib import Path
from typing import Any, Callable

from fastmcp import FastMCP


@dataclass
class PromptConfig:
    """Configuration for a single prompt."""

    name: str
    """The prompt function name"""

    file_name: str
    """The .txt file name (without extension)"""

    description: str
    """Description shown to the LLM"""

    parameters: list[str] | None = None
    """List of parameter names, if the prompt takes arguments"""

    returns_list: bool = False
    """Whether the prompt returns a list[str] instead of str"""

    placeholders: dict[str, str] | None = None
    """Placeholder replacements for dynamic content"""


class PromptManager:
    """Manages and registers prompts for the Selent MCP server."""

    PROMPT_CONFIGS = [
        PromptConfig(
            name="multi_key_startup_guide",
            file_name="multi_key_startup_guide",
            description="Multi-key setup guide - Run discover_all_organizations() first!",
        ),
        PromptConfig(
            name="parameter_examples_guide",
            file_name="parameter_examples_guide",
            description="Common parameter formats and examples for Meraki API",
        ),
        PromptConfig(
            name="meraki_api_workflow",
            file_name="meraki_api_workflow",
            description="Guide for discovering and using Meraki API endpoints",
            parameters=["task"],
            returns_list=True,
            placeholders={
                "kwargs='ADDITIONAL_PARAMS_PLACEHOLDER'": (
                    'kwargs=\'{"additional": "parameters"}\''
                ),
                "kwargs='EXAMPLE_PARAMS_PLACEHOLDER'": (
                    'kwargs=\'{"timespan": 3600, "perPage": 50}\''
                ),
            },
        ),
        PromptConfig(
            name="search_endpoints_guide",
            file_name="search_endpoints_guide",
            description="Quick reference for searching Meraki API endpoints",
        ),
        PromptConfig(
            name="parameters_guide",
            file_name="parameters_guide",
            description="Guide for understanding endpoint parameters",
            parameters=["section", "method"],
            placeholders={
                "kwargs='JSON_PLACEHOLDER'": (
                    'kwargs=\'{"timespan": 3600, "perPage": 50}\''
                ),
                "JSON_DICT_PLACEHOLDER": '{"vlan": 10, "enabled": true}',
            },
        ),
        PromptConfig(
            name="troubleshooting_guide",
            file_name="troubleshooting_guide",
            description="Troubleshooting guide for common API execution errors",
        ),
        PromptConfig(
            name="multi_key_workflow",
            file_name="multi_key_workflow",
            description="Guide for using Selent MCP with multiple API keys (MSP Mode)",
        ),
    ]

    def __init__(self, mcp: FastMCP):
        """Initialize the prompt manager with an MCP instance."""
        self.mcp = mcp
        self.prompts_dir = Path(__file__).parent / "prompts"

    def _read_prompt_file(self, filename: str) -> str:
        """Read a prompt file from the prompts directory."""
        file_path = self.prompts_dir / f"{filename}.txt"
        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {file_path}\n"
                f"Create {filename}.txt in the prompts directory."
            )
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _replace_placeholders(self, text: str, replacements: dict[str, str]) -> str:
        """Replace multiple placeholders in text efficiently."""
        for placeholder, replacement in replacements.items():
            text = text.replace(placeholder, replacement)
        return text

    def _create_prompt_handler(self, config: PromptConfig) -> Callable[..., Any]:
        """Create a prompt handler function based on configuration."""

        if config.parameters:
            def handler(**kwargs: str) -> str | list[str]:
                missing = set(config.parameters or []) - set(kwargs.keys())
                if missing:
                    raise TypeError(
                        f"{config.name}() missing required arguments: "
                        f"{', '.join(missing)}"
                    )

                template = self._read_prompt_file(config.file_name)
                content = template.format(**kwargs)

                if config.placeholders:
                    content = self._replace_placeholders(content, config.placeholders)

                return content.split("\n") if config.returns_list else content

            parameters = [
                Parameter(name, Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
                for name in config.parameters
            ]
            return_type = list[str] if config.returns_list else str
            handler.__signature__ = Signature(  # type: ignore
                parameters, return_annotation=return_type
            )
            handler.__annotations__ = {param: str for param in config.parameters}
            handler.__annotations__["return"] = return_type

        else:
            def handler() -> str:
                return self._read_prompt_file(config.file_name)

        handler.__name__ = config.name
        handler.__doc__ = f"{config.description}\n\nFile: {config.file_name}.txt"

        return handler

    def register_all_prompts(self) -> None:
        """Automatically register all prompts."""
        for config in self.PROMPT_CONFIGS:
            handler = self._create_prompt_handler(config)
            self.mcp.prompt(description=config.description)(handler)


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts with the MCP server (backward compatibility)."""
    manager = PromptManager(mcp)
    manager.register_all_prompts()
