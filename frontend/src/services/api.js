/**
 * API Service for Ira Backend
 */

const API_BASE = 'http://localhost:8000'

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`

    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    }

    const response = await fetch(url, config)

    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
    }

    return response.json()
}

/**
 * Conversation API
 */
export const conversationAPI = {
    list: () => fetchAPI('/api/conversations'),

    create: (title) => fetchAPI('/api/conversations', {
        method: 'POST',
        body: JSON.stringify({ title }),
    }),

    get: (id) => fetchAPI(`/api/conversations/${id}`),

    delete: (id) => fetchAPI(`/api/conversations/${id}`, {
        method: 'DELETE',
    }),

    update: (id, title) => fetchAPI(`/api/conversations/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ title }),
    }),
}

/**
 * Chat API
 */
export const chatAPI = {
    send: async (conversationId, message, imageBase64 = null) => {
        const formData = new FormData()
        formData.append('conversation_id', conversationId)
        formData.append('message', message)

        if (imageBase64) {
            // Convert base64 to blob
            const response = await fetch(imageBase64)
            const blob = await response.blob()
            formData.append('image', blob, 'image.png')
        }

        const res = await fetch(`${API_BASE}/api/chat?conversation_id=${conversationId}&message=${encodeURIComponent(message)}`, {
            method: 'POST',
        })

        if (!res.ok) {
            throw new Error(`Chat API error: ${res.status}`)
        }

        return res.json()
    },

    // WebSocket connection helper
    connectStream: (conversationId) => {
        return new WebSocket(`ws://127.0.0.1:8000/ws/chat/${conversationId}`)
    },
}

/**
 * Voice API
 */
export const voiceAPI = {
    transcribe: async (audioBlob) => {
        const formData = new FormData()
        formData.append('audio', audioBlob, 'recording.wav')

        const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
            method: 'POST',
            body: formData,
        })

        if (!response.ok) {
            throw new Error('Transcription failed')
        }

        return response.json()
    },

    synthesize: async (text) => {
        const response = await fetch(`${API_BASE}/api/voice/synthesize?text=${encodeURIComponent(text)}`, {
            method: 'POST',
        })

        if (!response.ok) {
            throw new Error('Speech synthesis failed')
        }

        return response.blob()
    },
}

/**
 * Document API
 */
export const documentAPI = {
    list: () => fetchAPI('/api/documents'),

    upload: async (file) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${API_BASE}/api/documents/upload`, {
            method: 'POST',
            body: formData,
        })

        if (!response.ok) {
            throw new Error('Document upload failed')
        }

        return response.json()
    },

    delete: (id) => fetchAPI(`/api/documents/${id}`, {
        method: 'DELETE',
    }),

    query: (query, topK = 5) => fetchAPI(`/api/documents/query?query=${encodeURIComponent(query)}&top_k=${topK}`, {
        method: 'POST',
    }),
}

/**
 * Home Assistant API
 */
export const homeAPI = {
    getEntities: () => fetchAPI('/api/home/entities'),

    executeCommand: (command) => fetchAPI('/api/home/command', {
        method: 'POST',
        body: JSON.stringify({ command }),
    }),
}
