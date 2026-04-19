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
        assert set(scenario.keys()) == {
            "scenario_meta",
            "candidate_profile",
            "company_profile",
            "evaluation_profile",
            "interview_content",
        }

    def test_fixed_scenario_candidate_profile_contains_required_fields(self):
        scenario = self.service.load_fixed_scenario()
        candidate_profile = scenario["candidate_profile"]

        assert set(candidate_profile.keys()) >= {
            "full_name",
            "kana_name",
            "age",
            "gender",
            "university",
            "faculty_type",
            "grade",
            "graduation_status",
            "gap_or_repeat",
            "desired_industry",
            "desired_job_family",
            "current_status_summary",
            "personality_summary",
        }

    def test_fixed_scenario_company_profile_contains_required_fields(self):
        scenario = self.service.load_fixed_scenario()
        company_profile = scenario["company_profile"]

        assert set(company_profile.keys()) >= {
            "company_name",
            "company_name_en",
            "industry",
            "philosophy",
            "business_areas",
            "job_role",
            "company_scale",
            "ideal_candidate_traits",
            "candidate_fit_points",
        }
        assert isinstance(company_profile["business_areas"], list)
        assert company_profile["business_areas"]
        assert isinstance(company_profile["ideal_candidate_traits"], list)
        assert company_profile["ideal_candidate_traits"]

    def test_fixed_scenario_interview_content_contains_all_seven_categories(self):
        scenario = self.service.load_fixed_scenario()
        interview_content = scenario["interview_content"]

        assert set(interview_content.keys()) == {
            "student_life",
            "teamwork",
            "motivation",
            "self_promotion",
            "work_values",
            "stress_tolerance",
            "engineering",
        }
        for content in interview_content.values():
            assert content["summary"]
            assert content["core_story"]
            assert isinstance(content["related_competencies"], list)
            assert content["related_competencies"]
            assert isinstance(content["hidden_signals"], list)
            assert content["hidden_signals"]
            assert isinstance(content["qa_pairs"], list)

    def test_generate_category_balance_has_unique_levels(self):
        balance = self.service.generate_category_balance(seed=10)
        assert set(balance.keys()) == {"action", "thinking", "teamwork"}
        assert sorted(balance.values()) == ["high", "low", "middle"]

    def test_generate_competency_scores_respects_balance_ranges(self):
        balance = {"action": "high", "thinking": "low", "teamwork": "middle"}
        scores = self.service.generate_competency_scores(balance, seed=5)

        assert set(scores.keys()) == set(COMPETENCY_DEFINITIONS.keys())
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
        for content_id, content in scenario["interview_content"].items():
            assert content["summary"]
            assert content["core_story"]
            assert content["related_competencies"]
            assert isinstance(content["hidden_signals"], list)
            assert content["hidden_signals"]

    def test_build_evidence_for_scores_returns_expected_fields(self):
        scores = {competency_id: 3 for competency_id in COMPETENCY_DEFINITIONS}

        evidence_map = self.service.build_evidence_for_scores(scores)

        assert set(evidence_map.keys()) == set(COMPETENCY_DEFINITIONS.keys())
        for competency_id, evidence in evidence_map.items():
            assert evidence["score"] == 3
            assert evidence["evidence_summary"]
            assert evidence["evidence_episode"]
            assert isinstance(evidence["observable_signals"], list)
            assert evidence["observable_signals"]
            assert evidence["signal_strength"] == "medium"
            assert evidence["question_tags"] == COMPETENCY_DEFINITIONS[competency_id]["question_tags"]

    def test_validate_scenario_rejects_invalid_balance(self):
        scenario = self.service.load_fixed_scenario()
        scenario["evaluation_profile"]["category_balance"]["teamwork"] = "high"

        try:
            self.service.validate_scenario(scenario)
        except ValueError as exc:
            assert "high, middle, low exactly once" in str(exc)
        else:
            raise AssertionError("validate_scenario should reject invalid balance")

    def test_validate_scenario_rejects_score_out_of_range_for_balance(self):
        scenario = self.service.load_fixed_scenario()
        scenario["evaluation_profile"]["competencies"]["initiative"]["score"] = 2

        try:
            self.service.validate_scenario(scenario)
        except ValueError as exc:
            assert "High category score out of range" in str(exc)
        else:
            raise AssertionError("validate_scenario should reject out-of-range scores for a category")
