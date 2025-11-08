"""
Session Reporter - Comprehensive analytics and reporting for completed onboarding sessions
Generates detailed reports with router performance, engagement metrics, and insights
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

from selfology_bot.database.onboarding_dao import OnboardingDAO


class SessionReportGenerator:
    """Generates comprehensive reports for completed onboarding sessions"""

    def __init__(self, onboarding_dao: OnboardingDAO, reports_dir: str = "reports/sessions"):
        self.dao = onboarding_dao
        self.reports_dir = Path(reports_dir)

    async def generate_session_report(
        self,
        session_id: int,
        user_id: int,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive session report

        Args:
            session_id: Session ID
            user_id: User ID
            session_data: Session context data from orchestrator

        Returns:
            Complete report dictionary
        """
        # Collect data from DB
        answers = await self.dao.get_session_answers(session_id)
        ai_insights = await self.dao.get_session_analysis_insights(session_id)

        # Build report sections
        report = {
            "session_info": self._build_session_info(session_id, user_id, session_data),
            "participation": self._analyze_participation(answers, session_data),
            "router_performance": self._analyze_router_performance(session_data, answers),
            "domain_analysis": self._analyze_domains(answers, ai_insights),
            "depth_progression": self._analyze_depth_progression(answers),
            "engagement_trends": self._analyze_engagement(answers, ai_insights),
            "special_moments": self._identify_special_moments(ai_insights, answers),
            "insights": self._generate_insights(answers, ai_insights, session_data),
            "generated_at": datetime.now().isoformat()
        }

        return report

    def _build_session_info(
        self,
        session_id: int,
        user_id: int,
        session_data: Dict
    ) -> Dict[str, Any]:
        """Basic session metadata"""
        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": session_data.get("status", "unknown"),
            "total_questions_asked": session_data.get("questions_asked", 0),
            "started_at": session_data.get("started_at"),
            "completed_at": datetime.now().isoformat()
        }

    def _analyze_participation(
        self,
        answers: List[Dict],
        session_data: Dict
    ) -> Dict[str, Any]:
        """Analyze user participation metrics"""
        total_asked = session_data.get("questions_asked", 0)
        answered = len([a for a in answers if a.get("is_answered")])
        skipped = len([a for a in answers if a.get("is_skipped")])

        avg_answer_length = 0
        if answered > 0:
            total_length = sum(len(a.get("answer_text", "")) for a in answers if a.get("is_answered"))
            avg_answer_length = total_length / answered

        return {
            "questions_asked": total_asked,
            "questions_answered": answered,
            "questions_skipped": skipped,
            "answer_rate": round(answered / total_asked * 100, 1) if total_asked > 0 else 0,
            "avg_answer_length": round(avg_answer_length, 1),
            "completion_percentage": session_data.get("completion_percentage", 0)
        }

    def _analyze_router_performance(
        self,
        session_data: Dict,
        answers: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze router decision-making performance"""
        # Extract router events from session_data
        router_events = session_data.get("router_events", [])

        # Count strategy usage
        strategy_counter = Counter()
        fallback_count = 0
        flagged_filtered = 0

        for event in router_events:
            if event.get("type") == "strategy_selected":
                strategy_counter[event.get("strategy")] += 1
            elif event.get("type") == "fallback_used":
                fallback_count += 1
            elif event.get("type") == "flagged_filtered":
                flagged_filtered += event.get("count", 0)

        return {
            "strategies_used": dict(strategy_counter),
            "fallback_count": fallback_count,
            "flagged_questions_filtered": flagged_filtered,
            "avg_candidates_per_selection": self._calc_avg_candidates(router_events)
        }

    def _analyze_domains(
        self,
        answers: List[Dict],
        ai_insights: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze domain coverage and interest levels"""
        domain_stats = defaultdict(lambda: {
            "questions_asked": 0,
            "questions_answered": 0,
            "avg_quality": 0,
            "quality_scores": [],
            "emotional_count": 0,
            "breakthroughs": 0,
            "crisis": 0
        })

        # Create insight lookup by question_id
        insights_by_question = {
            insight["question_json_id"]: insight
            for insight in ai_insights
        }

        for answer in answers:
            domain = answer.get("domain", "UNKNOWN")
            stats = domain_stats[domain]

            stats["questions_asked"] += 1
            if answer.get("is_answered"):
                stats["questions_answered"] += 1

                # Get AI insights for this answer
                insight = insights_by_question.get(answer.get("question_json_id"))
                if insight:
                    quality = insight.get("quality_score", 0)
                    stats["quality_scores"].append(quality)

                    emotional = insight.get("emotional_state", "")
                    if emotional and emotional != "neutral":
                        stats["emotional_count"] += 1

                    special = insight.get("special_situation", "")
                    if special == "breakthrough":
                        stats["breakthroughs"] += 1
                    elif special == "crisis":
                        stats["crisis"] += 1

        # Calculate averages
        domain_analysis = {}
        for domain, stats in domain_stats.items():
            if stats["quality_scores"]:
                stats["avg_quality"] = round(
                    sum(stats["quality_scores"]) / len(stats["quality_scores"]),
                    2
                )
            else:
                stats["avg_quality"] = 0

            # Remove raw scores list (keep only average)
            stats.pop("quality_scores")
            domain_analysis[domain] = stats

        return {
            "domains_covered": len(domain_stats),
            "domain_breakdown": domain_analysis,
            "most_engaged_domain": self._find_top_domain(domain_analysis, "avg_quality"),
            "most_emotional_domain": self._find_top_domain(domain_analysis, "emotional_count")
        }

    def _analyze_depth_progression(self, answers: List[Dict]) -> Dict[str, Any]:
        """Analyze progression through depth levels"""
        depth_counter = Counter()
        depth_sequence = []

        for answer in answers:
            depth = answer.get("depth_level", "UNKNOWN")
            depth_counter[depth] += 1
            depth_sequence.append(depth)

        return {
            "depth_distribution": dict(depth_counter),
            "deepest_level_reached": self._get_deepest_level(depth_sequence),
            "depth_progression_smooth": self._check_smooth_progression(depth_sequence)
        }

    def _analyze_engagement(
        self,
        answers: List[Dict],
        ai_insights: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze engagement trends over session"""
        insights_by_question = {
            insight["question_json_id"]: insight
            for insight in ai_insights
        }

        quality_trend = []
        confidence_trend = []

        for answer in answers:
            if answer.get("is_answered"):
                insight = insights_by_question.get(answer.get("question_json_id"))
                if insight:
                    quality_trend.append(insight.get("quality_score", 0))
                    confidence_trend.append(insight.get("confidence_score", 0))

        return {
            "avg_quality_score": round(sum(quality_trend) / len(quality_trend), 2) if quality_trend else 0,
            "avg_confidence_score": round(sum(confidence_trend) / len(confidence_trend), 2) if confidence_trend else 0,
            "quality_trend": "increasing" if self._is_increasing(quality_trend) else "stable",
            "engagement_stable": self._check_stability(quality_trend)
        }

    def _identify_special_moments(
        self,
        ai_insights: List[Dict],
        answers: List[Dict]
    ) -> Dict[str, Any]:
        """Identify breakthrough moments and crisis points"""
        breakthroughs = []
        crisis_points = []

        # Create answer lookup
        answers_by_question = {
            answer["question_json_id"]: answer
            for answer in answers
        }

        for insight in ai_insights:
            special = insight.get("special_situation", "")
            question_id = insight["question_json_id"]
            answer = answers_by_question.get(question_id, {})

            moment = {
                "question_id": question_id,
                "domain": answer.get("domain", "UNKNOWN"),
                "emotional_state": insight.get("emotional_state", ""),
                "quality_score": insight.get("quality_score", 0)
            }

            if special == "breakthrough":
                breakthroughs.append(moment)
            elif special == "crisis":
                crisis_points.append(moment)

        return {
            "breakthroughs": breakthroughs,
            "crisis_points": crisis_points,
            "total_special_moments": len(breakthroughs) + len(crisis_points)
        }

    def _generate_insights(
        self,
        answers: List[Dict],
        ai_insights: List[Dict],
        session_data: Dict
    ) -> Dict[str, Any]:
        """Generate actionable insights for next session"""
        insights = {
            "strengths": [],
            "areas_for_exploration": [],
            "recommended_domains": [],
            "recommended_depth": None,
            "energy_balance": None
        }

        # Analyze domain interest
        domain_quality = defaultdict(list)
        for insight in ai_insights:
            answer = next((a for a in answers if a["question_json_id"] == insight["question_json_id"]), None)
            if answer:
                domain = answer.get("domain", "UNKNOWN")
                domain_quality[domain].append(insight.get("quality_score", 0))

        # Find high-interest domains
        for domain, scores in domain_quality.items():
            avg = sum(scores) / len(scores) if scores else 0
            if avg > 0.7:
                insights["strengths"].append(f"High engagement in {domain}")
                insights["recommended_domains"].append(domain)

        # Find unexplored domains
        all_domains = ["IDENTITY", "WORK", "RELATIONSHIPS", "EMOTIONS", "VALUES", "BODY", "CRISIS"]
        explored = set(domain_quality.keys())
        unexplored = set(all_domains) - explored
        if unexplored:
            insights["areas_for_exploration"] = list(unexplored)

        # Recommend depth
        depth_counter = Counter(a.get("depth_level") for a in answers)
        if depth_counter.get("CORE", 0) > 0:
            insights["recommended_depth"] = "CORE"
        elif depth_counter.get("SHADOW", 0) > 0:
            insights["recommended_depth"] = "SHADOW"
        else:
            insights["recommended_depth"] = "EDGE"

        return insights

    # Helper methods

    def _calc_avg_candidates(self, router_events: List[Dict]) -> float:
        """Calculate average candidates per selection"""
        candidate_counts = [
            event.get("candidate_count", 0)
            for event in router_events
            if event.get("type") == "candidates_found"
        ]
        if candidate_counts:
            return round(sum(candidate_counts) / len(candidate_counts), 1)
        return 0

    def _find_top_domain(self, domain_analysis: Dict, metric: str) -> str:
        """Find domain with highest metric value"""
        if not domain_analysis:
            return "NONE"

        top_domain = max(
            domain_analysis.items(),
            key=lambda x: x[1].get(metric, 0)
        )
        return top_domain[0]

    def _get_deepest_level(self, depth_sequence: List[str]) -> str:
        """Get deepest level reached in session"""
        depth_order = ["SURFACE", "CONSCIOUS", "EDGE", "SHADOW", "CORE"]
        reached = set(depth_sequence)
        for depth in reversed(depth_order):
            if depth in reached:
                return depth
        return "SURFACE"

    def _check_smooth_progression(self, depth_sequence: List[str]) -> bool:
        """Check if depth progression was smooth (no big jumps)"""
        depth_map = {"SURFACE": 1, "CONSCIOUS": 2, "EDGE": 3, "SHADOW": 4, "CORE": 5}
        numeric_sequence = [depth_map.get(d, 0) for d in depth_sequence]

        # Check for jumps > 2 levels
        for i in range(1, len(numeric_sequence)):
            if abs(numeric_sequence[i] - numeric_sequence[i-1]) > 2:
                return False
        return True

    def _is_increasing(self, trend: List[float]) -> bool:
        """Check if trend is generally increasing"""
        if len(trend) < 3:
            return False

        first_half_avg = sum(trend[:len(trend)//2]) / (len(trend)//2)
        second_half_avg = sum(trend[len(trend)//2:]) / (len(trend) - len(trend)//2)

        return second_half_avg > first_half_avg

    def _check_stability(self, trend: List[float]) -> bool:
        """Check if engagement remained stable (no dramatic drops)"""
        if len(trend) < 2:
            return True

        # Check for drops > 0.3
        for i in range(1, len(trend)):
            if trend[i-1] - trend[i] > 0.3:
                return False
        return True

    async def save_report_files(
        self,
        report: Dict[str, Any],
        user_id: int,
        session_id: int
    ) -> Dict[str, str]:
        """
        Save report to JSON and Markdown files

        Returns:
            Dict with file paths
        """
        # Create user directory
        user_dir = self.reports_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = user_dir / f"session_{session_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Save Markdown
        md_path = user_dir / f"session_{session_id}.md"
        markdown_content = self._format_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return {
            "json": str(json_path),
            "markdown": str(md_path)
        }

    def _format_markdown(self, report: Dict[str, Any]) -> str:
        """Format report as human-readable Markdown"""
        md = []

        # Header
        session_info = report["session_info"]
        md.append(f"# 📊 Session Report #{session_info['session_id']}")
        md.append(f"**User:** {session_info['user_id']}")
        md.append(f"**Status:** {session_info['status']}")
        md.append(f"**Completed:** {session_info['completed_at']}")
        md.append("")

        # Participation
        part = report["participation"]
        md.append("## 👤 Participation")
        md.append(f"- Questions asked: {part['questions_asked']}")
        md.append(f"- Answered: {part['questions_answered']} ({part['answer_rate']}%)")
        md.append(f"- Skipped: {part['questions_skipped']}")
        md.append(f"- Avg answer length: {part['avg_answer_length']} chars")
        md.append(f"- Completion: {part['completion_percentage']}%")
        md.append("")

        # Router Performance
        router = report["router_performance"]
        md.append("## 🎯 Router Performance")
        md.append(f"**Strategies used:**")
        for strategy, count in router["strategies_used"].items():
            md.append(f"- {strategy}: {count}")
        md.append(f"- Fallbacks: {router['fallback_count']}")
        md.append(f"- Flagged filtered: {router['flagged_questions_filtered']}")
        md.append("")

        # Domain Analysis
        domains = report["domain_analysis"]
        md.append("## 🗺️ Domain Coverage")
        md.append(f"**Covered:** {domains['domains_covered']} domains")
        md.append(f"**Most engaged:** {domains['most_engaged_domain']}")
        md.append(f"**Most emotional:** {domains['most_emotional_domain']}")
        md.append("")

        # Special Moments
        special = report["special_moments"]
        if special["total_special_moments"] > 0:
            md.append("## ✨ Special Moments")
            md.append(f"- Breakthroughs: {len(special['breakthroughs'])}")
            md.append(f"- Crisis points: {len(special['crisis_points'])}")
            md.append("")

        # Insights
        insights = report["insights"]
        md.append("## 💡 Insights")
        if insights["strengths"]:
            md.append("**Strengths:**")
            for strength in insights["strengths"]:
                md.append(f"- {strength}")
        if insights["recommended_domains"]:
            md.append(f"**Recommended domains:** {', '.join(insights['recommended_domains'])}")
        md.append(f"**Recommended depth:** {insights['recommended_depth']}")
        md.append("")

        return "\n".join(md)

    def format_telegram_digest(self, report: Dict[str, Any]) -> str:
        """Format brief digest for Telegram notification"""
        part = report["participation"]
        domains = report["domain_analysis"]
        special = report["special_moments"]

        digest = [
            "🎉 <b>Сессия онбординга завершена!</b>\n",
            f"📊 <b>Участие:</b> {part['questions_answered']}/{part['questions_asked']} ответов ({part['answer_rate']}%)",
            f"🗺️ <b>Домены:</b> исследовано {domains['domains_covered']}, лучший — {domains['most_engaged_domain']}",
        ]

        if special["total_special_moments"] > 0:
            digest.append(f"✨ <b>Особые моменты:</b> {len(special['breakthroughs'])} прорывов, {len(special['crisis_points'])} кризисов")

        engagement = report["engagement_trends"]
        digest.append(f"📈 <b>Вовлеченность:</b> {engagement['avg_quality_score']:.1f}/1.0 ({engagement['quality_trend']})")

        return "\n".join(digest)
