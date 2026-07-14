"""Smart element selection — pick deepest/most specific node at coordinates."""

from __future__ import annotations

from typing import Optional

from inspectiq.domain.models import ElementNode

_GENERIC_LAYOUTS = frozenset({
    "FrameLayout",
    "LinearLayout",
    "RelativeLayout",
    "ViewGroup",
    "View",
    "ConstraintLayout",
    "CoordinatorLayout",
    "DrawerLayout",
    "NestedScrollView",
    "ScrollView",
    "HorizontalScrollView",
    "Merge",
    "DecorView",
})


class SmartElementSelector:
    """Resolves the best target element when user clicks on screen."""

    def find_at_coordinates(self, tree: ElementNode, x: int, y: int) -> Optional[ElementNode]:
        candidates = self._collect_containing_nodes(tree, x, y)
        if not candidates:
            return None
        return self._rank_candidates(candidates)

    def _collect_containing_nodes(
        self, node: ElementNode, x: int, y: int, acc: Optional[list[ElementNode]] = None
    ) -> list[ElementNode]:
        if acc is None:
            acc = []
        if node.bounds and node.bounds.contains(x, y):
            acc.append(node)
        for child in node.children:
            self._collect_containing_nodes(child, x, y, acc)
        return acc

    @staticmethod
    def _short_class_name(node: ElementNode) -> str:
        return (node.class_name or "").split(".")[-1]

    @classmethod
    def _is_generic_container(cls, node: ElementNode) -> bool:
        short = cls._short_class_name(node)
        if short in _GENERIC_LAYOUTS:
            return True
        return short.endswith("Layout") and short not in ("TabLayout",)

    @staticmethod
    def _has_identity(node: ElementNode) -> bool:
        return bool(
            node.resource_id
            or node.content_desc
            or node.accessibility_id
            or node.text
            or node.label
            or node.name
        )

    def _rank_candidates(self, candidates: list[ElementNode]) -> ElementNode:
        def sort_key(n: ElementNode) -> tuple:
            area = n.bounds.area if n.bounds else 10**9
            short = self._short_class_name(n)
            is_generic = self._is_generic_container(n)
            has_identity = self._has_identity(n)
            is_leaf = len(n.children) == 0
            is_interactive = n.clickable or n.long_clickable or n.checkable or n.focusable
            is_text_field = "EditText" in short or "TextField" in short
            is_button = "Button" in short or short.endswith("ImageButton")

            return (
                is_generic,
                not has_identity,
                area,
                -n.depth,
                not is_button,
                not is_text_field,
                not is_leaf,
                not is_interactive,
            )

        return sorted(candidates, key=sort_key)[0]

    def find_by_id(self, tree: ElementNode, element_id: str) -> Optional[ElementNode]:
        if tree.id == element_id:
            return tree
        for child in tree.children:
            found = self.find_by_id(child, element_id)
            if found:
                return found
        return None

    def get_parent(self, tree: ElementNode, target: ElementNode) -> Optional[ElementNode]:
        for child in tree.children:
            if child.id == target.id:
                return tree
            found = self.get_parent(child, target)
            if found is not None:
                return found
        return None

    def get_context(self, tree: ElementNode, target: ElementNode) -> dict:
        parent = self.get_parent(tree, target)
        siblings_before: list[ElementNode] = []
        siblings_after: list[ElementNode] = []
        if parent:
            found = False
            for child in parent.children:
                if child.id == target.id:
                    found = True
                    continue
                if not found:
                    siblings_before.append(child)
                else:
                    siblings_after.append(child)
        return {
            "parent": parent,
            "children": list(target.children),
            "siblings_before": siblings_before,
            "siblings_after": siblings_after,
        }

    def get_ancestors(self, tree: ElementNode, target: ElementNode) -> list[ElementNode]:
        path = self.get_path_to_element(tree, target)
        if not path or len(path) < 2:
            return []
        return list(reversed(path[1:]))

    def get_path_to_element(self, tree: ElementNode, target: ElementNode) -> Optional[list[ElementNode]]:
        path: list[ElementNode] = []

        def walk(node: ElementNode) -> bool:
            path.append(node)
            if node.id == target.id:
                return True
            for child in node.children:
                if walk(child):
                    return True
            path.pop()
            return False

        if walk(tree):
            return path
        return None

    def flatten(self, tree: ElementNode) -> list[ElementNode]:
        result = [tree]
        for child in tree.children:
            result.extend(self.flatten(child))
        return result

    def count_matches(self, tree: ElementNode, predicate) -> int:
        return sum(1 for n in self.flatten(tree) if predicate(n))
