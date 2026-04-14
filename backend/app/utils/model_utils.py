"""
Утилиты для работы с моделями.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.game_session import GameSession, SessionStatus
from app.models.round import Round, RoundStatus
from app.models.location_zone import LocationZone
from app.models.enums import GameMode, ZoneCategory, ScoreTier

logger = logging.getLogger(__name__)


class ModelUtils:
    """Утилиты для работы с моделями"""
    
    @staticmethod
    async def get_user_stats(
        session: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Получить расширенную статистику пользователя.
        
        Args:
            session: Асинхронная сессия БД
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        try:
            # Получаем пользователя
            user_stmt = select(User).where(User.id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"error": "User not found"}
            
            # Получаем завершённые сессии
            sessions_stmt = select(GameSession).where(
                GameSession.user_id == user_id,
                GameSession.status.in_([SessionStatus.FINISHED, SessionStatus.ABANDONED])
            )
            sessions_result = await session.execute(sessions_stmt)
            sessions = sessions_result.scalars().all()
            
            # Получаем все раунды пользователя
            rounds_stmt = select(Round).join(GameSession).where(
                GameSession.user_id == user_id,
                Round.status == RoundStatus.GUESSED
            )
            rounds_result = await session.execute(rounds_stmt)
            rounds = rounds_result.scalars().all()
            
            # Базовая статистика
            stats = {
                "user_id": user.id,
                "username": user.username,
                "total_score": user.total_score,
                "games_played": len(sessions),
                "total_rounds": len(rounds),
                "average_score": user.average_score or 0,
                "average_distance": user.average_distance or 0,
                "best_score": user.best_score,
                "worst_score": user.worst_score,
                "elo_rating": user.elo_rating,
                "rank": user.get_rank(),
                "level": user.level,
                "experience": user.experience,
                "experience_progress": user.get_experience_progress(),
            }
            
            # Статистика по режимам игры
            game_modes = {}
            for mode in GameMode:
                mode_sessions = [s for s in sessions if s.mode == mode.value]
                if mode_sessions:
                    game_modes[mode.value] = {
                        "games_played": len(mode_sessions),
                        "total_score": sum(s.total_score for s in mode_sessions),
                        "average_score": sum(s.total_score for s in mode_sessions) / len(mode_sessions),
                        "best_score": max(s.total_score for s in mode_sessions),
                        "worst_score": min(s.total_score for s in mode_sessions),
                    }
            
            stats["game_modes"] = game_modes
            
            # Статистика по категориям зон
            zone_categories = {}
            for round_obj in rounds:
                category = round_obj.zone.category
                if category not in zone_categories:
                    zone_categories[category] = {
                        "rounds_played": 0,
                        "total_score": 0,
                        "average_score": 0,
                        "average_distance": 0,
                        "distances": [],
                    }
                
                zone_categories[category]["rounds_played"] += 1
                zone_categories[category]["total_score"] += round_obj.score
                if round_obj.distance_km:
                    zone_categories[category]["average_distance"] += float(round_obj.distance_km)
                    zone_categories[category]["distances"].append(float(round_obj.distance_km))
            
            # Вычисляем средние значения
            for category, data in zone_categories.items():
                if data["rounds_played"] > 0:
                    data["average_score"] = data["total_score"] / data["rounds_played"]
                    if data["distances"]:
                        data["average_distance"] = sum(data["distances"]) / len(data["distances"])
                    else:
                        data["average_distance"] = 0
                
                # Удаляем временный список расстояний
                if "distances" in data:
                    del data["distances"]
            
            stats["zone_categories"] = zone_categories
            
            # Распределение очков по уровням
            score_tiers = {tier.value: 0 for tier in ScoreTier}
            for round_obj in rounds:
                tier = round_obj.get_score_tier()
                score_tiers[tier.value] += 1
            
            stats["score_tiers"] = score_tiers
            
            # Временная статистика (последние 30 дней)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_sessions = [s for s in sessions if s.started_at >= thirty_days_ago]
            recent_rounds = [r for r in rounds if r.created_at >= thirty_days_ago]
            
            stats["recent_30_days"] = {
                "games_played": len(recent_sessions),
                "rounds_played": len(recent_rounds),
                "total_score": sum(s.total_score for s in recent_sessions),
                "average_score": sum(s.total_score for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0,
            }
            
            # Прогресс по дням (последние 7 дней)
            daily_progress = {}
            for i in range(7):
                day = datetime.utcnow() - timedelta(days=i)
                day_str = day.strftime("%Y-%m-%d")
                
                day_sessions = [s for s in sessions if s.started_at.date() == day.date()]
                day_rounds = [r for r in rounds if r.created_at.date() == day.date()]
                
                daily_progress[day_str] = {
                    "games_played": len(day_sessions),
                    "rounds_played": len(day_rounds),
                    "total_score": sum(s.total_score for s in day_sessions),
                    "average_score": sum(s.total_score for s in day_sessions) / len(day_sessions) if day_sessions else 0,
                }
            
            stats["daily_progress"] = daily_progress
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def get_global_stats(
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Получить глобальную статистику игры.
        
        Args:
            session: Асинхронная сессия БД
            
        Returns:
            Словарь со статистикой
        """
        try:
            # Общее количество пользователей
            users_stmt = select(func.count(User.id)).where(User.is_active == True)
            users_result = await session.execute(users_stmt)
            total_users = users_result.scalar() or 0
            
            # Общее количество игр
            games_stmt = select(func.count(GameSession.id))
            games_result = await session.execute(games_stmt)
            total_games = games_result.scalar() or 0
            
            # Общее количество раундов
            rounds_stmt = select(func.count(Round.id)).where(Round.status == RoundStatus.GUESSED)
            rounds_result = await session.execute(rounds_stmt)
            total_rounds = rounds_result.scalar() or 0
            
            # Общий счёт всех пользователей
            total_score_stmt = select(func.sum(User.total_score))
            total_score_result = await session.execute(total_score_stmt)
            global_total_score = total_score_result.scalar() or 0
            
            # Самые популярные зоны
            popular_zones_stmt = select(
                LocationZone.id,
                LocationZone.name,
                LocationZone.category,
                LocationZone.difficulty,
                func.count(Round.id).label("rounds_count"),
                func.avg(Round.score).label("average_score")
            ).join(
                Round, LocationZone.id == Round.zone_id
            ).where(
                Round.status == RoundStatus.GUESSED
            ).group_by(
                LocationZone.id
            ).order_by(
                func.count(Round.id).desc()
            ).limit(10)
            
            popular_zones_result = await session.execute(popular_zones_stmt)
            popular_zones = []
            
            for row in popular_zones_result:
                popular_zones.append({
                    "id": row.id,
                    "name": row.name,
                    "category": row.category,
                    "difficulty": row.difficulty,
                    "rounds_count": row.rounds_count,
                    "average_score": float(row.average_score) if row.average_score else 0,
                })
            
            # Лучшие игроки
            top_players_stmt = select(
                User.id,
                User.username,
                User.total_score,
                User.games_played,
                User.average_score,
                User.elo_rating
            ).where(
                User.is_active == True
            ).order_by(
                User.elo_rating.desc()
            ).limit(10)
            
            top_players_result = await session.execute(top_players_stmt)
            top_players = []
            
            for row in top_players_result:
                top_players.append({
                    "id": row.id,
                    "username": row.username,
                    "total_score": row.total_score,
                    "games_played": row.games_played,
                    "average_score": float(row.average_score) if row.average_score else 0,
                    "elo_rating": row.elo_rating,
                    "rank": User.get_rank(User(elo_rating=row.elo_rating)),  # Создаём временный объект
                })
            
            # Статистика по категориям
            category_stats_stmt = select(
                LocationZone.category,
                func.count(Round.id).label("rounds_count"),
                func.avg(Round.score).label("average_score"),
                func.avg(Round.distance_km).label("average_distance")
            ).join(
                Round, LocationZone.id == Round.zone_id
            ).where(
                Round.status == RoundStatus.GUESSED,
                LocationZone.category.is_not(None)
            ).group_by(
                LocationZone.category
            )
            
            category_stats_result = await session.execute(category_stats_stmt)
            category_stats = {}
            
            for row in category_stats_result:
                category_stats[row.category] = {
                    "rounds_count": row.rounds_count,
                    "average_score": float(row.average_score) if row.average_score else 0,
                    "average_distance": float(row.average_distance) if row.average_distance else 0,
                }
            
            # Активность по дням (последние 7 дней)
            daily_activity = {}
            for i in range(7):
                day = datetime.utcnow() - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                day_games_stmt = select(func.count(GameSession.id)).where(
                    GameSession.started_at.between(day_start, day_end)
                )
                day_games_result = await session.execute(day_games_stmt)
                day_games = day_games_result.scalar() or 0
                
                day_rounds_stmt = select(func.count(Round.id)).where(
                    Round.created_at.between(day_start, day_end)
                )
                day_rounds_result = await session.execute(day_rounds_stmt)
                day_rounds = day_rounds_result.scalar() or 0
                
                day_str = day.strftime("%Y-%m-%d")
                daily_activity[day_str] = {
                    "games": day_games,
                    "rounds": day_rounds,
                }
            
            return {
                "total_users": total_users,
                "total_games": total_games,
                "total_rounds": total_rounds,
                "global_total_score": global_total_score,
                "popular_zones": popular_zones,
                "top_players": top_players,
                "category_stats": category_stats,
                "daily_activity": daily_activity,
            }
            
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def get_zone_stats(
        session: AsyncSession,
        zone_id: int
    ) -> Dict[str, Any]:
        """
        Получить статистику по конкретной зоне.
        
        Args:
            session: Асинхронная сессия БД
            zone_id: ID зоны
            
        Returns:
            Словарь со статистикой
        """
        try:
            # Получаем зону
            zone_stmt = select(LocationZone).where(LocationZone.id == zone_id)
            zone_result = await session.execute(zone_stmt)
            zone = zone_result.scalar_one_or_none()
            
            if not zone:
                return {"error": "Zone not found"}
            
            # Получаем раунды для этой зоны
            rounds_stmt = select(Round).where(
                Round.zone_id == zone_id,
                Round.status == RoundStatus.GUESSED
            )
            rounds_result = await session.execute(rounds_stmt)
            rounds = rounds_result.scalars().all()
            
            if not rounds:
                return {
                    "zone": zone.to_dict(),
                    "statistics": {
                        "total_rounds": 0,
                        "average_score": 0,
                        "average_distance": 0,
                        "score_distribution": {},
                        "player_stats": [],
                    }
                }
            
            # Базовая статистика
            total_rounds = len(rounds)
            total_score = sum(r.score for r in rounds)
            average_score = total_score / total_rounds
            
            # Среднее расстояние
            distances = [float(r.distance_km) for r in rounds if r.distance_km is not None]
            average_distance = sum(distances) / len(distances) if distances else 0
            
            # Распределение очков
            score_distribution = {tier.value: 0 for tier in ScoreTier}
            for round_obj in rounds:
                tier = round_obj.get_score_tier()
                score_distribution[tier.value] += 1
            
            # Статистика по игрокам
            player_stats = {}
            for round_obj in rounds:
                user_id = round_obj.session.user_id
                username = round_obj.session.user.username
                
                if user_id not in player_stats:
                    player_stats[user_id] = {
                        "user_id": user_id,
                        "username": username,
                        "rounds_played": 0,
                        "total_score": 0,
                        "average_score": 0,
                        "best_score": 0,
                        "worst_score": float('inf'),
                        "distances": [],
                    }
                
                stats = player_stats[user_id]
                stats["rounds_played"] += 1
                stats["total_score"] += round_obj.score
                stats["best_score"] = max(stats["best_score"], round_obj.score)
                stats["worst_score"] = min(stats["worst_score"], round_obj.score)
                
                if round_obj.distance_km:
                    stats["distances"].append(float(round_obj.distance_km))
            
            # Вычисляем средние значения для игроков
            player_stats_list = []
            for user_id, stats in player_stats.items():
                stats["average_score"] = stats["total_score"] / stats["rounds_played"]
                if stats["distances"]:
                    stats["average_distance"] = sum(stats["distances"]) / len(stats["distances"])
                else:
                    stats["average_distance"] = 0
                
                # Удаляем временный список расстояний
                if "distances" in stats:
                    del stats["distances"]
                
                # Преобразуем худший счёт обратно в нормальное число
                if stats["worst_score"] == float('inf'):
                    stats["worst_score"] = 0
                
                player_stats_list.append(stats)
            
            # Сортируем игроков по среднему счёту
            player_stats_list.sort(key=lambda x: x["average_score"], reverse=True)
            
            return {
                "zone": zone.to_dict(),
                "statistics": {
                    "total_rounds": total_rounds,
                    "average_score": average_score,
                    "average_distance": average_distance,
                    "score_distribution": score_distribution,
                    "player_stats": player_stats_list[:10],  # Топ-10 игроков
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting zone stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def cleanup_old_sessions(
        session: AsyncSession,
        days_old: int = 30
    ) -> Dict[str, int]:
        """
        Очистить старые сессии.
        
        Args:
            session: Асинхронная сессия БД
            days_old: Удалять сессии старше этого количества дней
            
        Returns:
            Словарь с количеством удалённых сессий и раундов
        """
        try:
            from sqlalchemy import delete
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Находим старые завершённые сессии
            old_sessions_stmt = select(GameSession).where(
                GameSession.status.in_([SessionStatus.FINISHED, SessionStatus.ABANDONED]),
                GameSession.finished_at < cutoff_date
            )
            
            old_sessions_result = await session.execute(old_sessions_stmt)
            old_sessions = old_sessions_result.scalars().all()
            
            deleted_sessions = 0
            deleted_rounds = 0
            
            for game_session in old_sessions:
                # Удаляем раунды сессии
                rounds_stmt = delete(Round).where(Round.session_id == game_session.id)
                result = await session.execute(rounds_stmt)
                deleted_rounds += result.rowcount
                
                # Удаляем сессию
                session.delete(game_session)
                deleted_sessions += 1
            
            await session.commit()
            
            logger.info(f"Cleaned up {deleted_sessions} old sessions and {deleted_rounds} rounds")
            
            return {
                "deleted_sessions": deleted_sessions,
                "deleted_rounds": deleted_rounds,
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error cleaning up old sessions: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def generate_daily_challenge(
        session: AsyncSession,
        date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Сгенерировать ежедневный челлендж.
        
        Args:
            session: Асинхронная сессия БД
            date: Дата челленджа (по умолчанию сегодня)
            
        Returns:
            Информация о челлендже или None
        """
        try:
            from app.services.challenge_generator import ChallengeGenerator
            
            if date is None:
                date = datetime.utcnow()
            
            # Используем seed на основе даты для детерминированного выбора
            seed = date.strftime("%Y%m%d")
            import random
            random.seed(seed)
            
            # Выбираем случайную зону
            generator = ChallengeGenerator(session)
            zones = await generator.get_available_zones(limit=100)
            
            if not zones:
                return None
            
            # Выбираем зону на основе seed
            zone = random.choice(zones)
            
            # Генерируем точку в зоне
            point = await generator.generate_random_point_in_zone(zone.id)
            if not point:
                return None
            
            challenge_id = f"daily_{date.strftime('%Y%m%d')}"
            
            return {
                "challenge_id": challenge_id,
                "date": date.strftime("%Y-%m-%d"),
                "zone": zone.to_dict(),
                "target_point": point,
                "view_extent_km": 10,  # Стандартный размер для ежедневных челленджей
                "description": f"Ежедневный челлендж {date.strftime('%d.%m.%Y')} - {zone.name}",
                "difficulty": zone.difficulty,
                "category": zone.category,
            }
            
        except Exception as e:
            logger.error(f"Error generating daily challenge: {e}")
            return None
    
    @staticmethod
    async def get_leaderboard(
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Получить таблицу лидеров.
        
        Args:
            session: Асинхронная сессия БД
            limit: Максимальное количество записей
            offset: Смещение
            
        Returns:
            Таблица лидеров
        """
        try:
            # Общий рейтинг (по ELO)
            elo_leaderboard_stmt = select(
                User.id,
                User.username,
                User.elo_rating,
                User.total_score,
                User.games_played,
                User.average_score,
                User.level
            ).where(
                User.is_active == True
            ).order_by(
                User.elo_rating.desc()
            ).limit(limit).offset(offset)
            
            elo_result = await session.execute(elo_leaderboard_stmt)
            elo_leaderboard = []
            
            for i, row in enumerate(elo_result, start=offset + 1):
                elo_leaderboard.append({
                    "rank": i,
                    "user_id": row.id,
                    "username": row.username,
                    "elo_rating": row.elo_rating,
                    "total_score": row.total_score,
                    "games_played": row.games_played,
                    "average_score": float(row.average_score) if row.average_score else 0,
                    "level": row.level,
                })
            
            # Рейтинг по общему счёту
            score_leaderboard_stmt = select(
                User.id,
                User.username,
                User.total_score,
                User.games_played,
                User.average_score,
                User.level
            ).where(
                User.is_active == True
            ).order_by(
                User.total_score.desc()
            ).limit(limit).offset(offset)
            
            score_result = await session.execute(score_leaderboard_stmt)
            score_leaderboard = []
            
            for i, row in enumerate(score_result, start=offset + 1):
                score_leaderboard.append({
                    "rank": i,
                    "user_id": row.id,
                    "username": row.username,
                    "total_score": row.total_score,
                    "games_played": row.games_played,
                    "average_score": float(row.average_score) if row.average_score else 0,
                    "level": row.level,
                })
            
            # Рейтинг по среднему счёту (минимум 10 игр)
            avg_score_leaderboard_stmt = select(
                User.id,
                User.username,
                User.average_score,
                User.games_played,
                User.total_score,
                User.level
            ).where(
                User.is_active == True,
                User.games_played >= 10
            ).order_by(
                User.average_score.desc()
            ).limit(limit).offset(offset)
            
            avg_score_result = await session.execute(avg_score_leaderboard_stmt)
            avg_score_leaderboard = []
            
            for i, row in enumerate(avg_score_result, start=offset + 1):
                avg_score_leaderboard.append({
                    "rank": i,
                    "user_id": row.id,
                    "username": row.username,
                    "average_score": float(row.average_score) if row.average_score else 0,
                    "games_played": row.games_played,
                    "total_score": row.total_score,
                    "level": row.level,
                })
            
            return {
                "elo_leaderboard": elo_leaderboard,
                "score_leaderboard": score_leaderboard,
                "avg_score_leaderboard": avg_score_leaderboard,
                "total_players": await ModelUtils._get_total_players(session),
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def _get_total_players(session: AsyncSession) -> int:
        """Получить общее количество активных игроков"""
        try:
            stmt = select(func.count(User.id)).where(User.is_active == True)
            result = await session.execute(stmt)
            return result.scalar() or 0
        except:
            return 0