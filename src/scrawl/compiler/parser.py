"""Recursive descent parser for ScratchText.

Converts a token stream into an AST of scripts, each containing
a hat block and a body of statements. C-blocks (forever, if, repeat)
use 'end' tokens to close, not indentation.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from scrawl.compiler.ast_nodes import (
    BlockNode,
    BroadcastInput,
    CustomBlockDef,
    FieldNode,
    InputNode,
    LiteralInput,
    ReporterInput,
    ScriptNode,
    StatementNode,
    VariableInput,
)
from scrawl.compiler.errors import ParseError, UnclosedBlockError, UnknownBlockError
from scrawl.compiler.registry import BlockRegistry, BlockShape, InputSpec
from scrawl.compiler.tokens import Token, TokenType


class Parser:
    """Parse a token stream into a list of scripts / custom block defs."""

    def __init__(self, tokens: list[Token], registry: BlockRegistry):
        self.tokens = tokens
        self.pos = 0
        self.registry = registry
        self._custom_blocks: dict[str, CustomBlockDef] = {}  # proccode → def

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> list[ScriptNode | CustomBlockDef]:
        """Parse all scripts from the token stream."""
        scripts: list[ScriptNode | CustomBlockDef] = []
        while not self._at_eof():
            self._skip_newlines()
            if self._at_eof():
                break
            if self._peek_type() == TokenType.DEFINE:
                scripts.append(self._parse_custom_block_def())
            else:
                script = self._parse_script()
                if script is not None:
                    scripts.append(script)
        return scripts

    # ------------------------------------------------------------------
    # Script parsing
    # ------------------------------------------------------------------

    def _parse_script(self) -> Optional[ScriptNode]:
        """Parse a hat block followed by its body."""
        line = self._current_line()

        # Collect tokens for the hat line
        line_start, line_end = self._collect_line_range()
        if line_start == line_end:
            return None

        # Try to match as hat block
        match = self.registry.match_line(
            self.tokens, line_start, line_end, context="hat"
        )

        if match is None:
            # Not a hat — try as a standalone statement (headless script)
            self.pos = line_start
            body = self._parse_body()
            if not body:
                # Unknown line — skip it
                self.pos = line_end
                self._skip_newlines()
                return None
            # Create a synthetic script with a "when flag clicked" hat
            hat = BlockNode(opcode="event_whenflagclicked", line=line)
            return ScriptNode(hat=hat, body=body, line=line)

        block_def, captures, consumed_pos = match
        self.pos = line_end  # Move past the hat line
        self._skip_newlines()

        hat = self._build_block_node(block_def, captures, line)

        # Parse the body
        body = self._parse_body()

        return ScriptNode(hat=hat, body=body, line=line)

    def _parse_body(self) -> list[StatementNode]:
        """Parse a sequence of statements until end/else/EOF/hat."""
        statements: list[StatementNode] = []

        while not self._at_eof():
            self._skip_newlines()
            if self._at_eof():
                break

            # Check for body-ending tokens
            if self._peek_type() in (TokenType.END, TokenType.ELSE):
                break

            # Check if this line starts a new script (hat block or define)
            if self._is_hat_line() or self._peek_type() == TokenType.DEFINE:
                break

            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)

        return statements

    def _parse_statement(self) -> Optional[StatementNode]:
        """Parse a single statement (block + optional substacks)."""
        line = self._current_line()
        line_start, line_end = self._collect_line_range()
        if line_start == line_end:
            return None

        match = self.registry.match_line(
            self.tokens, line_start, line_end, context="statement"
        )

        if match is None:
            # Try matching as a procedure call before giving up
            proc_result = self._try_match_procedure_call(line_start, line_end, line)
            if proc_result is not None:
                self.pos = line_end
                self._skip_newlines()
                return StatementNode(block=proc_result)

            raise UnknownBlockError(
                f"Unrecognized block: {self._tokens_to_text(line_start, line_end)}",
                line=line,
            )

        block_def, captures, consumed_pos = match
        self.pos = line_end
        self._skip_newlines()

        block_node = self._build_block_node(block_def, captures, line)
        substacks: list[list[StatementNode]] = []

        if block_def.shape == BlockShape.C_BLOCK:
            # Parse first substack
            substack1 = self._parse_body()
            substacks.append(substack1)

            # Check for else (upgrade control_if to control_if_else)
            if self._peek_type() == TokenType.ELSE:
                self._consume()  # eat 'else'
                self._skip_newlines()
                substack2 = self._parse_body()
                substacks.append(substack2)
                # Upgrade opcode
                if block_node.opcode == "control_if":
                    block_node.opcode = "control_if_else"

            # Expect 'end'
            if self._peek_type() == TokenType.END:
                self._consume()  # eat 'end'
                self._skip_newlines()
            else:
                raise UnclosedBlockError(
                    f"Missing 'end' for '{block_def.opcode}' block",
                    line=line,
                )

        return StatementNode(block=block_node, substacks=substacks)

    # ------------------------------------------------------------------
    # Custom block definitions
    # ------------------------------------------------------------------

    def _parse_custom_block_def(self) -> CustomBlockDef:
        """Parse a 'define' custom block definition."""
        line = self._current_line()
        self._consume()  # eat 'define'

        # Read the rest of the define line
        proccode_parts: list[str] = []
        arg_names: list[str] = []
        arg_types: list[str] = []  # "s" for string/number, "b" for boolean

        while not self._at_eof() and self._peek_type() != TokenType.NEWLINE:
            tok = self._peek()
            if tok.type == TokenType.WORD:
                proccode_parts.append(tok.value)
                self._consume()
            elif tok.type == TokenType.LPAREN:
                self._consume()  # eat (
                # Read parameter name
                if self._peek_type() == TokenType.STRING:
                    name = self._consume().value
                elif self._peek_type() == TokenType.WORD:
                    name = self._consume().value
                else:
                    name = f"arg{len(arg_names)}"
                # Expect )
                if self._peek_type() == TokenType.RPAREN:
                    self._consume()
                arg_names.append(name)
                arg_types.append("s")
                proccode_parts.append("%s")
            elif tok.type == TokenType.LANGLE:
                self._consume()  # eat <
                if self._peek_type() in (TokenType.STRING, TokenType.WORD):
                    name = self._consume().value
                else:
                    name = f"arg{len(arg_names)}"
                if self._peek_type() == TokenType.RANGLE:
                    self._consume()
                arg_names.append(name)
                arg_types.append("b")
                proccode_parts.append("%b")
            else:
                self._consume()  # skip unexpected tokens

        self._skip_newlines()

        proccode = " ".join(proccode_parts)

        # Parse body until 'end'
        body = self._parse_body()

        if self._peek_type() == TokenType.END:
            self._consume()
            self._skip_newlines()
        else:
            raise UnclosedBlockError("Missing 'end' for 'define' block", line=line)

        custom_def = CustomBlockDef(
            proccode=proccode,
            argument_names=arg_names,
            argument_types=arg_types,
            warp=False,
            body=body,
            line=line,
        )
        self._custom_blocks[proccode] = custom_def
        return custom_def

    # ------------------------------------------------------------------
    # Procedure call matching
    # ------------------------------------------------------------------

    def _try_match_procedure_call(
        self, line_start: int, line_end: int, line: int
    ) -> Optional[BlockNode]:
        """Try to match a line as a custom block call (procedures_call).

        Matches against all custom blocks defined so far in this compile unit.
        Returns a BlockNode with opcode='procedures_call' and mutation, or None.
        """
        if not self._custom_blocks:
            return None

        line_tokens = self.tokens[line_start:line_end]
        if not line_tokens:
            return None

        for proccode, custom_def in self._custom_blocks.items():
            result = self._try_match_proccode(
                proccode, custom_def, line_tokens, line
            )
            if result is not None:
                return result

        return None

    def _try_match_proccode(
        self,
        proccode: str,
        custom_def: CustomBlockDef,
        line_tokens: list[Token],
        line: int,
    ) -> Optional[BlockNode]:
        """Try to match line tokens against a specific proccode pattern.

        Proccode format: "word1 word2 %s word3 %b" — %s = string/number arg, %b = boolean arg.
        """
        parts = proccode.split()
        tp = 0  # token position
        arg_idx = 0
        arg_values: list[Any] = []

        for part in parts:
            if tp >= len(line_tokens):
                return None

            if part == "%s":
                # Expect a paren group (VALUE) or bracket [VALUE]
                tok = line_tokens[tp]
                if tok.type == TokenType.LPAREN:
                    tp += 1
                    inner_start = tp
                    depth = 1
                    while tp < len(line_tokens) and depth > 0:
                        if line_tokens[tp].type == TokenType.LPAREN:
                            depth += 1
                        elif line_tokens[tp].type == TokenType.RPAREN:
                            depth -= 1
                        if depth > 0:
                            tp += 1
                    if depth != 0:
                        return None
                    arg_values.append(line_tokens[inner_start:tp])
                    tp += 1  # skip RPAREN
                elif tok.type == TokenType.LBRACKET:
                    tp += 1
                    if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.STRING:
                        return None
                    str_value = line_tokens[tp].value
                    tp += 1
                    if tp >= len(line_tokens) or line_tokens[tp].type != TokenType.RBRACKET:
                        return None
                    tp += 1
                    arg_values.append(str_value)
                else:
                    return None
                arg_idx += 1

            elif part == "%b":
                # Expect an angle bracket group <CONDITION>
                tok = line_tokens[tp]
                if tok.type != TokenType.LANGLE:
                    return None
                tp += 1
                inner_start = tp
                depth = 1
                while tp < len(line_tokens) and depth > 0:
                    if line_tokens[tp].type == TokenType.LANGLE:
                        depth += 1
                    elif line_tokens[tp].type == TokenType.RANGLE:
                        depth -= 1
                    if depth > 0:
                        tp += 1
                if depth != 0:
                    return None
                arg_values.append(line_tokens[inner_start:tp])
                tp += 1  # skip RANGLE
                arg_idx += 1

            else:
                # Literal word match
                tok = line_tokens[tp]
                if tok.type != TokenType.WORD or tok.value.lower() != part.lower():
                    return None
                tp += 1

        # Must have consumed all tokens
        if tp != len(line_tokens):
            return None

        # Build the procedures_call BlockNode
        inputs: dict[str, InputNode] = {}
        arg_ids = []
        for i, (arg_name, arg_type) in enumerate(
            zip(custom_def.argument_names, custom_def.argument_types)
        ):
            arg_id = arg_name  # Use arg name as the input key
            arg_ids.append(arg_id)
            raw = arg_values[i]

            if arg_type == "b":
                # Boolean arg — parse as boolean
                if isinstance(raw, list) and all(isinstance(r, Token) for r in raw):
                    inputs[arg_id] = self._parse_boolean_from_tokens(raw)
                else:
                    inputs[arg_id] = LiteralInput(value="", input_type="string")
            else:
                # String/number arg
                if isinstance(raw, str):
                    inputs[arg_id] = LiteralInput(value=raw, input_type="string")
                elif isinstance(raw, list) and all(isinstance(r, Token) for r in raw):
                    from scrawl.compiler.registry import InputSpec
                    inputs[arg_id] = self._resolve_input(
                        raw, InputSpec(name=arg_id, type="string")
                    )
                else:
                    inputs[arg_id] = LiteralInput(value=str(raw), input_type="string")

        mutation = {
            "tagName": "mutation",
            "children": [],
            "proccode": proccode,
            "argumentids": json.dumps(arg_ids),
            "warp": "false",
        }

        return BlockNode(
            opcode="procedures_call",
            inputs=inputs,
            line=line,
            mutation=mutation,
        )

    # ------------------------------------------------------------------
    # Block node construction
    # ------------------------------------------------------------------

    def _build_block_node(
        self, block_def: Any, captures: dict[str, Any], line: int
    ) -> BlockNode:
        """Build a BlockNode from a matched pattern and its captures."""
        inputs: dict[str, InputNode] = {}
        fields: dict[str, FieldNode] = {}

        # Process input specs
        for input_spec in block_def.inputs:
            if input_spec.name in captures:
                raw = captures[input_spec.name]
                inputs[input_spec.name] = self._resolve_input(
                    raw, input_spec
                )

        # Process field specs
        for field_spec in block_def.fields:
            if field_spec.name in captures:
                raw = captures[field_spec.name]
                fields[field_spec.name] = FieldNode(value=raw)
            elif field_spec.default_value is not None:
                fields[field_spec.name] = FieldNode(value=field_spec.default_value)

        # Handle menu blocks — the menu field/input value comes from captures
        if block_def.menu:
            menu = block_def.menu
            if menu.field_name in captures:
                val = captures[menu.field_name]
                fields[menu.field_name] = FieldNode(value=val)

        return BlockNode(
            opcode=block_def.opcode, inputs=inputs, fields=fields, line=line
        )

    def _resolve_input(
        self, raw: Any, input_spec: InputSpec
    ) -> InputNode:
        """Resolve a captured input value into an InputNode."""
        # Boolean inputs — raw is a list of tokens inside < >
        if input_spec.type == "boolean":
            if isinstance(raw, list) and all(isinstance(r, Token) for r in raw):
                return self._parse_boolean_from_tokens(raw)
            return LiteralInput(value="", input_type="string")

        # Broadcast inputs
        if input_spec.type == "broadcast":
            if isinstance(raw, str):
                return BroadcastInput(name=raw)
            if isinstance(raw, list) and len(raw) == 1:
                return BroadcastInput(name=str(raw[0].value))
            return BroadcastInput(name=str(raw))

        # String/number inputs — raw is a list of tokens or a string
        if isinstance(raw, str):
            return LiteralInput(value=raw, input_type=input_spec.type)

        if isinstance(raw, list) and all(isinstance(r, Token) for r in raw):
            tokens_list: list[Token] = raw
            if len(tokens_list) == 0:
                default = input_spec.default or ""
                return LiteralInput(value=default, input_type=input_spec.type)

            if len(tokens_list) == 1:
                tok = tokens_list[0]
                if tok.type == TokenType.NUMBER:
                    return LiteralInput(value=str(tok.value), input_type=input_spec.type)
                if tok.type == TokenType.COLOR:
                    return LiteralInput(value=str(tok.value), input_type="color")
                if tok.type == TokenType.STRING:
                    # Try matching as reporter block (e.g., "x position", "volume", "timer")
                    reporter = self._try_string_as_reporter(tok.value, tok.line)
                    if reporter is not None:
                        return reporter
                    # Otherwise treat as variable reference — codegen will resolve
                    return VariableInput(name=tok.value)

            # Multiple tokens → try matching as a reporter expression
            return self._parse_reporter_from_tokens(tokens_list)

        # Fallback
        default = input_spec.default or ""
        return LiteralInput(value=default, input_type=input_spec.type)

    def _parse_reporter_from_tokens(self, tokens_list: list[Token]) -> InputNode:
        """Try to parse tokens as a reporter block expression."""
        match = self.registry.match_line(
            tokens_list, 0, len(tokens_list), context="reporter"
        )
        if match:
            block_def, captures, _ = match
            line = tokens_list[0].line if tokens_list else 0
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        # Also try boolean context
        match = self.registry.match_line(
            tokens_list, 0, len(tokens_list), context="boolean"
        )
        if match:
            block_def, captures, _ = match
            line = tokens_list[0].line if tokens_list else 0
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        # Fallback: treat as string
        text = " ".join(str(t.value) for t in tokens_list if t.value is not None)
        return LiteralInput(value=text, input_type="string")

    def _parse_boolean_from_tokens(self, tokens_list: list[Token]) -> InputNode:
        """Parse tokens from inside < > as a boolean expression."""
        match = self.registry.match_line(
            tokens_list, 0, len(tokens_list), context="boolean"
        )
        if match:
            block_def, captures, _ = match
            line = tokens_list[0].line if tokens_list else 0
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        # Also try reporter context (some reporters can be used as booleans)
        match = self.registry.match_line(
            tokens_list, 0, len(tokens_list), context="reporter"
        )
        if match:
            block_def, captures, _ = match
            line = tokens_list[0].line if tokens_list else 0
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        # Fallback: just return a literal
        text = " ".join(str(t.value) for t in tokens_list if t.value is not None)
        return LiteralInput(value=text, input_type="string")

    def _try_string_as_reporter(self, text: str, line: int) -> Optional[InputNode]:
        """Try to interpret a multi-word string as a reporter block.

        For example, "x position" should match the motion_xposition reporter.
        """
        from scrawl.compiler.lexer import Lexer

        # Re-tokenize the string as words
        mini_tokens: list[Token] = []
        for word in text.split():
            mini_tokens.append(Token(TokenType.WORD, word, line, 0))

        if not mini_tokens:
            return None

        match = self.registry.match_line(
            mini_tokens, 0, len(mini_tokens), context="reporter"
        )
        if match:
            block_def, captures, _ = match
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        # Also try boolean context
        match = self.registry.match_line(
            mini_tokens, 0, len(mini_tokens), context="boolean"
        )
        if match:
            block_def, captures, _ = match
            inner_block = self._build_block_node(block_def, captures, line)
            return ReporterInput(block=inner_block)

        return None

    # ------------------------------------------------------------------
    # Token navigation helpers
    # ------------------------------------------------------------------

    def _at_eof(self) -> bool:
        return self.pos >= len(self.tokens) or self.tokens[self.pos].type == TokenType.EOF

    def _peek(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, None, 0, 0)
        return self.tokens[self.pos]

    def _peek_type(self) -> TokenType:
        return self._peek().type

    def _consume(self) -> Token:
        tok = self._peek()
        self.pos += 1
        return tok

    def _current_line(self) -> int:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos].line
        return 0

    def _skip_newlines(self) -> None:
        while (
            self.pos < len(self.tokens)
            and self.tokens[self.pos].type == TokenType.NEWLINE
        ):
            self.pos += 1

    def _collect_line_range(self) -> tuple[int, int]:
        """Collect the index range [start, end) of the current line's tokens.

        Advances self.pos past the line (to the NEWLINE or EOF).
        """
        start = self.pos
        while (
            self.pos < len(self.tokens)
            and self.tokens[self.pos].type not in (TokenType.NEWLINE, TokenType.EOF)
        ):
            self.pos += 1
        return start, self.pos

    def _is_hat_line(self) -> bool:
        """Check if the current position starts a hat block (without consuming)."""
        saved_pos = self.pos
        line_start = self.pos
        # Find line end
        end = self.pos
        while (
            end < len(self.tokens)
            and self.tokens[end].type not in (TokenType.NEWLINE, TokenType.EOF)
        ):
            end += 1

        if line_start == end:
            return False

        match = self.registry.match_line(
            self.tokens, line_start, end, context="hat"
        )
        return match is not None

    def _tokens_to_text(self, start: int, end: int) -> str:
        """Convert a range of tokens back to approximate text for error messages."""
        parts = []
        for t in self.tokens[start:end]:
            if t.value is not None:
                parts.append(str(t.value))
            elif t.type == TokenType.LPAREN:
                parts.append("(")
            elif t.type == TokenType.RPAREN:
                parts.append(")")
            elif t.type == TokenType.LBRACKET:
                parts.append("[")
            elif t.type == TokenType.RBRACKET:
                parts.append("]")
            elif t.type == TokenType.LANGLE:
                parts.append("<")
            elif t.type == TokenType.RANGLE:
                parts.append(">")
        return " ".join(parts)
