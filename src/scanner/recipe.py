import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console

console = Console()
RECIPES_DIR = Path("recipes")
RECIPES_DIR.mkdir(exist_ok=True)


class RecipeManager:
    @staticmethod
    def load_recipe(name_or_path: str) -> Dict[str, Any]:
        """
        Load a recipe from a file.
        Tries to load directly if path exists, otherwise looks in RECIPES_DIR.
        """
        path = Path(name_or_path)
        if not path.suffix:
            path = path.with_suffix(".yaml")

        if not path.exists():
            # Try looking in recipes folder
            possible_path = RECIPES_DIR / path
            if possible_path.exists():
                path = possible_path
            else:
                console.print(f"[red]Recipe not found: {name_or_path}[/red]")
                return {}

        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[red]Error loading recipe {path}: {e}[/red]")
            return {}

    @staticmethod
    def save_recipe(name: str, config: Dict[str, Any]):
        """
        Save the current configuration to a recipe file in the recipes directory.
        """
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix(".yaml")

        # If user provided a path with directory, use it. Otherwise use default dir.
        if len(path.parts) == 1:
            path = RECIPES_DIR / path

        try:
            with open(path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            console.print(f"[green]Recipe saved to {path}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving recipe to {path}: {e}[/red]")
