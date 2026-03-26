from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any

import yaml


CATEGORY_LABELS = {
    "action": "前に踏み出す力",
    "thinking": "考え抜く力",
    "teamwork": "チームで働く力",
}

INTERVIEW_CONTENT_COMPETENCIES = {
    "student_life": ["initiative", "influence", "execution", "issue_finding", "planning"],
    "teamwork": ["communication", "listening", "flexibility", "situational_awareness"],
    "motivation": ["communication", "discipline"],
    "self_promotion": ["initiative", "discipline", "stress_control"],
    "work_values": ["execution", "discipline"],
    "stress_tolerance": ["listening", "flexibility", "stress_control"],
    "engineering": ["issue_finding", "creativity"],
}

COMPETENCY_DEFINITIONS = {
    "initiative": {
        "label": "主体性",
        "category_id": "action",
        "question_tags": ["student_life", "self_promotion"],
        "situation": "役割が曖昧な場面",
        "high_behavior": "自分から役割を取り、周囲へ提案して前に進めた",
        "middle_behavior": "自分にできる範囲で動いたが、周囲を大きく巻き込むほどではなかった",
        "low_behavior": "様子見が多く、自分から動き出すまでに時間がかかった",
        "high_signal": "自分から動いた経験を具体的に話す",
        "low_signal": "指示待ちの表現が多い",
    },
    "influence": {
        "label": "働きかけ力",
        "category_id": "action",
        "question_tags": ["teamwork", "student_life"],
        "situation": "周囲の参加が必要な場面",
        "high_behavior": "相手に声をかけて協力を引き出した",
        "middle_behavior": "必要な声かけはしたが、相手ごとの調整は限定的だった",
        "low_behavior": "周囲への働きかけが弱く、流れを変えられなかった",
        "high_signal": "相手を巻き込むために工夫した点を話す",
        "low_signal": "自分だけで抱えた説明が多い",
    },
    "execution": {
        "label": "実行力",
        "category_id": "action",
        "question_tags": ["student_life", "work_values"],
        "situation": "締切や制約がある場面",
        "high_behavior": "優先順位をつけて最後までやり切った",
        "middle_behavior": "必要最低限は完了させたが、余裕を持った進行ではなかった",
        "low_behavior": "やるべきことを完了まで持っていけなかった",
        "high_signal": "最後までやり切った過程を話す",
        "low_signal": "着手したが完了しなかった話が中心になる",
    },
    "issue_finding": {
        "label": "課題発見力",
        "category_id": "thinking",
        "question_tags": ["student_life", "engineering"],
        "situation": "問題が起きた場面",
        "high_behavior": "原因を切り分けて、本質的な問題を見つけた",
        "middle_behavior": "表面的な問題は見えていたが、深い原因特定は十分ではなかった",
        "low_behavior": "原因を整理できず、思いついた対応を順に試す形になった",
        "high_signal": "原因と結果を分けて説明する",
        "low_signal": "分析より対応策の話が先に出る",
    },
    "planning": {
        "label": "計画力",
        "category_id": "thinking",
        "question_tags": ["student_life", "teamwork"],
        "situation": "複数の作業を整理する場面",
        "high_behavior": "段取りや依存関係まで考えて進行を設計した",
        "middle_behavior": "大まかな計画は立てたが、細かな見積もりは粗かった",
        "low_behavior": "その場で考えながら進めることが多く、計画の精度が低かった",
        "high_signal": "準備や段取りの考え方を具体的に話す",
        "low_signal": "まずやってみるという表現が中心になる",
    },
    "creativity": {
        "label": "創造力",
        "category_id": "thinking",
        "question_tags": ["student_life", "engineering"],
        "situation": "改善策を考える場面",
        "high_behavior": "既存案にとらわれず、新しい打ち手を提案した",
        "middle_behavior": "既存の方法を組み合わせて改善した",
        "low_behavior": "前例をなぞることが多く、新しい発想は少なかった",
        "high_signal": "独自の工夫を具体的に話す",
        "low_signal": "参考事例ベースの説明が多い",
    },
    "communication": {
        "label": "発信力",
        "category_id": "teamwork",
        "question_tags": ["teamwork", "motivation"],
        "situation": "情報共有が必要な場面",
        "high_behavior": "相手に合わせて伝え方を変えながら共有した",
        "middle_behavior": "必要な共有はできたが、伝わりやすさにばらつきがあった",
        "low_behavior": "伝達が不足し、認識ずれを生みやすかった",
        "high_signal": "相手に応じた説明の工夫を話す",
        "low_signal": "伝えたつもりで終わる表現が多い",
    },
    "listening": {
        "label": "傾聴力",
        "category_id": "teamwork",
        "question_tags": ["teamwork", "stress_tolerance"],
        "situation": "相手の意見を受け止める場面",
        "high_behavior": "相手の背景まで聞き取り、考えを整理できた",
        "middle_behavior": "一通り意見は聞いたが、深掘りは十分ではなかった",
        "low_behavior": "相手の話を十分に受け止められず、自分の考えを優先した",
        "high_signal": "相手の背景や意図まで確認した話が出る",
        "low_signal": "自分の案を通した話が中心になる",
    },
    "flexibility": {
        "label": "柔軟性",
        "category_id": "teamwork",
        "question_tags": ["teamwork", "stress_tolerance"],
        "situation": "方針変更や想定外が起きた場面",
        "high_behavior": "状況変化に応じて役割や進め方を柔軟に変えた",
        "middle_behavior": "変更には対応したが、最適化まではできなかった",
        "low_behavior": "変化への適応が遅れ、対応に苦戦した",
        "high_signal": "状況に合わせて対応を変えた例を話す",
        "low_signal": "変更に引きずられた話が多い",
    },
    "situational_awareness": {
        "label": "状況把握力",
        "category_id": "teamwork",
        "question_tags": ["teamwork", "student_life"],
        "situation": "周囲の状態を見る場面",
        "high_behavior": "周囲の負荷や進捗を早めに察知して調整した",
        "middle_behavior": "状況は把握できたが、先回りした対応は少なかった",
        "low_behavior": "状況の変化に気づくのが遅く、対応が後手になった",
        "high_signal": "周囲を見て調整した話が出る",
        "low_signal": "問題が顕在化してから動いた話が中心になる",
    },
    "discipline": {
        "label": "規律性",
        "category_id": "teamwork",
        "question_tags": ["self_promotion", "work_values"],
        "situation": "約束や期限を守る場面",
        "high_behavior": "基本動作を安定して守り、周囲の信頼につなげた",
        "middle_behavior": "大きな問題なく守れていたが、強みとして際立つほどではなかった",
        "low_behavior": "期限や約束の管理が甘く、周囲に影響を出した",
        "high_signal": "期限や約束を守る工夫を話す",
        "low_signal": "忙しさを理由に管理が崩れた話が多い",
    },
    "stress_control": {
        "label": "ストレスコントロール",
        "category_id": "teamwork",
        "question_tags": ["stress_tolerance", "self_promotion"],
        "situation": "負荷が重なった場面",
        "high_behavior": "感情や体調を整えながら持続的に対応した",
        "middle_behavior": "短期的には乗り切れたが、無理も出やすかった",
        "low_behavior": "根性で乗り切る場面が多く、持続的な対処が弱かった",
        "high_signal": "セルフマネジメントの工夫を話す",
        "low_signal": "気合いで乗り切ったという表現が出る",
    },
}


