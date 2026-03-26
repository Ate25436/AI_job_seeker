from datetime import datetime, UTC

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.game_session_service import GameSessionService
from app.services.scenario_service import COMPETENCY_DEFINITIONS


class DummyRAGService:
    async def generate_answer(self, question, history=None):
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

    def test_start_game_session(self):
        response = self.client.post("/api/game/start", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["candidate_name"] == "就活 太郎"
        assert data["company_name"] == "フロンティアソフト株式会社"

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

    def test_score_rejects_incomplete_scores(self):
        start_response = self.client.post("/api/game/start", json={})
        session_id = start_response.json()["session_id"]
        self.client.post("/api/game/end", json={"session_id": session_id})

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": {"initiative": 3}},
        )
        assert score_response.status_code == 400
