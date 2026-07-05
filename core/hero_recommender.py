"""
Overwatch Assistant - Hero Recommender Module
英雄推荐系统模块

根据队友已选英雄和敌方阵容，推荐最适合的英雄选择。
"""

import os
import json
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    HEROES_BY_ROLE, ALL_HEROES, HERO_NAME_CN,
    HERO_SYNERGIES, HERO_COUNTERS, TEAM_COMPOSITIONS,
    TeamComp
)


@dataclass
class HeroRecommendation:
    """英雄推荐结果"""
    hero: str
    hero_cn: str
    role: str
    score: float
    reasons: List[str] = field(default_factory=list)
    synergies: List[str] = field(default_factory=list)
    counters: List[str] = field(default_factory=list)
    
    def __repr__(self):
        return f"Recommendation({self.hero_cn}, score={self.score:.1f})"


class HeroRecommender:
    """英雄推荐器"""
    
    def __init__(self):
        self._hero_roles: Dict[str, str] = {}
        for role, heroes in HEROES_BY_ROLE.items():
            for hero in heroes:
                self._hero_roles[hero] = role
    
    def get_role(self, hero: str) -> Optional[str]:
        """获取英雄的职责"""
        return self._hero_roles.get(hero)
    
    def analyze_team_composition(self, team_heroes: List[str]) -> Dict:
        """
        分析当前队伍阵容
        
        Args:
            team_heroes: 队友已选英雄列表
            
        Returns:
            分析结果字典
        """
        roles = Counter()
        valid_heroes = []
        
        for hero in team_heroes:
            if hero in self._hero_roles:
                roles[self._hero_roles[hero]] += 1
                valid_heroes.append(hero)
        
        return {
            'tank_count': roles.get('tank', 0),
            'damage_count': roles.get('damage', 0),
            'support_count': roles.get('support', 0),
            'heroes': valid_heroes,
            'missing_roles': self._get_missing_roles(roles)
        }
    
    def _get_missing_roles(self, roles: Counter) -> List[str]:
        """获取缺少的职责"""
        missing = []
        if roles.get('tank', 0) < 1:
            missing.append('tank')
        if roles.get('damage', 0) < 2:
            missing.append('damage')
        if roles.get('support', 0) < 2:
            missing.append('support')
        return missing
    
    def recommend_for_role(self, 
                          team_heroes: List[str],
                          target_role: str,
                          enemy_heroes: Optional[List[str]] = None,
                          top_n: int = 3) -> List[HeroRecommendation]:
        """
        为指定职责推荐英雄
        
        Args:
            team_heroes: 队友已选英雄
            target_role: 目标职责 (tank/damage/support)
            enemy_heroes: 敌方英雄（可选）
            top_n: 返回推荐数量
            
        Returns:
            推荐列表
        """
        candidates = HEROES_BY_ROLE.get(target_role, [])
        if not candidates:
            return []
        
        scored = []
        for hero in candidates:
            score, reasons, synergies, counters = self._score_hero(
                hero, team_heroes, enemy_heroes
            )
            scored.append((hero, score, reasons, synergies, counters))
        
        # 按分数排序
        scored.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for hero, score, reasons, synergies, counters in scored[:top_n]:
            rec = HeroRecommendation(
                hero=hero,
                hero_cn=HERO_NAME_CN.get(hero, hero),
                role=target_role,
                score=min(score, 100.0),
                reasons=reasons,
                synergies=synergies,
                counters=counters
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _score_hero(self, 
                   hero: str, 
                   team_heroes: List[str],
                   enemy_heroes: Optional[List[str]]) -> Tuple[float, List[str], List[str], List[str]]:
        """
        为单个英雄打分
        
        Returns:
            (分数, 理由, 协同英雄, 克制英雄)
        """
        score = 50.0  # 基础分
        reasons = []
        synergies = []
        counters = []
        
        # 1. 协同加分
        hero_synergies = HERO_SYNERGIES.get(hero, [])
        for teammate in team_heroes:
            if teammate in hero_synergies:
                score += 15.0
                synergies.append(teammate)
                reasons.append(f"与 {HERO_NAME_CN.get(teammate, teammate)} 有良好协同")
        
        # 2. 阵容完整性加分
        team_analysis = self.analyze_team_composition(team_heroes + [hero])
        if team_analysis['tank_count'] >= 1 and team_analysis['damage_count'] >= 2 and team_analysis['support_count'] >= 2:
            score += 10.0
            reasons.append("补全阵容配置")
        
        # 3. 阵容类型匹配
        comp_match = self._check_compatibility(hero, team_heroes)
        if comp_match > 0:
            score += comp_match
            reasons.append("契合当前阵容风格")
        
        # 4. 敌方克制
        if enemy_heroes:
            enemy_countered = []
            for enemy in enemy_heroes:
                if enemy in HERO_COUNTERS.get(hero, []):
                    score += 12.0
                    enemy_countered.append(enemy)
                    reasons.append(f"克制敌方 {HERO_NAME_CN.get(enemy, enemy)}")
            
            # 5. 被敌方克制扣分
            for enemy in enemy_heroes:
                counters_list = HERO_COUNTERS.get(enemy, [])
                if hero in counters_list:
                    score -= 15.0
                    counters.append(enemy)
                    reasons.append(f"被敌方 {HERO_NAME_CN.get(enemy, enemy)} 克制")
        
        # 6. 通用性加分（适合大多数阵容的英雄）
        versatile_heroes = {
            'tank': ['Winston', 'Sigma', 'Orisa'],
            'damage': ['Soldier: 76', 'Cassidy', 'Tracer'],
            'support': ['Ana', 'Kiriko', 'Baptiste']
        }
        role = self.get_role(hero)
        if role and hero in versatile_heroes.get(role, []):
            score += 5.0
            reasons.append("通用性强，适应多种阵容")
        
        return score, reasons, synergies, counters
    
    def _check_compatibility(self, hero: str, team_heroes: List[str]) -> float:
        """检查英雄与当前阵容的契合度"""
        bonus = 0.0
        
        for comp in TEAM_COMPOSITIONS:
            # 检查已有英雄有多少在阵容中
            matched = sum(1 for h in team_heroes if h in comp.required_tank or 
                         h in comp.required_dps or h in comp.required_support)
            
            # 检查推荐英雄是否在阵容中
            if matched >= 1:
                if hero in comp.required_tank or hero in comp.required_dps or hero in comp.required_support:
                    bonus += matched * 3.0
        
        return bonus
    
    def get_full_recommendation(self,
                               team_heroes: List[str],
                               enemy_heroes: Optional[List[str]] = None,
                               player_role: Optional[str] = None) -> str:
        """
        获取完整的推荐文本（用于叠加层显示）
        
        Args:
            team_heroes: 队友已选英雄
            enemy_heroes: 敌方英雄
            player_role: 玩家当前职责（如果已确定）
            
        Returns:
            格式化推荐文本
        """
        analysis = self.analyze_team_composition(team_heroes)
        
        lines = []
        lines.append("=" * 30)
        lines.append("英雄推荐")
        lines.append("=" * 30)
        
        # 显示当前阵容
        lines.append(f"\n当前阵容: {len(analysis['heroes'])}/5")
        for hero in analysis['heroes']:
            cn = HERO_NAME_CN.get(hero, hero)
            role_icon = {"tank": "🛡️", "damage": "⚔️", "support": "💚"}.get(
                self.get_role(hero), "?"
            )
            lines.append(f"  {role_icon} {cn}")
        
        # 推荐英雄
        roles_to_recommend = [player_role] if player_role else analysis['missing_roles']
        if not roles_to_recommend:
            roles_to_recommend = ['tank', 'damage', 'support']
        
        for role in roles_to_recommend:
            role_name = {"tank": "重装", "damage": "输出", "support": "支援"}.get(role, role)
            lines.append(f"\n【{role_name}推荐】")
            
            recs = self.recommend_for_role(team_heroes, role, enemy_heroes, top_n=2)
            if recs:
                for i, rec in enumerate(recs, 1):
                    lines.append(f"  {i}. {rec.hero_cn} (评分: {rec.score:.0f})")
                    for reason in rec.reasons[:2]:  # 只显示前2个理由
                        lines.append(f"     → {reason}")
            else:
                lines.append("  暂无推荐")
        
        # 阵容建议
        lines.append(f"\n【阵容分析】")
        if analysis['missing_roles']:
            missing_names = [
                {"tank": "重装", "damage": "输出", "support": "支援"}.get(r, r)
                for r in analysis['missing_roles']
            ]
            lines.append(f"  缺少: {' / '.join(missing_names)}")
        else:
            lines.append("  阵容完整！")
        
        lines.append("=" * 30)
        
        return "\n".join(lines)
    
    def get_quick_recommendation(self,
                                team_heroes: List[str],
                                enemy_heroes: Optional[List[str]] = None,
                                player_role: Optional[str] = None) -> str:
        """
        获取精简版推荐（适合叠加层单行显示）
        """
        analysis = self.analyze_team_composition(team_heroes)
        
        roles_to_recommend = [player_role] if player_role else analysis['missing_roles']
        if not roles_to_recommend:
            return "阵容已完整，可自由发挥"
        
        recommendations = []
        for role in roles_to_recommend[:1]:  # 只取第一个缺少的职责
            recs = self.recommend_for_role(team_heroes, role, enemy_heroes, top_n=1)
            if recs:
                role_name = {"tank": "重装", "damage": "输出", "support": "支援"}.get(role, role)
                rec = recs[0]
                reasons_str = " / ".join(rec.reasons[:2])
                recommendations.append(
                    f"建议选{role_name}: {rec.hero_cn} ({reasons_str})"
                )
        
        return " | ".join(recommendations) if recommendations else "暂无推荐"
    
    def suggest_counter_pick(self, 
                            enemy_heroes: List[str],
                            player_role: Optional[str] = None,
                            top_n: int = 3) -> List[HeroRecommendation]:
        """
        根据敌方阵容推荐克制英雄
        
        Args:
            enemy_heroes: 敌方英雄列表
            player_role: 限制推荐职责
            top_n: 推荐数量
            
        Returns:
            克制英雄推荐列表
        """
        # 统计每个英雄对敌方的克制分数
        candidates = ALL_HEROES
        if player_role:
            candidates = HEROES_BY_ROLE.get(player_role, [])
        
        scored = []
        for hero in candidates:
            score = 0.0
            reasons = []
            counters = []
            
            for enemy in enemy_heroes:
                # 这个英雄是否克制敌方
                if enemy in HERO_COUNTERS.get(hero, []):
                    score += 20.0
                    reasons.append(f"克制 {HERO_NAME_CN.get(enemy, enemy)}")
                    counters.append(enemy)
            
            # 计算被敌方克制的扣分
            for enemy in enemy_heroes:
                if hero in HERO_COUNTERS.get(enemy, []):
                    score -= 15.0
                    reasons.append(f"被 {HERO_NAME_CN.get(enemy, enemy)} 克制")
            
            if score > 0:
                scored.append((hero, score, reasons, [], counters))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for hero, score, reasons, _, counters in scored[:top_n]:
            rec = HeroRecommendation(
                hero=hero,
                hero_cn=HERO_NAME_CN.get(hero, hero),
                role=self.get_role(hero) or "unknown",
                score=min(score, 100.0),
                reasons=reasons,
                counters=counters
            )
            recommendations.append(rec)
        
        return recommendations


# 测试代码
if __name__ == "__main__":
    print("测试英雄推荐系统...")
    
    recommender = HeroRecommender()
    
    # 测试阵容
    team = ["Winston", "Genji"]
    enemy = ["Pharah", "Mercy", "Echo"]
    
    print("\n测试1: 放狗阵容缺少支援")
    recs = recommender.recommend_for_role(team, "support", enemy, top_n=3)
    for r in recs:
        print(f"  {r.hero_cn}: {r.score:.1f}分 - {r.reasons}")
    
    print("\n测试2: 完整推荐")
    print(recommender.get_full_recommendation(team, enemy))
    
    print("\n测试3: 克制推荐")
    counters = recommender.suggest_counter_pick(enemy, "damage")
    for r in counters:
        print(f"  {r.hero_cn}: {r.score:.1f}分")
