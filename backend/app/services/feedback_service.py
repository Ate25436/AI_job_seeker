from __future__ import annotations

from typing import Any

from .scenario_service import COMPETENCY_DEFINITIONS, INTERVIEW_CONTENT_COMPETENCIES


QUESTION_TAG_KEYWORDS = {
    "student_life": ["学生時代", "ガクチカ", "頑張", "学園祭", "サークル", "研究", "学業"],
    "teamwork": ["チーム", "協働", "役割", "連携", "メンバー", "対立", "協力"],
    "motivation": ["志望動機", "御社", "企業", "入社", "志望", "なぜこの会社"],
    "self_promotion": ["自己pr", "強み", "弱み", "長所", "短所", "自分らしさ"],
    "work_values": ["価値観", "将来", "キャリア", "5年後", "10年後", "働きたい"],
    "stress_tolerance": ["ストレス", "プレッシャー", "忙しい", "意見の合わない", "体調", "リフレッシュ", "困難"],
    "engineering": ["技術", "プログラミング", "開発", "ポートフォリオ", "技術選定", "エンジニア"],
}

FOLLOW_UP_KEYWORDS = ["なぜ", "具体", "詳しく", "深掘", "そのとき", "理由", "背景", "どうして", "工夫"]


class FeedbackService:
    def build_feedback(
        self,
        scenario: dict[str, Any],
        history: list[dict[str, Any]],
        submitted_scores: dict[str, int],
        correct_scores: dict[str, int],
        score_diffs: dict[str, int],
    ) -> dict[str, Any]:
        user_questions = [
            item["content"].strip()
            for item in history
            if item.get("role") == "user" and isinstance(item.get("content"), str)
        ]
        detected_by_question = self._infer_competencies_from_questions(user_questions)

        detected_competencies = sorted(
            competency_id
            for competency_id in detected_by_question
            if abs(score_diffs.get(competency_id, 99)) <= 1
        )
        missed_competencies = sorted(
            competency_id
            for competency_id in COMPETENCY_DEFINITIONS
            if competency_id not in detected_competencies
        )

        if not detected_competencies and not missed_competencies:
            missed_competencies = sorted(COMPETENCY_DEFINITIONS.keys())

        question_angle_gaps = self._build_question_angle_gaps(
            scenario=scenario,
            detected_by_question=detected_by_question,
            missed_competencies=missed_competencies,
            score_diffs=score_diffs,
        )
        shallow_follow_up_flags = self._build_shallow_follow_up_flags(user_questions)

        return {
            "feedback_mode": "rule_based",
            "feedback_summary": self._build_feedback_summary(
                detected_competencies=detected_competencies,
                missed_competencies=missed_competencies,
                question_angle_gaps=question_angle_gaps,
                shallow_follow_up_flags=shallow_follow_up_flags,
            ),
            "detected_competencies": detected_competencies,
            "missed_competencies": missed_competencies,
            "question_angle_gaps": question_angle_gaps,
            "shallow_follow_up_flags": shallow_follow_up_flags,
        }

    def _infer_competencies_from_questions(self, questions: list[str]) -> set[str]:
        detected_tags: set[str] = set()
        for question in questions:
            normalized = question.lower()
            for tag, keywords in QUESTION_TAG_KEYWORDS.items():
                if any(keyword.lower() in normalized for keyword in keywords):
                    detected_tags.add(tag)

        detected_competencies: set[str] = set()
        for tag in detected_tags:
            detected_competencies.update(INTERVIEW_CONTENT_COMPETENCIES.get(tag, []))
        return detected_competencies

    def _build_question_angle_gaps(
        self,
        scenario: dict[str, Any],
        detected_by_question: set[str],
        missed_competencies: list[str],
        score_diffs: dict[str, int],
    ) -> dict[str, list[str]]:
        competencies = scenario["evaluation_profile"]["competencies"]
        gap_candidates = [
            competency_id
            for competency_id in COMPETENCY_DEFINITIONS
            if competency_id in missed_competencies or abs(score_diffs.get(competency_id, 0)) >= 2
        ]

        question_angle_gaps: dict[str, list[str]] = {}
        for competency_id in gap_candidates:
            definition = COMPETENCY_DEFINITIONS[competency_id]
            scenario_competency = competencies[competency_id]
            gaps = []

            if competency_id not in detected_by_question:
                gaps.append(f"{definition['label']}が出る場面として「{definition['situation']}」を聞けていません。")

            gaps.append(f"可観測シグナルとして「{scenario_competency['observable_signals'][0]}」を確認する質問が不足しています。")
            gaps.append(f"{definition['label']}の根拠を掘るために、行動の理由と結果を追加で聞いてください。")

            question_angle_gaps[competency_id] = gaps

        return question_angle_gaps

    def _build_shallow_follow_up_flags(self, questions: list[str]) -> list[str]:
        if not questions:
            return ["質問履歴が少ないため、深掘りの有無を判定できませんでした。"]

        matched_tags: dict[str, int] = {}
        follow_up_count = 0
        for question in questions:
            normalized = question.lower()
            if any(keyword in normalized for keyword in FOLLOW_UP_KEYWORDS):
                follow_up_count += 1
            for tag, keywords in QUESTION_TAG_KEYWORDS.items():
                if any(keyword.lower() in normalized for keyword in keywords):
                    matched_tags[tag] = matched_tags.get(tag, 0) + 1

        flags = [
            f"{tag}に関する質問が{count}回で止まっており、追加の深掘りが不足しています。"
            for tag, count in matched_tags.items()
            if count == 1
        ]

        if follow_up_count == 0:
            flags.append("理由・背景・再現性を問う追質問が不足しており、表面的な確認で終わっています。")

        return flags or ["主要トピックでは追質問できていますが、因果関係の確認をもう一段増やせます。"]

    @staticmethod
    def _build_feedback_summary(
        detected_competencies: list[str],
        missed_competencies: list[str],
        question_angle_gaps: dict[str, list[str]],
        shallow_follow_up_flags: list[str],
    ) -> str:
        detected_labels = "、".join(COMPETENCY_DEFINITIONS[item]["label"] for item in detected_competencies[:3])
        missed_labels = "、".join(COMPETENCY_DEFINITIONS[item]["label"] for item in missed_competencies[:3])

        summary_parts = []
        if detected_labels:
            summary_parts.append(f"今回の面接では {detected_labels} は比較的見抜けています。")
        if missed_labels:
            summary_parts.append(f"一方で {missed_labels} は質問観点が不足し、評価根拠が薄くなりました。")
        if question_angle_gaps:
            summary_parts.append("次回は場面・行動理由・結果まで確認する質問を増やしてください。")
        if shallow_follow_up_flags:
            summary_parts.append("単発質問で終わったトピックがあり、深掘り不足が残っています。")

        return " ".join(summary_parts) or "十分なフィードバックを生成できませんでした。"
