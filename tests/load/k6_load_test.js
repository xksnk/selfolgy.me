/**
 * K6 Load Testing Script for Selfology Microservices
 *
 * Tests:
 * - Onboarding flow (session creation + questions)
 * - Answer submission + analysis
 * - Chat interactions
 * - Profile queries
 *
 * Load profiles:
 * - smoke: 1 VU for 30s (basic validation)
 * - load: 50 VUs for 5m (normal traffic)
 * - stress: 100 VUs ramping to 200 (peak traffic)
 * - spike: 200 VUs for 1m (sudden spike)
 *
 * Run:
 *   k6 run --env PROFILE=smoke tests/load/k6_load_test.js
 *   k6 run --env PROFILE=load tests/load/k6_load_test.js
 *   k6 run --env PROFILE=stress tests/load/k6_load_test.js
 *
 * Thresholds:
 * - Instant analysis: p95 < 500ms
 * - Question selection: p95 < 200ms
 * - Profile query: p95 < 300ms
 * - Success rate: > 95%
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================================
// CUSTOM METRICS
// ============================================================================

const instantAnalysisLatency = new Trend('instant_analysis_latency');
const deepAnalysisLatency = new Trend('deep_analysis_latency');
const questionSelectionLatency = new Trend('question_selection_latency');
const profileQueryLatency = new Trend('profile_query_latency');
const chatLatency = new Trend('chat_latency');

const errorRate = new Rate('errors');
const successRate = new Rate('success');

const onboardingCompleted = new Counter('onboarding_completed');
const chatMessagesExchanged = new Counter('chat_messages_exchanged');

// ============================================================================
// LOAD PROFILES
// ============================================================================

const profiles = {
    smoke: {
        stages: [
            { duration: '30s', target: 1 }
        ],
        thresholds: {
            'http_req_duration': ['p95<1000'],
            'errors': ['rate<0.05']
        }
    },
    load: {
        stages: [
            { duration: '1m', target: 20 },   // Ramp-up
            { duration: '5m', target: 50 },   // Sustained load
            { duration: '1m', target: 0 }     // Ramp-down
        ],
        thresholds: {
            'instant_analysis_latency': ['p95<500'],
            'question_selection_latency': ['p95<200'],
            'profile_query_latency': ['p95<300'],
            'chat_latency': ['p95<1000'],
            'errors': ['rate<0.05'],
            'success': ['rate>0.95']
        }
    },
    stress: {
        stages: [
            { duration: '2m', target: 50 },
            { duration: '5m', target: 100 },
            { duration: '2m', target: 200 },  // Stress zone
            { duration: '2m', target: 100 },
            { duration: '1m', target: 0 }
        ],
        thresholds: {
            'instant_analysis_latency': ['p95<800'],
            'errors': ['rate<0.10']
        }
    },
    spike: {
        stages: [
            { duration: '10s', target: 50 },
            { duration: '30s', target: 200 }, // Spike
            { duration: '1m', target: 50 },
            { duration: '10s', target: 0 }
        ],
        thresholds: {
            'errors': ['rate<0.15']
        }
    }
};

const PROFILE = __ENV.PROFILE || 'smoke';
export const options = profiles[PROFILE];

// ============================================================================
// CONFIGURATION
// ============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const REDIS_HOST = __ENV.REDIS_HOST || 'n8n-redis';
const DB_HOST = __ENV.DB_HOST || 'n8n-postgres';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function generateUserId() {
    return Math.floor(Math.random() * 1000000) + 100000;
}

function publishEvent(eventType, payload) {
    /**
     * Simulates publishing event to EventBus via HTTP API
     * (In real setup, you'd need a REST API wrapper for Redis Streams)
     */
    const response = http.post(`${BASE_URL}/api/v1/events`, JSON.stringify({
        event_type: eventType,
        payload: payload,
        timestamp: new Date().toISOString()
    }), {
        headers: { 'Content-Type': 'application/json' },
        timeout: '5s'
    });

    return response;
}

function queryDatabase(query) {
    /**
     * Simulates database query via HTTP API
     */
    const response = http.post(`${BASE_URL}/api/v1/db/query`, JSON.stringify({
        query: query
    }), {
        headers: { 'Content-Type': 'application/json' },
        timeout: '3s'
    });

    return response;
}

// ============================================================================
// SCENARIO: ONBOARDING FLOW
// ============================================================================

