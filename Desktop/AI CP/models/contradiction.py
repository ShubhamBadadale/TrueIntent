"""
Layer 5: UPI Contradiction Engine
Checks stated intent vs requested action
"""

import re
from typing import Dict, Tuple

class ContradictionEngine:
    """Layer 5 - Detect intent-action contradictions"""
    
    def __init__(self):
        # Define contradiction rules
        self.rules = [
            {
                "intent_patterns": [
                    r'\b(receive|get|credit|refund|cashback|prize|won)\b',
                ],
                "action_patterns": [
                    r'\b(enter|share|provide|submit)\s+(pin|upi\s+pin|password)\b',
                ],
                "contradiction": "PIN is ONLY needed to SEND money, not RECEIVE",
                "severity": "CRITICAL"
            },
            {
                "intent_patterns": [
                    r'\b(receive|refund|get\s+money|credit)\b',
                ],
                "action_patterns": [
                    r'\b(approve|accept)\s+(collect\s+request|payment\s+request)\b',
                ],
                "contradiction": "You NEVER approve a collect request to RECEIVE money",
                "severity": "CRITICAL"
            },
            {
                "intent_patterns": [
                    r'\b(verify|confirm|check|validate|update)\s+(identity|kyc|account|details)\b',
                ],
                "action_patterns": [
                    r'\b(download|install)\s+\w+\.(apk|exe|app)\b',
                ],
                "contradiction": "Official verification NEVER requires downloading APK files",
                "severity": "CRITICAL"
            },
            {
                "intent_patterns": [
                    r'\b(bank|official|govt|government)\b',
                ],
                "action_patterns": [
                    r'(bit\.ly|tinyurl|short\.link|t\.co)/',
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP address
                ],
                "contradiction": "Banks NEVER use shortened links or IP addresses",
                "severity": "HIGH"
            },
            {
                "intent_patterns": [
                    r'\b(balance|check\s+balance|account\s+balance)\b',
                ],
                "action_patterns": [
                    r'\b(enter|provide)\s+cvv\b',
                ],
                "contradiction": "Checking balance does NOT require CVV",
                "severity": "HIGH"
            },
        ]
    
    def extract_intent(self, text: str) -> str:
        """Extract stated intent from text"""
        text_lower = text.lower()
        
        intents = []
        
        if re.search(r'\b(receive|get|credit|refund|cashback|prize|won)\b', text_lower):
            intents.append("RECEIVE_MONEY")
        
        if re.search(r'\b(verify|confirm|kyc|update\s+details)\b', text_lower):
            intents.append("VERIFY_IDENTITY")
        
        if re.search(r'\b(send|pay|transfer)\b', text_lower):
            intents.append("SEND_MONEY")
        
        if re.search(r'\b(balance|check)\b', text_lower):
            intents.append("CHECK_BALANCE")
        
        return " | ".join(intents) if intents else "UNKNOWN"
    
    def extract_actions(self, text: str) -> str:
        """Extract requested actions from text"""
        text_lower = text.lower()
        
        actions = []
        
        if re.search(r'\b(enter|share|provide)\s+(pin|otp|password|cvv)\b', text_lower):
            actions.append("ENTER_CREDENTIALS")
        
        if re.search(r'\b(approve|accept)\s+request\b', text_lower):
            actions.append("APPROVE_REQUEST")
        
        if re.search(r'\b(download|install)\b', text_lower):
            actions.append("DOWNLOAD_FILE")
        
        if re.search(r'\b(click|tap)\s+(link|here|below)\b', text_lower):
            actions.append("CLICK_LINK")
        
        if re.search(r'\b(call|contact)\s+\d{10}\b', text_lower):
            actions.append("CALL_NUMBER")
        
        return " | ".join(actions) if actions else "NONE"
    
    def check_contradictions(self, text: str) -> Dict:
        """Check for intent-action contradictions"""
        text_lower = text.lower()
        contradictions_found = []
        
        for rule in self.rules:
            # Check if intent pattern matches
            intent_match = any(
                re.search(pattern, text_lower)
                for pattern in rule["intent_patterns"]
            )
            
            # Check if action pattern matches
            action_match = any(
                re.search(pattern, text_lower)
                for pattern in rule["action_patterns"]
            )
            
            # If both match, contradiction detected
            if intent_match and action_match:
                contradictions_found.append({
                    "contradiction": rule["contradiction"],
                    "severity": rule["severity"]
                })
        
        has_contradiction = len(contradictions_found) > 0
        
        return {
            "has_contradiction": has_contradiction,
            "contradictions": contradictions_found,
            "intent": self.extract_intent(text),
            "actions": self.extract_actions(text)
        }
    
    def get_risk_override(self, text: str) -> Tuple[bool, float]:
        """
        Check if contradiction should override risk to CRITICAL
        
        Returns:
            (should_override, risk_score)
        """
        result = self.check_contradictions(text)
        
        if result["has_contradiction"]:
            # Check for CRITICAL severity
            has_critical = any(
                c["severity"] == "CRITICAL"
                for c in result["contradictions"]
            )
            
            if has_critical:
                return True, 1.0  # Override to maximum risk
        
        return False, 0.0

# Test
if __name__ == "__main__":
    engine = ContradictionEngine()
    
    test_cases = [
        "You have refund of Rs 10000. Enter your UPI PIN to receive money.",
        "Your Amazon order has shipped. Track at amazon.in",
        "Verify your bank KYC by downloading this APK file.",
        "SBI refund Rs 5000 credited. Approve collect request to claim.",
        "Your account balance is low. Check by entering CVV.",
    ]
    
    print("Testing Contradiction Engine:\n")
    for msg in test_cases:
        print(f"Message: {msg}\n")
        result = engine.check_contradictions(msg)
        override, risk = engine.get_risk_override(msg)
        
        print(f"Intent: {result['intent']}")
        print(f"Actions: {result['actions']}")
        print(f"Contradiction: {result['has_contradiction']}")
        
        if result['has_contradiction']:
            print(f"Risk Override: {override} → {risk:.1f}")
            for c in result['contradictions']:
                print(f"  ⛔ {c['contradiction']} (Severity: {c['severity']})")
        
        print("\n" + "="*70 + "\n")
