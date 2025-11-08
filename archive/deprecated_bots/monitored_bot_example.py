#!/usr/bin/env python3
"""
Example: Selfology Bot with Comprehensive Monitoring Integration

This file demonstrates how to integrate the comprehensive monitoring system
with the main Selfology bot. It shows best practices for logging, tracing,
health monitoring, and metrics collection.
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add core monitoring modules to path
sys.path.append(str(Path(__file__).parent / "core"))

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Import monitoring system
from core.monitoring_orchestrator import (
    initialize_monitoring_system,
    start_monitoring_system,
    stop_monitoring_system,
    MonitoringConfig,
    get_monitoring_orchestrator
)
from core.enhanced_logging import (
    EnhancedLoggerMixin,
    trace_operation,
    set_user_context,
    EventType
)
from core.monitoring_dashboard import (
    track_user_activity,
    track_performance,
    track_ai_usage
)
from core.health_monitoring import get_health_monitor


class MonitoredSelfologyBot(EnhancedLoggerMixin):
    """
    Selfology Bot with comprehensive monitoring integration.
    Demonstrates best practices for monitoring a production bot.
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.startup_time = datetime.now(timezone.utc)
        
        # Setup message handlers with monitoring
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup bot handlers with monitoring integration"""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message, state: FSMContext):
            await self.handle_start_command(message, state)
        
        @self.dp.message(Command('health'))
        async def health_handler(message: Message):
            await self.handle_health_command(message)
        
        @self.dp.message(Command('stats'))
        async def stats_handler(message: Message):
            await self.handle_stats_command(message)
        
        @self.dp.message()
        async def message_handler(message: Message, state: FSMContext):
            await self.handle_user_message(message, state)
    
    async def handle_start_command(self, message: Message, state: FSMContext):
        """Handle /start command with monitoring"""
        user_id = message.from_user.id
        
        # Set user context for tracing
        set_user_context(user_id)
        
        with trace_operation("start_command", user_id=user_id) as trace:
            start_time = time.time()
            
            try:
                # Track user activity
                track_user_activity(user_id, "start_command", {
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name
                })
                
                # Log user action
                self.log_user_action("start_command", user_id, 
                                   username=message.from_user.username)
                
                # Send welcome message
                welcome_text = (
                    "🧠 Welcome to Selfology - Your AI Psychology Coach!\n\n"
                    "I'm here to help you understand yourself better through "
                    "personalized psychological assessments and conversations.\n\n"
                    "Commands:\n"
                    "• /health - Check system health\n"
                    "• /stats - View monitoring statistics\n"
                    "\nJust send me a message to start our conversation!"
                )
                
                await message.reply(welcome_text)
                
                # Track performance
                duration = time.time() - start_time
                track_performance("start_command", duration)
                self.log_performance("start_command", duration, user_id=user_id)
                
                # Log successful completion
                self.log_with_trace('info', "Start command completed successfully")
                
            except Exception as e:
                # Log error with trace context
                self.log_error("START_COMMAND_ERROR", 
                              f"Failed to handle start command: {e}",
                              user_id=user_id)
                
                await message.reply(
                    "Sorry, there was an issue processing your request. "
                    "Please try again later."
                )
                raise
    
    async def handle_health_command(self, message: Message):
        """Handle /health command - show system health status"""
        user_id = message.from_user.id
        set_user_context(user_id)
        
        with trace_operation("health_command", user_id=user_id):
            try:
                # Get health status from monitoring system
                health_monitor = get_health_monitor()
                if health_monitor:
                    health_status = await health_monitor.get_current_health_status()
                    
                    # Format health report
                    status_emoji = "🟢" if health_status['status'] == 'healthy' else "🔴"
                    health_text = f"{status_emoji} **System Health Status**\n\n"
                    health_text += f"Overall Status: {health_status['status'].title()}\n"
                    health_text += f"Last Check: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    
                    # Add service details
                    health_text += "**Services:**\n"
                    for service, details in health_status.get('services', {}).items():
                        service_emoji = "✅" if details.get('status') == 'healthy' else "❌"
                        response_time = details.get('response_time', 0)
                        health_text += f"{service_emoji} {service}: {details.get('status', 'unknown')} ({response_time:.2f}s)\n"
                    
                    # Add system metrics
                    system_metrics = health_status.get('system_metrics', {})
                    if system_metrics:
                        health_text += "\n**System Metrics:**\n"
                        health_text += f"💻 CPU: {system_metrics.get('cpu_percent', 0):.1f}%\n"
                        health_text += f"💾 Memory: {system_metrics.get('memory_percent', 0):.1f}%\n"
                        health_text += f"🗺️ Disk: {system_metrics.get('disk_percent', 0):.1f}%\n"
                else:
                    health_text = "⚠️ Health monitoring system is not available."
                
                await message.reply(health_text, parse_mode="Markdown")
                
                # Track health command usage
                track_user_activity(user_id, "health_command")
                
            except Exception as e:
                self.log_error("HEALTH_COMMAND_ERROR", f"Health command failed: {e}", user_id=user_id)
                await message.reply("❌ Failed to get health status.")
    
    async def handle_stats_command(self, message: Message):
        """Handle /stats command - show monitoring statistics"""
        user_id = message.from_user.id
        set_user_context(user_id)
        
        with trace_operation("stats_command", user_id=user_id):
            try:
                # Get monitoring orchestrator
                orchestrator = get_monitoring_orchestrator()
                if orchestrator:
                    # Get system status
                    system_status = await orchestrator.get_system_status()
                    
                    # Format stats report
                    stats_text = "📊 **Monitoring Statistics**\n\n"
                    
                    # System info
                    uptime_hours = system_status['uptime_seconds'] / 3600
                    stats_text += f"🚀 Service: {system_status['service_name']}\n"
                    stats_text += f"⏰ Uptime: {uptime_hours:.1f} hours\n"
                    stats_text += f"🌍 Environment: {system_status['environment']}\n\n"
                    
                    # Component status
                    stats_text += "**Components:**\n"
                    for component, details in system_status['components'].items():
                        status_emoji = "✅" if details['status'] == 'active' else "❌"
                        stats_text += f"{status_emoji} {component}: {details['status']}\n"
                    
                    # Monitoring stats
                    monitoring_stats = system_status.get('monitoring_stats', {})
                    if monitoring_stats:
                        stats_text += "\n**Performance:**\n"
                        error_stats = monitoring_stats.get('errors', {})
                        perf_stats = monitoring_stats.get('performance', {})
                        
                        stats_text += f"🚨 Total Errors: {error_stats.get('total_errors', 0)}\n"
                        stats_text += f"📈 Active Spans: {monitoring_stats.get('active_spans', 0)}\n"
                        stats_text += f"⚠️ Active Alerts: {monitoring_stats.get('active_alerts', 0)}\n"
                    
                    # Endpoints
                    if system_status.get('endpoints'):
                        stats_text += "\n**Endpoints:**\n"
                        for endpoint, url in system_status['endpoints'].items():
                            stats_text += f"🌐 {endpoint}: {url}\n"
                else:
                    stats_text = "⚠️ Monitoring system is not available."
                
                await message.reply(stats_text, parse_mode="Markdown")
                
                # Track stats command usage
                track_user_activity(user_id, "stats_command")
                
            except Exception as e:
                self.log_error("STATS_COMMAND_ERROR", f"Stats command failed: {e}", user_id=user_id)
                await message.reply("❌ Failed to get statistics.")
    
    async def handle_user_message(self, message: Message, state: FSMContext):
        """Handle regular user messages with comprehensive monitoring"""
        user_id = message.from_user.id
        message_text = message.text or ""
        
        # Set user context for all subsequent operations
        set_user_context(user_id)
        
        with trace_operation("user_message", user_id=user_id, message_length=len(message_text)) as trace:
            start_time = time.time()
            
            try:
                # Track user activity with detailed context
                track_user_activity(user_id, "message_sent", {
                    "message_length": len(message_text),
                    "message_type": message.content_type,
                    "username": message.from_user.username,
                    "has_entities": bool(message.entities)
                })
                
                # Log user action
                self.log_user_action("message_received", user_id,
                                   message_length=len(message_text),
                                   message_type=message.content_type)
                
                # Simulate AI processing with monitoring
                ai_response = await self._process_with_ai(message_text, user_id)
                
                # Send response
                await message.reply(ai_response)
                
                # Track successful completion
                duration = time.time() - start_time
                track_performance("message_processing", duration)
                track_user_activity(user_id, "response_sent", {
                    "response_length": len(ai_response),
                    "processing_time": duration
                })
                
                self.log_performance("message_processing", duration, 
                                   user_id=user_id, success=True)
                
                # Log business event
                self.log_business_event("conversation_interaction", 
                                       user_id=user_id,
                                       interaction_type="message_response",
                                       duration=duration)
                
            except Exception as e:
                # Comprehensive error handling with monitoring
                duration = time.time() - start_time
                
                # Log error with full context
                self.log_error("MESSAGE_PROCESSING_ERROR", 
                              f"Failed to process user message: {e}",
                              user_id=user_id,
                              message_length=len(message_text),
                              processing_time=duration)
                
                # Track failed performance
                track_performance("message_processing_failed", duration)
                
                # Send user-friendly error message
                await message.reply(
                    "I apologize, but I'm having trouble processing your message right now. "
                    "Please try again in a moment. If the issue persists, use /health to check system status."
                )
                
                # Re-raise for monitoring system to catch
                raise
    
    async def _process_with_ai(self, message_text: str, user_id: int) -> str:
        """Simulate AI processing with monitoring"""
        with trace_operation("ai_processing", user_id=user_id, model="simulated") as trace:
            start_time = time.time()
            
            try:
                # Simulate AI API call delay
                await asyncio.sleep(0.5)  # Simulate processing time
                
                # Track AI usage (simulated)
                duration = time.time() - start_time
                estimated_tokens = len(message_text.split()) * 1.3  # Rough estimate
                estimated_cost = estimated_tokens * 0.0001  # Rough cost estimate
                
                track_ai_usage("simulated_model", estimated_cost, int(estimated_tokens))
                
                # Log AI interaction
                self.log_ai_interaction(
                    "simulated_model",
                    tokens=int(estimated_tokens),
                    cost=estimated_cost,
                    response_time=duration,
                    user_id=user_id
                )
                
                # Generate response based on message
                if "hello" in message_text.lower():
                    response = "👋 Hello! I'm your AI psychology coach. How can I help you today?"
                elif "how are you" in message_text.lower():
                    response = "I'm functioning well, thank you! I'm here to help you explore your thoughts and feelings. What's on your mind?"
                elif "assessment" in message_text.lower():
                    response = "📋 I can help you with psychological assessments! Would you like to start with a personality assessment or explore specific areas like stress, anxiety, or mood?"
                else:
                    response = f"I understand you're sharing: '{message_text[:100]}...' Let me help you explore this further. What aspects of this situation would you like to discuss?"
                
                return response
                
            except Exception as e:
                # Log AI processing error
                self.log_error("AI_PROCESSING_ERROR", 
                              f"AI processing failed: {e}",
                              user_id=user_id,
                              model="simulated_model")
                raise
    
    async def start_bot(self):
        """Start the bot with monitoring integration"""
        try:
            self.log_with_trace('info', "Starting Selfology Bot with monitoring")
            
            # Log startup event
            self.log_business_event("bot_startup", 
                                   startup_time=self.startup_time.isoformat())
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            self.log_error("BOT_STARTUP_ERROR", f"Failed to start bot: {e}")
            raise
    
    async def stop_bot(self):
        """Stop the bot gracefully"""
        try:
            self.log_with_trace('info', "Stopping Selfology Bot")
            
            # Log shutdown event
            uptime = (datetime.now(timezone.utc) - self.startup_time).total_seconds()
            self.log_business_event("bot_shutdown", 
                                   uptime_seconds=uptime)
            
            await self.bot.session.close()
            
        except Exception as e:
            self.log_error("BOT_SHUTDOWN_ERROR", f"Error during bot shutdown: {e}")


async def main():
    """Main function with monitoring system initialization"""
    print("🧠 Initializing Selfology Bot with Comprehensive Monitoring...")
    
    # Get configuration from environment
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ Error: BOT_TOKEN environment variable is required")
        return
    
    try:
        # 1. Initialize monitoring system first
        print("📈 Initializing monitoring system...")
        config = MonitoringConfig(
            service_name="selfology_example",
            environment=os.getenv("ENVIRONMENT", "development"),
            dashboard_port=8000,
            api_port=8001,
            telegram_bot={"token": bot_token}
        )
        
        orchestrator = initialize_monitoring_system(config)
        
        # 2. Start monitoring system
        print("🚀 Starting monitoring system...")
        monitoring_started = await start_monitoring_system()
        
        if not monitoring_started:
            print("⚠️ Warning: Monitoring system failed to start completely")
        else:
            print("✅ Monitoring system started successfully")
            
            # Display monitoring endpoints
            system_status = await orchestrator.get_system_status()
            if system_status.get('endpoints'):
                print("\n🌐 Available monitoring endpoints:")
                for endpoint, url in system_status['endpoints'].items():
                    print(f"  • {endpoint.title()}: {url}")
        
        # 3. Initialize and start bot
        print("\n🤖 Initializing Selfology Bot...")
        bot = MonitoredSelfologyBot(bot_token)
        
        print("🚀 Starting bot polling...")
        print("\n🎉 Selfology Bot is running with comprehensive monitoring!")
        print("\nCommands:")
        print("  • /start - Welcome message")
        print("  • /health - System health status")
        print("  • /stats - Monitoring statistics")
        print("\nPress Ctrl+C to stop")
        
        # Start bot
        await bot.start_bot()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'bot' in locals():
            await bot.stop_bot()
        
        print("📋 Stopping monitoring system...")
        await stop_monitoring_system()
        print("✅ Shutdown complete")


if __name__ == "__main__":
    # Run the bot with monitoring
    asyncio.run(main())
