"""
Machine Learning Anomaly Detection for Agent Behavior
Detects unusual patterns in agent actions
"""
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pickle
import hashlib
from collections import defaultdict, deque
import json

from core.models import ActionRequest, ActionType, Decision


@dataclass
class BehavioralProfile:
    """Behavioral profile for an agent"""
    agent_id: str
    action_patterns: Dict[str, int]  # action_type -> count
    parameter_vectors: List[np.ndarray]  # Numerical feature vectors
    time_patterns: Dict[int, int]  # hour_of_day -> count
    target_patterns: Dict[str, int]  # target -> count
    avg_parameters: Dict[str, Any]
    updated_at: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "agent_id": self.agent_id,
            "action_patterns": self.action_patterns,
            "parameter_vectors": [vec.tolist() for vec in self.parameter_vectors],
            "time_patterns": self.time_patterns,
            "target_patterns": self.target_patterns,
            "avg_parameters": self.avg_parameters,
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BehavioralProfile':
        """Create from dictionary"""
        return cls(
            agent_id=data["agent_id"],
            action_patterns=data["action_patterns"],
            parameter_vectors=[np.array(vec) for vec in data.get("parameter_vectors", [])],
            time_patterns=data["time_patterns"],
            target_patterns=data["target_patterns"],
            avg_parameters=data["avg_parameters"],
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


class AnomalyDetector:
    """
    ML-based anomaly detection for agent behavior
    Uses Isolation Forest and statistical profiling
    """
    
    def __init__(self, model_path: str = "models/anomaly_detector.pkl"):
        self.model_path = model_path
        self.profiles: Dict[str, BehavioralProfile] = {}
        self.anomaly_scores: Dict[str, List[float]] = defaultdict(list)
        self.load_model()
        
        # Training data
        self.training_window = deque(maxlen=10000)
        self.min_training_samples = 100
        
        print(f"AnomalyDetector initialized. Profiles: {len(self.profiles)}")
    
    def load_model(self):
        """Load trained ML model"""
        try:
            import joblib
            self.model = joblib.load(self.model_path)
            print(f"Loaded ML model from {self.model_path}")
        except (FileNotFoundError, ImportError):
            print("No ML model found, using statistical detection only")
            self.model = None
    
    def save_model(self):
        """Save ML model"""
        try:
            import joblib
            joblib.dump(self.model, self.model_path)
            print(f"Saved ML model to {self.model_path}")
        except ImportError:
            print("joblib not installed, cannot save model")
    
    def extract_features(self, action: ActionRequest) -> np.ndarray:
        """Extract numerical features from action"""
        features = []
        
        # Action type encoding
        action_type_enc = {
            ActionType.TOOL_CALL: 0,
            ActionType.API_CALL: 1,
            ActionType.MEMORY_READ: 2,
            ActionType.MEMORY_WRITE: 3,
            ActionType.FILE_READ: 4,
            ActionType.FILE_WRITE: 5,
            ActionType.DATABASE_QUERY: 6,
            ActionType.NETWORK_REQUEST: 7
        }
        features.append(action_type_enc.get(action.action_type, -1))
        
        # Time features
        hour = action.timestamp.hour
        minute = action.timestamp.minute
        day_of_week = action.timestamp.weekday()
        
        features.extend([
            hour / 24.0,  # Normalized hour
            minute / 60.0,  # Normalized minute
            day_of_week / 7.0  # Normalized day
        ])
        
        # Parameter complexity
        param_json = json.dumps(action.parameters)
        features.append(len(param_json) / 1000.0)  # Normalized size
        features.append(len(action.parameters))  # Parameter count
        
        # Target hash (simple encoding)
        target_hash = int(hashlib.md5(action.target.encode()).hexdigest()[:8], 16)
        features.append(target_hash % 1000 / 1000.0)
        
        return np.array(features)
    
    def update_profile(self, agent_id: str, action: ActionRequest, is_anomaly: bool = False):
        """Update behavioral profile for agent"""
        if agent_id not in self.profiles:
            self.profiles[agent_id] = BehavioralProfile(
                agent_id=agent_id,
                action_patterns={},
                parameter_vectors=[],
                time_patterns={},
                target_patterns={},
                avg_parameters={},
                updated_at=datetime.utcnow()
            )
        
        profile = self.profiles[agent_id]
        
        # Update action patterns
        action_key = action.action_type.value
        profile.action_patterns[action_key] = profile.action_patterns.get(action_key, 0) + 1
        
        # Update time patterns
        hour = action.timestamp.hour
        profile.time_patterns[hour] = profile.time_patterns.get(hour, 0) + 1
        
        # Update target patterns
        profile.target_patterns[action.target] = profile.target_patterns.get(action.target, 0) + 1
        
        # Update parameter vectors (keep last 100)
        features = self.extract_features(action)
        profile.parameter_vectors.append(features)
        if len(profile.parameter_vectors) > 100:
            profile.parameter_vectors = profile.parameter_vectors[-100:]
        
        # Update average parameters (simplified)
        if not profile.avg_parameters:
            profile.avg_parameters = action.parameters.copy()
        else:
            # Simple moving average for numerical parameters
            for key, value in action.parameters.items():
                if isinstance(value, (int, float)):
                    if key in profile.avg_parameters and isinstance(profile.avg_parameters[key], (int, float)):
                        profile.avg_parameters[key] = (profile.avg_parameters[key] * 0.9 + value * 0.1)
                    else:
                        profile.avg_parameters[key] = value
        
        profile.updated_at = datetime.utcnow()
        
        # Add to training data if not anomaly
        if not is_anomaly:
            self.training_window.append((agent_id, features))
            if len(self.training_window) >= self.min_training_samples:
                self._train_model()
    
    def detect_anomaly(self, agent_id: str, action: ActionRequest) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Detect if action is anomalous for agent
        
        Returns:
            (is_anomaly, confidence_score, details)
        """
        if agent_id not in self.profiles:
            # New agent, can't determine anomaly yet
            return False, 0.0, {"reason": "New agent, insufficient data"}
        
        profile = self.profiles[agent_id]
        features = self.extract_features(action)
        
        # Statistical anomaly detection
        anomalies = []
        confidence = 0.0
        details = {}
        
        # 1. Action type anomaly
        action_type = action.action_type.value
        total_actions = sum(profile.action_patterns.values())
        action_prob = profile.action_patterns.get(action_type, 0) / total_actions if total_actions > 0 else 0
        
        if action_prob < 0.01 and total_actions > 10:  # Rare action type
            anomalies.append(f"Rare action type: {action_type} (probability: {action_prob:.3f})")
            confidence += 0.3
            details["action_type_anomaly"] = {
                "probability": action_prob,
                "expected": profile.action_patterns
            }
        
        # 2. Time anomaly
        hour = action.timestamp.hour
        hour_prob = profile.time_patterns.get(hour, 0) / total_actions if total_actions > 0 else 0
        
        if hour_prob < 0.05 and total_actions > 20:  # Unusual time
            anomalies.append(f"Unusual time: {hour}:00 (probability: {hour_prob:.3f})")
            confidence += 0.2
            details["time_anomaly"] = {
                "hour": hour,
                "probability": hour_prob,
                "typical_hours": sorted(profile.time_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            }
        
        # 3. Target anomaly
        target_prob = profile.target_patterns.get(action.target, 0) / total_actions if total_actions > 0 else 0
        
        if target_prob < 0.02 and total_actions > 15:  # Rare target
            anomalies.append(f"Rare target: {action.target} (probability: {target_prob:.3f})")
            confidence += 0.2
            details["target_anomaly"] = {
                "target": action.target,
                "probability": target_prob,
                "common_targets": sorted(profile.target_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            }
        
        # 4. ML-based anomaly detection
        if self.model is not None and len(profile.parameter_vectors) >= 10:
            try:
                # Use ML model to predict anomaly
                features_2d = features.reshape(1, -1)
                ml_score = self.model.decision_function(features_2d)[0]
                
                if ml_score < -0.5:  # Adjust threshold based on your model
                    anomalies.append(f"ML anomaly score: {ml_score:.3f}")
                    confidence += 0.3
                    details["ml_anomaly"] = {
                        "score": ml_score,
                        "threshold": -0.5
                    }
            except Exception as e:
                details["ml_error"] = str(e)
        
        # Calculate overall confidence
        confidence = min(confidence, 1.0)
        
        is_anomaly = len(anomalies) >= 2 or confidence > 0.5
        
        if is_anomaly:
            details["detected_anomalies"] = anomalies
            details["confidence"] = confidence
        
        return is_anomaly, confidence, details
    
    def _train_model(self):
        """Train or update ML model"""
        if len(self.training_window) < self.min_training_samples:
            return
        
        try:
            import joblib
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler
            
            # Extract features from training data
            X = np.array([features for _, features in self.training_window])
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train Isolation Forest
            model = IsolationForest(
                n_estimators=100,
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_scaled)
            
            self.model = model
            self.save_model()
            
            print(f"Trained ML model with {len(X)} samples")
            
        except ImportError:
            print("scikit-learn not installed, skipping ML training")
        except Exception as e:
            print(f"ML training failed: {e}")
    
    def get_agent_insights(self, agent_id: str) -> Dict[str, Any]:
        """Get insights about agent behavior"""
        if agent_id not in self.profiles:
            return {"error": "No profile found"}
        
        profile = self.profiles[agent_id]
        total_actions = sum(profile.action_patterns.values())
        
        return {
            "agent_id": agent_id,
            "total_actions": total_actions,
            "action_distribution": profile.action_patterns,
            "time_distribution": profile.time_patterns,
            "common_targets": sorted(profile.target_patterns.items(), key=lambda x: x[1], reverse=True)[:10],
            "profile_age_days": (datetime.utcnow() - profile.updated_at).days,
            "anomaly_score_history": self.anomaly_scores.get(agent_id, [])[-100:],  # Last 100 scores
            "is_trained": len(profile.parameter_vectors) >= 10
        }
    
    def save_profiles(self, filepath: str = "data/behavioral_profiles.json"):
        """Save all behavioral profiles"""
        import json
        data = {
            agent_id: profile.to_dict()
            for agent_id, profile in self.profiles.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(self.profiles)} behavioral profiles to {filepath}")
    
    def load_profiles(self, filepath: str = "data/behavioral_profiles.json"):
        """Load behavioral profiles"""
        import json
        import os
        
        if not os.path.exists(filepath):
            print(f"No profiles found at {filepath}")
            return
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.profiles = {
            agent_id: BehavioralProfile.from_dict(profile_data)
            for agent_id, profile_data in data.items()
        }
        
        print(f"Loaded {len(self.profiles)} behavioral profiles from {filepath}")