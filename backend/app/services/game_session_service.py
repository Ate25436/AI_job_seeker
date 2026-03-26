from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


class GameSessionService:
    def __init__(self, interview_duration_minutes: int = 10):
        self.interview_duration = timedelta(minutes=interview_duration_minutes)
        self._sessions: dict[str, dict[str, Any]] = {}

    def start_session(self, scenario: dict[str, Any]) -> dict[str, Any]:
        session_id = uuid4().hex
        started_at = datetime.now(UTC)
        expires_at = started_at + self.interview_duration

        session = {
            "session_id": session_id,
            "status": "active",
            "started_at": started_at,
            "expires_at": expires_at,
            "ended_at": None,
            "scenario": scenario,
            "history": [],
            "submitted_scores": None,
            "score_submitted_at": None,
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session["status"] == "active" and datetime.now(UTC) >= session["expires_at"]:
            self.end_session(session_id, reason="timeout")
        return self._sessions.get(session_id)

    def append_turn(self, session_id: str, question: str, answer: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        self._ensure_active(session)

        now = datetime.now(UTC)
        session["history"].append({"role": "user", "content": question, "timestamp": now.isoformat()})
        session["history"].append({"role": "assistant", "content": answer, "timestamp": now.isoformat()})
        return session

    def end_session(self, session_id: str, reason: str = "manual") -> dict[str, Any]:
        session = self.require_session(session_id)
        if session["status"] != "ended":
            session["status"] = "ended"
            session["ended_at"] = datetime.now(UTC)
            session["end_reason"] = reason
        return session

    def submit_scores(self, session_id: str, scores: dict[str, int]) -> dict[str, Any]:
        session = self.require_session(session_id)
        if session["status"] == "active" and datetime.now(UTC) >= session["expires_at"]:
            self.end_session(session_id, reason="timeout")
        if session["status"] != "ended":
            raise ValueError("Interview session must be ended before scoring.")

        session["submitted_scores"] = scores
        session["score_submitted_at"] = datetime.now(UTC)
        return session

    def build_result(self, session_id: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        scenario = session["scenario"]
        correct_scores = {
            competency_id: competency["score"]
            for competency_id, competency in scenario["evaluation_profile"]["competencies"].items()
        }
        submitted_scores = session["submitted_scores"]
        score_diffs = None
        if submitted_scores:
            score_diffs = {
                competency_id: submitted_scores[competency_id] - correct_scores[competency_id]
                for competency_id in correct_scores
            }

        return {
            "session_id": session["session_id"],
            "status": session["status"],
            "started_at": session["started_at"],
            "expires_at": session["expires_at"],
            "ended_at": session["ended_at"],
            "end_reason": session.get("end_reason"),
            "candidate_name": scenario["candidate_profile"]["full_name"],
            "company_name": scenario["company_profile"]["company_name"],
            "scenario_title": scenario["scenario_meta"]["title"],
            "answer_count": len(session["history"]) // 2,
            "remaining_seconds": self._remaining_seconds(session),
            "score_submitted": submitted_scores is not None,
            "submitted_scores": submitted_scores,
            "correct_scores": correct_scores if submitted_scores is not None else None,
            "score_diffs": score_diffs,
            "category_balance": scenario["evaluation_profile"]["category_balance"] if submitted_scores is not None else None,
        }

    def require_session(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session not found: {session_id}")
        return session

    def build_history_payload(self, session_id: str) -> list[dict[str, str]]:
        session = self.require_session(session_id)
        return [{"role": item["role"], "content": item["content"]} for item in session["history"]]

    def _ensure_active(self, session: dict[str, Any]) -> None:
        if session["status"] != "active":
            raise ValueError("Interview session has already ended.")
        if datetime.now(UTC) >= session["expires_at"]:
            self.end_session(session["session_id"], reason="timeout")
            raise ValueError("Interview session has already ended.")

    @staticmethod
    def _remaining_seconds(session: dict[str, Any]) -> int:
        if session["status"] != "active":
            return 0
        return max(0, int((session["expires_at"] - datetime.now(UTC)).total_seconds()))
