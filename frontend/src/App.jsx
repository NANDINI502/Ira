import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import {
    MessageSquare,
    Plus,
    Send,
    Mic,
    MicOff,
    Image as ImageIcon,
    FileText,
    Code,
    Home,
    X,
    Volume2,
    VolumeX,
    Edit2,
    Trash2,
    Check
} from 'lucide-react'
import { chatAPI, voiceAPI, conversationAPI } from './services/api'
import DocumentPanel from './DocumentPanel'

function App() {
    const [conversations, setConversations] = useState([])
    const [activeConversation, setActiveConversation] = useState(null)
    const [messages, setMessages] = useState([])
    const [inputValue, setInputValue] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isRecording, setIsRecording] = useState(false)
    const [selectedImage, setSelectedImage] = useState(null)
    const [isOnline, setIsOnline] = useState(true)
    const [isDocPanelOpen, setIsDocPanelOpen] = useState(false)
    const [speakingMsgIdx, setSpeakingMsgIdx] = useState(null)
    const [editingConvId, setEditingConvId] = useState(null)
    const [editTitle, setEditTitle] = useState('')

    const messagesEndRef = useRef(null)
    const fileInputRef = useRef(null)
    const textareaRef = useRef(null)

    // Initialize
    useEffect(() => {
        loadConversations()
        checkConnection()
    }, [])

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
        }
    }, [inputValue])

    const checkConnection = async () => {
        try {
            const response = await fetch('http://127.0.0.1:8000/')
            setIsOnline(response.ok)
        } catch {
            setIsOnline(false)
        }
    }

    const loadConversations = async () => {
        try {
            const data = await conversationAPI.list()
            setConversations(data.conversations || [])
        } catch (error) {
            console.error('Failed to load conversations:', error)
        }
    }

    const createNewConversation = async () => {
        try {
            const conversation = await conversationAPI.create('New Chat')
            setConversations(prev => [conversation, ...prev])
            setActiveConversation(conversation.id)
            setMessages([])
        } catch (error) {
            console.error('Failed to create conversation:', error)
        }
    }

    const selectConversation = async (id) => {
        try {
            const data = await conversationAPI.get(id)
            setActiveConversation(id)
            setMessages(data.messages || [])
        } catch (error) {
            console.error('Failed to load conversation:', error)
        }
    }

    const startEditing = (conv, e) => {
        e.stopPropagation()
        setEditingConvId(conv.id)
        setEditTitle(conv.title)
    }

    const saveTitle = async (id, e) => {
        e.stopPropagation()
        if (!editTitle.trim()) return

        // Optimistic update
        setConversations(prev => prev.map(c => c.id === id ? { ...c, title: editTitle } : c))
        setEditingConvId(null)

        try {
            await conversationAPI.update(id, editTitle)
        } catch (error) {
            console.error('Failed to update conversation:', error)
            // Revert on error would be ideal, but for now just log
        }
    }

    const cancelEditing = (e) => {
        e.stopPropagation()
        setEditingConvId(null)
        setEditTitle('')
    }

    const deleteConversation = async (id, e) => {
        e.stopPropagation()
        if (!window.confirm("Delete this chat?")) return

        setConversations(prev => prev.filter(c => c.id !== id))

        if (activeConversation === id) {
            setActiveConversation(null)
            setMessages([])
        }

        try {
            await conversationAPI.delete(id)
        } catch (error) {
            console.error('Failed to delete conversation:', error)
        }
    }

    const handleSend = async () => {
        if (!inputValue.trim() && !selectedImage) return
        if (!activeConversation) {
            await createNewConversation()
        }

        const userMessage = {
            role: 'user',
            content: inputValue,
            image: selectedImage
        }

        setMessages(prev => [...prev, userMessage])
        setInputValue('')
        setSelectedImage(null)
        setIsLoading(true)

        try {
            // Use WebSocket for streaming
            const ws = new WebSocket(`ws://127.0.0.1:8000/ws/chat/${activeConversation}`)

            let assistantMessage = { role: 'assistant', content: '' }
            setMessages(prev => [...prev, assistantMessage])

            ws.onopen = () => {
                ws.send(JSON.stringify({
                    message: inputValue,
                    image: selectedImage
                }))
            }

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)

                if (data.type === 'chunk') {
                    setMessages(prev => {
                        const updated = [...prev]
                        updated[updated.length - 1] = {
                            ...updated[updated.length - 1],
                            content: updated[updated.length - 1].content + data.content
                        }
                        return updated
                    })
                } else if (data.type === 'done') {
                    setIsLoading(false)
                    ws.close()
                }
            }

            ws.onerror = () => {
                // Fallback to REST API
                handleSendREST(inputValue)
            }

        } catch (error) {
            console.error('WebSocket error, falling back to REST:', error)
            handleSendREST(inputValue)
        }
    }

    const handleSendREST = async (message) => {
        try {
            const response = await chatAPI.send(activeConversation, message, selectedImage)
            setMessages(prev => [
                ...prev.slice(0, -1), // Remove loading placeholder
                { role: 'assistant', content: response.response }
            ])
        } catch (error) {
            console.error('Failed to send message:', error)
            setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: 'Sorry, I encountered an error. Please check if the backend is running.' }
            ])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleImageSelect = (e) => {
        const file = e.target.files?.[0]
        if (file) {
            const reader = new FileReader()
            reader.onload = (e) => {
                setSelectedImage(e.target.result)
            }
            reader.readAsDataURL(file)
        }
    }

    const toggleRecording = async () => {
        if (isRecording) {
            // Stop recording
            if (window.speechRecognition) {
                window.speechRecognition.stop()
            }
            setIsRecording(false)
        } else {
            // Use browser's built-in Speech Recognition API
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
            if (SpeechRecognition) {
                const recognition = new SpeechRecognition()
                window.speechRecognition = recognition
                recognition.continuous = false
                recognition.interimResults = true
                recognition.lang = 'en-US'

                recognition.onresult = (event) => {
                    let transcript = ''
                    for (let i = 0; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript
                    }
                    if (event.results[0]?.isFinal) {
                        setInputValue(prev => (prev ? prev + ' ' : '') + transcript.trim())
                    }
                }

                recognition.onend = () => {
                    setIsRecording(false)
                    window.speechRecognition = null
                }

                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error)
                    setIsRecording(false)
                    window.speechRecognition = null
                }

                recognition.start()
                setIsRecording(true)
            } else {
                console.error('Speech recognition not supported in this browser')
                alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.')
            }
        }
    }

    const speakMessage = async (text, msgIdx) => {
        if (speakingMsgIdx === msgIdx) {
            // Stop speaking
            if (window.currentAudio) {
                window.currentAudio.pause()
                window.currentAudio = null
            }
            window.speechSynthesis?.cancel()
            setSpeakingMsgIdx(null)
            return
        }

        // Strip markdown formatting for cleaner speech
        const cleanText = text
            .replace(/```[\s\S]*?```/g, ' code block ')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/#{1,6}\s/g, '')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/[-*+]\s/g, '')
            .trim()

        if (!cleanText) return

        setSpeakingMsgIdx(msgIdx)

        // Use browser's built-in Web Speech API
        if ('speechSynthesis' in window) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel()

            const utterance = new SpeechSynthesisUtterance(cleanText)
            utterance.rate = 1.0
            utterance.pitch = 1.05
            utterance.volume = 1.0

            // Get voices - may need to wait for them to load
            let voices = window.speechSynthesis.getVoices()
            if (voices.length === 0) {
                // Voices not loaded yet, wait for them
                await new Promise(resolve => {
                    window.speechSynthesis.onvoiceschanged = () => {
                        voices = window.speechSynthesis.getVoices()
                        resolve()
                    }
                    // Timeout after 1 second
                    setTimeout(resolve, 1000)
                })
            }

            // Pick a female English voice
            const preferred = voices.find(v => v.name.includes('Microsoft Zira'))
                || voices.find(v => v.name.includes('Microsoft Eva'))
                || voices.find(v => v.lang.startsWith('en') && /female|zira|eva|samantha|karen|fiona|moira|susan|hazel|linda/i.test(v.name))
                || voices.find(v => v.lang.startsWith('en'))
            if (preferred) {
                utterance.voice = preferred
                console.log('Using voice:', preferred.name)
            }

            utterance.onend = () => {
                setSpeakingMsgIdx(null)
            }
            utterance.onerror = (e) => {
                console.error('Speech error:', e)
                setSpeakingMsgIdx(null)
            }

            window.speechSynthesis.speak(utterance)
        } else {
            console.error('Speech synthesis not supported in this browser')
            setSpeakingMsgIdx(null)
        }
    }

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <div className="logo">Ira</div>
                    <span className="sidebar-title">AI Assistant</span>
                </div>

                <button className="new-chat-btn" onClick={createNewConversation}>
                    <Plus size={18} />
                    New Chat
                </button>

                <div className="conversation-list">
                    {conversations.map(conv => (
                        <div
                            key={conv.id}
                            className={`conversation-item ${conv.id === activeConversation ? 'active' : ''}`}
                            onClick={() => selectConversation(conv.id)}
                        >
                            <MessageSquare size={16} />

                            {editingConvId === conv.id ? (
                                <div className="edit-title-container">
                                    <input
                                        className="edit-title-input"
                                        value={editTitle}
                                        onChange={e => setEditTitle(e.target.value)}
                                        onClick={e => e.stopPropagation()}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') saveTitle(conv.id, e)
                                            if (e.key === 'Escape') cancelEditing(e)
                                        }}
                                        autoFocus
                                    />
                                    <button className="conv-action-btn" onClick={e => saveTitle(conv.id, e)}><Check size={14} /></button>
                                    <button className="conv-action-btn" onClick={cancelEditing}><X size={14} /></button>
                                </div>
                            ) : (
                                <div className="conv-content">
                                    <span>{conv.title}</span>
                                    <div className="conv-actions">
                                        <button className="conv-action-btn" onClick={e => startEditing(conv, e)} title="Rename"><Edit2 size={13} /></button>
                                        <button className="conv-action-btn delete" onClick={e => deleteConversation(conv.id, e)} title="Delete"><Trash2 size={13} /></button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <button
                    className="sidebar-docs-btn"
                    onClick={() => setIsDocPanelOpen(true)}
                >
                    <FileText size={18} />
                    Documents
                </button>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <header className="chat-header">
                    <span className="chat-title">
                        {activeConversation ? 'Chat' : 'Welcome'}
                    </span>
                    <div className="status-indicator">
                        <span className={`status-dot ${isOnline ? '' : 'offline'}`}></span>
                        {isOnline ? 'Online' : 'Offline'}
                    </div>
                </header>

                {!activeConversation ? (
                    <WelcomeScreen onNewChat={createNewConversation} />
                ) : (
                    <>
                        <div className="messages-container">
                            {messages.map((msg, idx) => (
                                <div key={idx} className={`message ${msg.role}`}>
                                    <div className="message-avatar">
                                        {msg.role === 'user' ? 'You' : 'Ira'}
                                    </div>
                                    <div className="message-content">
                                        {msg.image && (
                                            <img
                                                src={msg.image}
                                                alt="Uploaded"
                                                style={{ maxWidth: '300px', borderRadius: '8px', marginBottom: '12px' }}
                                            />
                                        )}
                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        {isLoading && idx === messages.length - 1 && msg.role === 'assistant' && !msg.content && (
                                            <div className="typing-indicator">
                                                <span></span>
                                                <span></span>
                                                <span></span>
                                            </div>
                                        )}
                                        {msg.role === 'assistant' && msg.content && (
                                            <button
                                                className={`speak-btn ${speakingMsgIdx === idx ? 'speaking' : ''}`}
                                                onClick={() => speakMessage(msg.content, idx)}
                                                title={speakingMsgIdx === idx ? 'Stop speaking' : 'Read aloud'}
                                            >
                                                {speakingMsgIdx === idx ? <VolumeX size={16} /> : <Volume2 size={16} />}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>

                        <div className="input-container">
                            {selectedImage && (
                                <div className="image-preview">
                                    <img src={selectedImage} alt="Selected" />
                                    <button className="remove-btn" onClick={() => setSelectedImage(null)}>
                                        <X size={14} />
                                    </button>
                                </div>
                            )}

                            <div className="input-wrapper">
                                <div className="input-actions">
                                    <button
                                        className="action-btn"
                                        onClick={() => fileInputRef.current?.click()}
                                        title="Upload image"
                                    >
                                        <ImageIcon size={20} />
                                    </button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        accept="image/*"
                                        onChange={handleImageSelect}
                                        style={{ display: 'none' }}
                                    />
                                    <button
                                        className={`action-btn ${isRecording ? 'recording' : ''}`}
                                        onClick={toggleRecording}
                                        title={isRecording ? 'Stop recording' : 'Voice input'}
                                    >
                                        {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
                                    </button>
                                </div>

                                <textarea
                                    ref={textareaRef}
                                    className="message-input"
                                    placeholder="Type a message... (Shift+Enter for new line)"
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    rows={1}
                                />

                                <button
                                    className="send-btn"
                                    onClick={handleSend}
                                    disabled={isLoading || (!inputValue.trim() && !selectedImage)}
                                >
                                    <Send size={18} />
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </main>

            <DocumentPanel
                isOpen={isDocPanelOpen}
                onClose={() => setIsDocPanelOpen(false)}
            />
        </div>
    )
}

function WelcomeScreen({ onNewChat }) {
    return (
        <div className="welcome-screen">
            <div className="welcome-logo">Ira</div>
            <h1 className="welcome-title">Welcome to Ira</h1>
            <p className="welcome-subtitle">
                Your fully offline AI assistant. Chat, analyze images, ask questions about your documents, and control your smart home.
            </p>

            <div className="feature-grid">
                <div className="feature-card" onClick={onNewChat}>
                    <div className="feature-icon">
                        <MessageSquare size={20} />
                    </div>
                    <div className="feature-title">Chat</div>
                    <div className="feature-desc">Natural conversation with memory</div>
                </div>

                <div className="feature-card" onClick={onNewChat}>
                    <div className="feature-icon">
                        <ImageIcon size={20} />
                    </div>
                    <div className="feature-title">Vision</div>
                    <div className="feature-desc">Analyze and understand images</div>
                </div>

                <div className="feature-card" onClick={onNewChat}>
                    <div className="feature-icon">
                        <FileText size={20} />
                    </div>
                    <div className="feature-title">Documents</div>
                    <div className="feature-desc">Q&A over your files</div>
                </div>

                <div className="feature-card" onClick={onNewChat}>
                    <div className="feature-icon">
                        <Code size={20} />
                    </div>
                    <div className="feature-title">Coding</div>
                    <div className="feature-desc">Code assistance & execution</div>
                </div>
            </div>
        </div>
    )
}

export default App
