import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    is_valid: bool
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    violations: List[str]
    sanitized_input: str

class InputValidator:
    """Security-focused input validation and sanitization for LLM prompts"""
    
    def __init__(self):
        self.setup_patterns()
    
    def setup_patterns(self):
        """Initialize security patterns for detection"""
        
        # Jailbreak attempt patterns
        self.jailbreak_patterns = [
            r"ignore.*(?:previous|above|system|instruction)",
            r"forget.*(?:previous|above|system|instruction)",
            r"disregard.*(?:previous|above|system|instruction)",
            r"(?:act|behave|pretend).*(?:as|like).*(?:dan|jailbreak|evil|harmful)",
            r"you are now.*(?:uncensored|unrestricted|free)",
            r"override.*(?:safety|guideline|restriction|rule)",
            r"bypass.*(?:safety|guideline|restriction|rule)",
            r"roleplay.*(?:uncensored|unrestricted|harmful)",
            r"simulate.*(?:uncensored|unrestricted|harmful)",
            r"hypothetically.*(?:illegal|harmful|inappropriate)",
            r"in.*(?:developer|admin|god|root).*mode",
            r"enable.*(?:developer|admin|god|root).*mode",
            r"new.*(?:persona|character|role).*(?:uncensored|unrestricted)",
            r"switch.*(?:persona|character|role|mode)",
            r"opposite.*(?:day|mode|instruction)",
            r"evil.*(?:mode|version|twin|side)",
            r"dark.*(?:mode|version|twin|side)",
            r"shadow.*(?:mode|version|twin|side)",
            r"unlock.*(?:hidden|secret|restricted).*(?:mode|feature|capability)",
            r"reveal.*(?:hidden|secret|restricted).*(?:mode|feature|capability)",
            r"access.*(?:hidden|secret|restricted).*(?:mode|feature|capability)",
            r"\\[\\w+\\].*(?:mode|instruction|command)",
            r"\\{\\w+\\}.*(?:mode|instruction|command)",
        ]
        
        # System prompt extraction attempts
        self.system_extraction_patterns = [
            r"what.*(?:are|is).*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"show.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"tell.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"reveal.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"display.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"print.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"output.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"copy.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"repeat.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"echo.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"describe.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"explain.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"list.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"enumerate.*(?:your|the).*(?:instruction|prompt|system|rule)",
            r"how.*(?:are|were).*you.*(?:programmed|instructed|configured|trained)",
            r"what.*(?:are|were).*you.*(?:programmed|instructed|configured|trained)",
            r"show.*(?:original|initial|base).*(?:instruction|prompt|system)",
            r"\\\\n.*(?:instruction|prompt|system|rule)",
            r"\\\\.*(?:instruction|prompt|system|rule)",
            r"\\\".*(?:instruction|prompt|system|rule)",
            r"\\'.*(?:instruction|prompt|system|rule)",
        ]
        
        # NSFW and inappropriate content patterns
        self.nsfw_patterns = [
            r"\\b(?:sex|sexual|porn|erotic|nude|naked|orgasm|masturbat|vagina|penis|breast|ass|fuck|shit|damn|bitch|slut|whore|cunt|dick|cock|pussy)\\b",
            r"\\b(?:rape|molest|abuse|violence|kill|murder|suicide|death|torture|harm|hurt|pain|blood|gore|drug|cocaine|heroin|meth|cannabis|marijuana)\\b",
            r"\\b(?:hate|racism|nazi|terrorist|bomb|weapon|gun|knife|explosive|attack|threat|intimidat|harass|stalk|doxx)\\b",
            r"generate.*(?:explicit|sexual|violent|harmful|illegal|inappropriate).*(?:content|material|image|text)",
            r"create.*(?:explicit|sexual|violent|harmful|illegal|inappropriate).*(?:content|material|image|text)",
            r"write.*(?:explicit|sexual|violent|harmful|illegal|inappropriate).*(?:content|material|story|text)",
            r"produce.*(?:explicit|sexual|violent|harmful|illegal|inappropriate).*(?:content|material|image|text)",
        ]
        
        # Code injection patterns
        self.injection_patterns = [
            r"<script.*?>.*?</script>",
            r"javascript:",
            r"data:.*?base64",
            r"\\x[0-9a-fA-F]{2}",
            r"\\u[0-9a-fA-F]{4}",
            r"\\\\x[0-9a-fA-F]{2}",
            r"\\\\u[0-9a-fA-F]{4}",
            r"(?:eval|exec|import|__import__|compile|open|file|input|raw_input)\\s*\\(",
            r"(?:subprocess|os|sys|shutil|pathlib|glob)\\.",
            r"(?:urllib|requests|http|socket|ftplib|telnetlib)\\.",
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = {
            'jailbreak': [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.jailbreak_patterns],
            'system_extraction': [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.system_extraction_patterns],
            'nsfw': [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.nsfw_patterns],
            'injection': [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.injection_patterns],
        }
    
    def validate_input(self, user_input: str) -> ValidationResult:
        """Validate and analyze user input for security risks"""
        
        violations = []
        risk_level = 'low'
        
        # Check for jailbreak attempts
        jailbreak_matches = self._check_patterns(user_input, 'jailbreak')
        if jailbreak_matches:
            violations.extend([f"Jailbreak attempt detected: {match}" for match in jailbreak_matches])
            risk_level = 'critical'
        
        # Check for system extraction attempts
        system_matches = self._check_patterns(user_input, 'system_extraction')
        if system_matches:
            violations.extend([f"System extraction attempt: {match}" for match in system_matches])
            risk_level = max(risk_level, 'high', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
        
        # Check for NSFW content
        nsfw_matches = self._check_patterns(user_input, 'nsfw')
        if nsfw_matches:
            violations.extend([f"Inappropriate content detected: {match}" for match in nsfw_matches])
            risk_level = max(risk_level, 'high', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
        
        # Check for injection attempts
        injection_matches = self._check_patterns(user_input, 'injection')
        if injection_matches:
            violations.extend([f"Code injection attempt: {match}" for match in injection_matches])
            risk_level = max(risk_level, 'high', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
        
        # Additional heuristic checks
        if self._check_excessive_special_chars(user_input):
            violations.append("Excessive special characters detected")
            risk_level = max(risk_level, 'medium', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
        
        if self._check_suspicious_encoding(user_input):
            violations.append("Suspicious encoding detected")
            risk_level = max(risk_level, 'medium', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
        
        # Sanitize input
        sanitized_input = self._sanitize_input(user_input)
        
        # Determine if input is valid
        is_valid = risk_level in ['low', 'medium']
        
        return ValidationResult(
            is_valid=is_valid,
            risk_level=risk_level,
            violations=violations,
            sanitized_input=sanitized_input
        )
    
    def _check_patterns(self, text: str, pattern_type: str) -> List[str]:
        """Check text against compiled patterns"""
        matches = []
        for pattern in self.compiled_patterns[pattern_type]:
            found = pattern.findall(text)
            matches.extend(found)
        return matches
    
    def _check_excessive_special_chars(self, text: str) -> bool:
        """Check for excessive special characters (potential obfuscation)"""
        special_chars = sum(1 for char in text if not char.isalnum() and not char.isspace())
        total_chars = len(text)
        if total_chars > 0:
            ratio = special_chars / total_chars
            return ratio > 0.3  # More than 30% special characters
        return False
    
    def _check_suspicious_encoding(self, text: str) -> bool:
        """Check for suspicious encoding patterns"""
        suspicious_patterns = [
            r'%[0-9a-fA-F]{2}',  # URL encoding
            r'&[#\w]+;',         # HTML entities
            r'\\\\[xuU][0-9a-fA-F]+',  # Unicode/hex escapes
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize input by removing or replacing dangerous patterns"""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove JavaScript
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove data URIs
        text = re.sub(r'data:.*?base64.*?', '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
        
        return text.strip()
    
    def is_safe_for_llm(self, user_input: str) -> Tuple[bool, str]:
        """Quick safety check for LLM processing"""
        result = self.validate_input(user_input)
        
        if not result.is_valid:
            logger.warning(f"Unsafe input detected: {result.violations}")
            return False, f"Input contains prohibited content: {', '.join(result.violations)}"
        
        return True, result.sanitized_input


# Global validator instance
input_validator = InputValidator()
