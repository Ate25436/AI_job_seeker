# Test Plan For `tasks.md` Items 1-12

## Reference Frame

This plan uses [test_perspective.md](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\test_perspective.md) as the primary organizing reference.

That means each case is designed with these lenses in mind:

- `Functional correctness`: does the feature behave as specified?
- `Edge cases and error handling`: does it reject invalid or conflicting input safely?
- `Security/input validation`: are untrusted inputs constrained by schema and API validation?
- `UI / user flow`: for backend-owned flows, does the session/state transition work end-to-end?
- `Maintainability`: can the behavior be verified with stable unit/integration tests rather than fragile E2E checks?

The repo currently supports backend/service/API verification much more strongly than frontend/E2E verification, so this plan emphasizes unit and integration tests first, consistent with the test pyramid in `test_perspective.md`.

## Current Evidence Base

Primary implementation sources:

- [backend/app/services/scenario_service.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\services\scenario_service.py)
- [backend/app/services/game_session_service.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\services\game_session_service.py)
- [backend/app/services/rag_service.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\services\rag_service.py)
- [backend/app/services/vector_db_manager.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\services\vector_db_manager.py)
- [backend/app/main.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\main.py)
- [backend/app/models.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\models.py)
- [scenarios/frontiersoft_taro.yaml](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\scenarios\frontiersoft_taro.yaml)

Existing automated tests relevant to tasks 1-12:

- [backend/test_scenario_service.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scenario_service.py)
- [backend/test_game_api.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_game_api.py)
- [backend/test_backend.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_backend.py)
- [backend/test_scoring_task8.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scoring_task8.py)
- [backend/test_feedback_task9.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_feedback_task9.py)
- [backend/test_tasks10_12_spec.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_tasks10_12_spec.py)

Status labels used below:

- `Covered`: already backed by automated tests
- `Partial`: some evidence exists, but coverage is incomplete or indirect
- `Specified only`: expected behavior is documented in tests/plan but not implemented yet

## Task 1. Specification Consolidation

Task 1 is mostly specification-level work, so the testable surface is indirect: schema shape, scenario shape, session flow, and result payload shape.

### Must-pass cases

1. `test_fixed_scenario_has_required_top_level_sections`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Maintainability`
   - Target: fixed scenario structure
   - Assert: scenario contains `scenario_meta`, `candidate_profile`, `company_profile`, `evaluation_profile`, `interview_content`
   - Status: `Partial`

2. `test_game_flow_supports_start_then_question_then_end_then_result`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Target: basic 1-play flow
   - Assert: session moves through `active` to `ended`, with result retrieval available
   - Status: `Covered`
   - Evidence: [backend/test_game_api.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_game_api.py)

3. `test_result_payload_contains_defined_result_fields`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Target: result screen contract visible from API
   - Assert: result payload includes session info, answer count, score submission state, and scoring-related fields when available
   - Status: `Partial`

### Notes

- Task 1 items about “10-minute interview” and “result display contents” are only partially testable today through `remaining_seconds`, session expiry, and result payload structure.
- No frontend timing/display tests exist yet.

## Task 2. Evaluation Items And Scoring Rule Design

This task maps well to stable unit tests.

### Must-pass cases

1. `test_competency_definitions_cover_exactly_12_items`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Maintainability`
   - Assert: exactly 12 competencies exist, each with category, label, question tags, behavior text, and signal text
   - Status: `Partial`

2. `test_generate_category_balance_assigns_high_middle_low_once_each`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: `action`, `thinking`, `teamwork` get unique `high / middle / low`
   - Status: `Covered`