export function onboardingFlow() {
    const userId = generateUserId();
    const sessionId = `session_${userId}_${Date.now()}`;

    // Step 1: Initiate onboarding
    let response = publishEvent('user.onboarding.initiated', {
        user_id: userId,
        timestamp: new Date().toISOString()
    });

    check(response, {
        'onboarding initiated': (r) => r.status === 200
    }) ? successRate.add(1) : errorRate.add(1);

    sleep(1); // Wait for session creation

    // Step 2: Request questions (3 cycles)
    for (let i = 0; i < 3; i++) {
        const startQuestion = Date.now();

        response = queryDatabase(`
            SELECT question_id, question_text
            FROM selfology.questions_metadata
            WHERE id = (
                SELECT payload->>'question_id'
                FROM selfology.event_outbox
                WHERE event_type = 'question.selected'
                AND payload->>'session_id' = '${sessionId}'
                ORDER BY created_at DESC
                LIMIT 1
            )
        `);

        const questionLatency = Date.now() - startQuestion;
        questionSelectionLatency.add(questionLatency);

        check(response, {
            'question selected': (r) => r.status === 200,
            'question latency OK': (r) => questionLatency < 500
        }) ? successRate.add(1) : errorRate.add(1);

        // Step 3: Submit answer
        const answerText = `This is my thoughtful answer to question ${i + 1}. It reflects my personality and values deeply.`;

        const startInstantAnalysis = Date.now();

        response = publishEvent('user.answer.submitted', {
            user_id: userId,
            session_id: sessionId,
            question_id: `q_${i + 1}`,
            answer_text: answerText,
            answer_length: answerText.length
        });

        check(response, {
            'answer submitted': (r) => r.status === 200
        }) ? successRate.add(1) : errorRate.add(1);

        sleep(0.5); // Wait for instant analysis

        // Verify instant analysis completed
        const instantLatency = Date.now() - startInstantAnalysis;
        instantAnalysisLatency.add(instantLatency);

        check(instantLatency, {
            'instant analysis < 500ms': (latency) => latency < 500
        });

        sleep(1); // Natural delay between questions
    }

    // Step 4: Verify profile created
    sleep(3); // Wait for deep analysis

    const startProfileQuery = Date.now();

    response = queryDatabase(`
        SELECT profile_data
        FROM selfology.personality_profiles
        WHERE user_id = ${userId}
    `);

    const profileLatency = Date.now() - startProfileQuery;
    profileQueryLatency.add(profileLatency);

    const profileCreated = check(response, {
        'profile created': (r) => r.status === 200 && r.body.includes('big_five'),
        'profile query fast': (r) => profileLatency < 300
    });

    if (profileCreated) {
        onboardingCompleted.add(1);
        successRate.add(1);
    } else {
        errorRate.add(1);
    }
}

// ============================================================================
// SCENARIO: CHAT INTERACTION
// ============================================================================

export function chatInteraction() {
    const userId = generateUserId();
    const messageText = "I'm feeling anxious about my future career. What should I do?";

    // Step 1: Send user message
    const startChat = Date.now();

    let response = publishEvent('user.message.received', {
        user_id: userId,
        message_text: messageText,
        current_state: 'chat_active'
    });

    check(response, {
        'message received': (r) => r.status === 200
    }) ? successRate.add(1) : errorRate.add(1);

    sleep(2); // Wait for AI response

    // Step 2: Verify coach response
    response = queryDatabase(`
        SELECT content
        FROM selfology.conversations
        WHERE user_id = ${userId}
        AND role = 'assistant'
        ORDER BY created_at DESC
        LIMIT 1
    `);

    const chatLatencyValue = Date.now() - startChat;
    chatLatency.add(chatLatencyValue);

    const responseReceived = check(response, {
        'coach responded': (r) => r.status === 200 && r.body.length > 50,
        'response time acceptable': (r) => chatLatencyValue < 3000
    });

    if (responseReceived) {
        chatMessagesExchanged.add(1);
        successRate.add(1);
    } else {
        errorRate.add(1);
    }
}

// ============================================================================
// SCENARIO: PROFILE QUERY (READ-HEAVY)
// ============================================================================

export function profileQuery() {
    const userId = Math.floor(Math.random() * 10000) + 1; // Query existing profiles

    const startQuery = Date.now();

    const response = queryDatabase(`
        SELECT profile_data, updated_at
        FROM selfology.personality_profiles
        WHERE user_id = ${userId}
    `);

    const queryLatency = Date.now() - startQuery;
    profileQueryLatency.add(queryLatency);

    check(response, {
        'profile query successful': (r) => r.status === 200,
        'query fast': (r) => queryLatency < 300
    }) ? successRate.add(1) : errorRate.add(1);
}

// ============================================================================
// DEFAULT SCENARIO (MIX OF ALL)
// ============================================================================

export default function() {
    const scenario = Math.random();

    if (scenario < 0.4) {
        // 40% onboarding flows
        onboardingFlow();
    } else if (scenario < 0.7) {
        // 30% chat interactions
        chatInteraction();
    } else {
        // 30% profile queries
        profileQuery();
    }

    sleep(Math.random() * 2 + 1); // 1-3s between requests
}

// ============================================================================
// TEARDOWN
// ============================================================================

export function teardown(data) {
    console.log('=====================================');
    console.log('LOAD TEST SUMMARY');
    console.log('=====================================');
    console.log(`Profile: ${PROFILE}`);
    console.log(`Total Onboardings Completed: ${onboardingCompleted.value}`);
    console.log(`Total Chat Messages Exchanged: ${chatMessagesExchanged.value}`);
    console.log('=====================================');
}
