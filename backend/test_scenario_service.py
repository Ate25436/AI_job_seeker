from app.services.scenario_service import COMPETENCY_DEFINITIONS, ScenarioService


class TestScenarioService:
    def setup_method(self):
        self.service = ScenarioService()

    def test_list_fixed_scenarios(self):
        scenarios = self.service.list_fixed_scenarios()
        assert "frontiersoft_taro.yaml" in scenarios

    def test_load_fixed_scenario(self):
        scenario = self.service.load_fixed_scenario()
        assert scenario["scenario_meta"]["scenario_id"] == "frontiersoft_taro_v1"
        assert scenario["candidate_profile"]["full_name"] == "就活 太郎"

    def test_generate_category_balance_has_unique_levels(self):
        balance = self.service.generate_category_balance(seed=10)
        assert set(balance.keys()) == {"action", "thinking", "teamwork"}
        assert sorted(balance.values()) == ["high", "low", "middle"]

    def test_generate_competency_scores_respects_balance_ranges(self):
        balance = {"action": "high", "thinking": "low", "teamwork": "middle"}
        scores = self.service.generate_competency_scores(balance, seed=5)

        for competency_id, definition in COMPETENCY_DEFINITIONS.items():
            score = scores[competency_id]
            level = balance[definition["category_id"]]
            if level == "high":
                assert score in {4, 5}
            elif level == "middle":
                assert score in {2, 3, 4}
            else:
                assert score in {1, 2}

    def test_generate_scenario_builds_consistent_payload(self):
        balance = {"action": "high", "thinking": "low", "teamwork": "middle"}
        scenario = self.service.generate_scenario(seed=12, fixed_category_balance=balance)

        assert scenario["evaluation_profile"]["category_balance"] == balance
        assert len(scenario["evaluation_profile"]["competencies"]) == 12
        assert set(scenario["interview_content"].keys()) == {
            "student_life",
            "teamwork",
            "motivation",
            "self_promotion",
            "work_values",
            "stress_tolerance",
            "engineering",
        }

    def test_validate_scenario_rejects_invalid_balance(self):
        scenario = self.service.load_fixed_scenario()
        scenario["evaluation_profile"]["category_balance"]["teamwork"] = "high"

        try:
            self.service.validate_scenario(scenario)
        except ValueError as exc:
            assert "high, middle, low exactly once" in str(exc)
        else:
            raise AssertionError("validate_scenario should reject invalid balance")
