from __future__ import annotations

import pytest
from datetime import UTC, datetime

import app.main as main_module
from app.main import app
from app.services.game_session_service import GameSessionService
from app.services.scenario_service import COMPETENCY_DEFINITIONS
from fastapi.testclient import TestClient


class DummyRAGService:
    async def generate_answer(self, question, history=None, scenario_id=None):
        return {
            "answer": f"dummy answer for: {question}",
            "sources": ["frontiersoft_taro/02_student_life.md - ガクチカ"],
            "timestamp": datetime.now(UTC).isoformat(),
            "processing_time_ms": 10,
        }


def build_uniform_scores(value: int) -> dict[str, int]:
    return {competency_id: value for competency_id in COMPETENCY_DEFINITIONS}


class TestTask9FeedbackSpecification:
    def setup_method(self):
        self.client = TestClient(app)
        main_module.game_session_service = GameSessionService()
        main_module.rag_service = DummyRAGService()

    def _play_and_score_session(self, questions: list[str], score_value: int = 3) -> dict:
        start_response = self.client.post("/api/game/start", json={})
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        for question in questions:
            ask_response = self.client.post(
                "/api/game/ask",
                json={"session_id": session_id, "question": question},
            )
            assert ask_response.status_code == 200

        end_response = self.client.post("/api/game/end", json={"session_id": session_id})
        assert end_response.status_code == 200

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": build_uniform_scores(score_value)},
        )
        assert score_response.status_code == 200

        result_response = self.client.get(f"/api/game/result/{session_id}")
        assert result_response.status_code == 200
        return result_response.json()

    def test_result_includes_feedback_summary_after_score_submission(self):
        result = self._play_and_score_session(
            ["学生時代に力を入れたことは何ですか？", "そのとき工夫したことを教えてください。"]
        )

        assert "feedback_summary" in result
        assert result["feedback_summary"]
        assert result["feedback_mode"] in {"rule_based", "llm"}

    def test_feedback_identifies_correctly_and_incorrectly_inferred_competencies(self):
        result = self._play_and_score_session(
            ["自己PRを教えてください。", "困難な場面でどう対応しましたか？"]
        )

        assert "detected_competencies" in result
        assert "missed_competencies" in result
        assert isinstance(result["detected_competencies"], list)
        assert isinstance(result["missed_competencies"], list)
        assert result["detected_competencies"] or result["missed_competencies"]

    def test_feedback_surfaces_missing_question_angles_per_competency(self):
        result = self._play_and_score_session(
            ["チームで何を頑張りましたか？"]
        )

        assert "question_angle_gaps" in result
        assert isinstance(result["question_angle_gaps"], dict)
        assert result["question_angle_gaps"]
        for competency_id, gaps in result["question_angle_gaps"].items():
            assert competency_id in COMPETENCY_DEFINITIONS
            assert isinstance(gaps, list)
            assert gaps

    def test_feedback_uses_conversation_logs_to_flag_shallow_follow_up(self):
        result = self._play_and_score_session(
            [
                "学生時代に力を入れたことは何ですか？",
                "チーム経験について教えてください。",
            ]
        )

        assert "shallow_follow_up_flags" in result
        assert isinstance(result["shallow_follow_up_flags"], list)
        assert result["shallow_follow_up_flags"]

    def test_feedback_defaults_to_rule_based_mode_in_initial_implementation(self):
        result = self._play_and_score_session(
            ["志望動機を教えてください。", "その理由をもう少し詳しく教えてください。"]
        )

        assert result["feedback_mode"] == "rule_based"

    def test_feedback_contract_allows_future_llm_generated_feedback(self):
        result = self._play_and_score_session(
            ["最近学んだ技術について教えてください。", "その技術選定の理由は何ですか？"]
        )

        assert result["feedback_mode"] in {"rule_based", "llm"}
        assert "feedback_summary" in result
        assert "detected_competencies" in result
        assert "missed_competencies" in result
