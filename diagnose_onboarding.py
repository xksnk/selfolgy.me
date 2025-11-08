#!/usr/bin/env python3
"""
Диагностика системы онбординга
Полный анализ что произошло с сессией пользователя
"""

import asyncio
import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "intelligent_question_core"))

from selfology_bot.database import DatabaseService, OnboardingDAO
from selfology_bot.services.onboarding import OnboardingOrchestrator
from intelligent_question_core.api.core_api import SelfologyQuestionCore

async def diagnose_system():
    """Полная диагностика системы"""
    
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ ОНБОРДИНГА")
    print("=" * 50)
    
    user_id = 98005572
    
    try:
        # 1. Проверяем Question Core
        print("\n🧠 QUESTION CORE:")
        core = SelfologyQuestionCore()
        print(f"✅ Загружено вопросов: {len(core.questions_lookup)}")
        
        # Найдем q_143
        q_143 = core.get_question("q_143")
        if q_143:
            print(f"📝 Вопрос q_143: {q_143['text'][:50]}...")
            print(f"🏷️ Домен: {q_143['classification']['domain']}")
            print(f"🔍 Есть elaborations: {'elaborations' in q_143}")
        
        # 2. Проверяем базу данных
        print("\n🗄️ DATABASE:")
        db_service = DatabaseService()
        await db_service.initialize()
        
        dao = OnboardingDAO(db_service)
        
        # Проверяем сессии
        async with db_service.get_connection() as conn:
            sessions = await conn.fetch("""
                SELECT id, started_at, status, questions_asked, questions_answered 
                FROM onboarding_sessions 
                WHERE user_id = $1 
                ORDER BY started_at DESC
            """, user_id)
            
            print(f"📊 Сессий найдено: {len(sessions)}")
            for session in sessions:
                print(f"  • Session {session['id']}: {session['status']}, вопросов: {session['questions_asked']}")
            
            # Проверяем ответы
            answers = await conn.fetch("""
                SELECT ua.*, os.user_id 
                FROM user_answers_new ua
                JOIN onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
                ORDER BY ua.answered_at DESC
            """, user_id)
            
            print(f"💬 Ответов найдено: {len(answers)}")
            for answer in answers:
                print(f"  • Вопрос {answer['question_json_id']}: {answer['raw_answer'][:50]}...")
            
            # Проверяем анализы
            analyses = await conn.fetch("""
                SELECT aa.*, ua.question_json_id
                FROM answer_analysis aa
                JOIN user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN onboarding_sessions os ON ua.session_id = os.id  
                WHERE os.user_id = $1
                ORDER BY aa.processed_at DESC
            """, user_id)
            
            print(f"🧠 Анализов найдено: {len(analyses)}")
            for analysis in analyses:
                print(f"  • {analysis['question_json_id']}: модель {analysis['ai_model_used']}, качество {analysis['quality_score']}")
        
        # 3. Проверяем OnboardingOrchestrator
        print("\n🎯 ONBOARDING ORCHESTRATOR:")
        orchestrator = OnboardingOrchestrator()
        status = await orchestrator.get_system_status()
        
        print(f"📊 Статус: {status['status']}")
        print(f"🔧 Компоненты: {status['components']}")
        print(f"📈 Активных сессий: {status['active_sessions']}")
        
        # 4. Тестируем Question Router
        print("\n🎯 QUESTION ROUTER TEST:")
        
        # Проверяем разные типы поиска
        opening_questions = core.search_questions(energy="OPENING")
        safe_questions = core.search_questions(min_safety=3)
        any_questions = core.search_questions()
        
        print(f"🔍 OPENING вопросы: {len(opening_questions)}")
        print(f"🔍 Безопасные (min_safety=3): {len(safe_questions)}")
        print(f"🔍 Любые вопросы: {len(any_questions)}")
        
        if opening_questions:
            print(f"  • Первый OPENING: {opening_questions[0]['id']} - {opening_questions[0]['text'][:50]}")
        
        # 5. Проверяем векторную базу (mock)
        print("\n📈 VECTOR STORAGE (MOCK):")
        embedding_stats = await orchestrator.embedding_creator.get_embedding_stats()
        print(f"📊 Embedding статистика: {embedding_stats}")
        
        await db_service.close()
        
    except Exception as e:
        print(f"❌ Ошибка диагностики: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_system())