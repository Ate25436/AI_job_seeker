from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.game_session_service import GameSessionService
from app.services.scenario_service import COMPETENCY_DEFINITIONS, ScenarioService


def build_uniform_scores(value: int) -> dict[str, int]:
    return {competency_id: value for competency_id in COMPETENCY_DEFINITIONS}


def build_inverse_scores(correct_scores: dict[str, int]) -> dict[str, int]:
    # Mirror the 1-5 scale around the center while staying in-range.
    return {competency_id: 6 - score for competency_id, score in correct_scores.items()}


def extract_grade_value(payload: dict, *field_names: str):
    for field_name in field_names:
        if field_name in payload:
            return payload[field_name]
    return None


class TestTask8ScoringCurrentBehavior:
    def setup_method(self):
        self.client = TestClient(app)
        main_module.game_session_service = GameSessionService()
        main_module.rag_service = None
        self.scenario_service = ScenarioService()

    def _start_and_end_fixed_session(self) -> str:
        start_response = self.client.post("/api/game/start", json={})
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        end_response = self.client.post("/api/game/end", json={"session_id": session_id})
        assert end_response.status_code == 200
        return session_id

    def test_score_input_requires_all_12_competencies(self):
        session_id = self._start_and_end_fixed_session()

        response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": {"initiative": 3}},
        )

        assert response.status_code == 400
        assert "all competency ids exactly once" in response.json()["message"]

    def test_score_input_rejects_extra_competency_keys(self):
        session_id = self._start_and_end_fixed_session()
        scores = build_uniform_scores(3)
        scores["unexpected_competency"] = 3

        response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": scores},
        )

        assert response.status_code == 400
        assert "all competency ids exactly once" in response.json()["message"]

    def test_score_input_rejects_non_mapping_shape(self):
        session_id = self._start_and_end_fixed_session()

        response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": [1, 2, 3]},
        )

        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"

    def test_score_diffs_are_calculated_as_submitted_minus_correct(self):
        session_id = self._start_and_end_fixed_session()
        correct_scores = {
            competency_id: competency["score"]
            for competency_id, competency in self.scenario_service.load_fixed_scenario()[
                "evaluation_profile"
            ]["competencies"].items()
        }
        submitted_scores = build_uniform_scores(3)

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": submitted_scores},
        )
        assert score_response.status_code == 200

        result_response = self.client.get(f"/api/game/result/{session_id}")
        assert result_response.status_code == 200
        data = result_response.json()

        expected_diffs = {
            competency_id: submitted_scores[competency_id] - correct_scores[competency_id]
            for competency_id in correct_scores
        }
        assert data["submitted_scores"] == submitted_scores
        assert data["correct_scores"] == correct_scores
        assert data["score_diffs"] == expected_diffs

    def test_score_submission_persists_and_remains_visible_in_result(self):
        session_id = self._start_and_end_fixed_session()
        submitted_scores = build_uniform_scores(4)

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": submitted_scores},
        )
        assert score_response.status_code == 200

        first_result = self.client.get(f"/api/game/result/{session_id}")
        second_result = self.client.get(f"/api/game/result/{session_id}")

        assert first_result.status_code == 200
        assert second_result.status_code == 200
        assert first_result.json()["score_submitted"] is True
        assert first_result.json()["submitted_scores"] == submitted_scores
        assert second_result.json()["submitted_scores"] == submitted_scores
        assert first_result.json()["correct_scores"] == second_result.json()["correct_scores"]
        assert first_result.json()["score_diffs"] == second_result.json()["score_diffs"]


class TestTask8ScoringExpectedBehavior:
    def setup_method(self):
        self.client = TestClient(app)
        main_module.game_session_service = GameSessionService()
        main_module.rag_service = None
        self.scenario_service = ScenarioService()
        self.correct_scores = {
            competency_id: competency["score"]
            for competency_id, competency in self.scenario_service.load_fixed_scenario()[
                "evaluation_profile"
            ]["competencies"].items()
        }

    def _submit_and_fetch_result(self, submitted_scores: dict[str, int]) -> dict:
        start_response = self.client.post("/api/game/start", json={})
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        end_response = self.client.post("/api/game/end", json={"session_id": session_id})
        assert end_response.status_code == 200

        score_response = self.client.post(
            "/api/game/score",
            json={"session_id": session_id, "scores": submitted_scores},
        )
        assert score_response.status_code == 200

        result_response = self.client.get(f"/api/game/result/{session_id}")
        assert result_response.status_code == 200
        return result_response.json()

    def test_result_includes_base_score_derived_from_score_diffs(self):
        perfect_result = self._submit_and_fetch_result(self.correct_scores)
        imperfect_result = self._submit_and_fetch_result(build_uniform_scores(3))

        perfect_base = extract_grade_value(perfect_result, "base_score", "base_grade")
        imperfect_base = extract_grade_value(imperfect_result, "base_score", "base_grade")

        assert perfect_base is not None
        assert imperfect_base is not None
        assert isinstance(perfect_base, (int, float))
        assert isinstance(imperfect_base, (int, float))
        assert perfect_base > imperfect_base

    def test_result_includes_50_centered_display_score(self):
        perfect_result = self._submit_and_fetch_result(self.correct_scores)
        average_result = self._submit_and_fetch_result(build_uniform_scores(3))
        poor_result = self._submit_and_fetch_result(build_inverse_scores(self.correct_scores))

        perfect_display = extract_grade_value(perfect_result, "display_score", "normalized_score", "adjusted_score")
        average_display = extract_grade_value(average_result, "display_score", "normalized_score", "adjusted_score")
        poor_display = extract_grade_value(poor_result, "display_score", "normalized_score", "adjusted_score")

        assert perfect_display is not None
        assert average_display is not None
        assert poor_display is not None
        assert poor_display < average_display < perfect_display
        assert 35 <= average_display <= 65

    def test_display_score_handles_extreme_cases_without_leaving_reasonable_bounds(self):
        perfect_result = self._submit_and_fetch_result(self.correct_scores)
        poor_result = self._submit_and_fetch_result(build_inverse_scores(self.correct_scores))

        perfect_display = extract_grade_value(perfect_result, "display_score", "normalized_score", "adjusted_score")
        poor_display = extract_grade_value(poor_result, "display_score", "normalized_score", "adjusted_score")

        assert perfect_display is not None
        assert poor_display is not None
        assert 0 <= poor_display <= 100
        assert 0 <= perfect_display <= 100
        assert perfect_display - poor_display < 100
