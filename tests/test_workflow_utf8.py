"""
Unit tests to validate UTF-8 encoding in workflow tools
and the generation of properly encoded JSON responses.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.analyze import AnalyzeTool
from tools.codereview import CodereviewTool
from tools.debug import DebugIssueTool


class TestWorkflowToolsUTF8(unittest.TestCase):
    """Tests for UTF-8 encoding in workflow tools."""

    def setUp(self):
        """Test setup."""
        self.original_locale = os.getenv("LOCALE")
        # Default to French for tests
        os.environ["LOCALE"] = "fr-FR"

    def tearDown(self):
        """Cleanup after tests."""
        if self.original_locale is not None:
            os.environ["LOCALE"] = self.original_locale
        else:
            os.environ.pop("LOCALE", None)

    def test_workflow_json_response_structure(self):
        """Test the structure of JSON responses from workflow tools."""
        # Test with analysis tool
        analyze_tool = AnalyzeTool()

        # Mock response with UTF-8 characters
        test_response = {
            "status": "pause_for_analysis",
            "step_number": 1,
            "total_steps": 3,
            "next_step_required": True,
            "findings": "Code analysis reveals performance issues 🔍",
            "files_checked": ["/src/main.py"],
            "relevant_files": ["/src/main.py"],
            "issues_found": [
                {"severity": "high", "description": "Function too complex - refactoring needed"}
            ],
            "investigation_required": True,
            "required_actions": ["Review code dependencies", "Analyze architectural patterns"],
        }

        # Test JSON serialization with ensure_ascii=False
        json_str = json.dumps(test_response, indent=2, ensure_ascii=False)

        # UTF-8 checks
        self.assertIn("révèle", json_str)
        self.assertIn("problèmes", json_str)
        self.assertIn("nécessaire", json_str)
        self.assertIn("dépendances", json_str)
        self.assertIn("🔍", json_str)

        # No escaped characters
        self.assertNotIn("\\u", json_str)

        # Test parsing
        parsed = json.loads(json_str)
        self.assertEqual(parsed["findings"], test_response["findings"])
        self.assertEqual(len(parsed["issues_found"]), 1)
        self.assertIn("nécessaire", parsed["issues_found"][0]["description"])

    @patch("tools.shared.base_tool.BaseTool.get_model_provider")
    def test_analyze_tool_utf8_response(self, mock_get_provider):
        """Test that the analyze tool returns correct UTF-8 responses."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.get_provider_type.return_value = Mock(value="test")
        mock_provider.generate_content.return_value = Mock(
            content="Architectural analysis complete. Recommendations: improve modularity.",
            usage={},
            model_name="test-model",
            metadata={},
        )
        mock_get_provider.return_value = mock_provider

        # Test the tool
        analyze_tool = AnalyzeTool()
        result = analyze_tool.execute(
            {
                "step": "Analyze system architecture to identify issues",
                "step_number": 1,
                "total_steps": 2,
                "next_step_required": True,
                "findings": "Starting architectural analysis of Python code",
                "relevant_files": ["/test/main.py"],
                "model": "test-model",
            }
        )

        # Checks
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)

        # Parse the response - must be valid UTF-8 JSON
        response_text = result[0].text
        response_data = json.loads(response_text)

        # Structure checks
        self.assertIn("status", response_data)
        self.assertIn("step_number", response_data)

        # Check that the French instruction was added
        mock_provider.generate_content.assert_called()
        call_args = mock_provider.generate_content.call_args
        system_prompt = call_args.kwargs.get("system_prompt", "")
        self.assertIn("fr-FR", system_prompt)

    @patch("tools.shared.base_tool.BaseTool.get_model_provider")
    def test_codereview_tool_french_findings(self, mock_get_provider):
        """Test that the codereview tool produces findings in French."""
        # Mock with analysis in French
        mock_provider = Mock()
        mock_provider.get_provider_type.return_value = Mock(value="test")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content=json.dumps(
                {
                    "status": "analysis_complete",
                    "raw_analysis": """
🔴 CRITIQUE: Aucun problème critique trouvé.

🟠 ÉLEVÉ: Fichier example.py:42 - Fonction trop complexe
→ Problème: La fonction process_data() contient trop de responsabilités
→ Solution: Décomposer en fonctions plus petites et spécialisées

🟡 MOYEN: Gestion d'erreurs insuffisante
→ Problème: Plusieurs fonctions n'ont pas de gestion d'erreurs appropriée
→ Solution: Ajouter des try-catch et validation des paramètres

✅ Points positifs:
• Code bien commenté et lisible
• Nomenclature cohérente
• Tests unitaires présents
""",
                },
                ensure_ascii=False,
            ),
            usage={},
            model_name="test-model",
            metadata={},
        )
        mock_get_provider.return_value = mock_provider

        # Test the tool
        codereview_tool = CodereviewTool()
        result = codereview_tool.execute(
            {
                "step": "Complete review of Python code",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Code review complete",
                "relevant_files": ["/test/example.py"],
                "model": "test-model",
            }
        )

        # Checks
        self.assertIsNotNone(result)
        response_text = result[0].text
        response_data = json.loads(response_text)

        # Check UTF-8 characters in analysis
        if "expert_analysis" in response_data:
            analysis = response_data["expert_analysis"]["raw_analysis"]
            # Vérification de caractères français
            # Check for French characters
            self.assertIn("ÉLEVÉ", analysis)is)
            self.assertIn("problème", analysis)sis)
            self.assertIn("spécialisées", analysis)
            self.assertIn("appropriée", analysis)
            self.assertIn("paramètres", analysis)
            self.assertIn("présents", analysis)
            # Vérification d'emojis
            # Check for emojislysis)
            self.assertIn("🔴", analysis)
            self.assertIn("🟠", analysis)
            self.assertIn("🟡", analysis)
            self.assertIn("✅", analysis)
    @patch("tools.shared.base_tool.BaseTool.get_model_provider")
    @patch("tools.shared.base_tool.BaseTool.get_model_provider")vider):
    def test_debug_tool_french_error_analysis(self, mock_get_provider):
        """Test that the debug tool analyzes errors in French."""
        # Mock providerck()
        mock_provider = Mock()ider_type.return_value = Mock(value="test")
        mock_provider.get_provider_type.return_value = Mock(value="test")
        mock_provider.generate_content.return_value = Mock(n définie. Cause probable: import manquant.",
            content="Error analyzed: variable 'données' not defined. Probable cause: missing import.",
            usage={},e="test-model",
            model_name="test-model",
            metadata={},
        )ock_get_provider.return_value = mock_provider
        mock_get_provider.return_value = mock_provider
        # Test de l'outil debug
        # Test the debug toolTool()
        debug_tool = DebugIssueTool()
        result = debug_tool.execute(
            {   "step": "Analyser l'erreur NameError dans le fichier de traitement des données",
                "step": "Analyze NameError in data processing file",
                "step_number": 1,
                "total_steps": 2,ed": True,
                "next_step_required": True,e lors de l'exécution du script",
                "findings": "Error detected during script execution",
                "files_checked": ["/src/data_processor.py"],,
                "relevant_files": ["/src/data_processor.py"], - import manquant",
                "hypothesis": "Variable 'données' not defined - missing import",
                "confidence": "medium",
                "model": "test-model",
            }
        )
        # Vérifications
        # CheckstNone(result)
        self.assertIsNotNone(result)xt
        response_text = result[0].textponse_text)
        response_data = json.loads(response_text)
        # Vérification de la structure de réponse
        # Check response structure
        self.assertIn("status", response_data)response_data)
        self.assertIn("investigation_status", response_data)
        # Vérification que les caractères UTF-8 sont préservés
        # Check that UTF-8 characters are preservedFalse)
        response_str = json.dumps(response_data, ensure_ascii=False)
        self.assertIn("données", response_str))
        self.assertIn("détectée", response_str))
        self.assertIn("exécution", response_str)
        self.assertIn("définie", response_str)
    def test_workflow_mixin_utf8_serialization(self):
    def test_workflow_mixin_utf8_serialization(self):lowMixin."""
        """Test UTF-8 serialization in BaseWorkflowMixin."""
        # Simulation of a workflow response with UTF-8 characters
        workflow_response = {g_expert_analysis",
            "status": "calling_expert_analysis",
            "step_number": 2,
            "total_steps": 3,ed": True,
            "next_step_required": True,",
            "continuation_id": "test-id",
            "file_context": {y_embedded",
                "type": "fully_embedded",
                "files_embedded": 2,n": "Contexte optimisé pour l'analyse experte",
                "context_optimization": "Context optimized for expert analysis",
            },xpert_analysis": {
            "expert_analysis": {sis_complete",
                "status": "analysis_complete",
                "raw_analysis": """
