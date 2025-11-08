/**
 * K6 Load Testing Script for Selfology
 * Tests system performance under load
 *
 * Run: k6 run tests/performance/load-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiDuration = new Trend('api_duration');
const successfulRequests = new Counter('successful_requests');
const failedRequests = new Counter('failed_requests');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '3m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 50 },   // Ramp down to 50 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    'http_req_duration': ['p(95)<5000'], // 95% of requests should be below 5s
    'errors': ['rate<0.1'],               // Error rate should be below 10%
    'http_req_failed': ['rate<0.05'],     // Failed requests should be below 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8001';
const TELEGRAM_BOT_TOKEN = __ENV.TELEGRAM_BOT_TOKEN || 'test_token';

/**
 * Generate random user ID
 */
function randomUserId() {
  return Math.floor(Math.random() * 100000) + 1;
}

/**
 * Simulate user onboarding flow
 */
export default function() {
  const userId = randomUserId();

  // Test 1: Health check
  testHealthCheck();
  sleep(1);

  // Test 2: Start onboarding
  testStartOnboarding(userId);
  sleep(2);

  // Test 3: Answer questions
  testAnswerQuestions(userId, 5);
  sleep(2);

  // Test 4: Get profile
  testGetProfile(userId);
  sleep(1);
}

/**
 * Test health check endpoint
 */
function testHealthCheck() {
  const res = http.get(`${BASE_URL}/health`);

  const success = check(res, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 500ms': (r) => r.timings.duration < 500,
  });

  errorRate.add(!success);
  apiDuration.add(res.timings.duration);

  if (success) {
    successfulRequests.add(1);
  } else {
    failedRequests.add(1);
  }
}

/**
 * Test onboarding start
 */
function testStartOnboarding(userId) {
  const payload = JSON.stringify({
    user_id: userId,
    action: 'start_onboarding',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/api/onboarding/start`, payload, params);

  const success = check(res, {
    'start onboarding status is 200': (r) => r.status === 200,
    'start onboarding has session_id': (r) => {
      try {
        const json = JSON.parse(r.body);
        return json.session_id !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  errorRate.add(!success);
  apiDuration.add(res.timings.duration);

  if (success) {
    successfulRequests.add(1);
    return JSON.parse(res.body).session_id;
  } else {
    failedRequests.add(1);
    return null;
  }
}

/**
 * Test answering questions
 */
function testAnswerQuestions(userId, count) {
  const answers = [
    "Я стремлюсь к глубокому пониманию себя",
    "Иногда я чувствую неопределенность",
    "Мои отношения важны для меня",
    "Я хочу развиваться и расти",
    "Я ценю честность и открытость",
  ];

  for (let i = 0; i < count; i++) {
    const payload = JSON.stringify({
      user_id: userId,
      question_id: `Q${i + 1}`,
      answer: answers[i % answers.length],
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const res = http.post(`${BASE_URL}/api/onboarding/answer`, payload, params);

    const success = check(res, {
      [`answer ${i + 1} status is 200`]: (r) => r.status === 200,
      [`answer ${i + 1} response time < 10s`]: (r) => r.timings.duration < 10000,
    });

    errorRate.add(!success);
    apiDuration.add(res.timings.duration);

    if (success) {
      successfulRequests.add(1);
    } else {
      failedRequests.add(1);
    }

    sleep(1); // Wait between questions
  }
}

/**
 * Test getting user profile
 */
function testGetProfile(userId) {
  const res = http.get(`${BASE_URL}/api/profile/${userId}`);

  const success = check(res, {
    'get profile status is 200': (r) => r.status === 200,
    'get profile has personality data': (r) => {
      try {
        const json = JSON.parse(r.body);
        return json.personality !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  errorRate.add(!success);
  apiDuration.add(res.timings.duration);

  if (success) {
    successfulRequests.add(1);
  } else {
    failedRequests.add(1);
  }
}

/**
 * Setup function - runs once per VU
 */
export function setup() {
  console.log('=================================');
  console.log('Starting Selfology Load Test');
  console.log('=================================');
  console.log(`Base URL: ${BASE_URL}`);
  console.log('Test duration: 21 minutes');
  console.log('Max concurrent users: 100');
  console.log('=================================');
}

/**
 * Teardown function - runs once after all VUs finish
 */
export function teardown(data) {
  console.log('=================================');
  console.log('Load Test Completed');
  console.log('=================================');
  console.log('Check the summary above for results');
}

/**
 * Test Event Bus Monitor
 */
export function testEventBusMonitor() {
  const res = http.get('http://localhost:8080/metrics');

  check(res, {
    'event bus monitor is up': (r) => r.status === 200,
    'metrics are available': (r) => {
      try {
        const json = JSON.parse(r.body);
        return json.system_health !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
}

/**
 * Stress test - higher load
 */
export const stressOptions = {
  stages: [
    { duration: '5m', target: 200 },  // Ramp up to 200 users
    { duration: '10m', target: 200 }, // Stay at 200 users
    { duration: '5m', target: 0 },    // Ramp down
  ],
};

/**
 * Spike test - sudden traffic increase
 */
export const spikeOptions = {
  stages: [
    { duration: '1m', target: 10 },   // Normal load
    { duration: '1m', target: 500 },  // Spike!
    { duration: '1m', target: 10 },   // Back to normal
  ],
};

/**
 * Soak test - sustained load over time
 */
export const soakOptions = {
  stages: [
    { duration: '5m', target: 50 },   // Ramp up
    { duration: '60m', target: 50 },  // Soak for 1 hour
    { duration: '5m', target: 0 },    // Ramp down
  ],
};
