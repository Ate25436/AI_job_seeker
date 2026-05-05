from datetime import datetime, UTC

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.game_session_service import GameSessionService
from app.services.scenario_service import COMPETENCY_DEFINITIONS


class DummyRAGService:
    def __init__(self):
        self.calls = []

    async def generate_answer(self, question, history=None, scenario_id=None):
        self.calls.append(
            {"question": question, "history": history, "scenario_id": scenario_id}
        )
        return {
            "answer": f"dummy answer for: {question}",
            "sources": ["frontiersoft_taro/02_student_life.md - ガクチカ"],
            "timestamp": datetime.now(UTC).isoformat(),
            "processing_time_ms": 12,
        }


class TestGameApi:
    def setup_method(self):
        self.client = TestClient(app)
        main_module.game_session_service = GameSessionService()
        main_module.rag_service = DummyRAGService()
        self.rag_service = main_module.rag_service

    def test_get_game_briefing(self):
        response = self.client.get("/api/game/briefing")
        assert response.status_code == 200

        data = response.json()
        assert data["candidate_profile"]["full_name"] == "就活 太郎"
        assert data["company_profile"]["company_name"] == "フロンティアソフト株式会社"
        entry_sheet_sections = data["candidate_profile"]["entry_sheet_sections"]
        assert len(entry_sheet_sections) == 3
        assert [section["title"] for section in entry_sheet_sections] == [
            "志望動機を教えてください。",
            "学生時代に力を入れたことを教えてください。",
            "チームワークを発揮した経験を教えてください。",
        ]
        assert "志望する理由" in entry_sheet_sections[0]["summary"]
        assert "もともと" in entry_sheet_sections[0]["summary"]
        assert "入社後は" in entry_sheet_sections[0]["summary"]
        assert "学園祭の出店企画" in entry_sheet_sections[1]["summary"]
        assert "企画案と担当表" in entry_sheet_sections[1]["summary"]
        assert "業務でも" in entry_sheet_sections[1]["summary"]
        assert "進捗共有と役割調整" in entry_sheet_sections[2]["summary"]
        assert "個別に声をかけていました" in entry_sheet_sections[2]["summary"]
        assert "業務でも" in entry_sheet_sections[2]["summary"]
        for section in entry_sheet_sections:
            assert "1." not in section["summary"]
            assert 180 <= len(section["summary"]) <= 420
        assert len(data["evaluation_criteria"]) == len(COMPETENCY_DEFINITIONS)

    def test_start_game_session(self):
        response = self.client.post("/api/game/start", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["candidate_name"] == "就活 太郎"
        assert data["company_name"] == "フロンティアソフト株式会社"
        assert "correct_scores" not in data
        assert "category_balance" not in data
        assert "submitted_scores" not in data

    def test_start_generated_game_session(self):
        response = self.client.post(
            "/api/game/start",
            json={"scenario_mode": "generated", "seed": 12},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["scenario_title"].endswith("生成版")

    def test_game_question_flow(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]

        ask_response = self.client.post(
            "/api/game/ask",
            json={"session_id": session_id, "question": "学生時代に力を入れたことは何ですか？"},
        )

        assert ask_response.status_code == 200
        data = ask_response.json()
        assert data["session_id"] == session_id
        assert "dummy answer" in data["answer"]
        assert data["status"] == "active"
        assert "correct_scores" not in data
        assert "category_balance" not in data

    def test_game_question_flow_accumulates_history_and_scenario_id(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]

        first_response = self.client.post(
            "/api/game/ask",
            json={"session_id": session_id, "question": "学生時代に力を入れたことは何ですか？"},
        )
        assert first_response.status_code == 200

        second_response = self.client.post(
            "/api/game/ask",
            json={"session_id": session_id, "question": "そのときの課題は何でしたか？"},
        )

        assert second_response.status_code == 200
        assert self.rag_service.calls[0]["history"] == []
        assert self.rag_service.calls[0]["scenario_id"] == "frontiersoft_taro_v1"
        assert self.rag_service.calls[1]["history"] == [
            {"role": "user", "content": "学生時代に力を入れたことは何ですか？"},
            {"role": "assistant", "content": "dummy answer for: 学生時代に力を入れたことは何ですか？"},
        ]
        assert self.rag_service.calls[1]["scenario_id"] == "frontiersoft_taro_v1"

    def test_end_score_and_result_flow(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]

        end_response = self.client.post("/api/game/end", json={"session_id": session_id})
        assert end_response.status_code == 200
        assert end_response.json()["status"] == "ended"

        scores = {competency_id: 3 for competency_id in COMPETENCY_DEFINITIONS}
        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": scores},
        )
        assert score_response.status_code == 200

        result_response = self.client.get(f"/api/game/result/{session_id}")
        assert result_response.status_code == 200
        data = result_response.json()
        assert data["score_submitted"] is True
        assert data["submitted_scores"] == scores
        assert set(data["correct_scores"].keys()) == set(COMPETENCY_DEFINITIONS.keys())
        assert set(data.keys()) >= {
            "session_id",
            "status",
            "started_at",
            "expires_at",
            "candidate_name",
            "company_name",
            "scenario_title",
            "answer_count",
            "remaining_seconds",
            "score_submitted",
            "submitted_scores",
            "correct_scores",
            "score_diffs",
            "category_balance",
        }

    def test_result_hides_correct_scores_before_submission(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]

        end_response = self.client.post("/api/game/end", json={"session_id": session_id})
        assert end_response.status_code == 200

        result_response = self.client.get(f"/api/game/result/{session_id}")
        assert result_response.status_code == 200
        data = result_response.json()
        assert data["score_submitted"] is False
        assert data["submitted_scores"] is None
        assert data["correct_scores"] is None
        assert data["score_diffs"] is None
        assert data["category_balance"] is None

    def test_score_rejects_incomplete_scores(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]
        self.client.post("/api/game/end", json={"session_id": session_id})

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": {"initiative": 3}},
        )
        assert score_response.status_code == 400

    def test_score_rejects_invalid_score_values(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]
        self.client.post("/api/game/end", json={"session_id": session_id})

        scores = {competency_id: 3 for competency_id in COMPETENCY_DEFINITIONS}
        scores["initiative"] = 6

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": scores},
        )
        assert score_response.status_code == 400

    def test_score_rejects_submission_before_session_end(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]
        scores = {competency_id: 3 for competency_id in COMPETENCY_DEFINITIONS}

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": scores},
        )
        assert score_response.status_code == 409

    def test_unknown_session_returns_404_across_game_endpoints(self):
        missing_session_id = "missing-session"
        scores = {competency_id: 3 for competency_id in COMPETENCY_DEFINITIONS}

        ask_response = self.client.post(
            "/api/game/ask",
            json={"session_id": missing_session_id, "question": "自己PRを教えてください"},
        )
        assert ask_response.status_code == 404

        end_response = self.client.post(
            "/api/game/end",
            json={"session_id": missing_session_id},
        )
        assert end_response.status_code == 404

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": missing_session_id, "scores": scores},
        )
        assert score_response.status_code == 404

        result_response = self.client.get(f"/api/game/result/{missing_session_id}")
        assert result_response.status_code == 404
