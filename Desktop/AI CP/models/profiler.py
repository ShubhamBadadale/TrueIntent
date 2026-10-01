"""
Layer 4: Psychological Profiler
Detects 5 manipulation pillars in scam messages
"""

import re
from typing import Dict, List

class PsychologicalProfiler:
    """Layer 4 - Detect psychological manipulation tactics"""
    
    def __init__(self):
        # Define patterns for each pillar
        self.patterns = {
            "AUTHORITY_PRETEXTING": {
                "keywords": [
                    'bank', 'police', 'officer', 'department', 'rbi', 'govt',
                    'government', 'official', 'ministry', 'authority', 'sbi',
                    'hdfc', 'icici', 'income tax', 'customs', 'telecom',
                    'cyber crime', 'court', 'judge', 'inspector'
                ],
                "patterns": [
                    r'\b(bank|police|rbi|govt|officer|department)\b',
                    r'\b(income\s+tax|cyber\s+crime)\b',
                ]
            },
            
            "ARTIFICIAL_URGENCY": {
                "keywords": [
                    'urgent', 'immediately', 'now', 'hurry', 'quick',
                    'expire', 'expiring', 'minutes', 'hours', 'today',
                    'final notice', 'last chance', 'limited time'
                ],
                "patterns": [
                    r'\b(urgent|immediately|hurry|asap)\b',
                    r'within\s+\d+\s+(minutes?|hours?|days?)',
                    r'\d+\s+(minutes?|hours?)\s+(left|remaining)',
                    r'(expire|expir ing)\s+(today|soon|now)',
                ]
            },
            
            "LOSS_FRAMING": {
                "keywords": [
                    'block', 'blocked', 'suspend', 'suspended', 'penalty',
                    'fine', 'lose', 'lost', 'terminate', 'close', 'closed',
                    'deactivate', 'cancel', 'legal action', 'arrest',
                    'warrant', 'freeze', 'frozen'
                ],
                "patterns": [
                    r'\b(block|suspend|terminate|deactivate)\b',
                    r'(legal\s+action|arrest\s+warrant)',
                    r'(account|card|service)\s+(will\s+be\s+)?(block|suspend|close)',
                ]
            },
            
            "COERCED_ACTION": {
                "keywords": [
                    'pin', 'password', 'otp', 'cvv', 'click', 'link',
                    'download', 'install', 'verify', 'confirm', 'update',
                    'submit', 'enter', 'share', 'provide', 'approve',
                    'accept', 'upi', 'collect request'
                ],
                "patterns": [
                    r'\b(enter|share|provide)\s+(pin|otp|password|cvv)\b',
                    r'(click|tap)\s+(here|link|below)',
                    r'(approve|accept)\s+(request|payment)',
                    r'(download|install)\s+\w+\.(apk|exe)',
                ]
            },
            
            "ISOLATION_TACTIC": {
                "keywords": [
                    "don't tell", "don't share", "don't inform",
                    "keep secret", "confidential", "private",
                    "only you", "do not disclose", "alone"
                ],
                "patterns": [
                    r"don'?t\s+(tell|share|inform|disclose)",
                    r"(keep|maintain)\s+(secret|confidential)",
                    r"(only|just)\s+you\s+(can|should)",
                ]
            }
        }
    
    def detect_pillar(self, text: str, pillar: str) -> Dict:
        """Detect specific pillar in text"""
        text_lower = text.lower()
        
        # Check keywords
        keyword_matches = []
        for keyword in self.patterns[pillar]["keywords"]:
            if keyword in text_lower:
                keyword_matches.append(keyword)
        
        # Check regex patterns
        pattern_matches = []
        for pattern in self.patterns[pillar]["patterns"]:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                pattern_matches.extend(matches)
        
        # Calculate confidence
        total_matches = len(keyword_matches) + len(pattern_matches)
        present = total_matches > 0
        
        if total_matches == 0:
            confidence = 0.0
        elif total_matches == 1:
            confidence = 0.70
        elif total_matches == 2:
            confidence = 0.85
        else:
            confidence = 0.95
        
        # Generate trigger description
        trigger = ""
        if keyword_matches:
            trigger = f"Detected: {', '.join(keyword_matches[:2])}"
        elif pattern_matches:
            trigger = f"Pattern: {pattern_matches[0]}"
        
        return {
            "present": present,
            "confidence": confidence,
            "trigger": trigger,
            "matches": total_matches
        }
    
    def profile(self, text: str) -> Dict:
        """Generate complete psychological profile"""
        profile = {}
        
        for pillar in self.patterns.keys():
            profile[pillar] = self.detect_pillar(text, pillar)
        
        return profile
    
    def get_detected_tactics(self, profile: Dict) -> List[str]:
        """Get list of detected tactics"""
        return [pillar for pillar, data in profile.items() if data["present"]]
    
    def calculate_risk_score(self, profile: Dict) -> float:
        """Calculate risk score based on profile"""
        detected = self.get_detected_tactics(profile)
        
        if len(detected) == 0:
            return 0.0
        elif len(detected) == 1:
            return 0.40
        elif len(detected) == 2:
            return 0.65
        elif len(detected) == 3:
            return 0.80
        else:
            return 0.95

# Test
if __name__ == "__main__":
    profiler = PsychologicalProfiler()
    
    test_messages = [
        "URGENT: Your SBI account will be blocked within 24 hours. Enter PIN to verify KYC.",
        "Your Amazon order has been shipped.",
        "Police notice: Legal action will be taken. Call now and don't tell anyone.",
        "You won Rs 50000! Click here to claim prize immediately.",
    ]
    
    print("Testing Psychological Profiler:\n")
    for msg in test_messages:
        print(f"Message: {msg}\n")
        profile = profiler.profile(msg)
        detected = profiler.get_detected_tactics(profile)
        risk = profiler.calculate_risk_score(profile)
        
        print(f"Detected tactics: {detected}")
        print(f"Risk score: {risk:.2f}\n")
        
        for pillar, data in profile.items():
            if data["present"]:
                print(f"  • {pillar}: {data['trigger']} (confidence: {data['confidence']:.2f})")
        print("\n" + "="*70 + "\n")