3. `test_generate_competency_scores_respect_high_middle_low_ranges`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Edge cases and error handling`
   - Assert: `high -> {4,5}`, `middle -> {2,3,4}`, `low -> {1,2}`
   - Status: `Covered`

4. `test_build_evidence_for_scores_returns_required_evidence_format`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: each competency produces `score`, `evidence_summary`, `evidence_episode`, `observable_signals`, `signal_strength`, `question_tags`
   - Status: `Covered`

5. `test_interview_content_competency_mapping_is_present_in_generated_scenario`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: generated interview content carries `related_competencies` and non-empty explanatory fields
   - Status: `Partial`

### Error-path cases

6. `test_validate_scenario_rejects_invalid_category_balance`
   - Type: `Unit`
   - Perspective: `Edge cases and error handling`, `Security/input validation`
   - Status: `Covered`

7. `test_validate_scenario_rejects_score_out_of_range_for_balance`
   - Type: `Unit`
   - Perspective: `Edge cases and error handling`
   - Status: `Covered`

## Task 3. Job-Seeker Scenario Data Design

This task is mostly data-contract verification against the checked-in scenario.

### Must-pass cases

1. `test_fixed_scenario_candidate_profile_contains_required_fields`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: candidate profile includes the agreed identity, academic, and preference fields
   - Status: `Specified only`

2. `test_fixed_scenario_company_profile_contains_required_fields`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: company profile includes name, business context, target role, scale, and fit traits
   - Status: `Specified only`

3. `test_fixed_scenario_interview_content_contains_all_seven_categories`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: `student_life`, `teamwork`, `motivation`, `self_promotion`, `work_values`, `stress_tolerance`, `engineering`
   - Status: `Specified only`

4. `test_fixed_scenario_is_valid_yaml_and_loads_via_service`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Maintainability`
   - Assert: YAML file loads through `ScenarioService` and passes validation
   - Status: `Partial`

### Notes

- Task 3 is a strong candidate for pure unit tests because the data is fixed and stable.

## Task 4. RAG Content Preparation

Task 4 is partly a content-production task. The most reliable automated checks here are structural and routing-oriented.

### Must-pass cases

