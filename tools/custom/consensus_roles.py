"""
Consensus Role Definitions and Domain Mappings.

Provides role assignments for different organizational levels and domains,
enabling easy creation of domain-specific consensus tools.
"""

from __future__ import annotations

from typing import Dict, List

# Professional role definitions with focus areas and perspectives
ROLE_DEFINITIONS: Dict[str, Dict[str, str]] = {
    # Level 1 Roles (Foundation - Free tier)
    "code_reviewer": {
        "focus": "Code quality, standards, maintainability",
        "questions": "Security vulnerabilities? Performance impacts? Technical debt? Best practices compliance?",
        "perspective": "Critical analysis of implementation quality and maintainability",
    },
    "security_checker": {
        "focus": "Security implications, threat modeling, compliance",
        "questions": "Security risks? Compliance issues? Attack vectors? Data protection concerns?",
        "perspective": "Security-first analysis with threat assessment",
    },
    "technical_validator": {
        "focus": "Technical feasibility, implementation complexity",
        "questions": "Is this technically sound? Implementation challenges? Resource requirements?",
        "perspective": "Practical validation of technical approach",
    },
    # Level 2 Roles (Professional - Economy tier)
    "senior_developer": {
        "focus": "Development best practices, team impact, productivity",
        "questions": "Team productivity impact? Development complexity? Maintenance overhead?",
        "perspective": "Senior developer's practical implementation concerns",
    },
    "system_architect": {
        "focus": "System design, scalability, integration patterns",
        "questions": "Architecture fit? Scalability concerns? Integration complexity? Design patterns?",
        "perspective": "Architectural and system design evaluation",
    },
    "devops_engineer": {
        "focus": "Deployment, operations, monitoring, infrastructure",
        "questions": "Deployment complexity? Operational overhead? Monitoring requirements? Infrastructure impact?",
        "perspective": "Operations and infrastructure impact assessment",
    },
    # Level 3 Roles (Executive - Premium tier)
    "lead_architect": {
        "focus": "Strategic technical direction, enterprise architecture",
        "questions": "Strategic alignment? Enterprise impact? Long-term technical debt? Portfolio fit?",
        "perspective": "Strategic technical leadership perspective",
    },
    "technical_director": {
        "focus": "Executive technical decisions, business alignment",
        "questions": "Business value? Technical risk? Resource allocation? Strategic impact?",
        "perspective": "Executive technical decision-making viewpoint",
    },
    # Additional domain-specific roles
    "vulnerability_scanner": {
        "focus": "Vulnerability detection, attack surface analysis",
        "questions": "Known vulnerabilities? Attack surface? Exploit potential? Patch status?",
        "perspective": "Vulnerability assessment and risk quantification",
    },
    "compliance_validator": {
        "focus": "Regulatory compliance, policy adherence",
        "questions": "Compliance requirements? Regulatory risks? Policy violations? Audit concerns?",
        "perspective": "Compliance and regulatory evaluation",
    },
    "penetration_tester": {
        "focus": "Active security testing, exploit validation",
        "questions": "Exploitable weaknesses? Attack scenarios? Defense effectiveness? Security controls?",
        "perspective": "Offensive security and penetration testing viewpoint",
    },
    "security_architect": {
        "focus": "Security architecture, defense in depth",
        "questions": "Security architecture? Defense layers? Trust boundaries? Encryption strategy?",
        "perspective": "Security architecture and design patterns",
    },
    "threat_modeler": {
        "focus": "Threat analysis, risk modeling, attack trees",
        "questions": "Threat actors? Attack paths? Risk levels? Mitigation strategies?",
        "perspective": "Threat modeling and risk analysis",
    },
    "security_director": {
        "focus": "Security strategy, risk management, governance",
        "questions": "Security strategy? Risk appetite? Governance compliance? Security ROI?",
        "perspective": "Executive security leadership and strategy",
    },
    "compliance_officer": {
        "focus": "Compliance strategy, regulatory relationships, audits",
        "questions": "Compliance strategy? Regulatory changes? Audit readiness? Policy effectiveness?",
        "perspective": "Executive compliance leadership",
    },
    "integration_specialist": {
        "focus": "System integration, API design, data flow",
        "questions": "Integration complexity? API design? Data consistency? Service dependencies?",
        "perspective": "Integration architecture and API design",
    },
    "performance_engineer": {
        "focus": "Performance optimization, scalability, load testing",
        "questions": "Performance bottlenecks? Scalability limits? Load characteristics? Optimization opportunities?",
        "perspective": "Performance analysis and optimization",
    },
    "scalability_expert": {
        "focus": "Horizontal scaling, distributed systems, capacity planning",
        "questions": "Scaling strategy? Distributed system challenges? Capacity planning? Resource efficiency?",
        "perspective": "Scalability architecture and planning",
    },
    "enterprise_architect": {
        "focus": "Enterprise integration, portfolio management, technology strategy",
        "questions": "Enterprise alignment? Portfolio impact? Technology strategy? Governance compliance?",
        "perspective": "Enterprise architecture and strategic technology planning",
    },
}

