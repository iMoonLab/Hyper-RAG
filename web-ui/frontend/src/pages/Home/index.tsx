import React, { useState, useEffect, useRef } from 'react'
import { observer } from 'mobx-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import {
    MessageCircle,
    Send,
    Plus,
    Database,
    Settings,
    User,
    Bot,
    Trash2,
    RotateCcw,
    Loader2,
    Zap,
    Layers,
    BookOpen,
    GitCompare,
} from 'lucide-react'
import {
    Button,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    ScrollArea,
    Textarea,
    Separator,
    Avatar,
    AvatarFallback,
    AvatarImage
} from '../../components/ui'
import { storeGlobalUser } from '../../store/globalUser'
import { SERVER_URL } from '../../utils'
import DatabaseSelector from '../../components/DatabaseSelector'
import RetrievalInfo from '../../components/RetrievalInfo'
import RetrievalHyperGraph from '../../components/RetrievalHyperGraph'
import { conversations as defaultConversations } from './data'

const HyperRAGHome = () => {
    // State
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState('')
    const [inputValue, setInputValue] = useState('')
    const [queryMode, setQueryMode] = useState('hyper')
    const [isLoading, setIsLoading] = useState(false)
    const [availableModes, setAvailableModes] = useState(['naive', 'graph', 'hyper'])
    const messagesEndRef = useRef(null)

    // 新增对比模式相关状态
    const [isCompareMode, setIsCompareMode] = useState(false)
    const [compareMode1, setCompareMode1] = useState('hyper')
    const [compareMode2, setCompareMode2] = useState('naive')

    // Storage keys
    const STORAGE_KEYS = {
        CONVERSATIONS: 'hyperrag_conversations_v2',
        ACTIVE_ID: 'hyperrag_active_conversation_v2'
    }

    // 定义所有可用的模式配置
    const allModes = [
        // { value: 'llm', label: 'LLM', icon: Bot, color: 'bg-yellow-500' },
        // { value: 'naive', label: 'RAG', icon: BookOpen, color: 'bg-blue-500' },
        // { value: 'graph', label: 'Graph-RAG', icon: Bot, color: 'bg-orange-500' },
        { value: 'hyper', label: 'Hyper-RAG', icon: Zap, color: 'bg-purple-500' },
        // { value: 'hyper-lite', label: 'Hyper-RAG-Lite', icon: Layers, color: 'bg-green-500' }
    ]

    // 从localStorage加载Mode配置
    const loadModeSettings = () => {
        try {
            const modeSettings = localStorage.getItem('hyperrag_mode_settings')
            if (modeSettings) {
                const parsed = JSON.parse(modeSettings)
                if (parsed.availableModes && Array.isArray(parsed.availableModes) && parsed.availableModes.length > 0) {
                    setAvailableModes(['hyper'])
                    // 如果当前选择的mode不在可用列表中，选择第一个可用的mode
                    if (!parsed.availableModes.includes(queryMode)) {
                        setQueryMode(parsed.availableModes[0])
                    }
                } else {
                    // 如果没有配置或配置为空，使用默认配置
                    setAvailableModes(['hyper'])
                }
            }
        } catch (error) {
            console.error('Failed to load mode settings:', error)
            // 出错时使用默认配置
            setAvailableModes(['hyper'])
        }
    }

    // 监听localStorage变化
    const handleStorageChange = (e) => {
        if (e.key === 'hyperrag_mode_settings') {
            loadModeSettings()
        }
    }

    // 获取当前启用的模式列表
    const enabledModes = allModes.filter(mode => availableModes.includes(mode.value))

    // 获取模式标签的函数
    const getModeLabel = (roleValue) => {
        if (roleValue === 'user') {
return '用户'
}
        const mode = allModes.find(m => m.value === roleValue)
        return mode ? mode.label : roleValue
    }

    // Utility functions
    const saveToStorage = () => {
        localStorage.setItem(STORAGE_KEYS.CONVERSATIONS, JSON.stringify(conversations))
        localStorage.setItem(STORAGE_KEYS.ACTIVE_ID, activeConversationId)
    }

    const loadFromStorage = () => {
        try {
            const savedConversations = localStorage.getItem(STORAGE_KEYS.CONVERSATIONS)
            const savedActiveId = localStorage.getItem(STORAGE_KEYS.ACTIVE_ID)

            if (savedConversations) {
                const parsed = JSON.parse(savedConversations)
                setConversations(parsed)

                if (savedActiveId && parsed.find((c) => c.id === savedActiveId)) {
                    setActiveConversationId(savedActiveId)
                } else if (parsed.length > 0) {
                    setActiveConversationId(parsed[0].id)
                }
            } else {
                // Create default conversation
                const defaultConv = {
                    id: 'default',
                    title: `Chat ${new Date().toLocaleString('zh-CN', { hour12: false })}`,
                    messages: [],
                    createdAt: new Date()
                }
                setConversations([defaultConv])
                setActiveConversationId('default')
            }
        } catch (error) {
            console.error('Failed to load from storage:', error)
        }
    }

    const createNewConversation = () => {
        const newConv = {
            id: Date.now().toString(),
            title: `Chat ${new Date().toLocaleString('zh-CN', { hour12: false })}`,
            messages: [],
            createdAt: new Date()
        }
        setConversations(prev => [newConv, ...prev])
        setActiveConversationId(newConv.id)
    }

    const deleteConversation = (id) => {
        setConversations(prev => prev.filter(c => c.id !== id))
        if (activeConversationId === id) {
            const remaining = conversations.filter(c => c.id !== id)
            if (remaining.length > 0) {
                setActiveConversationId(remaining[0].id)
            } else {
                createNewConversation()
            }
        }
    }

    const clearAllChats = () => {
        setConversations([])
        createNewConversation()
    }

    const activeConversation = conversations.find(c => c.id === activeConversationId)

    const addMessage = (content, role, extraData = null) => {
        const newMessage = {
            id: Date.now(),
            content,
            role,
            timestamp: new Date(),
            // 添加检索信息字段
            entities: extraData?.entities || [],
            hyperedges: extraData?.hyperedges || [],
            text_units: extraData?.text_units || [],
            // 新增对比模式字段
            isCompare: extraData?.isCompare || false,
            compareResults: extraData?.compareResults || null
        }

        setConversations(prev =>
            prev.map(conv =>
                conv.id === activeConversationId
                    ? { ...conv, messages: [...conv.messages, newMessage] }
                    : conv
            )
        )
    }

    const updateLastMessage = (content, extraData = null) => {
        setConversations(prev =>
            prev.map(conv =>
                conv.id === activeConversationId
                    ? {
                        ...conv,
                        messages: conv.messages.map((msg, index) =>
                            index === conv.messages.length - 1
                                ? {
                                    ...msg,
                                    content,
                                    timestamp: new Date(), 
                                    // 如果有新的检索信息，更新它们
                                    entities: extraData?.entities || msg.entities || [],
                                    hyperedges: extraData?.hyperedges || msg.hyperedges || [],
                                    text_units: extraData?.text_units || msg.text_units || [],
                                    // 更新对比结果
                                    isCompare: extraData?.isCompare !== undefined ? extraData.isCompare : msg.isCompare,
                                    compareResults: extraData?.compareResults || msg.compareResults
                                }
                                : msg
                        )
                    }
                    : conv
            )
        )
    }

    // 单模式查询函数
    const querySingleMode = async (question, mode) => {
        const response = await fetch(`${SERVER_URL}/hyperrag/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                mode: mode,
                top_k: 60,
                max_token_for_text_unit: 1600,
                max_token_for_entity_context: 300,
                max_token_for_relation_context: 1600,
                only_need_context: false,
                response_type: 'Multiple Paragraphs',
                database: storeGlobalUser.selectedDatabase
            }),
        })
        console.log('response:', response)
        if (!response.ok) {
            throw new Error(`Network error: ${response.status}`)
        }

        return response.json()
    }

    const handleSubmit = async () => {
        if (!inputValue.trim() || isLoading) {
return
}

        const userMessage = inputValue.trim()
        setInputValue('')
        setIsLoading(true)

        // Add user message
        addMessage(userMessage, 'user')

        if (isCompareMode) {
            // 对比模式：同时查询两个模式
            addMessage('正在对比分析中...', 'compare', { isCompare: true })

            try {
                const [result1, result2] = await Promise.all([
                    querySingleMode(userMessage, compareMode1),
                    querySingleMode(userMessage, compareMode2)
                ])

                const modeNames = {
                    'hyper': 'Hyper-RAG',
                    'hyper-lite': 'Hyper-RAG-Lite',
                    'graph': 'Graph-RAG',
                    'naive': 'RAG',
                    'llm': 'LLM',
                }

                const compareResults = {
                    mode1: {
                        name: modeNames[compareMode1] || compareMode1,
                        mode: compareMode1,
                        response: result1.success ? (result1.response || 'No response content') : `Error: ${result1.message}`,
                        entities: result1.entities || [],
                        hyperedges: result1.hyperedges || [],
                        text_units: result1.text_units || [],
                        success: result1.success
                    },
                    mode2: {
                        name: modeNames[compareMode2] || compareMode2,
                        mode: compareMode2,
                        response: result2.success ? (result2.response || 'No response content') : `Error: ${result2.message}`,
                        entities: result2.entities || [],
                        hyperedges: result2.hyperedges || [],
                        text_units: result2.text_units || [],
                        success: result2.success
                    }
                }

                updateLastMessage('对比分析完成', {
                    isCompare: true,
                    compareResults: compareResults
                })

            } catch (error) {
                console.error('Error in compare mode:', error)
                updateLastMessage(`对比分析出错: ${error instanceof Error ? error.message : 'Unknown error'}`, {
                    isCompare: true
                })
            }
        } else {
            // 单模式查询（原有逻辑）
            addMessage('正在思考中...', queryMode)

            try {
                const data = await querySingleMode(userMessage, queryMode)

                if (data.success) {
                    const modeNames = {
                        'hyper': 'Hyper-RAG',
                        'hyper-lite': 'Hyper-RAG-Lite',
                        'graph': 'Graph-RAG',
                        'naive': 'RAG',
                        'llm': 'LLM',
                    }
                    const modeName = modeNames[queryMode] || queryMode

                    let responseContent = data.response || 'No response content'
                    responseContent += `\n\n---\n*Mode: ${modeName}*`

                    updateLastMessage(responseContent, {
                        entities: data.entities || [],
                        hyperedges: data.hyperedges || [],
                        text_units: data.text_units || []
                    })
                } else {
                    throw new Error(data.message || 'Query failed')
                }
            } catch (error) {
                console.error('Error sending message:', error)
                
                updateLastMessage(`Sorry, an error occurred: ${error instanceof Error ? error.message : 'Unknown error'}`)
            }
        }

        setIsLoading(false)
    }

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    // Effects
    useEffect(() => {
        storeGlobalUser.restoreSelectedDatabase()
        storeGlobalUser.loadDatabases()
        loadFromStorage()
        loadModeSettings()

        // 添加storage事件监听器
        window.addEventListener('storage', handleStorageChange)

        return () => {
            window.removeEventListener('storage', handleStorageChange)
        }
    }, [])

    useEffect(() => {
        if (conversations.length > 0) {
            saveToStorage()
        }
    }, [conversations, activeConversationId])

    // 当availableModes变化时，确保当前选择的mode在可用列表中
    useEffect(() => {
        if (availableModes.length > 0 && !availableModes.includes(queryMode)) {
            setQueryMode(availableModes[0])
        }
    }, [availableModes, queryMode])

    // 当对比模式切换时，确保选择的模式在可用列表中
    useEffect(() => {
        if (availableModes.length > 0) {
            if (!availableModes.includes(compareMode1)) {
                setCompareMode1(availableModes[0])
            }
            if (!availableModes.includes(compareMode2)) {
                setCompareMode2(availableModes[Math.min(1, availableModes.length - 1)])
            }
        }
    }, [availableModes, compareMode1, compareMode2])

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'nearest'
            })
        }
    }, [activeConversation?.messages, isLoading])

    return (
        <div className="flex bg-gray-50">
            {/* Sidebar */}
            <div className="w-52 bg-gray-100 border-r border-gray-200 flex flex-col">

                {/* Mode Selector */}
            
                
                {/* Header */}
                <Separator className="my-3" />
                <div className="p-4 border-b border-gray-200">
                    <Button
                        onClick={createNewConversation}
                        className="w-full"
                        variant="outline"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        开启新对话
                    </Button>
                </div>

                {/* Conversations List */}
                <ScrollArea className="flex-1 p-2">
                    <div className="space-y-2">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                className={`group p-1 rounded-lg cursor-pointer transition-colors ${activeConversationId === conv.id
                                    ? 'bg-blue-50 border border-blue-200'
                                    : 'hover:bg-gray-50'
                                    }`}
                                onClick={() => setActiveConversationId(conv.id)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                                        <MessageCircle className="w-4 h-4 text-gray-500" />
                                        <span className="text-sm font-medium text-gray-900 truncate">
                                            {conv.title}
                                        </span>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="opacity-0 group-hover:opacity-100 h-6 w-6"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            deleteConversation(conv.id)
                                        }}
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </Button>
                                </div>

                            </div>
                        ))}
                    </div>
                </ScrollArea>

                {/* Controls */}
                <div className="p-4 border-t border-gray-200 space-y-4">
                    <Button
                        variant="outline"
                        onClick={clearAllChats}
                        className="w-full"
                    >
                        <RotateCcw className="w-4 h-4 mr-2" />
                        删除所有对话
                    </Button>
                </div>

            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Top Bar */}
                {/* <div className="bg-white border-b border-gray-200 p-4">
                    <div className="flex items-center justify-between w-full">
                        <div className="flex items-center space-x-4">
                            <Database className="w-5 h-5 text-gray-500" />
                            <span className="font-medium text-gray-700">Database:</span>
                            <DatabaseSelector
                                mode="buttons"
                                showCurrent={true}
                                showRefresh={true}
                                placeholder=""
                                style={{}}
                                size="small"
                                disabled={false}
                            />
                        </div>
                    </div>
                </div> */}

                {/* Chat Area */}
                <div className="flex-1 flex flex-col">
                    {/* Messages */}
                    <ScrollArea className="p-4 pb-0 h-[calc(100vh-210px)] bg-white">
                        {activeConversation?.messages.length === 0 ? (
                            <div className="flex-1 flex items-center justify-center mt-20">
                                <div className="text-center">
                                    <Bot className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                                        欢迎使用 Hyper-RAG
                                    </h3>
                                    <p className="text-gray-500 max-w-md">
                                        请询问关于您知识库的任何问题。
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6 mx-auto">
                                    {activeConversation?.messages.map((message, index) => {
                                        // 判断是否是最后一条消息
                                        const isLastMessage = index === activeConversation.messages.length - 1;

                                        return (
                                            <div key={message.id + message.content}
                                                ref={isLastMessage ? messagesEndRef : null}
                                                className="flex space-x-4"
                                            >
                                            <Avatar>
                                                {message.role === 'user' ? (
                                                    <AvatarFallback>
                                                        <User className="w-5 h-5" />
                                                    </AvatarFallback>
                                                ) : (
                                                    <AvatarFallback>
                                                        {message.isCompare ? (
                                                            <GitCompare className="w-5 h-5" />
                                                        ) : (
                                                            <Bot className="w-5 h-5" />
                                                        )}
                                                    </AvatarFallback>
                                                )}
                                            </Avatar>

                                            <div className="flex-1 space-y-2">
                                                <div className="flex items-center space-x-2">
                                                    <span className="font-medium text-gray-900">
                                                        {message.isCompare ? '对比分析' : getModeLabel(message.role)}
                                                    </span>
                                                    <span className="text-xs text-gray-500">
                                                        {new Date(message.timestamp).toLocaleTimeString()}
                                                    </span>
                                                </div>

                                                {message.isCompare && message.compareResults ? (
                                                    /* 对比模式的消息展示 */
                                                    <div className="grid grid-cols-2 gap-4">
                                                        {/* 模式1结果 */}
                                                        <div className="flex flex-col bg-blue-50 border border-blue-200 rounded-lg p-4">
                                                            <div className="flex items-center space-x-2 mb-3">
                                                                <div className="flex items-center space-x-2">
                                                                    {(() => {
                                                                        const mode = allModes.find(m => m.value === message.compareResults.mode1.mode)
                                                                        const IconComponent = mode?.icon || Bot
                                                                        return <IconComponent className="w-4 h-4" />
                                                                    })()}
                                                                    <span className="font-medium text-blue-800">
                                                                        {message.compareResults.mode1.name}
                                                                    </span>
                                                                </div>
                                                                {!message.compareResults.mode1.success && (
                                                                    <span className="text-xs text-red-500">Failed</span>
                                                                )}
                                                            </div>

                                                            <div className="flex-1 flex flex-col">
                                                                <div className="flex-1 prose prose-sm">
                                                                    <ReactMarkdown
                                                                        remarkPlugins={[remarkGfm, remarkMath]}
                                                                        rehypePlugins={[rehypeRaw, rehypeKatex]}
                                                                        components={{
                                                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                            code: ({ children, className }) => (
                                                                                <code className={`${className} bg-blue-100 px-1 rounded`}>
                                                                                    {children}
                                                                                </code>
                                                                            ),
                                                                            pre: ({ children }) => (
                                                                                <pre className="bg-blue-100 p-3 rounded-md overflow-x-auto">
                                                                                    {children}
                                                                                </pre>
                                                                            ),
                                                                            table: ({ children }) => (
                                                                                <div className="overflow-x-auto my-4">
                                                                                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                                                                                        {children}
                                                                                    </table>
                                                                                </div>
                                                                            ),
                                                                            thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                                                                            th: ({ children }) => (
                                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                                                                                    {children}
                                                                                </th>
                                                                            ),
                                                                            tbody: ({ children }) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
                                                                            tr: ({ children }) => <tr>{children}</tr>,
                                                                            td: ({ children }) => (
                                                                                <td className="px-6 py-4 whitespace-pre-wrap text-sm text-gray-500 border-b border-gray-200">
                                                                                    {children}
                                                                                </td>
                                                                            ),
                                                                        }}
                                                                    >
                                                                        {message.compareResults.mode1.response}
                                                                    </ReactMarkdown>
                                                                </div>

                                                                {message.compareResults.mode1.success && (
                                                                    <div className='overflow-auto pl-2'>
                                                                        <RetrievalInfo
                                                                            entities={message.compareResults.mode1.entities || []}
                                                                            hyperedges={message.compareResults.mode1.hyperedges || []}
                                                                            textUnits={message.compareResults.mode1.text_units || []}
                                                                            mode={message.compareResults.mode1.mode}
                                                                        />

                                                                        {/* {((message.compareResults.mode1.entities && message.compareResults.mode1.entities.length > 0) ||
                                                                        (message.compareResults.mode1.hyperedges && message.compareResults.mode1.hyperedges.length > 0)) && (
                                                                            <div className="mt-4">
                                                                                <RetrievalHyperGraph
                                                                                    entities={message.compareResults.mode1.entities || []}
                                                                                    hyperedges={message.compareResults.mode1.hyperedges || []}
                                                                                    height="300px"
                                                                                    mode={message.compareResults.mode1.mode}
                                                                                    graphId={`compare-graph-1-${message.id}`}
                                                                                />
                                                                            </div>
                                                                        )} */}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* 模式2结果 */}
                                                        <div className="flex flex-col bg-green-50 border border-green-200 rounded-lg p-4">
                                                            <div className="flex items-center space-x-2 mb-3">
                                                                <div className="flex items-center space-x-2">
                                                                    {(() => {
                                                                        const mode = allModes.find(m => m.value === message.compareResults.mode2.mode)
                                                                        const IconComponent = mode?.icon || Bot
                                                                        return <IconComponent className="w-4 h-4" />
                                                                    })()}
                                                                    <span className="font-medium text-green-800">
                                                                        {message.compareResults.mode2.name}
                                                                    </span>
                                                                </div>
                                                                {!message.compareResults.mode2.success && (
                                                                    <span className="text-xs text-red-500">Failed</span>
                                                                )}
                                                            </div>

                                                            <div className="flex-1 flex flex-col">
                                                                <div className="flex-1 prose prose-sm">
                                                                    <ReactMarkdown
                                                                        remarkPlugins={[remarkGfm, remarkMath]}
                                                                        rehypePlugins={[rehypeRaw, rehypeKatex]}
                                                                        components={{
                                                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                            code: ({ children, className }) => (
                                                                                <code className={`${className} bg-blue-100 px-1 rounded`}>
                                                                                    {children}
                                                                                </code>
                                                                            ),
                                                                            pre: ({ children }) => (
                                                                                <pre className="bg-blue-100 p-3 rounded-md overflow-x-auto">
                                                                                    {children}
                                                                                </pre>
                                                                            ),
                                                                            table: ({ children }) => (
                                                                                <div className="overflow-x-auto my-4">
                                                                                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                                                                                        {children}
                                                                                    </table>
                                                                                </div>
                                                                            ),
                                                                            thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                                                                            th: ({ children }) => (
                                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                                                                                    {children}
                                                                                </th>
                                                                            ),
                                                                            tbody: ({ children }) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
                                                                            tr: ({ children }) => <tr>{children}</tr>,
                                                                            td: ({ children }) => (
                                                                                <td className="px-6 py-4 whitespace-pre-wrap text-sm text-gray-500 border-b border-gray-200">
                                                                                    {children}
                                                                                </td>
                                                                            ),
                                                                        }}
                                                                    >
                                                                        {message.compareResults.mode2.response}
                                                                    </ReactMarkdown>
                                                                </div>

                                                                {message.compareResults.mode2.success && (
                                                                    <div className='overflow-auto pl-2'>
                                                                        <RetrievalInfo
                                                                            entities={message.compareResults.mode2.entities || []}
                                                                            hyperedges={message.compareResults.mode2.hyperedges || []}
                                                                            textUnits={message.compareResults.mode2.text_units || []}
                                                                            mode={message.compareResults.mode2.mode}
                                                                        />

                                                                        {/* {((message.compareResults.mode2.entities && message.compareResults.mode2.entities.length > 0) ||
                                                                        (message.compareResults.mode2.hyperedges && message.compareResults.mode2.hyperedges.length > 0)) && (
                                                                            <div className="mt-4">
                                                                                <RetrievalHyperGraph
                                                                                    entities={message.compareResults.mode2.entities || []}
                                                                                    hyperedges={message.compareResults.mode2.hyperedges || []}
                                                                                    height="300px"
                                                                                    mode={message.compareResults.mode2.mode}
                                                                                    graphId={`compare-graph-2-${message.id}`}
                                                                                />
                                                                            </div>
                                                                        )} */}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    /* 单模式的消息展示（原有逻辑） */
                                                    <div className={`rounded-lg p-4 ${message.role === 'user'
                                                        ? 'bg-blue-50 border border-blue-200'
                                                        : 'bg-gray-50 border border-gray-200'
                                                        }`}>
                                                        {message.role !== 'user' ? (
                                                            <div className='flex'>
                                                                <div className="flex-1 prose prose-sm z-0">
                                                                    <ReactMarkdown
                                                                        remarkPlugins={[remarkGfm, remarkMath]}
                                                                        rehypePlugins={[rehypeRaw, rehypeKatex]}
                                                                        components={{
                                                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                            code: ({ children, className }) => (
                                                                                <code className={`${className} bg-blue-100 px-1 rounded`}>
                                                                                    {children}
                                                                                </code>
                                                                            ),
                                                                            pre: ({ children }) => (
                                                                                <pre className="bg-blue-100 p-3 rounded-md overflow-x-auto">
                                                                                    {children}
                                                                                </pre>
                                                                            ),
                                                                            table: ({ children }) => (
                                                                                <div className="overflow-x-auto my-4">
                                                                                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                                                                                        {children}
                                                                                    </table>
                                                                                </div>
                                                                            ),
                                                                            thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                                                                            th: ({ children }) => (
                                                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                                                                                    {children}
                                                                                </th>
                                                                            ),
                                                                            tbody: ({ children }) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
                                                                            tr: ({ children }) => <tr>{children}</tr>,
                                                                            td: ({ children }) => (
                                                                                <td className="px-6 py-4 whitespace-pre-wrap text-sm text-gray-500 border-b border-gray-200">
                                                                                    {children}
                                                                                </td>
                                                                            ),
                                                                        }}
                                                                    >
                                                                        {message.content}
                                                                    </ReactMarkdown>
                                                                </div>
                                                                <div className='flex-[0.7] overflow-auto pl-2 z-10'>
                                                                    {/* 显示检索信息 */}
                                                                    <RetrievalInfo
                                                                        entities={message.entities || []}
                                                                        hyperedges={message.hyperedges || []}
                                                                        textUnits={message.text_units || []}
                                                                        mode={message.role}
                                                                    />

                                                                    {/* 超图可视化展示 */}
                                                                    {/* {((message.entities && message.entities.length > 0) ||
                                                                    (message.hyperedges && message.hyperedges.length > 0)) && (
                                                                        <div className="mt-4">
                                                                            <RetrievalHyperGraph
                                                                                entities={message.entities || []}
                                                                                hyperedges={message.hyperedges || []}
                                                                                height="400px"
                                                                                mode={message.role}
                                                                                graphId={`retrieval-graph-${message.id}`}
                                                                            />
                                                                        </div>
                                                                    )} */}
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <p className="text-gray-900 whitespace-pre-wrap m-0">
                                                                {message.content}
                                                            </p>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </ScrollArea>

                    {/* Input Area */}
                    <div className="border-t border-gray-200 bg-white p-2 pb-10">
                        <div className="max-w-4xl mx-auto">
                            <div className="flex space-x-4 items-center">
                                <Textarea
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder={isCompareMode
                                        ? `对比 ${getModeLabel(compareMode1)} 和 ${getModeLabel(compareMode2)} 的回答...`
                                        : "提出您的问题..."
                                    }
                                    className="flex-1 h-7 resize-none"
                                    disabled={isLoading}
                                />
                                <Button
                                    onClick={handleSubmit}
                                    disabled={!inputValue.trim() || isLoading}
                                    size="lg"
                                    className="px-6"
                                >
                                    {isLoading ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default observer(HyperRAGHome)