import React, { useState, useEffect, useRef } from 'react'
import { FileText, Upload, Trash2, X, Check, Loader } from 'lucide-react'
import { documentAPI } from './services/api'

/**
 * DocumentPanel - Sidebar panel for uploading and managing documents
 */
function DocumentPanel({ isOpen, onClose }) {
    const [documents, setDocuments] = useState([])
    const [isUploading, setIsUploading] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(null)
    const [dragActive, setDragActive] = useState(false)
    const [error, setError] = useState(null)
    const fileInputRef = useRef(null)

    useEffect(() => {
        if (isOpen) {
            loadDocuments()
        }
    }, [isOpen])

    const loadDocuments = async () => {
        try {
            const data = await documentAPI.list()
            setDocuments(data.documents || [])
            setError(null)
        } catch (error) {
            console.error('Failed to load documents:', error)
            setError(error.message || 'Failed to connect to server')
        }
    }

    const handleUpload = async (files) => {
        if (!files || files.length === 0) return

        setIsUploading(true)

        for (const file of files) {
            try {
                setUploadProgress(file.name)
                await documentAPI.upload(file)
            } catch (error) {
                console.error(`Failed to upload ${file.name}:`, error)
                alert(`Upload failed: ${error.message || 'Unknown error'}`)
            }
        }

        setIsUploading(false)
        setUploadProgress(null)
        loadDocuments()
    }

    const handleDelete = async (docId) => {
        try {
            await documentAPI.delete(docId)
            setDocuments(prev => prev.filter(d => d.id !== docId))
        } catch (error) {
            console.error('Failed to delete document:', error)
        }
    }

    const handleDrag = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true)
        } else if (e.type === 'dragleave') {
            setDragActive(false)
        }
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleUpload(Array.from(e.dataTransfer.files))
        }
    }

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleUpload(Array.from(e.target.files))
        }
    }

    if (!isOpen) return null

    return (
        <div className="document-panel-overlay" onClick={onClose}>
            <div className="document-panel" onClick={e => e.stopPropagation()}>
                <div className="document-panel-header">
                    <h2>📄 Documents</h2>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div
                    className={`upload-zone ${dragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    {isUploading ? (
                        <>
                            <Loader size={32} className="spin" />
                            <p>Uploading {uploadProgress}...</p>
                        </>
                    ) : (
                        <>
                            <Upload size={32} />
                            <p>Drag & drop files here</p>
                            <span>or click to browse</span>
                            <span className="file-types">PDF, TXT, DOCX, MD</span>
                        </>
                    )}
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".pdf,.txt,.docx,.md,application/pdf,text/plain,text/markdown"
                        onChange={handleFileSelect}
                        style={{ display: 'none' }}
                    />
                </div>

                <div className="document-list">
                    {error ? (
                        <div className="empty-state">
                            <FileText size={40} color="var(--error)" />
                            <p style={{ color: 'var(--error)' }}>Connection Failed</p>
                            <span>{error}</span>
                            <button
                                onClick={() => loadDocuments()}
                                style={{
                                    marginTop: '12px',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer'
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    ) : documents.length === 0 ? (
                        <div className="empty-state">
                            <FileText size={40} />
                            <p>No documents uploaded</p>
                            <span>Upload documents to chat about them</span>
                        </div>
                    ) : (
                        documents.map(doc => (
                            <div key={doc.id} className="document-item">
                                <FileText size={18} />
                                <div className="document-info">
                                    <span className="doc-name">{doc.filename}</span>
                                    <span className="doc-chunks">{doc.chunks} chunks</span>
                                </div>
                                <button
                                    className="delete-btn"
                                    onClick={() => handleDelete(doc.id)}
                                    title="Delete document"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))
                    )}
                </div>

                <div className="document-panel-footer">
                    <p>📝 Uploaded documents are automatically used to answer your questions</p>
                </div>
            </div>
        </div>
    )
}

export default DocumentPanel
