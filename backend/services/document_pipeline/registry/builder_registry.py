from typing import List, Dict, Set
from services.document_pipeline.builders import BaseBuilder, ALL_BUILDERS

class BuilderRegistry:
    def __init__(self):
        self.builders: Dict[str, BaseBuilder] = {b.name: b for b in ALL_BUILDERS}

    def get_builder(self, name: str) -> BaseBuilder:
        return self.builders[name]

    def get_ordered_builders(self, targets: List[str] = None) -> List[BaseBuilder]:
        """
        Performs topological sort on all builders.
        """
        visited: Set[str] = set()
        temp_visited: Set[str] = set()
        order: List[str] = []

        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected at {name}")
            if name not in visited:
                temp_visited.add(name)
                builder = self.builders.get(name)
                if builder:
                    for dep in builder.dependencies:
                        visit(dep)
                temp_visited.remove(name)
                visited.add(name)
                order.append(name)

        all_names = list(self.builders.keys())
        for name in all_names:
            visit(name)

        full_order = [self.builders[name] for name in order if name in self.builders]

        if targets is None:
            return full_order

        # 1. Expand targets to include downstream dependents (downstream invalidation)
        invalidated = set(targets)
        changed = True
        while changed:
            changed = False
            for name, builder in self.builders.items():
                if name not in invalidated:
                    # If any dependency of this builder is invalidated, invalidate this builder too
                    if any(dep in invalidated for dep in builder.dependencies):
                        invalidated.add(name)
                        changed = True

        # 2. Return only the invalidated builders, ordered by topological sort order
        return [b for b in full_order if b.name in invalidated]