# Domain-specific role assignments per level (additive architecture)
DOMAIN_ROLES: Dict[str, Dict[int, List[str]]] = {
    "code_review": {
        1: ["code_reviewer", "security_checker", "technical_validator"],
        2: [
            # Level 1 roles (ADDITIVE)
            "code_reviewer",
            "security_checker",
            "technical_validator",
            # Level 2 additions
            "senior_developer",
            "system_architect",
            "devops_engineer",
        ],
        3: [
            # Level 1 + 2 roles (ADDITIVE)
            "code_reviewer",
            "security_checker",
            "technical_validator",
            "senior_developer",
            "system_architect",
            "devops_engineer",
            # Level 3 additions
            "lead_architect",
            "technical_director",
        ],
    },
    "security": {
        1: ["security_checker", "vulnerability_scanner", "compliance_validator"],
        2: [
            # Level 1 roles (ADDITIVE)
            "security_checker",
            "vulnerability_scanner",
            "compliance_validator",
            # Level 2 additions
            "penetration_tester",
            "security_architect",
            "threat_modeler",
        ],
        3: [
            # Level 1 + 2 roles (ADDITIVE)
            "security_checker",
            "vulnerability_scanner",
            "compliance_validator",
            "penetration_tester",
            "security_architect",
            "threat_modeler",
            # Level 3 additions
            "security_director",
            "compliance_officer",
        ],
    },
    "architecture": {
        1: ["system_architect", "technical_validator", "integration_specialist"],
        2: [
            # Level 1 roles (ADDITIVE)
            "system_architect",
            "technical_validator",
            "integration_specialist",
            # Level 2 additions
            "lead_architect",
            "performance_engineer",
            "scalability_expert",
        ],
        3: [
            # Level 1 + 2 roles (ADDITIVE)
            "system_architect",
            "technical_validator",
            "integration_specialist",
            "lead_architect",
            "performance_engineer",
            "scalability_expert",
            # Level 3 additions
            "technical_director",
            "enterprise_architect",
        ],
    },
    "general": {
        # Alias for code_review (default domain)
        1: ["code_reviewer", "security_checker", "technical_validator"],
        2: [
            "code_reviewer",
            "security_checker",
            "technical_validator",
            "senior_developer",
            "system_architect",
            "devops_engineer",
        ],
        3: [
            "code_reviewer",
            "security_checker",
            "technical_validator",
            "senior_developer",
            "system_architect",
            "devops_engineer",
            "lead_architect",
            "technical_director",
        ],
    },
}


class RoleAssigner:
    """
    Assigns professional roles to models based on organizational level and domain.

    Implements additive role architecture where higher levels include all lower level roles.
    """

    def __init__(self):
        """Initialize role assigner with domain definitions."""
        self.role_definitions = ROLE_DEFINITIONS
        self.domain_roles = DOMAIN_ROLES

    def get_roles_for_level(self, level: int, domain: str = "code_review") -> List[str]:
        """
        Get professional roles for specified level and domain.

        Args:
            level: Organizational level (1, 2, or 3)
            domain: Domain type (code_review, security, architecture, general)

        Returns:
            List of role names (additive - higher levels include all lower level roles)

        Raises:
            ValueError: If level is invalid or domain not found
        """
        if level not in [1, 2, 3]:
            raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3")

        if domain not in self.domain_roles:
            raise ValueError(
                f"Invalid domain: {domain}. "
                f"Valid domains: {', '.join(self.domain_roles.keys())}"
            )

        return self.domain_roles[domain][level]

    def get_role_definition(self, role: str) -> Dict[str, str]:
        """
        Get definition for a specific role.

        Args:
            role: Role name

        Returns:
            Dictionary with focus, questions, and perspective

        Raises:
            ValueError: If role not found
        """
        if role not in self.role_definitions:
            raise ValueError(
                f"Invalid role: {role}. "
                f"Valid roles: {', '.join(self.role_definitions.keys())}"
            )

        return self.role_definitions[role]

    def get_available_domains(self) -> List[str]:
        """
        Get list of available domains.

        Returns:
            List of domain names
        """
        return list(self.domain_roles.keys())

    def get_available_roles(self) -> List[str]:
        """
        Get list of all defined roles.

        Returns:
            List of role names
        """
        return list(self.role_definitions.keys())

    def validate_role_assignments(self) -> Dict[str, List[str]]:
        """
        Validate that all roles in domain assignments have definitions.

        Returns:
            Dictionary of issues found (empty if validation passes)
        """
        issues = {}

        for domain, levels in self.domain_roles.items():
            for level, roles in levels.items():
                for role in roles:
                    if role not in self.role_definitions:
                        issue_key = f"{domain}.level_{level}"
                        if issue_key not in issues:
                            issues[issue_key] = []
                        issues[issue_key].append(f"Undefined role: {role}")

        return issues


def create_role_prompt(role: str, prompt: str) -> str:
    """
    Create a role-specific prompt for consensus analysis.

    Args:
        role: Role name
        prompt: User's question/proposal

    Returns:
        Enhanced prompt with role context
    """
    assigner = RoleAssigner()
    role_def = assigner.get_role_definition(role)

    return f"""You are acting as a {role.replace('_', ' ')}.

**Your Focus:** {role_def['focus']}

**Key Questions to Address:** {role_def['questions']}

**Your Perspective:** {role_def['perspective']}

**Question/Proposal to Analyze:**
{prompt}

**Instructions:**
1. Analyze the question from your professional role's perspective
2. Address the key questions relevant to your expertise
3. Identify risks, concerns, or opportunities within your domain
4. Provide specific, actionable insights
5. Be concise but thorough - focus on what matters most from your perspective

**Your Analysis:**"""
