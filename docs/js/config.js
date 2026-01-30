/**
 * Application Configuration
 * @module config
 */

// API Configuration
export const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run';

// Timeouts
export const TIMEOUTS = {
    FAST: 5000,
    NORMAL: 10000,
    SLOW: 30000,
    UPLOAD: 60000
};

// Status Colors
export const COLORS = {
    status: {
        active: { color: 'var(--green)', emoji: '🟢', label: 'Active' },
        pending: { color: 'var(--yellow)', emoji: '🟡', label: 'Pending' },
        closed: { color: 'var(--text-muted)', emoji: '⚪', label: 'Closed' }
    },
    risk: {
        critical: 'var(--red)',
        high: 'var(--red)',
        elevated: 'var(--yellow)',
        moderate: 'var(--green)',
        low: 'var(--text-muted)',
        none: 'var(--green)'
    },
    strategy: {
        momentum: '#3b82f6',
        catalyst: '#8b5cf6',
        breakout: '#10b981',
        value: '#f59e0b',
        growth: '#ec4899'
    }
};

// Emojis
export const EMOJIS = {
    lifecycle: {
        'Early Growth': '🌱',
        'Rapid Expansion': '🚀',
        'Peak': '⛰️',
        'Mature': '🏢',
        'Declining': '📉'
    },
    recommendation: {
        'STRONG BUY': '🟢🟢',
        'BUY': '🟢',
        'WATCH': '🟡',
        'HOLD': '⚪',
        'AVOID': '🔴',
        'strong_buy': '💚',
        'buy': '🟢',
        'hold': '🟡',
        'sell': '🔴',
        'strong_sell': '🔴🔴'
    },
    strategy: {
        'momentum': '🚀',
        'catalyst': '⚡',
        'breakout': '📈',
        'value': '💎',
        'growth': '🌱'
    }
};

// Chart Configuration
export const CHART_CONFIG = {
    radar: {
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: '#3b82f6',
        borderWidth: 2,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#3b82f6'
    },
    colors: {
        primary: '#3b82f6',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        muted: '#6b7280'
    }
};
