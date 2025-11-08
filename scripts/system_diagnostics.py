#!/usr/bin/env python3
"""
System Diagnostics - Проверка целостности всей системы Selfology

Проверяет:
1. Контракты между компонентами
2. Целостность данных
3. Состояние векторной БД
4. Consistency между PostgreSQL и Qdrant
"""

import asyncio
import asyncpg
import aiohttp
from typing import Dict, List, Any
from datetime import datetime
import json

class SystemDiagnostics:
    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "user": "n8n",
            "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
            "database": "n8n"
        }
        self.qdrant_url = "http://localhost:6333"

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "errors": [],
            "warnings": []
        }

    async def run_all_checks(self):
        """Запустить все проверки"""

        print("🔍 Starting System Diagnostics...\n")

        # PostgreSQL checks
        await self.check_database_connection()
        await self.check_data_integrity()
        await self.check_contract_compliance()

        # Qdrant checks
        await self.check_qdrant_connection()
        await self.check_vector_integrity()

        # Cross-system checks
        await self.check_data_consistency()

        # Generate report
        self.generate_report()

    async def check_database_connection(self):
        """Проверка подключения к PostgreSQL"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            await conn.execute("SELECT 1")
            await conn.close()

            self._add_check("✅ PostgreSQL connection", "OK")
        except Exception as e:
            self._add_error("PostgreSQL connection", str(e))

    async def check_data_integrity(self):
        """Проверка целостности данных в PostgreSQL"""

        conn = await asyncpg.connect(**self.db_config)

        try:
            # 1. Количество ответов
            total_answers = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology.user_answers_new"
            )
            self._add_check(f"📊 Total answers", total_answers)

            # 2. Статусы ответов
            statuses = await conn.fetch("""
                SELECT analysis_status, COUNT(*) as count
                FROM selfology.user_answers_new
                GROUP BY analysis_status
            """)
            for status_row in statuses:
                self._add_check(
                    f"  - Status '{status_row['analysis_status']}'",
                    status_row['count']
                )

            # 3. Количество анализов
            total_analyses = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology.answer_analysis"
            )
            self._add_check(f"🔬 Total analyses", total_analyses)

            # 4. Несоответствия: answered но без анализа
            orphaned = await conn.fetch("""
                SELECT ua.id, ua.analysis_status
                FROM selfology.user_answers_new ua
                LEFT JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
                WHERE ua.analysis_status IN ('analyzed', 'completed')
                  AND aa.id IS NULL
            """)

            if orphaned:
                for row in orphaned:
                    self._add_warning(
                        f"Orphaned answer {row['id']}",
                        f"Marked as '{row['analysis_status']}' but NO analysis found"
                    )

            # 5. Проверка personality_summary в анализах
            analyses_without_summary = await conn.fetch("""
                SELECT id, user_answer_id
                FROM selfology.answer_analysis
                WHERE NOT (raw_ai_response ? 'personality_summary')
                   OR raw_ai_response->'personality_summary' = 'null'::jsonb
                   OR raw_ai_response->'personality_summary' = '{}'::jsonb
            """)

            if analyses_without_summary:
                self._add_warning(
                    f"{len(analyses_without_summary)} analyses WITHOUT personality_summary",
                    f"IDs: {[r['id'] for r in analyses_without_summary]}"
                )
            else:
                self._add_check("✅ All analyses have personality_summary", "OK")

        finally:
            await conn.close()

    async def check_contract_compliance(self):
        """Проверка соблюдения контрактов"""

        conn = await asyncpg.connect(**self.db_config)

        try:
            # Проверяем последний анализ
            last_analysis = await conn.fetchrow("""
                SELECT id, raw_ai_response
                FROM selfology.answer_analysis
                ORDER BY id DESC
                LIMIT 1
            """)

            if last_analysis:
                response = last_analysis['raw_ai_response']

                # Парсим JSON если строка
                if isinstance(response, str):
                    response = json.loads(response)

                # Обязательные ключи по контракту (РЕАЛЬНАЯ СТРУКТУРА)
                required_keys = [
                    "personality_summary",
                    "psychological_analysis",  # ✅ DICT, не psychological_insights
                    "personality_traits",      # ✅ DICT, не trait_scores
                    "quality_metadata",
                    "router_recommendations",
                    "processing_metadata",
                    "analysis_version",
                    "created_at"
                ]

                missing_keys = [k for k in required_keys if k not in response]

                if missing_keys:
                    self._add_error(
                        f"❌ CONTRACT VIOLATION in analysis {last_analysis['id']}",
                        f"Missing keys: {missing_keys}"
                    )
                else:
                    self._add_check("✅ Last analysis follows contract", "OK")

                # Проверяем структуру personality_summary
                if "personality_summary" in response:
                    summary = response["personality_summary"]
                    required_summary_keys = ["nano", "narrative", "embedding_prompt"]
                    missing_summary = [k for k in required_summary_keys if k not in summary]

                    if missing_summary:
                        self._add_warning(
                            f"personality_summary incomplete",
                            f"Missing: {missing_summary}"
                        )
                    else:
                        self._add_check("✅ personality_summary structure valid", "OK")

        finally:
            await conn.close()

    async def check_qdrant_connection(self):
        """Проверка подключения к Qdrant"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.qdrant_url}/collections") as resp:
                    if resp.status == 200:
                        self._add_check("✅ Qdrant connection", "OK")
                    else:
                        self._add_error("Qdrant connection", f"Status {resp.status}")
        except Exception as e:
            self._add_error("Qdrant connection", str(e))

    async def check_vector_integrity(self):
        """Проверка векторов в Qdrant"""

        # ✅ ИСПРАВЛЕНО: используем РЕАЛЬНЫЕ имена коллекций из embedding_creator.py
        collections = [
            "personality_profiles",      # Standard personality (1536D)
            "quick_match",               # Quick search (512D)
            "personality_evolution"      # Evolution tracking (1536D)
        ]

        async with aiohttp.ClientSession() as session:
            for collection in collections:
                try:
                    async with session.get(f"{self.qdrant_url}/collections/{collection}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            points_count = data["result"]["points_count"]
                            self._add_check(f"📈 {collection}", f"{points_count} vectors")

                            if points_count == 0:
                                self._add_warning(
                                    f"{collection} is EMPTY",
                                    "No vectors created"
                                )
                        else:
                            self._add_error(f"{collection}", f"Status {resp.status}")

                except Exception as e:
                    self._add_error(f"{collection}", str(e))

    async def check_data_consistency(self):
        """Проверка consistency между PostgreSQL и Qdrant"""

        conn = await asyncpg.connect(**self.db_config)

        try:
            # Сколько ответов с completed анализом?
            completed = await conn.fetchval("""
                SELECT COUNT(*)
                FROM selfology.user_answers_new ua
                JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
                WHERE ua.analysis_status = 'completed'
            """)

            # Сколько векторов в Qdrant?
            total_vectors = 0
            async with aiohttp.ClientSession() as session:
                # ✅ ИСПРАВЛЕНО: используем РЕАЛЬНЫЕ имена коллекций
                for collection in ["personality_profiles", "quick_match", "personality_evolution"]:
                    try:
                        async with session.get(f"{self.qdrant_url}/collections/{collection}") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                total_vectors += data["result"]["points_count"]
                    except:
                        pass

            self._add_check(f"🔗 Completed analyses", completed)
            self._add_check(f"📊 Total vectors in Qdrant", total_vectors)

            # Они должны совпадать!
            if completed > total_vectors:
                self._add_error(
                    "❌ DATA INCONSISTENCY",
                    f"{completed} completed analyses but only {total_vectors} vectors!"
                )
            elif completed == total_vectors == 0:
                self._add_warning(
                    "⚠️ No data",
                    "Both PostgreSQL and Qdrant are empty"
                )
            else:
                self._add_check("✅ Data consistency", "OK")

        finally:
            await conn.close()

    def _add_check(self, name: str, value: Any):
        self.results["checks"].append({"name": name, "value": value})
        print(f"{name}: {value}")

    def _add_error(self, name: str, message: str):
        self.results["errors"].append({"name": name, "message": message})
        print(f"❌ ERROR - {name}: {message}")

    def _add_warning(self, name: str, message: Any):
        self.results["warnings"].append({"name": name, "message": message})
        print(f"⚠️  WARNING - {name}: {message}")

    def generate_report(self):
        """Генерация итогового отчета"""

        print("\n" + "="*60)
        print("📋 DIAGNOSTIC REPORT")
        print("="*60)

        print(f"\n✅ Checks passed: {len(self.results['checks'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"❌ Errors: {len(self.results['errors'])}")

        if self.results['errors']:
            print("\n🔴 CRITICAL ERRORS:")
            for error in self.results['errors']:
                print(f"  - {error['name']}: {error['message']}")

        if self.results['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in self.results['warnings']:
                print(f"  - {warning['name']}: {warning['message']}")

        # Сохраняем в файл
        report_file = f"/tmp/selfology_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n📄 Full report saved to: {report_file}")


async def main():
    diagnostics = SystemDiagnostics()
    await diagnostics.run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
