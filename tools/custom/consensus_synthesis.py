"""
Consensus Synthesis Engine.

Aggregates multiple model perspectives, identifies consensus and disagreements,
and generates executive summaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Perspective:
    """Single perspective from a role-model combination."""

    role: str
    model: str
    analysis: str
    key_points: List[str]
    concerns: List[str]
    recommendations: List[str]


@dataclass
class ConsensusResult:
    """Complete consensus analysis result."""

    prompt: str
    level: int
    domain: str
    perspectives: List[Perspective]
    consensus_points: List[str]
    disagreements: List[Dict[str, any]]
    synthesis: str
    executive_summary: str
    models_used: List[str]
    total_cost: float
    metadata: Dict[str, any]


class SynthesisEngine:
    """
    Generates consensus analysis from multiple model perspectives.

    Identifies:
    - Points of consensus (agreement across perspectives)
    - Points of disagreement (conflicting viewpoints)
    - Key insights from each professional role
    - Executive summary with actionable recommendations
    """

    def __init__(self):
        """Initialize synthesis engine."""
        self.perspectives: List[Perspective] = []

    def add_perspective(
        self,
        role: str,
        model: str,
        analysis: str,
        key_points: Optional[List[str]] = None,
        concerns: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
    ):
        """
        Add a perspective from a role-model combination.

        Args:
            role: Professional role name
            model: Model name that provided the analysis
            analysis: Full analysis text
            key_points: Key points identified (extracted if None)
            concerns: Concerns raised (extracted if None)
            recommendations: Recommendations provided (extracted if None)
        """
        # Extract structured data if not provided
        if key_points is None:
            key_points = self._extract_key_points(analysis)
        if concerns is None:
            concerns = self._extract_concerns(analysis)
        if recommendations is None:
            recommendations = self._extract_recommendations(analysis)

        perspective = Perspective(
            role=role,
            model=model,
            analysis=analysis,
            key_points=key_points,
            concerns=concerns,
            recommendations=recommendations,
        )

        self.perspectives.append(perspective)

    def generate_consensus(
        self,
        prompt: str,
        level: int,
        domain: str,
        models_used: List[str],
        total_cost: float,
    ) -> ConsensusResult:
        """
        Generate complete consensus analysis from all perspectives.

        Args:
            prompt: Original user prompt
            level: Organizational level used
            domain: Domain type used
            models_used: List of all models consulted
            total_cost: Total cost of consensus analysis

        Returns:
            ConsensusResult with complete analysis
        """
        # Identify consensus points
        consensus_points = self._identify_consensus_points()

        # Identify disagreements
        disagreements = self._identify_disagreements()

        # Generate synthesis
        synthesis = self._generate_synthesis(consensus_points, disagreements)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(consensus_points, disagreements)

        return ConsensusResult(
            prompt=prompt,
            level=level,
            domain=domain,
            perspectives=self.perspectives,
            consensus_points=consensus_points,
            disagreements=disagreements,
            synthesis=synthesis,
            executive_summary=executive_summary,
            models_used=models_used,
            total_cost=total_cost,
            metadata={
                "perspective_count": len(self.perspectives),
                "unique_roles": len(set(p.role for p in self.perspectives)),
                "unique_models": len(set(p.model for p in self.perspectives)),
            },
        )

    def _extract_key_points(self, analysis: str) -> List[str]:
        """
        Extract key points from analysis text.

        Simple extraction - looks for bullet points, numbered lists, etc.

        Args:
            analysis: Analysis text

        Returns:
            List of key points
        """
        key_points = []

        # Split into lines and look for bullet points or numbered items
        lines = analysis.split('\n')
        for line in lines:
            line = line.strip()
            # Match bullets (-, *, •) or numbers (1., 2., etc.)
            if line.startswith(('-', '*', '•')) or (len(line) > 2 and line[0].isdigit() and line[1:3] in ['. ', ') ']):
                # Remove bullet/number prefix
                point = line.lstrip('-*•0123456789.) ').strip()
                if point and len(point) > 10:  # Filter out very short items
                    key_points.append(point)

        # If no structured points found, take first few sentences
        if not key_points:
            sentences = [s.strip() for s in analysis.split('.') if s.strip()]
            key_points = sentences[:3]

        return key_points[:5]  # Limit to top 5

    def _extract_concerns(self, analysis: str) -> List[str]:
        """
        Extract concerns from analysis text.

        Args:
            analysis: Analysis text

        Returns:
            List of concerns
        """
        concerns = []

        # Look for concern indicators
        concern_keywords = [
            'concern', 'risk', 'issue', 'problem', 'warning',
            'caution', 'danger', 'vulnerability', 'weakness'
        ]

        lines = analysis.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in concern_keywords):
                concern = line.strip().lstrip('-*•0123456789.) ')
                if concern and len(concern) > 10:
                    concerns.append(concern)

        return concerns[:5]  # Limit to top 5

    def _extract_recommendations(self, analysis: str) -> List[str]:
        """
        Extract recommendations from analysis text.

        Args:
            analysis: Analysis text

        Returns:
            List of recommendations
        """
        recommendations = []

        # Look for recommendation indicators
        rec_keywords = [
            'recommend', 'suggest', 'should', 'propose',
            'advise', 'consider', 'implement', 'adopt'
        ]

        lines = analysis.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in rec_keywords):
                rec = line.strip().lstrip('-*•0123456789.) ')
                if rec and len(rec) > 10:
                    recommendations.append(rec)

        return recommendations[:5]  # Limit to top 5

    def _identify_consensus_points(self) -> List[str]:
        """
        Identify points where multiple perspectives agree.

        Returns:
            List of consensus points
        """
        if not self.perspectives:
            return []

        consensus_points = []

        # Collect all key points from all perspectives
        all_key_points = []
        for perspective in self.perspectives:
            all_key_points.extend(perspective.key_points)

        # Find common themes (simplified - real implementation would use NLP)
        # For now, look for key points mentioned by multiple perspectives
        from collections import Counter

        # Count similar points (very simple - just exact matches)
        point_counts = Counter(all_key_points)

        # Consensus = mentioned by at least 1/3 of perspectives
        consensus_threshold = max(2, len(self.perspectives) // 3)

        for point, count in point_counts.most_common(10):
            if count >= consensus_threshold:
                consensus_points.append(f"{point} (mentioned by {count}/{len(self.perspectives)} perspectives)")

        # If no exact matches, add top concerns/recommendations
        if not consensus_points:
            all_concerns = []
            all_recommendations = []

            for perspective in self.perspectives:
                all_concerns.extend(perspective.concerns)
                all_recommendations.extend(perspective.recommendations)

            if all_concerns:
                concern_counts = Counter(all_concerns)
                top_concern = concern_counts.most_common(1)[0][0]
                consensus_points.append(f"Common concern: {top_concern}")

            if all_recommendations:
                rec_counts = Counter(all_recommendations)
                top_rec = rec_counts.most_common(1)[0][0]
                consensus_points.append(f"Common recommendation: {top_rec}")

        return consensus_points[:10]  # Limit to top 10

    def _identify_disagreements(self) -> List[Dict[str, any]]:
        """
        Identify points where perspectives disagree.

        Returns:
            List of disagreement descriptions
        """
        if len(self.perspectives) < 2:
            return []

        disagreements = []

        # Group perspectives by role category
        role_groups = {}
        for perspective in self.perspectives:
            # Categorize roles
            if 'security' in perspective.role.lower():
                category = 'security'
            elif 'architect' in perspective.role.lower():
                category = 'architecture'
            elif 'developer' in perspective.role.lower():
                category = 'development'
            elif 'director' in perspective.role.lower() or 'lead' in perspective.role.lower():
                category = 'leadership'
            else:
                category = 'validation'

            if category not in role_groups:
                role_groups[category] = []
            role_groups[category].append(perspective)

        # Compare concerns between role categories
        if len(role_groups) >= 2:
            categories = list(role_groups.keys())
            for i, cat1 in enumerate(categories):
                for cat2 in categories[i + 1:]:
                    # Compare concerns between these categories
                    cat1_concerns = set()
                    for p in role_groups[cat1]:
                        cat1_concerns.update(p.concerns)

                    cat2_concerns = set()
                    for p in role_groups[cat2]:
                        cat2_concerns.update(p.concerns)

                    # Find unique concerns
                    unique_to_cat1 = cat1_concerns - cat2_concerns
                    unique_to_cat2 = cat2_concerns - cat1_concerns

                    if unique_to_cat1 or unique_to_cat2:
                        disagreement = {
                            "category1": cat1,
                            "category2": cat2,
                            "unique_to_category1": list(unique_to_cat1)[:3],
                            "unique_to_category2": list(unique_to_cat2)[:3],
                        }
                        disagreements.append(disagreement)

        return disagreements[:5]  # Limit to top 5

    def _generate_synthesis(self, consensus_points: List[str], disagreements: List[Dict[str, any]]) -> str:
        """
        Generate synthesis of all perspectives.

        Args:
            consensus_points: Identified consensus points
            disagreements: Identified disagreements

        Returns:
            Synthesis text
        """
        synthesis_parts = []

        # Overview
        synthesis_parts.append(
            f"## Consensus Analysis\n\n"
            f"Analyzed perspectives from {len(self.perspectives)} professional roles "
            f"using {len(set(p.model for p in self.perspectives))} AI models.\n"
        )

        # Consensus points
        if consensus_points:
            synthesis_parts.append("\n### Points of Consensus\n")
            for i, point in enumerate(consensus_points, 1):
                synthesis_parts.append(f"{i}. {point}")
        else:
            synthesis_parts.append("\n### Points of Consensus\n")
            synthesis_parts.append("No strong consensus identified across all perspectives.")

        # Disagreements
        if disagreements:
            synthesis_parts.append("\n\n### Points of Disagreement\n")
            for i, disagreement in enumerate(disagreements, 1):
                cat1 = disagreement['category1']
                cat2 = disagreement['category2']
                synthesis_parts.append(f"\n**{i}. {cat1.title()} vs {cat2.title()}:**")

                if disagreement['unique_to_category1']:
                    synthesis_parts.append(f"\n{cat1.title()} concerns:")
                    for concern in disagreement['unique_to_category1']:
                        synthesis_parts.append(f"- {concern}")

                if disagreement['unique_to_category2']:
                    synthesis_parts.append(f"\n{cat2.title()} concerns:")
                    for concern in disagreement['unique_to_category2']:
                        synthesis_parts.append(f"- {concern}")
        else:
            synthesis_parts.append("\n\n### Points of Disagreement\n")
            synthesis_parts.append("No major disagreements identified - perspectives are well-aligned.")

        # Role-specific insights
        synthesis_parts.append("\n\n### Role-Specific Insights\n")
        for perspective in self.perspectives:
            if perspective.key_points:
                synthesis_parts.append(f"\n**{perspective.role.replace('_', ' ').title()}:**")
                synthesis_parts.append(f"- {perspective.key_points[0]}")

        return '\n'.join(synthesis_parts)

    def _generate_executive_summary(self, consensus_points: List[str], disagreements: List[Dict[str, any]]) -> str:
        """
        Generate executive summary with actionable recommendations.

        Args:
            consensus_points: Identified consensus points
            disagreements: Identified disagreements

        Returns:
            Executive summary text
        """
        summary_parts = []

        summary_parts.append("## Executive Summary\n")

        # Overall assessment
        if consensus_points and not disagreements:
            summary_parts.append("**Overall Assessment:** Strong consensus across all perspectives.\n")
        elif consensus_points and disagreements:
            summary_parts.append("**Overall Assessment:** General consensus with some areas of disagreement.\n")
        elif not consensus_points and disagreements:
            summary_parts.append("**Overall Assessment:** Significant disagreements across perspectives.\n")
        else:
            summary_parts.append("**Overall Assessment:** Perspectives are aligned but highlight different priorities.\n")

        # Key takeaways
        summary_parts.append("\n**Key Takeaways:**\n")
        if consensus_points:
            for i, point in enumerate(consensus_points[:3], 1):
                # Remove the count suffix for cleaner summary
                clean_point = point.split(' (mentioned by')[0]
                summary_parts.append(f"{i}. {clean_point}")
        else:
            summary_parts.append("1. Each professional role highlighted different priorities")
            summary_parts.append("2. Consider all perspectives when making final decision")

        # Critical concerns
        all_concerns = []
        for perspective in self.perspectives:
            all_concerns.extend(perspective.concerns)

        if all_concerns:
            summary_parts.append("\n**Critical Concerns:**\n")
            # Get top 3 unique concerns
            unique_concerns = []
            for concern in all_concerns:
                if concern not in unique_concerns:
                    unique_concerns.append(concern)
                if len(unique_concerns) >= 3:
                    break

            for i, concern in enumerate(unique_concerns, 1):
                summary_parts.append(f"{i}. {concern}")

        # Recommendations
        all_recommendations = []
        for perspective in self.perspectives:
            all_recommendations.extend(perspective.recommendations)

        if all_recommendations:
            summary_parts.append("\n**Recommended Actions:**\n")
            # Get top 3 unique recommendations
            unique_recs = []
            for rec in all_recommendations:
                if rec not in unique_recs:
                    unique_recs.append(rec)
                if len(unique_recs) >= 3:
                    break

            for i, rec in enumerate(unique_recs, 1):
                summary_parts.append(f"{i}. {rec}")

        return '\n'.join(summary_parts)

    def clear(self):
        """Clear all perspectives for new analysis."""
        self.perspectives.clear()


def format_consensus_result(result: ConsensusResult, include_full_perspectives: bool = True) -> str:
    """
    Format consensus result for display.

    Args:
        result: ConsensusResult to format
        include_full_perspectives: Whether to include full perspective analyses

    Returns:
        Formatted text
    """
    output_parts = []

    # Header
    output_parts.append("=" * 80)
    output_parts.append(f"CONSENSUS ANALYSIS - Level {result.level} ({result.domain.upper()})")
    output_parts.append("=" * 80)
    output_parts.append(f"\n**Question:** {result.prompt}\n")

    # Executive summary
    output_parts.append(result.executive_summary)

    # Synthesis
    output_parts.append(f"\n\n{result.synthesis}")

    # Full perspectives (optional)
    if include_full_perspectives:
        output_parts.append("\n\n" + "=" * 80)
        output_parts.append("DETAILED PERSPECTIVES")
        output_parts.append("=" * 80)

        for i, perspective in enumerate(result.perspectives, 1):
            output_parts.append(f"\n### {i}. {perspective.role.replace('_', ' ').title()} ({perspective.model})\n")
            output_parts.append(perspective.analysis)
            output_parts.append("\n" + "-" * 80)

    # Metadata
    output_parts.append(f"\n\n**Metadata:**")
    output_parts.append(f"- Models consulted: {len(result.models_used)}")
    output_parts.append(f"- Unique perspectives: {result.metadata['perspective_count']}")
    output_parts.append(f"- Professional roles: {result.metadata['unique_roles']}")
    output_parts.append(f"- Estimated cost: ${result.total_cost:.4f}")

    return '\n'.join(output_parts)
