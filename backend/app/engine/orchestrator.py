from __future__ import annotations

import logging
import time
from typing import Callable, Awaitable
from uuid import uuid4

from app.config import settings
from app.models.session import Session, ConversationPhase
from app.models.messages import (
    WSFrame,
    WSMessageType,
    ChatMessage,
    MessageRole,
    TextContent,
)
from app.services.session_manager import session_manager
from app.services.llm_client import llm_client
from app.utils.json_parser import split_text_and_json
from app.engine.prompts.context_builder import build_prompt
from app.engine.understanding import parse_understanding_response, merge_requirements
from app.engine.clarifier import should_proceed_to_design, build_options_frame, get_next_gap
from app.engine.architect import parse_architecture_response

log = logging.getLogger("mcp.orchestrator")

SendCallback = Callable[[WSFrame], Awaitable[None]]

PHASE_MESSAGES = {
    ConversationPhase.UNDERSTANDING: "Analyzing your requirements...",
    ConversationPhase.CLARIFYING: "Processing your answer...",
    ConversationPhase.DESIGNING: "Designing your MCP server architecture...",
}


class Orchestrator:
    async def process(
        self,
        session: Session,
        user_text: str,
        send_callback: SendCallback,
    ) -> None:
        """Main processing pipeline: route user input through the conversation state machine."""

        log.info("=" * 60)
        log.info("STEP 1: Received user input (session=%s)", session.id)
        log.info("  Phase: %s", session.phase.value)
        log.info("  User text: %.120s%s", user_text, "..." if len(user_text) > 120 else "")

        # Phase transition on first message
        if session.phase == ConversationPhase.INITIAL:
            log.info("STEP 2: First message — transitioning INITIAL -> UNDERSTANDING")
            session_manager.set_phase(session.id, ConversationPhase.UNDERSTANDING)

        # Send progress update
        phase_msg = PHASE_MESSAGES.get(session.phase, "Processing...")
        log.info("STEP 2: Sending phase update to frontend: phase=%s", session.phase.value)
        await send_callback(
            WSFrame(
                type=WSMessageType.SYSTEM_MESSAGE,
                session_id=session.id,
                payload={"phase": session.phase.value, "message": phase_msg},
            )
        )

        # Build prompt and call LLM with streaming
        t_prompt_start = time.monotonic()
        messages = build_prompt(session)
        t_prompt_end = time.monotonic()
        log.info("STEP 3: Built prompt — %d messages for LLM (%.1fms)",
                 len(messages), (t_prompt_end - t_prompt_start) * 1000)
        for i, m in enumerate(messages):
            log.info("  msg[%d] role=%s len=%d", i, m["role"], len(m["content"]))

        full_response = ""
        msg_id = str(uuid4())
        chunk_count = 0
        separator = "---JSON---"
        sep_len = len(separator)  # 11
        send_buffer = ""  # Buffer to prevent separator leaking through
        found_separator = False
        t_first_chunk = None
        t_separator_found = None

        # Use higher max_tokens for design phase (architecture JSON is large)
        max_tokens = 8192 if session.phase == ConversationPhase.DESIGNING else 4096
        log.info("STEP 4: Calling LLM (streaming, max_tokens=%d)...", max_tokens)
        t_llm_start = time.monotonic()
        try:
            async for chunk in llm_client.stream_chat(messages, max_tokens=max_tokens):
                full_response += chunk
                chunk_count += 1

                if chunk_count == 1:
                    t_first_chunk = time.monotonic()
                    log.info("STEP 4: First chunk received (%.0fms after LLM call)",
                             (t_first_chunk - t_llm_start) * 1000)

                if found_separator:
                    continue

                send_buffer += chunk

                # Check if separator is fully present
                if separator in send_buffer:
                    found_separator = True
                    t_separator_found = time.monotonic()
                    log.info("STEP 4: ---JSON--- found at chunk %d (%.1fs into stream)",
                             chunk_count, t_separator_found - t_llm_start)
                    # Send only text before the separator
                    before_sep = send_buffer.split(separator, 1)[0]
                    if before_sep:
                        await send_callback(
                            WSFrame(
                                type=WSMessageType.ASSISTANT_CHUNK,
                                session_id=session.id,
                                payload={"chunk": before_sep, "message_id": msg_id},
                            )
                        )
                    send_buffer = ""
                    # Let the user know we're processing (they can't see JSON generation)
                    await send_callback(
                        WSFrame(
                            type=WSMessageType.SYSTEM_MESSAGE,
                            session_id=session.id,
                            payload={"phase": session.phase.value, "message": "Processing..."},
                        )
                    )
                    continue

                # Check if buffer might end with a partial separator (e.g. "---J")
                # Keep last sep_len-1 chars as buffer, send the rest safely
                safe_end = len(send_buffer) - (sep_len - 1)
                if safe_end > 0:
                    safe_text = send_buffer[:safe_end]
                    send_buffer = send_buffer[safe_end:]
                    await send_callback(
                        WSFrame(
                            type=WSMessageType.ASSISTANT_CHUNK,
                            session_id=session.id,
                            payload={"chunk": safe_text, "message_id": msg_id},
                        )
                    )

            # Flush any remaining buffer that wasn't part of the separator
            if send_buffer and not found_separator:
                await send_callback(
                    WSFrame(
                        type=WSMessageType.ASSISTANT_CHUNK,
                        session_id=session.id,
                        payload={"chunk": send_buffer, "message_id": msg_id},
                    )
                )
        except Exception as e:
            log.error("STEP 4 FAILED: LLM error: %s", e)
            await send_callback(
                WSFrame(
                    type=WSMessageType.ERROR,
                    session_id=session.id,
                    payload={
                        "code": "llm_error",
                        "message": f"LLM error: {e}",
                    },
                )
            )
            return

        t_llm_end = time.monotonic()
        log.info("STEP 4: LLM done — %d chunks, %d chars total (%.1fs total, %.1fs text, %.1fs json)",
                 chunk_count, len(full_response),
                 t_llm_end - t_llm_start,
                 (t_separator_found or t_llm_end) - t_llm_start,
                 t_llm_end - (t_separator_found or t_llm_end))

        # Split response into display text and structured JSON
        t_parse_start = time.monotonic()
        display_text, parsed_json = split_text_and_json(full_response)
        t_parse_end = time.monotonic()
        log.info("STEP 5: Parsed response — display_text=%d chars, json=%s (%.1fms)",
                 len(display_text), "YES" if parsed_json else "NO",
                 (t_parse_end - t_parse_start) * 1000)
        if parsed_json:
            log.info("  JSON keys: %s", list(parsed_json.keys()))

        # Send the completed assistant message
        await send_callback(
            WSFrame(
                type=WSMessageType.ASSISTANT_COMPLETE,
                session_id=session.id,
                payload={
                    "message_id": msg_id,
                    "full_text": display_text,
                    "phase": session.phase.value,
                },
            )
        )

        # Store assistant message
        assistant_msg = ChatMessage(
            id=msg_id,
            role=MessageRole.ASSISTANT,
            content=[TextContent(text=display_text)],
        )
        session_manager.add_message(session.id, assistant_msg)

        # If no JSON was parsed, try a fallback JSON-only call
        if parsed_json is None:
            log.info("STEP 5b: No JSON found — trying fallback JSON-only call...")
            try:
                fallback_messages = messages + [
                    {"role": "assistant", "content": full_response},
                    {
                        "role": "user",
                        "content": "Now provide the structured JSON output matching the schema described in the system prompt. Output ONLY valid JSON, nothing else.",
                    },
                ]
                fallback_raw = await llm_client.chat_json(fallback_messages)
                from app.utils.json_parser import extract_json
                parsed_json = extract_json(fallback_raw)
                log.info("STEP 5b: Fallback succeeded — keys: %s",
                         list(parsed_json.keys()) if parsed_json else "NONE")
            except Exception as e:
                log.error("STEP 5b FAILED: Fallback parse error: %s", e)
                await send_callback(
                    WSFrame(
                        type=WSMessageType.ERROR,
                        session_id=session.id,
                        payload={
                            "code": "parse_error",
                            "message": "Could not extract structured data from AI response. Please try rephrasing.",
                        },
                    )
                )
                return

        # Route based on phase
        log.info("STEP 6: Routing to phase handler: %s", session.phase.value)
        t_route_start = time.monotonic()
        if session.phase == ConversationPhase.UNDERSTANDING:
            await self._handle_understanding(session, parsed_json, send_callback)
        elif session.phase == ConversationPhase.CLARIFYING:
            await self._handle_clarification(session, parsed_json, send_callback)
        elif session.phase == ConversationPhase.DESIGNING:
            await self._handle_design(session, parsed_json, send_callback)
        t_route_end = time.monotonic()
        log.info("STEP 6: Phase handler done (%.1fs)", t_route_end - t_route_start)
        log.info("TOTAL: process() took %.1fs", t_route_end - t_prompt_start)

    async def _handle_understanding(
        self,
        session: Session,
        data: dict,
        send_callback: SendCallback,
    ) -> None:
        """Process understanding phase output.

        Always goes to CLARIFYING first — minimum rounds are enforced before design.
        """
        log.info("STEP 7 [UNDERSTANDING]: Parsing requirements from LLM output...")
        requirements = parse_understanding_response(data)
        session_manager.update_requirements(session.id, requirements)

        log.info("STEP 7: completeness=%.2f, tools=%d, gaps=%d — moving to CLARIFYING",
                 requirements.completeness_score,
                 len(requirements.tools_requested), len(requirements.gaps))

        # Always go to clarification first — min rounds ensure the user gets to weigh in
        session_manager.set_phase(session.id, ConversationPhase.CLARIFYING)
        gap = get_next_gap(requirements)
        if gap and gap.options:
            log.info("STEP 7: Next gap: category=%s priority=%s question=%.80s",
                     gap.category, gap.priority, gap.question)
            log.info("STEP 7: Sending options: %s", gap.options)
            await send_callback(build_options_frame(session.id, gap))
        else:
            # LLM didn't produce gaps — move to design (unusual for first pass)
            log.info("STEP 7: No gaps found — proceeding to DESIGNING")
            session_manager.set_phase(session.id, ConversationPhase.DESIGNING)
            await self._trigger_design(session, send_callback)

    async def _handle_clarification(
        self,
        session: Session,
        data: dict,
        send_callback: SendCallback,
    ) -> None:
        """Process clarification phase output.

        Fully dynamic, gap-driven decision logic:
        - If LLM produced gaps → show the next one (keep asking)
        - If LLM says ready AND no gaps → move to design
        - Force design after max rounds (safety net only)
        - The LLM decides what to ask and when it has enough info.
        """
        log.info("STEP 7 [CLARIFICATION]: Merging new data into requirements...")
        updated = merge_requirements(session.requirements, data)
        session_manager.update_requirements(session.id, updated)
        rounds = session_manager.increment_clarification(session.id)

        ready = data.get("ready_to_design", False)
        force = rounds >= settings.max_clarification_rounds
        has_gaps = len(updated.gaps) > 0

        # If LLM says ready but still has unresolved gaps, trust the gaps over the flag
        if ready and has_gaps:
            log.warning("STEP 7: ready_to_design=true but %d unresolved gaps remain — trusting gaps", len(updated.gaps))
            ready = False

        log.info("STEP 7: Round %d/%d — ready=%s, force=%s, gaps=%d, completeness=%.2f",
                 rounds, settings.max_clarification_rounds,
                 ready, force, len(updated.gaps), updated.completeness_score)

        # Try to get the next actionable gap
        gap = get_next_gap(updated)

        if gap and gap.options:
            # LLM still has questions — show them regardless of ready flag
            log.info("STEP 7: Showing gap: category=%s question=%.80s", gap.category, gap.question)
            await send_callback(build_options_frame(session.id, gap))
        elif ready or force:
            # No more gaps and LLM says ready (or forced after max rounds)
            log.info("STEP 7: -> DESIGNING (ready=%s, force=%s)", ready, force)
            session_manager.set_phase(session.id, ConversationPhase.DESIGNING)
            await self._trigger_design(session, send_callback)
        else:
            # No structured gap options — but AI may have asked in text.
            # Stay in clarifying so user can type a free-text answer.
            log.info("STEP 7: No structured gaps — waiting for user free-text input")

    async def _handle_design(
        self,
        session: Session,
        data: dict,
        send_callback: SendCallback,
    ) -> None:
        """Process architecture design output."""
        log.info("STEP 8 [DESIGN]: Parsing architecture from LLM output...")
        architecture = parse_architecture_response(data)
        session_manager.set_architecture(session.id, architecture)

        log.info("STEP 8: Architecture ready — server=%s, lang=%s, tools=%d, resources=%d",
                 architecture.server_name, architecture.language,
                 len(architecture.tools), len(architecture.resources))
        for t in architecture.tools:
            log.info("  Tool: %s — %s", t.name, t.description[:60])

        await send_callback(
            WSFrame(
                type=WSMessageType.ARCHITECTURE_READY,
                session_id=session.id,
                payload={
                    "architecture": architecture.model_dump(mode="json"),
                    "summary_text": (
                        f"Designed a {architecture.language} MCP server "
                        f"'{architecture.server_name}' with {len(architecture.tools)} tools."
                    ),
                },
            )
        )
        log.info("STEP 8: DONE — architecture sent to frontend")

    async def _trigger_design(
        self,
        session: Session,
        send_callback: SendCallback,
    ) -> None:
        """Trigger the design phase as a new LLM call."""
        t_design_start = time.monotonic()
        log.info("STEP 8: Triggering design phase LLM call...")
        await send_callback(
            WSFrame(
                type=WSMessageType.SYSTEM_MESSAGE,
                session_id=session.id,
                payload={
                    "phase": "designing",
                    "message": "Requirements complete! Designing your MCP server architecture...",
                },
            )
        )

        messages = build_prompt(session)
        log.info("STEP 8: Design prompt — %d messages (built in %.1fms)",
                 len(messages), (time.monotonic() - t_design_start) * 1000)
        full_response = ""
        msg_id = str(uuid4())
        chunk_count = 0
        separator = "---JSON---"
        sep_len = len(separator)
        send_buffer = ""
        found_separator = False

        t_design_llm_start = time.monotonic()
        try:
            async for chunk in llm_client.stream_chat(messages, max_tokens=8192):
                full_response += chunk
                chunk_count += 1

                if chunk_count == 1:
                    log.info("STEP 8: First design chunk (%.0fms after LLM call)",
                             (time.monotonic() - t_design_llm_start) * 1000)

                if found_separator:
                    continue

                send_buffer += chunk

                if separator in send_buffer:
                    found_separator = True
                    log.info("STEP 8: Design ---JSON--- found at chunk %d (%.1fs into stream)",
                             chunk_count, time.monotonic() - t_design_llm_start)
                    before_sep = send_buffer.split(separator, 1)[0]
                    if before_sep:
                        await send_callback(
                            WSFrame(
                                type=WSMessageType.ASSISTANT_CHUNK,
                                session_id=session.id,
                                payload={"chunk": before_sep, "message_id": msg_id},
                            )
                        )
                    send_buffer = ""
                    await send_callback(
                        WSFrame(
                            type=WSMessageType.SYSTEM_MESSAGE,
                            session_id=session.id,
                            payload={"phase": "designing", "message": "Finalizing architecture..."},
                        )
                    )
                    continue

                safe_end = len(send_buffer) - (sep_len - 1)
                if safe_end > 0:
                    safe_text = send_buffer[:safe_end]
                    send_buffer = send_buffer[safe_end:]
                    await send_callback(
                        WSFrame(
                            type=WSMessageType.ASSISTANT_CHUNK,
                            session_id=session.id,
                            payload={"chunk": safe_text, "message_id": msg_id},
                        )
                    )

            if send_buffer and not found_separator:
                await send_callback(
                    WSFrame(
                        type=WSMessageType.ASSISTANT_CHUNK,
                        session_id=session.id,
                        payload={"chunk": send_buffer, "message_id": msg_id},
                    )
                )
        except Exception as e:
            log.error("STEP 8 FAILED: Design LLM error: %s", e)
            await send_callback(
                WSFrame(
                    type=WSMessageType.ERROR,
                    session_id=session.id,
                    payload={
                        "code": "llm_error",
                        "message": f"Design failed: {e}",
                    },
                )
            )
            return

        t_design_llm_end = time.monotonic()
        log.info("STEP 8: Design LLM done — %d chunks, %d chars (%.1fs total)",
                 chunk_count, len(full_response), t_design_llm_end - t_design_llm_start)
        display_text, parsed_json = split_text_and_json(full_response)
        log.info("STEP 8: Design parsed — json=%s", "YES" if parsed_json else "NO")

        await send_callback(
            WSFrame(
                type=WSMessageType.ASSISTANT_COMPLETE,
                session_id=session.id,
                payload={
                    "message_id": msg_id,
                    "full_text": display_text,
                    "phase": "designing",
                },
            )
        )

        assistant_msg = ChatMessage(
            id=msg_id,
            role=MessageRole.ASSISTANT,
            content=[TextContent(text=display_text)],
        )
        session_manager.add_message(session.id, assistant_msg)

        if parsed_json:
            await self._handle_design(session, parsed_json, send_callback)
        else:
            log.info("STEP 8b: No JSON in design — trying fallback...")
            try:
                fallback_messages = messages + [
                    {"role": "assistant", "content": full_response},
                    {
                        "role": "user",
                        "content": "Now provide ONLY the JSON architecture output matching the schema. No text, just JSON.",
                    },
                ]
                from app.utils.json_parser import extract_json
                fallback_raw = await llm_client.chat_json(fallback_messages)
                parsed_json = extract_json(fallback_raw)
                log.info("STEP 8b: Design fallback succeeded")
                await self._handle_design(session, parsed_json, send_callback)
            except Exception as e:
                log.error("STEP 8b FAILED: Design fallback error: %s", e)
                await send_callback(
                    WSFrame(
                        type=WSMessageType.ERROR,
                        session_id=session.id,
                        payload={
                            "code": "parse_error",
                            "message": "Could not generate architecture. Please try again.",
                        },
                    )
                )

        log.info("STEP 8: _trigger_design() total: %.1fs", time.monotonic() - t_design_start)


orchestrator = Orchestrator()