1. `test_vector_chunking_tags_chunks_with_scenario_metadata`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Maintainability`
   - Assert: chunk metadata includes `scenario_id` and source file path
   - Status: `Covered`

2. `test_generated_or_loaded_scenario_contains_all_interview_content_blocks`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: every required content category exists and is non-empty enough for downstream use
   - Status: `Partial`

3. `test_fixed_scenario_content_and_evaluation_do_not_break_validation_rules`
   - Type: `Unit`
   - Perspective: `Edge cases and error handling`
   - Assert: scenario loads and validates without contradictions that the validator can detect
   - Status: `Partial`

### Spec/manual-assisted cases

4. `manual_review_markdown_content_matches_declared_scores`
   - Type: `Manual content review`
   - Perspective: `Functional correctness`, `Usability`
   - Target: task `4.9`
   - Status: `Specified only`

5. `manual_review_information_source_layout_is_game_oriented`
   - Type: `Manual repository review`
   - Perspective: `Maintainability`
   - Target: task `4.10`
   - Status: `Specified only`

## Task 5. Job-Seeker Generation Logic

This is mostly implemented in `ScenarioService` and is well suited to unit tests.

### Must-pass cases

1. `test_generate_category_balance_is_seedable_and_rule_compliant`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Status: `Covered`

2. `test_generate_competency_scores_returns_complete_12_item_map`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Status: `Specified only`

3. `test_build_evidence_for_scores_emits_story_and_signal_data`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Status: `Covered`

4. `test_generate_scenario_builds_consistent_payload`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Assert: generated scenario includes category balance, competency map, and all interview content blocks
   - Status: `Covered`

5. `test_validate_generated_scenario_catches_inconsistencies`
   - Type: `Unit`
   - Perspective: `Edge cases and error handling`
   - Status: `Covered`

6. `test_fixed_pattern_scenario_is_available`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Assert: default fixed scenario is listable and loadable
   - Status: `Covered`

## Task 6. Backend API Extension

This task should be verified mostly with integration tests against FastAPI.

### Must-pass happy-path cases

1. `test_post_game_start_returns_session_metadata`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Status: `Covered`

2. `test_post_game_start_generated_mode_returns_generated_scenario`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

3. `test_post_game_ask_returns_answer_payload_and_session_state`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Status: `Covered`

4. `test_post_game_end_marks_session_ended`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

5. `test_post_game_score_accepts_complete_score_submission_after_end`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

6. `test_get_game_result_returns_persisted_scoring_snapshot`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

### Error-path and validation cases

7. `test_score_input_rejects_incomplete_keys`
   - Type: `Integration`
   - Perspective: `Edge cases and error handling`, `Security/input validation`
   - Status: `Covered`

8. `test_score_input_rejects_extra_keys`
   - Type: `Integration`
   - Perspective: `Edge cases and error handling`, `Security/input validation`
   - Status: `Covered`

9. `test_score_input_rejects_non_mapping_payload`
   - Type: `Integration`
   - Perspective: `Security/input validation`
   - Status: `Covered`

10. `test_score_input_rejects_out_of_range_values`
    - Type: `Integration`
    - Perspective: `Edge cases and error handling`
    - Status: `Covered`

11. `test_scoring_before_session_end_returns_conflict`
    - Type: `Integration`
    - Perspective: `Edge cases and error handling`, `UI / user flow`
    - Status: `Covered`

12. `test_unknown_session_returns_404_across_game_endpoints`
    - Type: `Integration`
    - Perspective: `Edge cases and error handling`, `Security/input validation`
    - Status: `Covered`

13. `test_result_hides_correct_scores_before_submission`
    - Type: `Integration`
    - Perspective: `Functional correctness`
    - Status: `Covered`

## Task 7. RAG Response Logic Adjustment

LLM quality aspects are only partially automatable with the current codebase, but the routing and constraint mechanisms are testable.

### Must-pass cases

1. `test_rag_history_block_preserves_prior_turns`
   - Type: `Unit`
   - Perspective: `Functional correctness`, `Maintainability`
   - Status: `Covered`

2. `test_game_ask_passes_session_history_to_rag_service`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Status: `Covered`

3. `test_game_ask_passes_session_scenario_id_to_rag_service`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

4. `test_generate_answer_applies_scenario_filter_to_retrieval`
   - Type: `Unit`
   - Perspective: `Functional correctness`
   - Status: `Covered`

5. `test_start_and_ask_responses_do_not_expose_correct_scores`
   - Type: `Integration`
   - Perspective: `Security/input validation`, `Functional correctness`
   - Status: `Specified only`

### Specified-only quality cases

6. `prompt_snapshot_candidate_answers_sound_natural`
   - Type: `Prompt snapshot / contract test`
   - Perspective: `Usability`
   - Status: `Specified only`

7. `prompt_snapshot_reveals_information_progressively_under_follow_up`
   - Type: `Prompt snapshot / contract test`
   - Perspective: `Usability`
   - Status: `Specified only`

8. `retrieval_fallback_does_not_answer_outside_context`
   - Type: `Unit or prompt contract test`
   - Perspective: `Security/input validation`, `Functional correctness`
   - Status: `Specified only`

## Task 8. Scoring And Grade Calculation

This task currently has the clearest split between implemented and not-yet-implemented behavior.

### Must-pass cases for current implementation

1. `test_score_input_requires_all_12_competencies`
   - Type: `Integration`
   - Perspective: `Security/input validation`, `Edge cases and error handling`
   - Status: `Covered`
   - Evidence: [backend/test_scoring_task8.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scoring_task8.py)

2. `test_score_input_rejects_extra_competency_keys`
   - Type: `Integration`
   - Perspective: `Security/input validation`
   - Status: `Covered`

3. `test_score_input_rejects_non_mapping_shape`
   - Type: `Integration`
   - Perspective: `Security/input validation`
   - Status: `Covered`

4. `test_score_diffs_are_calculated_as_submitted_minus_correct`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Status: `Covered`

5. `test_score_submission_persists_and_remains_visible_in_result`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Status: `Covered`

### Expected-behavior cases blocked on implementation

6. `test_result_includes_base_score_derived_from_score_diffs`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Expected behavior: result payload exposes a base score or grade derived from diff quality
   - Status: `Specified only`
   - Current test form: strict `xfail`

7. `test_result_includes_50_centered_display_score`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `Usability`
   - Expected behavior: result payload exposes a normalized/adjusted score centered around 50
   - Status: `Specified only`
   - Current test form: strict `xfail`

8. `test_display_score_handles_extreme_cases_without_leaving_reasonable_bounds`
   - Type: `Integration`
   - Perspective: `Edge cases and error handling`, `Usability`
   - Expected behavior: perfect and poor scoring outcomes remain bounded and non-pathological
   - Status: `Specified only`
   - Current test form: strict `xfail`

### Implementation gap summary

- Implemented today:
  - score payload validation
  - score submission persistence
  - `correct_scores`
  - `score_diffs`
- Missing today:
  - base score calculation
  - adjusted/display score calculation
  - 50-centered normalization logic
  - explicit extreme-case handling in result payload

## Task 9. Feedback Generation

Task 9 is not implemented in the current backend, but it has a clear future verification surface. Based on the current planning style, the strongest first step is to define concrete integration-style payload expectations and keep them as specification tests until a feedback service or result payload extension exists.

### Must-have feedback cases

1. `test_result_includes_feedback_summary_after_score_submission`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Expected behavior: after a session is ended and scored, the result payload includes a top-level feedback object or equivalent summary fields
   - Minimum expected fields:
     - `feedback_summary`
     - `feedback_mode` such as `rule_based` or `llm`
   - Status: `Specified only`
   - Current test form: strict `xfail`

2. `test_feedback_identifies_correctly_and_incorrectly_inferred_competencies`
   - Type: `Integration`
   - Perspective: `Functional correctness`
   - Expected behavior: feedback distinguishes between:
     - competencies the interviewer inferred accurately
     - competencies missed or inferred poorly
   - Minimum expected fields:
     - `detected_competencies`
     - `missed_competencies`
     - optional per-item accuracy labels such as `correct`, `overestimated`, `underestimated`
   - Status: `Specified only`
   - Current test form: strict `xfail`

3. `test_feedback_surfaces_missing_question_angles_per_competency`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `Usability`
   - Expected behavior: for each weakly inferred competency, feedback suggests missing question angles such as:
     - cause analysis
     - planning detail
     - stakeholder handling
     - concrete action/result evidence
   - Minimum expected fields:
     - `question_angle_gaps`
     - per-competency non-empty angle suggestions
   - Status: `Specified only`
   - Current test form: strict `xfail`

4. `test_feedback_uses_conversation_logs_to_flag_shallow_follow_up`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `UI / user flow`
   - Expected behavior: using the stored conversation log, feedback identifies shallow questioning patterns, for example:
     - only one broad question in a category
     - no cause/result/probing follow-up after a candidate answer
     - repeated surface-level prompts without drilling into evidence
   - Minimum expected fields:
     - `shallow_follow_up_flags`
     - references to the relevant conversation turn or category
   - Status: `Specified only`
   - Current test form: strict `xfail`

5. `test_feedback_defaults_to_rule_based_mode_in_initial_implementation`
   - Type: `Integration`
   - Perspective: `Functional correctness`, `Maintainability`
   - Expected behavior: the first implemented version returns deterministic rule-based feedback before any LLM-generated feedback is introduced
   - Minimum expected fields:
     - `feedback_mode == "rule_based"`
   - Status: `Specified only`
   - Current test form: strict `xfail`

6. `test_feedback_contract_allows_future_llm_generated_feedback`
   - Type: `Integration or contract test`
   - Perspective: `Maintainability`, `Usability`
   - Expected behavior: the payload structure leaves room for later natural-language feedback generation without breaking the rule-based contract
   - Minimum expected fields:
     - `feedback_mode in {"rule_based", "llm"}`
     - stable structured fields remain present even if free-text feedback is LLM-produced
   - Status: `Specified only`
   - Current test form: strict `xfail`

### Recommended fixture patterns for task 9

These cases should be driven by at least three deterministic conversation fixtures:

1. `strong_inference_fixture`
   - The interviewer asks competency-revealing follow-ups across multiple categories and scoring is close to ground truth.
   - Expected feedback: many correctly inferred competencies, few angle gaps, limited shallow-follow-up flags.

2. `surface_only_fixture`
   - The interviewer asks broad top-level questions but rarely follows up on cause, action, difficulty, tradeoff, or result.
   - Expected feedback: several missed competencies, many missing question angles, multiple shallow-follow-up flags.

3. `misread_fixture`
   - The interviewer asks questions but systematically overestimates or underestimates certain competencies relative to the answer evidence.
   - Expected feedback: explicit “missed” or “misread” competency diagnostics.

### Current implementation gap summary

- Implemented today:
  - conversation history is stored in the session
  - submitted scores and correct scores are available after scoring
  - score diffs are available for comparison
- Missing today:
  - feedback generation service
  - feedback fields in the result payload
  - rule-based shallow-follow-up analysis
  - per-competency question-angle gap reporting
  - optional LLM feedback mode

## Task 10. Frontend Modification

Task 10 is primarily frontend-owned. The current frontend still behaves as a generic RAG chat UI rather than the planned interview game flow, so most cases are specification-only today. The most useful automated checks at this stage are contract tests around frontend API methods, result/feedback types, and state-persistence expectations.

### Must-have frontend flow cases

1. `test_frontend_renders_title_and_description_for_game_entry`
   - Type: `Component or E2E`
   - Perspective: `UI / user flow`, `Functional correctness`
   - Expected behavior: landing view clearly explains the game and leads into session start
   - Status: `Specified only`

2. `test_frontend_exposes_game_start_action_and_session_bootstrap`
   - Type: `Component or integration`
   - Perspective: `UI / user flow`, `Functional correctness`
   - Expected behavior: frontend can call `POST /api/game/start` and store the returned session context
   - Status: `Specified only`
   - Current test form: strict `xfail`

3. `test_frontend_interview_view_displays_timer_and_conversation_history`
   - Type: `Component or E2E`
   - Perspective: `UI / user flow`, `Usability`
   - Expected behavior: interview screen shows countdown timer and readable chat log
   - Status: `Specified only`
   - Current test form: strict `xfail`

4. `test_frontend_auto_ends_interview_when_timer_reaches_zero`
   - Type: `Component or E2E`
   - Perspective: `UI / user flow`, `Edge cases and error handling`
   - Expected behavior: after 10 minutes the UI transitions from interview to scoring without manual intervention
   - Status: `Specified only`
   - Current test form: strict `xfail`

5. `test_frontend_provides_12_item_score_input_form`
   - Type: `Component`
   - Perspective: `Functional correctness`, `Accessibility`
   - Expected behavior: scoring screen presents all 12 competencies with bounded 1-5 input controls
   - Status: `Specified only`
   - Current test form: strict `xfail`

6. `test_frontend_result_view_displays_grade_and_feedback_sections`
   - Type: `Component or E2E`
   - Perspective: `Functional correctness`, `Usability`
   - Expected behavior: result screen renders score summary and feedback summary once available
   - Status: `Specified only`
   - Current test form: strict `xfail`

7. `test_frontend_persists_game_session_state_for_reload_recovery`
   - Type: `Component or integration`
   - Perspective: `UI / user flow`, `Maintainability`
   - Expected behavior: current screen phase, session id, and recoverable state survive reload according to the chosen restoration policy
   - Status: `Specified only`
   - Current test form: strict `xfail`

### Current implementation gap summary

- Implemented today:
  - general chat UI
  - question input with local chat-history persistence
  - conversation display for the generic `/api/ask` flow
- Missing today:
  - game start screen
  - interview timer UI
  - game-session state machine on the frontend
  - scoring screen
  - result screen
  - feedback screen
  - reload recovery for game sessions

## Task 11. Testing

Task 11 is a meta-testing task. The strongest way to track it is through a coverage matrix that maps required test categories to actual test modules and remaining gaps.

### Must-have cases and coverage mapping

1. `test_evaluation_tendency_generation_is_unit_tested`
   - Type: `Meta / unit coverage check`
   - Perspective: `Maintainability`
   - Backing tests: category-balance generation in [backend/test_scenario_service.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scenario_service.py)
   - Status: `Covered`

2. `test_score_generation_logic_is_unit_tested`
   - Type: `Meta / unit coverage check`
   - Perspective: `Maintainability`
   - Backing tests: score-band generation and scenario generation tests
   - Status: `Covered`

3. `test_score_diff_calculation_is_tested`
   - Type: `Meta / integration coverage check`
   - Perspective: `Maintainability`
   - Backing tests: [backend/test_scoring_task8.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scoring_task8.py)
   - Status: `Covered`

4. `test_grade_normalization_logic_is_tested`
   - Type: `Meta / integration coverage check`
   - Perspective: `Maintainability`
   - Backing tests: strict `xfail` score-normalization cases in [backend/test_scoring_task8.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_scoring_task8.py)
   - Status: `Specified only`

5. `test_game_api_happy_path_is_covered`
   - Type: `Meta / integration coverage check`
   - Perspective: `Maintainability`
   - Backing tests: [backend/test_game_api.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\test_game_api.py)
   - Status: `Covered`

6. `test_game_api_error_path_is_covered`
   - Type: `Meta / integration coverage check`
   - Perspective: `Maintainability`
   - Backing tests: score validation and 404/409 behavior tests
   - Status: `Covered`

7. `test_timer_end_screen_transition_is_tested`
   - Type: `Meta / E2E or component coverage check`
   - Perspective: `Maintainability`, `UI / user flow`
   - Status: `Specified only`

8. `test_full_game_flow_integration_is_covered`
   - Type: `Meta / integration coverage check`
   - Perspective: `Maintainability`, `UI / user flow`
   - Backing tests: start -> ask -> end -> score -> result coverage
   - Status: `Covered`

### Notes

- Task 11 is partially satisfied by the backend suite already created for tasks 1-9.
- The main missing portion is frontend/game-timer coverage.

## Task 12. Operations And Deployment Readiness

Task 12 mixes documentation, operational policy, and deploy-config checks. Some of it is already testable through docs/config inspection.

### Must-pass cases

1. `test_readme_deployment_documents_reindex_endpoint_usage`
   - Type: `Unit / doc contract`
   - Perspective: `Maintainability`
   - Assert: deployment doc contains `/api/admin/reindex` and `X-Admin-Token`
   - Status: `Covered`

2. `test_render_config_declares_backend_and_frontend_services`
   - Type: `Unit / config contract`
   - Perspective: `Maintainability`, `Cross-environment compatibility`
   - Assert: `render.yaml` declares both backend and frontend services with expected roots and start/build commands
   - Status: `Covered`

3. `test_render_backend_config_includes_required_game_support_env_vars`
   - Type: `Unit / config contract`
   - Perspective: `Maintainability`
   - Assert: backend render config includes `OPENAI_API_KEY`, `CHROMA_DB_PATH`, `INFO_SOURCE_PATH`, `CORS_ALLOW_ORIGINS`, `REINDEX_TOKEN`
   - Status: `Covered`

4. `test_frontend_config_points_to_backend_api_base_url`
   - Type: `Unit / config contract`
   - Perspective: `Cross-environment compatibility`, `Maintainability`
   - Assert: frontend render config provides `NEXT_PUBLIC_API_BASE_URL`
   - Status: `Covered`

### Specified-only operational-policy cases

5. `test_docs_describe_how_to_add_a_new_scenario`
   - Type: `Doc contract`
   - Perspective: `Maintainability`
   - Expected behavior: repo docs contain a clear scenario-addition procedure
   - Status: `Specified only`
   - Current test form: strict `xfail`

6. `test_docs_describe_reindex_steps_after_markdown_updates`
   - Type: `Doc contract`
   - Perspective: `Maintainability`
   - Expected behavior: docs describe how markdown changes should be re-indexed in practice, not just that the endpoint exists
   - Status: `Specified only`
   - Current test form: strict `xfail`

7. `test_docs_or_config_define_production_session_persistence_strategy`
   - Type: `Doc or config contract`
   - Perspective: `Maintainability`, `Reliability`
   - Expected behavior: session persistence approach for production is documented or configured
   - Status: `Specified only`
   - Current test form: strict `xfail`

8. `test_docs_define_logging_strategy`
   - Type: `Doc contract`
   - Perspective: `Maintainability`, `Reliability`
   - Expected behavior: logging expectations for production/debugging are documented
   - Status: `Specified only`
   - Current test form: strict `xfail`

9. `test_render_deployment_contract_mentions_game_flow_support`
   - Type: `Doc or config contract`
   - Perspective: `Maintainability`, `Cross-environment compatibility`
   - Expected behavior: deployment docs/config explain how the multi-step game flow and related frontend/backend routing are supported
   - Status: `Specified only`
   - Current test form: strict `xfail`

## Coverage Summary By Task

- Task `1`: partial, mostly indirect through session-flow and result-shape tests
- Task `2`: strong backend unit-test coverage
- Task `3`: partially specified; more fixed-scenario field tests should be added
- Task `4`: partially covered structurally; content-consistency still needs manual or richer contract checks
- Task `5`: strong backend unit-test coverage
- Task `6`: strong backend integration-test coverage
- Task `7`: routing/history constraints covered; answer-quality constraints mostly specified only
- Task `8`: current validation/diff/persistence covered; grade/normalization behavior specified but not implemented
- Task `9`: feedback behavior is specified and scaffolded, but not implemented in the API/service layer
- Task `10`: mostly specified only; current frontend is still a generic chat UI rather than the game flow
- Task `11`: backend coverage is strong, but frontend timer/screen-transition coverage is still missing
- Task `12`: deployment/config basics are covered; operational policies and scenario/reindex procedures remain mostly specified only

## Recommended Next Documentation/Test Steps

1. Add direct fixed-scenario field-contract tests for tasks `1` and `3`.
2. Add a small prompt-contract suite for task `7` if RAG prompts become stable enough to snapshot.
3. When task `8` is implemented, convert the strict `xfail` scoring tests into normal passing integration tests and extend [backend/app/models.py](C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend\app\models.py) assertions accordingly.
4. When task `9` is implemented, convert the strict `xfail` feedback tests into normal integration tests and keep the payload contract stable even if an LLM mode is added later.
5. When task `10` frontend work lands, replace the task-10 `xfail` contract checks with real component/E2E coverage for timer, screen flow, and reload restoration.
6. When task `12` operational decisions are documented, convert the doc-policy `xfail` tests into normal contract checks.
