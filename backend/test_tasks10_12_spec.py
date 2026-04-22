from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestTask10FrontendSpecification:
    def test_frontend_exposes_game_start_action_and_session_bootstrap(self):
        api_source = (REPO_ROOT / "frontend" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")

        assert "/api/game/start" in api_source
        assert "startGame" in api_source or "startGameSession" in api_source

    def test_frontend_interview_view_displays_timer_and_conversation_history(self):
        page_source = (REPO_ROOT / "frontend" / "src" / "app" / "interview" / "page.tsx").read_text(encoding="utf-8")

        assert "remaining_seconds" in page_source or "timer" in page_source.lower()
        assert "ConversationHistory" in page_source
        assert "game" in page_source.lower() or "session" in page_source.lower()

    def test_frontend_provides_12_item_score_input_form(self):
        frontend_sources = [
            (REPO_ROOT / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8"),
            (REPO_ROOT / "frontend" / "src" / "app" / "interview" / "page.tsx").read_text(encoding="utf-8"),
            (REPO_ROOT / "frontend" / "src" / "types" / "api.ts").read_text(encoding="utf-8"),
        ]
        combined = "\n".join(frontend_sources)

        assert "ScoreSubmission" in combined or "submitted_scores" in combined
        assert "initiative" in combined and "stress_control" in combined

    def test_frontend_persists_game_session_state_for_reload_recovery(self):
        page_source = "\n".join(
            [
                (REPO_ROOT / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8"),
                (REPO_ROOT / "frontend" / "src" / "app" / "interview" / "page.tsx").read_text(encoding="utf-8"),
            ]
        )

        assert "session_id" in page_source
        assert "localStorage" in page_source
        assert "game" in page_source.lower() or "interview" in page_source.lower()


class TestTask11CoverageMapping:
    def test_task11_backend_test_modules_exist_for_core_game_and_scoring_coverage(self):
        expected_files = {
            "test_scenario_service.py",
            "test_game_api.py",
            "test_backend.py",
            "test_scoring_task8.py",
            "test_feedback_task9.py",
        }
        backend_test_files = {path.name for path in (REPO_ROOT / "backend").glob("test_*.py")}

        assert expected_files <= backend_test_files

    def test_task11_frontend_timer_end_transition_coverage_exists(self):
        backend_test_files = {path.name for path in (REPO_ROOT / "backend").glob("test_*.py")}
        frontend_test_files = {path.name for path in (REPO_ROOT / "frontend").rglob("*test*")}

        assert any("timer" in name.lower() for name in backend_test_files | frontend_test_files)
        assert any("transition" in name.lower() or "flow" in name.lower() for name in backend_test_files | frontend_test_files)


class TestTask12DeploymentContracts:
    def test_render_config_declares_backend_and_frontend_services(self):
        render_config = yaml.safe_load((REPO_ROOT / "render.yaml").read_text(encoding="utf-8"))

        services = render_config["services"]
        names = {service["name"] for service in services}

        assert "ai-job-seeker-backend" in names
        assert "ai-job-seeker-frontend" in names

    def test_render_backend_config_includes_required_game_support_env_vars(self):
        render_config = yaml.safe_load((REPO_ROOT / "render.yaml").read_text(encoding="utf-8"))

        backend_service = next(
            service for service in render_config["services"] if service["name"] == "ai-job-seeker-backend"
        )
        env_keys = {item["key"] for item in backend_service["envVars"]}

        assert {"OPENAI_API_KEY", "CHROMA_DB_PATH", "INFO_SOURCE_PATH", "CORS_ALLOW_ORIGINS", "REINDEX_TOKEN"} <= env_keys

    def test_frontend_config_points_to_backend_api_base_url(self):
        render_config = yaml.safe_load((REPO_ROOT / "render.yaml").read_text(encoding="utf-8"))

        frontend_service = next(
            service for service in render_config["services"] if service["name"] == "ai-job-seeker-frontend"
        )
        env_keys = {item["key"] for item in frontend_service["envVars"]}

        assert "NEXT_PUBLIC_API_BASE_URL" in env_keys

    def test_docs_describe_how_to_add_a_new_scenario(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        deployment_readme = (REPO_ROOT / "README_DEPLOYMENT.md").read_text(encoding="utf-8")
        combined = f"{readme}\n{deployment_readme}"

        assert "シナリオ追加" in combined or "add a scenario" in combined.lower()

    def test_docs_describe_reindex_steps_after_markdown_updates(self):
        deployment_readme = (REPO_ROOT / "README_DEPLOYMENT.md").read_text(encoding="utf-8")

        assert "re-index" in deployment_readme.lower()
        assert "markdown" in deployment_readme.lower()
        assert "after updating" in deployment_readme.lower() or "更新後" in deployment_readme

    def test_docs_or_config_define_production_session_persistence_strategy(self):
        combined = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "README_DEPLOYMENT.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "render.yaml").read_text(encoding="utf-8"),
            ]
        )

        assert "session persistence" in combined.lower() or "セッション保存" in combined

    def test_docs_define_logging_strategy(self):
        combined = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "README_DEPLOYMENT.md").read_text(encoding="utf-8"),
            ]
        )

        assert "logging strategy" in combined.lower() or "ログ出力方針" in combined

    def test_render_deployment_contract_mentions_game_flow_support(self):
        combined = "\n".join(
            [
                (REPO_ROOT / "README_DEPLOYMENT.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "render.yaml").read_text(encoding="utf-8"),
            ]
        )

        assert "game/result" in combined.lower() or "面接" in combined
        assert "frontend" in combined.lower() and "backend" in combined.lower()