class ScenarioService:
    def __init__(self, scenarios_dir: str | Path | None = None):
        if scenarios_dir is None:
            scenarios_dir = Path(__file__).resolve().parents[3] / "scenarios"
        self.scenarios_dir = Path(scenarios_dir)

    def list_fixed_scenarios(self) -> list[str]:
        return sorted(path.name for path in self.scenarios_dir.glob("*.yaml"))

    def load_fixed_scenario(self, file_name: str = "frontiersoft_taro.yaml") -> dict[str, Any]:
        scenario_path = self.scenarios_dir / file_name
        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

        with scenario_path.open("r", encoding="utf-8") as file:
            scenario = yaml.safe_load(file)

        self.validate_scenario(scenario)
        return scenario

    def generate_category_balance(self, seed: int | None = None) -> dict[str, str]:
        rng = random.Random(seed)
        levels = ["high", "middle", "low"]
        rng.shuffle(levels)
        return dict(zip(CATEGORY_LABELS.keys(), levels, strict=True))

    def generate_competency_scores(
        self,
        category_balance: dict[str, str],
        seed: int | None = None,
    ) -> dict[str, int]:
        rng = random.Random(seed)
        scores: dict[str, int] = {}

        for category_id in CATEGORY_LABELS:
            competency_ids = [
                competency_id
                for competency_id, definition in COMPETENCY_DEFINITIONS.items()
                if definition["category_id"] == category_id
            ]
            level = category_balance[category_id]
            category_scores = self._generate_scores_for_level(level, len(competency_ids), rng)
            for competency_id, score in zip(competency_ids, category_scores, strict=True):
                scores[competency_id] = score

        return scores

    def build_evidence_for_scores(self, scores: dict[str, int]) -> dict[str, dict[str, Any]]:
        evidence_map: dict[str, dict[str, Any]] = {}

        for competency_id, score in scores.items():
            definition = COMPETENCY_DEFINITIONS[competency_id]
            band = self._score_band(score)
            evidence_map[competency_id] = {
                "score": score,
                "evidence_summary": self._build_evidence_summary(definition["label"], band),
                "evidence_episode": self._build_evidence_episode(definition, band),
                "observable_signals": self._build_observable_signals(definition, band),
                "signal_strength": self._build_signal_strength(score),
                "question_tags": list(definition["question_tags"]),
            }

        return evidence_map

    def build_interview_content(
        self,
        competencies: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        interview_content: dict[str, dict[str, Any]] = {}

        for content_id, related_competencies in INTERVIEW_CONTENT_COMPETENCIES.items():
            strength_labels = self._labels_for_score_range(competencies, related_competencies, minimum=4)
            weakness_labels = self._labels_for_score_range(competencies, related_competencies, maximum=2)
            interview_content[content_id] = {
                "summary": self._build_interview_summary(content_id, strength_labels, weakness_labels),
                "core_story": self._build_core_story(content_id, strength_labels, weakness_labels),
                "related_competencies": related_competencies,
                "qa_pairs": [],
                "hidden_signals": self._build_hidden_signals(strength_labels, weakness_labels),
            }

        return interview_content

    def generate_scenario(
        self,
        seed: int | None = None,
        fixed_category_balance: dict[str, str] | None = None,
        template_file_name: str = "frontiersoft_taro.yaml",
    ) -> dict[str, Any]:
        template = copy.deepcopy(self.load_fixed_scenario(template_file_name))
        category_balance = fixed_category_balance or self.generate_category_balance(seed=seed)
        scores = self.generate_competency_scores(category_balance, seed=seed)
        competencies = self.build_evidence_for_scores(scores)

        template["scenario_meta"]["scenario_id"] = self._build_generated_scenario_id(seed)
        template["scenario_meta"]["title"] = f"{template['scenario_meta']['title']} 生成版"
        template["evaluation_profile"]["category_balance"] = category_balance
        template["evaluation_profile"]["competencies"] = competencies
        template["interview_content"] = self.build_interview_content(competencies)

        self.validate_scenario(template)
        return template

    def validate_scenario(self, scenario: dict[str, Any]) -> None:
        required_top_level = {
            "scenario_meta",
            "candidate_profile",
            "company_profile",
            "evaluation_profile",
            "interview_content",
        }
        missing_top_level = required_top_level - set(scenario.keys())
        if missing_top_level:
            raise ValueError(f"Scenario is missing top-level keys: {sorted(missing_top_level)}")

        balance = scenario["evaluation_profile"]["category_balance"]
        self._validate_category_balance(balance)

        competencies = scenario["evaluation_profile"]["competencies"]
        missing_competencies = set(COMPETENCY_DEFINITIONS.keys()) - set(competencies.keys())
        if missing_competencies:
            raise ValueError(f"Scenario is missing competencies: {sorted(missing_competencies)}")

        for competency_id, definition in COMPETENCY_DEFINITIONS.items():
            competency = competencies[competency_id]
            score = competency.get("score")
            if not isinstance(score, int) or not 1 <= score <= 5:
                raise ValueError(f"Invalid score for competency: {competency_id}")

            expected_level = balance[definition["category_id"]]
            if expected_level == "high" and score not in {4, 5}:
                raise ValueError(f"High category score out of range for competency: {competency_id}")
            if expected_level == "middle" and score not in {2, 3, 4}:
                raise ValueError(f"Middle category score out of range for competency: {competency_id}")
            if expected_level == "low" and score not in {1, 2}:
                raise ValueError(f"Low category score out of range for competency: {competency_id}")

            if not competency.get("evidence_summary"):
                raise ValueError(f"Missing evidence_summary for competency: {competency_id}")
            if not competency.get("evidence_episode"):
                raise ValueError(f"Missing evidence_episode for competency: {competency_id}")

        interview_content = scenario["interview_content"]
        missing_content = set(INTERVIEW_CONTENT_COMPETENCIES.keys()) - set(interview_content.keys())
        if missing_content:
            raise ValueError(f"Scenario is missing interview content blocks: {sorted(missing_content)}")

        for content_id, content in interview_content.items():
            if "qa_pairs" not in content or not isinstance(content["qa_pairs"], list):
                raise ValueError(f"Interview content must include qa_pairs list: {content_id}")
            if not content.get("summary"):
                raise ValueError(f"Interview content must include summary: {content_id}")
            if not content.get("core_story"):
                raise ValueError(f"Interview content must include core_story: {content_id}")

    def _generate_scores_for_level(self, level: str, count: int, rng: random.Random) -> list[int]:
        if level == "high":
            scores = [rng.choice([4, 5]) for _ in range(count)]
            return self._ensure_variation(scores, allowed={4, 5})
        if level == "low":
            scores = [rng.choice([1, 2]) for _ in range(count)]
            return self._ensure_variation(scores, allowed={1, 2})
        if level == "middle":
            scores = [3] * count
            variant_count = 1 if count <= 2 else max(1, count // 2 - 1)
            indexes = rng.sample(range(count), k=variant_count)
            for index in indexes:
                scores[index] = rng.choice([2, 4])
            return scores
        raise ValueError(f"Unknown level: {level}")

    @staticmethod
    def _ensure_variation(scores: list[int], allowed: set[int]) -> list[int]:
        if len(scores) > 1 and len(set(scores)) == 1 and len(allowed) > 1:
            alternative = next(value for value in allowed if value != scores[0])
            scores[-1] = alternative
        return scores

    @staticmethod
    def _score_band(score: int) -> str:
        if score >= 4:
            return "high"
        if score == 3:
            return "middle"
        return "low"

    @staticmethod
    def _build_signal_strength(score: int) -> str:
        if score in {1, 5}:
            return "strong"
        if score == 3:
            return "medium"
        return "weak"

    @staticmethod
    def _build_evidence_summary(label: str, band: str) -> str:
        if band == "high":
            return f"{label}は強みとして表れやすい。"
        if band == "middle":
            return f"{label}は一定水準にあるが、突出はしていない。"
        return f"{label}は課題として表れやすい。"

    @staticmethod
    def _build_evidence_episode(definition: dict[str, Any], band: str) -> str:
        if band == "high":
            behavior = definition["high_behavior"]
            ending = f"その結果、{definition['label']}の高さが見えた。"
        elif band == "middle":
            behavior = definition["middle_behavior"]
            ending = f"そのため、{definition['label']}は平均的な水準といえる。"
        else:
            behavior = definition["low_behavior"]
            ending = f"そのため、{definition['label']}には改善余地が残る。"
        return f"{definition['situation']}で、{behavior}。{ending}"

    @staticmethod
    def _build_observable_signals(definition: dict[str, Any], band: str) -> list[str]:
        if band == "high":
            return [definition["high_signal"]]
        if band == "middle":
            return [definition["high_signal"], definition["low_signal"]]
        return [definition["low_signal"]]

    @staticmethod
    def _build_generated_scenario_id(seed: int | None) -> str:
        suffix = f"seed_{seed}" if seed is not None else "generated"
        return f"frontiersoft_taro_{suffix}"

    @staticmethod
    def _validate_category_balance(balance: dict[str, str]) -> None:
        expected_categories = set(CATEGORY_LABELS.keys())
        if set(balance.keys()) != expected_categories:
            raise ValueError("Category balance must contain action, thinking, teamwork.")
        levels = list(balance.values())
        if sorted(levels) != ["high", "low", "middle"]:
            raise ValueError("Category balance must contain high, middle, low exactly once.")

    @staticmethod
    def _labels_for_score_range(
        competencies: dict[str, dict[str, Any]],
        related_competencies: list[str],
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> list[str]:
        labels: list[str] = []
        for competency_id in related_competencies:
            score = competencies[competency_id]["score"]
            if minimum is not None and score < minimum:
                continue
            if maximum is not None and score > maximum:
                continue
            labels.append(COMPETENCY_DEFINITIONS[competency_id]["label"])
        return labels

    @staticmethod
    def _join_labels(labels: list[str]) -> str:
        if not labels:
            return ""
        if len(labels) == 1:
            return labels[0]
        return "、".join(labels[:-1]) + f"と{labels[-1]}"

    def _build_interview_summary(
        self,
        content_id: str,
        strength_labels: list[str],
        weakness_labels: list[str],
    ) -> str:
        strengths = self._join_labels(strength_labels)
        weaknesses = self._join_labels(weakness_labels)
        if strengths and weaknesses:
            return f"{content_id}では、{strengths}が見えやすい一方、{weaknesses}は深掘りすると弱さが出やすい。"
        if strengths:
            return f"{content_id}では、{strengths}が比較的見えやすい。"
        if weaknesses:
            return f"{content_id}では、{weaknesses}の弱さが見えやすい。"
        return f"{content_id}では、全体として平均的な受け答えになる。"

    def _build_core_story(
        self,
        content_id: str,
        strength_labels: list[str],
        weakness_labels: list[str],
    ) -> str:
        strengths = self._join_labels(strength_labels)
        weaknesses = self._join_labels(weakness_labels)
        if strengths and weaknesses:
            return f"{content_id}に関する受け答えでは、{strengths}を支える経験を語れるが、{weaknesses}は詰めが甘い形で表れる。"
        if strengths:
            return f"{content_id}に関する受け答えでは、{strengths}につながる経験を比較的具体的に話せる。"
        if weaknesses:
            return f"{content_id}に関する受け答えでは、{weaknesses}の弱さがにじむ。"
        return f"{content_id}に関する受け答えでは、突出した特徴は出にくい。"

    @staticmethod
    def _build_hidden_signals(strength_labels: list[str], weakness_labels: list[str]) -> list[str]:
        signals: list[str] = []
        if strength_labels:
            signals.append(f"{'、'.join(strength_labels)}は会話の中で比較的見えやすい。")
        if weakness_labels:
            signals.append(f"{'、'.join(weakness_labels)}は深掘りすると甘さが見える。")
        if not signals:
            signals.append("大きな偏りは少なく、平均的な受け答えになる。")
        return signals