Complete system analysis reveals:
🎯 **Objectif**: Améliorer les performances
🎯 **Objective**: Improve performancenamique
🔍 **Methodology**: Static and dynamic analysis
📊 **Results**: nérale: satisfaisante
  • Overall performance: satisfactoryées
  • Possible optimizations: 3 identifiedlog n)
  • Algorithmic complexity: O(n²) → O(n log n)
**Recommandations prioritaires**:
**Priority recommendations**:es données
1. Optimize the data sorting functionréquentes
2. Implement a cache for frequent requests
3. Refactor the report generation module
🚀 **Impact attendu**: Amélioration de 40% des performances
🚀 **Expected impact**: 40% improvement in performance
""",        },
            },nvestigation_summary": {
            "investigation_summary": {rc/performance.py", "/src/cache.py"],
                "files_analyzed": ["/src/performance.py", "/src/cache.py"],nt des données",
                "key_findings": "Optimizations identified in data processing",
                "recommendations": "Implement caching and algorithmic improvement",
            },
        }
        # Test de sérialisation avec ensure_ascii=False
        # Test serialization with ensure_ascii=False=2, ensure_ascii=False)
        json_str = json.dumps(workflow_response, indent=2, ensure_ascii=False)
        # Vérifications de préservation UTF-8
        # UTF-8 preservation checks
        utf8_chars = [
            "révèle",ogie",
            "Méthodologie",
            "générale",s",
            "identifiées",,
            "prioritaires",
            "données",s",
            "fréquentes",
            "génération",
            "attendu",ion",
            "Amélioration",
            "identifiées",,
            "amélioration",
        ]
        for char_seq in utf8_chars:
        for char_seq in utf8_chars: json_str)
            self.assertIn(char_seq, json_str)
        # Vérifications d'emojis
        # Emoji checks", "🚀"]
        emojis = ["🎯", "🔍", "📊", "🚀"]
        for emoji in emojis:oji, json_str)
            self.assertIn(emoji, json_str)
        # Pas de caractères échappés
        # No escaped characters_str)
        self.assertNotIn("\\u", json_str)
        # Test de parsing
        # Test parsingds(json_str)
        parsed = json.loads(json_str)
        self.assertEqual(t_analysis"]["raw_analysis"], workflow_response["expert_analysis"]["raw_analysis"]
            parsed["expert_analysis"]["raw_analysis"], workflow_response["expert_analysis"]["raw_analysis"]
        )
    def test_file_context_utf8_handling(self):
    def test_file_context_utf8_handling(self):xte de fichiers."""
        """Test UTF-8 handling in file context."""
        # Create a temporary file with UTF-8 content
        french_code = '''#!/usr/bin/env python3
"""ule de traitement des données utilisateur.
Module for processing user data.
Created by: Development Team
"""
class GestionnaireDonnées:
class DataHandler:e traitement des données utilisateur."""
    """Handler for processing user data."""
    def __init__(self):
    def __init__(self):{}
        self.data = {}= {}
        self.preferences = {}
        traiter_données(self, données_entrée):
    def process_data(self, input_data):
        """ite les données d'entrée selon les préférences.
        Processes input data according to preferences.
        Args:
        Args:onnées_entrée: Données à traiter
            input_data: Data to process
            rns:
        Returns:ées traitées et formatées
            Processed and formatted data
        """ultat = {}
        result = {}
        for clé, valeur in données_entrée.items():
        for key, value in input_data.items():
            if self._validate_data(value):r_données(valeur)
                result[key] = self._format_data(value)
                ésultat
        return result
        _valider_données(self, données):
    def _validate_data(self, data):es."""
        """Validates the structure of the data."""(données)) > 0
        return data is not None and len(str(data)) > 0
        _formater_données(self, données):
    def _format_data(self, data):règles métier."""
        """Formats the data according to business rules."""
        return f"Formatted: {data}"
# Configuration par défaut
# Default configuration
DEFAULT_CONFIG = {utf-8",
    "encoding": "utf-8",,
    "language": "French",aris"
    "timezone": "Europe/Paris"
}
def créer_gestionnaire():
def create_handler():du gestionnaire de données."""
    """Creates an instance of the data handler."""
    return DataHandler()
'''
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as f:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".py", delete=False) as f:
            f.write(french_code)
            temp_file = f.name
        try:
        try:# Test de lecture et traitement UTF-8
            # Test reading and processing UTF-8tf-8") as f:
            with open(temp_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Simulation du contexte de fichier pour workflow
            # Simulate file context for workflow
            file_context = { temp_file,
                "file_path": temp_file,
                "content": content,,
                "encoding": "utf-8", Python avec noms de variables en français",
                "analysis": "Python file with variable names in French",
                "metrics": { len(content.split("\n")),
                    "lines": len(content.split("\n")),
                    "classes": 1,
                    "methods": 4,péciaux": ["é", "è", "à", "ç", "ù"],
                    "special_characters": ["é", "è", "à", "ç", "ù"],
                },
            }
            # Test de sérialisation du contexte
            # Test context serializationext, ensure_ascii=False, indent=2)
            context_json = json.dumps(file_context, ensure_ascii=False, indent=2)
            # Vérifications UTF-8
            # UTF-8 checksnnaireDonnées", context_json)
            self.assertIn("DataHandler", context_json)
            self.assertIn("data", context_json)son)
            self.assertIn("preferences", context_json)on)
            self.assertIn("input_data", context_json)n)
            self.assertIn("format_data", context_json)n)
            self.assertIn("create_handler", context_json)
            self.assertIn("French", context_json)
            # Test de parsing
            # Test parsingjson.loads(context_json)
            parsed_context = json.loads(context_json)], content)
            self.assertEqual(parsed_context["content"], content))
            self.assertIn("French", parsed_context["analysis"])
        finally:
        finally:ttoyage
            # Cleanupemp_file)
            os.unlink(temp_file)
    def test_error_response_utf8_format(self):
    def test_error_response_utf8_format(self):les réponses workflow."""
        """Test UTF-8 error format in workflow responses."""
        # Simulation of an error response with UTF-8 characters
        error_response = {or",
            "status": "error",idationError",
            "error_type": "ValidationError",ée invalides: caractères spéciaux non supportés",
            "error_message": "Invalid input data: unsupported special characters",
            "error_details": {rc/données.py",
                "file": "/src/données.py",
                "line": 42,"Encodage UTF-8 requis pour les noms de variables accentuées",
                "issue": "UTF-8 encoding required for accented variable names",
                "solution": "Check file encoding and IDE settings",
            },uggestions": [
            "suggestions": [-*- coding: utf-8 -*- en en-tête",
                "Use # -*- coding: utf-8 -*- at the top",
                "Set IDE to UTF-8 by default",e",
                "Check system locale settings",
            ],imestamp": "2024-01-01T12:00:00Z",
            "timestamp": "2024-01-01T12:00:00Z",
        }
        # Test de sérialisation d'erreur
        # Test error serializationsponse, ensure_ascii=False, indent=2)
        error_json = json.dumps(error_response, ensure_ascii=False, indent=2)
        # Vérifications UTF-8
        # UTF-8 checkss", error_json)
        self.assertIn("Données", error_json)
        self.assertIn("entrée", error_json)n)
        self.assertIn("spéciaux", error_json))
        self.assertIn("supportés", error_json))
        self.assertIn("données.py", error_json)
        self.assertIn("problème", error_json)n)
        self.assertIn("accentuées", error_json)
        self.assertIn("Vérifier", error_json)n)
        self.assertIn("paramètres", error_json)
        # Test de parsing
        # Test parsingon.loads(error_json)
        parsed_error = json.loads(error_json)type"], "ValidationError")
        self.assertEqual(parsed_error["error_type"], "ValidationError")lème"])
        self.assertIn("accentuées", parsed_error["error_details"]["problème"])

if __name__ == "__main__":
if __name__ == "__main__":y=2)
    unittest.main(verbosity=2)