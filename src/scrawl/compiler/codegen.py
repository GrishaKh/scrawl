"""Code generator — walks the AST and produces Scratch block JSON.

Handles block ID generation, next/parent wiring, input encoding,
variable/list/broadcast resolution, and menu shadow blocks.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from scrawl.compiler.ast_nodes import (
    BlockNode,
    BroadcastInput,
    CustomBlockDef,
    FieldNode,
    InputNode,
    LiteralInput,
    ListInput,
    ReporterInput,
    ScriptNode,
    StatementNode,
    VariableInput,
)
from scrawl.compiler.errors import CodeGenError
from scrawl.compiler.registry import BlockShape, MenuSpec
from scrawl.compiler.registry_data import ALL_BLOCKS
from scrawl.model import ScratchProject

# Set of opcodes that are boolean reporters
_BOOLEAN_OPCODES = frozenset(
    bd.opcode for bd in ALL_BLOCKS if bd.shape == BlockShape.BOOLEAN
)

# Map from opcode to BlockDef for looking up menu specs etc.
_OPCODE_TO_BLOCKDEF = {bd.opcode: bd for bd in ALL_BLOCKS}

# Primitive type codes
_PRIMITIVE_CODES = {
    "number": 4,
    "positive_number": 5,
    "positive_integer": 6,
    "integer": 7,
    "angle": 8,
    "color": 9,
    "string": 10,
}


class CodeGenerator:
    """Generate Scratch 3.0 block JSON from an AST."""

    def __init__(
        self,
        target: dict[str, Any],
        project: Optional[ScratchProject] = None,
    ):
        """
        Args:
            target: The target dict (sprite or stage) where blocks will be injected.
            project: Optional full project for global variable/broadcast resolution.
        """
        self.target = target
        self.project = project
        self.blocks: dict[str, dict[str, Any]] = {}

        # Resolution caches: name → ID
        self._var_cache: dict[str, str] = {}
        self._list_cache: dict[str, str] = {}
        self._broadcast_cache: dict[str, str] = {}

        self._build_resolution_caches()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self, scripts: list[ScriptNode | CustomBlockDef]
    ) -> dict[str, dict[str, Any]]:
        """Generate block JSON for all scripts and return the blocks dict."""
        y_offset = 0
        for script in scripts:
            if isinstance(script, CustomBlockDef):
                self._generate_custom_block(script, y_offset)
            else:
                self._generate_script(script, y_offset)
            y_offset += 300  # Space scripts vertically
        return self.blocks

    # ------------------------------------------------------------------
    # Script generation
    # ------------------------------------------------------------------

    def _generate_script(self, script: ScriptNode, y: int = 0) -> None:
        """Generate blocks for a full script (hat + body)."""
        hat_id = self._generate_block(
            script.hat, parent_id=None, is_top=True, x=0, y=y
        )

        if script.body:
            first_body_id = self._generate_chain(script.body, parent_id=hat_id)
            if first_body_id:
                self.blocks[hat_id]["next"] = first_body_id

    def _generate_chain(
        self, statements: list[StatementNode], parent_id: str
    ) -> Optional[str]:
        """Generate a chain of statement blocks. Returns ID of the first block."""
        if not statements:
            return None

        first_id: Optional[str] = None
        prev_id: Optional[str] = None

        for stmt in statements:
            block_id = self._generate_block(
                stmt.block,
                parent_id=prev_id if prev_id else parent_id,
                is_top=False,
            )

            if first_id is None:
                first_id = block_id

            if prev_id is not None:
                self.blocks[prev_id]["next"] = block_id

            # Generate substacks for C-blocks
            for i, substack in enumerate(stmt.substacks):
                substack_key = "SUBSTACK" if i == 0 else "SUBSTACK2"
                if substack:
                    first_sub_id = self._generate_chain(substack, parent_id=block_id)
                    if first_sub_id:
                        self.blocks[block_id]["inputs"][substack_key] = [
                            2,
                            first_sub_id,
                        ]

            prev_id = block_id

        return first_id

    # ------------------------------------------------------------------
    # Single block generation
    # ------------------------------------------------------------------

    def _generate_block(
        self,
        node: BlockNode,
        parent_id: Optional[str],
        is_top: bool,
        x: int = 0,
        y: int = 0,
    ) -> str:
        """Generate a single block dict and add it to self.blocks."""
        block_id = self._new_id()

        block: dict[str, Any] = {
            "opcode": node.opcode,
            "next": None,
            "parent": parent_id,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": is_top,
        }

        if is_top:
            block["x"] = x
            block["y"] = y

        self.blocks[block_id] = block

        # Generate inputs
        for input_name, input_node in node.inputs.items():
            input_spec = self._find_input_spec(node.opcode, input_name)
            block["inputs"][input_name] = self._generate_input(
                input_node, block_id, input_spec
            )

        # Generate fields
        for field_name, field_node in node.fields.items():
            block["fields"][field_name] = self._generate_field(
                field_name, field_node, node.opcode
            )

        # Handle menu shadow blocks
        block_def = _OPCODE_TO_BLOCKDEF.get(node.opcode)
        if block_def and block_def.menu:
            self._generate_menu_shadow(block_def.menu, node, block_id)

        # Handle mutation (procedures_call)
        if node.mutation is not None:
            block["mutation"] = node.mutation

        return block_id

    # ------------------------------------------------------------------
    # Input encoding
    # ------------------------------------------------------------------

    def _generate_input(
        self,
        input_node: InputNode,
        parent_id: str,
        input_spec: Optional[Any] = None,
    ) -> list:
        """Encode an input node into Scratch's input array format."""
        if isinstance(input_node, LiteralInput):
            prim_code = _PRIMITIVE_CODES.get(input_node.input_type, 10)
            return [1, [prim_code, str(input_node.value)]]

        if isinstance(input_node, VariableInput):
            var_id = self._resolve_variable_id(input_node.name)
            if var_id:
                # Shadow type 3 with fallback
                return [3, [12, input_node.name, var_id], [10, "0"]]
            # Not a known variable — treat as literal string
            prim_code = 10
            if input_spec and hasattr(input_spec, "primitive_code") and input_spec.primitive_code:
                prim_code = input_spec.primitive_code
            return [1, [prim_code, input_node.name]]

        if isinstance(input_node, ListInput):
            list_id = self._resolve_list_id(input_node.name)
            return [3, [13, input_node.name, list_id], [10, ""]]

        if isinstance(input_node, BroadcastInput):
            bc_id = self._resolve_broadcast_id(input_node.name)
            return [1, [11, input_node.name, bc_id]]

        if isinstance(input_node, ReporterInput):
            reporter_id = self._generate_block(
                input_node.block, parent_id=parent_id, is_top=False
            )
            if input_node.block.opcode in _BOOLEAN_OPCODES:
                return [2, reporter_id]
            return [3, reporter_id, [10, ""]]

        raise CodeGenError(f"Unknown input node type: {type(input_node)}")

    # ------------------------------------------------------------------
    # Field encoding
    # ------------------------------------------------------------------

    def _generate_field(
        self, field_name: str, field_node: FieldNode, opcode: str
    ) -> list:
        """Encode a field node into Scratch's field array format."""
        value = field_node.value

        # Variable fields need ID resolution
        if field_name == "VARIABLE":
            var_id = self._resolve_variable_id(value, auto_create=True)
            return [value, var_id]

        # List fields need ID resolution
        if field_name == "LIST":
            list_id = self._resolve_list_id(value, auto_create=True)
            return [value, list_id]

        # Broadcast fields need ID resolution
        if field_name == "BROADCAST_OPTION":
            bc_id = self._resolve_broadcast_id(value, auto_create=True)
            return [value, bc_id]

        # Stop option, clone option, etc. — just value + null
        return [value, None]

    # ------------------------------------------------------------------
    # Menu shadow blocks
    # ------------------------------------------------------------------

    def _generate_menu_shadow(
        self, menu: MenuSpec, node: BlockNode, parent_id: str
    ) -> None:
        """Generate a menu shadow block and wire it into the parent's inputs."""
        # Get the menu value from the parent's fields
        menu_value = ""
        if menu.field_name in node.fields:
            menu_value = node.fields[menu.field_name].value
            # Remove from parent fields — it goes in the shadow instead
            del self.blocks[parent_id]["fields"][menu.field_name]

        shadow_id = self._new_id()
        shadow_block: dict[str, Any] = {
            "opcode": menu.opcode,
            "next": None,
            "parent": parent_id,
            "inputs": {},
            "fields": {menu.field_name: [menu_value, None]},
            "shadow": True,
            "topLevel": False,
        }
        self.blocks[shadow_id] = shadow_block

        # Wire the shadow into the parent's inputs
        self.blocks[parent_id]["inputs"][menu.input_name] = [1, shadow_id]

    # ------------------------------------------------------------------
    # Custom blocks
    # ------------------------------------------------------------------

    def _generate_custom_block(
        self, custom_def: CustomBlockDef, y: int = 0
    ) -> None:
        """Generate a custom block definition (procedures_definition + prototype)."""
        def_id = self._new_id()
        proto_id = self._new_id()

        arg_ids = [self._new_id() for _ in custom_def.argument_names]

        # Build argument reporter shadow blocks
        proto_inputs: dict[str, list] = {}
        for arg_name, arg_type, arg_id in zip(
            custom_def.argument_names, custom_def.argument_types, arg_ids
        ):
            reporter_id = self._new_id()
            opcode = (
                "argument_reporter_boolean"
                if arg_type == "b"
                else "argument_reporter_string_number"
            )
            reporter_block = {
                "opcode": opcode,
                "next": None,
                "parent": proto_id,
                "inputs": {},
                "fields": {"VALUE": [arg_name, None]},
                "shadow": True,
                "topLevel": False,
            }
            self.blocks[reporter_id] = reporter_block
            proto_inputs[arg_id] = [1, reporter_id]

        # Build prototype block
        proto_block: dict[str, Any] = {
            "opcode": "procedures_prototype",
            "next": None,
            "parent": def_id,
            "inputs": proto_inputs,
            "fields": {},
            "shadow": True,
            "topLevel": False,
            "mutation": {
                "tagName": "mutation",
                "children": [],
                "proccode": custom_def.proccode,
                "argumentids": json.dumps(arg_ids),
                "argumentnames": json.dumps(custom_def.argument_names),
                "argumentdefaults": json.dumps(
                    ["" for _ in arg_ids]
                ),
                "warp": str(custom_def.warp).lower(),
            },
        }
        self.blocks[proto_id] = proto_block

        # Build definition hat block
        def_block: dict[str, Any] = {
            "opcode": "procedures_definition",
            "next": None,
            "parent": None,
            "inputs": {"custom_block": [1, proto_id]},
            "fields": {},
            "shadow": False,
            "topLevel": True,
            "x": 0,
            "y": y,
        }
        self.blocks[def_id] = def_block

        # Generate body chain
        if custom_def.body:
            first_body_id = self._generate_chain(
                custom_def.body, parent_id=def_id
            )
            if first_body_id:
                self.blocks[def_id]["next"] = first_body_id

    # ------------------------------------------------------------------
    # Variable / List / Broadcast resolution
    # ------------------------------------------------------------------

    def _build_resolution_caches(self) -> None:
        """Build name → ID mappings from the target and stage."""
        # Local variables and lists
        for var_id, var_data in self.target.get("variables", {}).items():
            if isinstance(var_data, list) and len(var_data) >= 2:
                self._var_cache[var_data[0]] = var_id

        for list_id, list_data in self.target.get("lists", {}).items():
            if isinstance(list_data, list) and len(list_data) >= 2:
                self._list_cache[list_data[0]] = list_id

        # Global variables/lists/broadcasts from stage
        if self.project and self.project.stage:
            stage = self.project.stage
            for var_id, var_data in stage.get("variables", {}).items():
                if isinstance(var_data, list) and len(var_data) >= 2:
                    if var_data[0] not in self._var_cache:
                        self._var_cache[var_data[0]] = var_id

            for list_id, list_data in stage.get("lists", {}).items():
                if isinstance(list_data, list) and len(list_data) >= 2:
                    if list_data[0] not in self._list_cache:
                        self._list_cache[list_data[0]] = list_id

            for bc_id, bc_name in stage.get("broadcasts", {}).items():
                self._broadcast_cache[bc_name] = bc_id

        # Broadcasts from target (non-stage sprites can also have them)
        for bc_id, bc_name in self.target.get("broadcasts", {}).items():
            if bc_name not in self._broadcast_cache:
                self._broadcast_cache[bc_name] = bc_id

    def _resolve_variable_id(
        self, name: str, auto_create: bool = False
    ) -> Optional[str]:
        """Resolve a variable name to its ID."""
        if name in self._var_cache:
            return self._var_cache[name]
        if auto_create:
            new_id = self._new_id()
            self.target.setdefault("variables", {})[new_id] = [name, 0]
            self._var_cache[name] = new_id
            return new_id
        return None

    def _resolve_list_id(
        self, name: str, auto_create: bool = True
    ) -> str:
        """Resolve a list name to its ID."""
        if name in self._list_cache:
            return self._list_cache[name]
        new_id = self._new_id()
        self.target.setdefault("lists", {})[new_id] = [name, []]
        self._list_cache[name] = new_id
        return new_id

    def _resolve_broadcast_id(
        self, name: str, auto_create: bool = True
    ) -> str:
        """Resolve a broadcast name to its ID."""
        if name in self._broadcast_cache:
            return self._broadcast_cache[name]
        new_id = self._new_id()
        # Broadcasts go on the stage
        stage = self.project.stage if self.project and self.project.stage else self.target
        stage.setdefault("broadcasts", {})[new_id] = name
        self._broadcast_cache[name] = new_id
        return new_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_input_spec(self, opcode: str, input_name: str) -> Optional[Any]:
        """Look up the InputSpec for a given opcode and input name."""
        block_def = _OPCODE_TO_BLOCKDEF.get(opcode)
        if block_def:
            for spec in block_def.inputs:
                if spec.name == input_name:
                    return spec
        return None

    @staticmethod
    def _new_id() -> str:
        """Generate a unique block ID."""
        return uuid.uuid4().hex[:20]
