"""User tier management domain service."""

from datetime import datetime, timedelta
from typing import Dict, List

from ..entities import User, UserTier, ChatMessage


class UserTierService:
    """Domain service for user tier management and limits."""
    
    # Tier limits configuration
    TIER_LIMITS = {
        UserTier.FREE: {
            "daily_messages": 20,
            "monthly_deep_analysis": 3,
            "personality_assessments": 1,
            "data_export": False,
            "advanced_ai": False,
            "priority_support": False,
        },
        UserTier.PREMIUM: {
            "daily_messages": 100, 
            "monthly_deep_analysis": 20,
            "personality_assessments": 5,
            "data_export": True,
            "advanced_ai": True,
            "priority_support": False,
        },
        UserTier.PROFESSIONAL: {
            "daily_messages": -1,  # Unlimited
            "monthly_deep_analysis": -1,  # Unlimited
            "personality_assessments": -1,  # Unlimited
            "data_export": True,
            "advanced_ai": True,
            "priority_support": True,
        }
    }
    
    def can_send_message(self, user: User, daily_messages_sent: int) -> bool:
        """Check if user can send another message today."""
        
        limit = self.TIER_LIMITS[user.tier]["daily_messages"]
        
        # Unlimited for professional tier
        if limit == -1:
            return True
        
        return daily_messages_sent < limit
    
    def can_perform_deep_analysis(self, user: User, monthly_deep_analysis: int) -> bool:
        """Check if user can perform deep analysis this month."""
        
        limit = self.TIER_LIMITS[user.tier]["monthly_deep_analysis"]
        
        # Unlimited for professional tier
        if limit == -1:
            return True
        
        return monthly_deep_analysis < limit
    
    def can_take_assessment(self, user: User, completed_assessments: int) -> bool:
        """Check if user can take another personality assessment."""
        
        limit = self.TIER_LIMITS[user.tier]["personality_assessments"]
        
        # Unlimited for professional tier
        if limit == -1:
            return True
        
        return completed_assessments < limit
    
    def can_export_data(self, user: User) -> bool:
        """Check if user can export their data."""
        
        return self.TIER_LIMITS[user.tier]["data_export"]
    
    def can_use_advanced_ai(self, user: User) -> bool:
        """Check if user can use advanced AI models."""
        
        return self.TIER_LIMITS[user.tier]["advanced_ai"]
    
    def has_priority_support(self, user: User) -> bool:
        """Check if user has priority support."""
        
        return self.TIER_LIMITS[user.tier]["priority_support"]
    
    def get_tier_limits(self, tier: UserTier) -> Dict:
        """Get limits for a specific tier."""
        
        return self.TIER_LIMITS[tier].copy()
    
    def get_usage_stats(self, user: User, messages: List[ChatMessage]) -> Dict:
        """Get current usage statistics for user."""
        
        now = datetime.utcnow()
        today = now.date()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Filter messages for today
        daily_messages = [
            msg for msg in messages 
            if msg.timestamp.date() == today and msg.is_user_message
        ]
        
        # Filter deep analysis messages for this month
        deep_analysis_messages = [
            msg for msg in messages
            if (msg.timestamp >= month_start and 
                msg.context and 
                msg.context.complexity_level == "deep")
        ]
        
        return {
            "daily_messages_sent": len(daily_messages),
            "monthly_deep_analysis": len(deep_analysis_messages),
            "tier": user.tier.value,
            "limits": self.get_tier_limits(user.tier)
        }
    
    def calculate_upgrade_benefits(self, current_tier: UserTier, target_tier: UserTier) -> Dict:
        """Calculate benefits gained by upgrading tiers."""
        
        current_limits = self.TIER_LIMITS[current_tier]
        target_limits = self.TIER_LIMITS[target_tier]
        
        benefits = {}
        
        for feature, target_limit in target_limits.items():
            current_limit = current_limits[feature]
            
            if isinstance(target_limit, bool) and target_limit != current_limit:
                benefits[feature] = "Enabled" if target_limit else "Disabled"
            elif isinstance(target_limit, int) and target_limit != current_limit:
                if target_limit == -1:
                    benefits[feature] = "Unlimited"
                elif current_limit == -1:
                    benefits[feature] = f"Limited to {target_limit}"
                else:
                    benefits[feature] = f"+{target_limit - current_limit}"
        
        return benefits
    
    def is_approaching_limits(self, user: User, usage_stats: Dict) -> Dict[str, bool]:
        """Check if user is approaching their tier limits."""
        
        limits = self.TIER_LIMITS[user.tier]
        warnings = {}
        
        # Check daily message limit (warn at 80%)
        daily_limit = limits["daily_messages"]
        if daily_limit > 0:  # Not unlimited
            daily_usage = usage_stats["daily_messages_sent"]
            warnings["daily_messages"] = daily_usage >= (daily_limit * 0.8)
        
        # Check monthly deep analysis limit (warn at 80%)
        monthly_limit = limits["monthly_deep_analysis"] 
        if monthly_limit > 0:  # Not unlimited
            monthly_usage = usage_stats["monthly_deep_analysis"]
            warnings["monthly_deep_analysis"] = monthly_usage >= (monthly_limit * 0.8)
        
        return warnings
    
    def suggest_tier_upgrade(self, user: User, usage_stats: Dict) -> UserTier:
        """Suggest appropriate tier based on usage patterns."""
        
        if user.tier == UserTier.PROFESSIONAL:
            return user.tier  # Already at highest tier
        
        limits = self.TIER_LIMITS[user.tier]
        
        # Check if user frequently hits limits
        daily_usage = usage_stats["daily_messages_sent"] 
        monthly_usage = usage_stats["monthly_deep_analysis"]
        
        daily_limit = limits["daily_messages"]
        monthly_limit = limits["monthly_deep_analysis"]
        
        needs_upgrade = False
        
        # Check daily message usage
        if daily_limit > 0 and daily_usage >= daily_limit * 0.9:
            needs_upgrade = True
        
        # Check monthly deep analysis usage
        if monthly_limit > 0 and monthly_usage >= monthly_limit * 0.9:
            needs_upgrade = True
        
        if needs_upgrade:
            if user.tier == UserTier.FREE:
                return UserTier.PREMIUM
            else:
                return UserTier.PROFESSIONAL
        
        return user.tier