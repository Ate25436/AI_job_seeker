from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from .feedback_service import FeedbackService


class GameSessionService:
    DISPLAY_SCORE_MEAN = 50.0
    DISPLAY_SCORE_SPREAD = 20.0
    DISPLAY_SCORE_MIN = 0.0
    DISPLAY_SCORE_MAX = 100.0

    def __init__(self, interview_duration_minutes: int = 10):
        self.interview_duration = timedelta(minutes=interview_duration_minutes)
        self._sessions: dict[str, dict[str, Any]] = {}
        self.feedback_service = FeedbackService()

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
            "score_result": None,
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

        correct_scores = self._extract_correct_scores(session["scenario"])
        session["submitted_scores"] = scores
        session["score_submitted_at"] = datetime.now(UTC)
        session["score_result"] = self._build_score_result(scores, correct_scores)
        return session

    def build_result(self, session_id: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        scenario = session["scenario"]
        correct_scores = self._extract_correct_scores(scenario)
        submitted_scores = session["submitted_scores"]
        score_result = session["score_result"]
        if submitted_scores is not None and score_result is None:
            score_result = self._build_score_result(submitted_scores, correct_scores)
        feedback = None
        if submitted_scores is not None and score_result is not None:
            feedback = self.feedback_service.build_feedback(
                scenario=scenario,
                history=session["history"],
                submitted_scores=submitted_scores,
                correct_scores=correct_scores,
                score_diffs=score_result["score_diffs"],
            )

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
            "score_diffs": score_result["score_diffs"] if score_result is not None else None,
            "total_absolute_diff": score_result["total_absolute_diff"] if score_result is not None else None,
            "base_score": score_result["base_score"] if score_result is not None else None,
            "display_score": score_result["display_score"] if score_result is not None else None,
            "feedback_mode": feedback["feedback_mode"] if feedback is not None else None,
            "feedback_summary": feedback["feedback_summary"] if feedback is not None else None,
            "detected_competencies": feedback["detected_competencies"] if feedback is not None else None,
            "missed_competencies": feedback["missed_competencies"] if feedback is not None else None,
            "question_angle_gaps": feedback["question_angle_gaps"] if feedback is not None else None,
            "shallow_follow_up_flags": feedback["shallow_follow_up_flags"] if feedback is not None else None,
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

    @staticmethod
    def _extract_correct_scores(scenario: dict[str, Any]) -> dict[str, int]:
        return {
            competency_id: competency["score"]
            for competency_id, competency in scenario["evaluation_profile"]["competencies"].items()
        }

    def _build_score_result(
        self,
        submitted_scores: dict[str, int],
        correct_scores: dict[str, int],
    ) -> dict[str, Any]:
        score_diffs = {
            competency_id: submitted_scores[competency_id] - correct_scores[competency_id]
            for competency_id in correct_scores
        }
        total_absolute_diff = sum(abs(diff) for diff in score_diffs.values())
        base_score = float(-total_absolute_diff)

        display_score = self._normalize_display_score(correct_scores, base_score)
        return {
            "score_diffs": score_diffs,
            "total_absolute_diff": total_absolute_diff,
            "base_score": round(base_score, 2),
            "display_score": round(display_score, 2),
        }

    def _normalize_display_score(
        self,
        correct_scores: dict[str, int],
        base_score: float,
    ) -> float:
        neutral_base, best_base, worst_base = self._display_score_reference_points(correct_scores)
        upper_range = best_base - neutral_base
        lower_range = neutral_base - worst_base

        if base_score >= neutral_base and upper_range > 0:
            scaled_distance = (base_score - neutral_base) / upper_range
            display_score = self.DISPLAY_SCORE_MEAN + (scaled_distance * self.DISPLAY_SCORE_SPREAD)
        elif base_score < neutral_base and lower_range > 0:
            scaled_distance = (neutral_base - base_score) / lower_range
            display_score = self.DISPLAY_SCORE_MEAN - (scaled_distance * self.DISPLAY_SCORE_SPREAD)
        else:
            return self.DISPLAY_SCORE_MEAN

        return min(self.DISPLAY_SCORE_MAX, max(self.DISPLAY_SCORE_MIN, display_score))

    @staticmethod
    def _display_score_reference_points(correct_scores: dict[str, int]) -> tuple[float, float, float]:
        neutral_absolute_diff = sum(abs(3 - correct_score) for correct_score in correct_scores.values())
        worst_absolute_diff = sum(max(correct_score - 1, 5 - correct_score) for correct_score in correct_scores.values())
        neutral_base = float(-neutral_absolute_diff)
        best_base = 0.0
        worst_base = float(-worst_absolute_diff)
        return neutral_base, best_base, worst_base
