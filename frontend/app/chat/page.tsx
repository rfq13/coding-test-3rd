"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  FileText,
  ChevronDown,
  Search,
  Trash2,
  Plus,
  Menu,
  X,
} from "lucide-react";
import { chatApi, documentApi } from "@/lib/api";
import { formatCurrency, formatLLMResponse } from "@/lib/utils";
import "katex/dist/katex.min.css";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: any[];
  metrics?: any;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<any[]>([]);
  const [loadingConversations, setLoadingConversations] =
    useState<boolean>(false);
  const [sidebarSearch, setSidebarSearch] = useState<string>("");
  const [documents, setDocuments] = useState<any[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState<boolean>(false);
  const [documentsError, setDocumentsError] = useState<string>("");
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load conversations on mount; don't create new automatically
    setLoadingConversations(true);
    chatApi
      .listConversations(undefined)
      .then((list) => {
        setConversations(list || []);
        if (list && list.length > 0) {
          const first = list[0];
          setConversationId(first.conversation_id);
          // Ensure complete history is loaded with getConversation call
          chatApi
            .getConversation(first.conversation_id)
            .then((conv) => {
              setMessages(
                (conv.messages || []).map((m: any) => ({
                  role: m.role,
                  content: m.content,
                  timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
                }))
              );
            })
            .catch((err) => {
              setErrorMsg(err?.message || "Failed to load first conversation");
            });
        }
      })
      .catch((err) => {
        setErrorMsg(err?.message || "Failed to load conversation list");
      })
      .finally(() => setLoadingConversations(false));
  }, []);

  useEffect(() => {
    // Load documents for selector
    setLoadingDocuments(true);
    setDocumentsError("");
    documentApi
      .list()
      .then((docs) => {
        setDocuments(docs || []);
      })
      .catch((err) => {
        setDocuments([]);
        setDocumentsError("Failed to load document list");
      })
      .finally(() => setLoadingDocuments(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshConversations = async (q?: string) => {
    try {
      const list = await chatApi.listConversations(undefined, q);
      setConversations(list || []);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to load conversation list");
    }
  };

  useEffect(() => {
    // Debounce search sidebar conversations
    const t = setTimeout(() => {
      refreshConversations(sidebarSearch || undefined);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sidebarSearch]);

  const handleNewConversation = async () => {
    try {
      const conv = await chatApi.createConversation(undefined);
      setConversationId(conv.conversation_id);
      setMessages([]);
      await refreshConversations();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to create conversation");
    }
  };

  const handleSelectConversation = async (cid: string) => {
    if (cid === conversationId) return;
    setConversationId(cid);
    try {
      const conv = await chatApi.getConversation(cid);
      setMessages(
        (conv.messages || []).map((m: any) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }))
      );
    } catch (e) {
      setErrorMsg((e as any)?.message || "Failed to load conversation");
    }
  };

  const handleDeleteConversation = async (cid: string) => {
    try {
      await chatApi.deleteConversation(cid);
      await refreshConversations();
      if (cid === conversationId) {
        const list = await chatApi.listConversations(undefined);
        if (list && list.length > 0) {
          const first = list[0];
          setConversationId(first.conversation_id);
          setMessages(
            (first.messages || []).map((m: any) => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
            }))
          );
        } else {
          // Do not create new conversation automatically; leave empty
          setConversationId(undefined);
          setMessages([]);
        }
      }
    } catch (e) {
      setErrorMsg((e as any)?.message || "Failed to delete conversation");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    // Create conversation if none exists on first send

    let cid = conversationId;
    if (!cid) {
      try {
        const conv = await chatApi.createConversation(undefined);
        cid = conv.conversation_id;
        setConversationId(cid);
        await refreshConversations();
      } catch (err) {
        setErrorMsg((err as any)?.message || "Failed to create conversation");
      }
    }

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await chatApi.query(
        input,
        undefined,
        cid,
        selectedDocumentIds.length ? selectedDocumentIds : undefined
      );

      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        metrics: response.metrics,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      setErrorMsg(error?.message || "Failed to send message");
      const errorMessage: Message = {
        role: "assistant",
        content: `Sorry, I encountered an error: ${
          error.response?.data?.detail || error.message
        }`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-12rem)] px-4 sm:px-6 lg:px-8">
      <div className="mb-4 sm:mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-1 sm:mb-2">
              Fund Analysis Chat
            </h1>
            <p className="text-sm sm:text-base text-gray-600">
              Ask questions about fund performance, metrics, and transactions
            </p>
          </div>
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {sidebarOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-4 flex items-start justify-between rounded border border-red-300 bg-red-50 text-red-700 p-3">
          <span className="text-sm">{errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            className="ml-2 text-sm underline hover:text-red-900"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md grid grid-cols-1 md:grid-cols-12 h-full">
        <div
          className={`${
            sidebarOpen
              ? "block absolute inset-y-0 left-0 z-50 w-3/4 sm:w-1/2 md:w-2/5 bg-white shadow-lg"
              : "hidden"
          } md:block md:col-span-4 lg:col-span-3 xl:col-span-3 border-r flex flex-col h-full`}
        >
          <div className="p-3 sm:p-4 border-b space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Conversations</h2>
              <button
                onClick={handleNewConversation}
                className="inline-flex items-center px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <Plus className="w-3 h-3 mr-1" /> New
              </button>
            </div>
            <div className="relative">
              <input
                type="text"
                value={sidebarSearch}
                onChange={(e) => setSidebarSearch(e.target.value)}
                placeholder="Search conversations..."
                className="w-full pl-8 pr-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Search className="w-4 h-4 text-gray-400 absolute left-2 top-2.5" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingConversations ? (
              <div className="p-4 text-gray-500 text-sm">Loading...</div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-gray-500 text-sm">No conversations</div>
            ) : (
              <ul>
                {conversations.map((c: any) => {
                  const firstUserMsg = (c.messages || []).find(
                    (m: any) => m.role === "user"
                  );
                  const baseMsg = firstUserMsg || (c.messages || [])[0];
                  const title = baseMsg
                    ? baseMsg.content.slice(0, 40)
                    : "Chat pertama";
                  const active = c.conversation_id === conversationId;
                  return (
                    <li
                      key={c.conversation_id}
                      className={`border-b p-3 flex items-center justify-between cursor-pointer ${
                        active ? "bg-blue-50" : ""
                      }`}
                      onClick={() => {
                        handleSelectConversation(c.conversation_id);
                        setSidebarOpen(false); // Close sidebar on mobile after selection
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 line-clamp-1">
                          {title}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(c.updated_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        className="text-gray-400 hover:text-red-600 flex-shrink-0 ml-2"
                        title="Delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConversation(c.conversation_id);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Panel chat */}
        <div className="col-span-1 md:col-span-8 lg:col-span-9 xl:col-span-9 flex flex-col">
          {/* Controls */}
          <div className="border-b p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center gap-3 relative">
            <div className="flex items-center gap-3">
              <DocumentSelector
                documents={documents}
                selectedIds={selectedDocumentIds}
                onChange={setSelectedDocumentIds}
                loading={loadingDocuments}
                error={documentsError}
              />
              <button
                type="button"
                className="text-xs text-blue-600 hover:underline whitespace-nowrap"
                onClick={() => setSelectedDocumentIds([])}
              >
                Use All Documents
              </button>
            </div>
            <div className="ml-auto" />
          </div>
          {/* Selected chips preview */}
          {selectedDocumentIds.length > 0 && (
            <div className="border-b px-3 sm:px-4 py-2 flex flex-wrap gap-2">
              {documents
                .filter((d: any) => selectedDocumentIds.includes(d.id))
                .slice(0, 5)
                .map((d: any) => (
                  <span
                    key={d.id}
                    className="text-xs px-2 py-1 bg-gray-100 border border-gray-200 rounded truncate max-w-[120px] sm:max-w-none"
                    title={d.file_name}
                  >
                    {d.file_name}
                  </span>
                ))}
              {selectedDocumentIds.length > 5 && (
                <span className="text-xs text-gray-500">
                  +{selectedDocumentIds.length - 5} lainnya
                </span>
              )}
            </div>
          )}
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6 max-h-[50vh] sm:max-h-[60vh] md:max-h-[64vh]">
            {messages.length === 0 && (
              <div className="text-center py-8 sm:py-12">
                <div className="text-gray-400 mb-4">
                  <FileText className="w-12 h-12 sm:w-16 sm:h-16 mx-auto" />
                </div>
                <h3 className="text-base sm:text-lg font-medium text-gray-900 mb-2">
                  Start a conversation
                </h3>
                <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-6">
                  Try asking questions like:
                </p>
                <div className="space-y-2 max-w-md mx-auto">
                  <SampleQuestion
                    question="What is the current DPI?"
                    onClick={() => setInput("What is the current DPI?")}
                  />
                  <SampleQuestion
                    question="Calculate the IRR for this fund"
                    onClick={() => setInput("Calculate the IRR for this fund")}
                  />
                  <SampleQuestion
                    question="What does Paid-In Capital mean?"
                    onClick={() => setInput("What does Paid-In Capital mean?")}
                  />
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

            {loading && (
              <div className="flex items-center space-x-2 text-gray-500">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Thinking...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t p-3 sm:p-4">
            <form onSubmit={handleSubmit} className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question using selected documents..."
                className="flex-1 px-3 sm:px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:text-base"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function DocumentSelector({
  documents,
  selectedIds,
  onChange,
  loading,
  error,
}: {
  documents: any[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  loading?: boolean;
  error?: string;
}) {
  const [open, setOpen] = useState(false);
  const [searchText, setSearchText] = useState("");

  const toggleOpen = () => setOpen((o) => !o);
  const close = () => setOpen(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const filtered = (documents || []).filter((d: any) =>
    (d.file_name || "").toLowerCase().includes(searchText.toLowerCase())
  );

  const isSelected = (id: number) => selectedIds.includes(id);
  const toggleId = (id: number) => {
    if (isSelected(id)) {
      onChange(selectedIds.filter((x) => x !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectAllVisible = () => {
    const visibleIds = filtered.map((d: any) => d.id);
    const merged = Array.from(new Set([...selectedIds, ...visibleIds]));
    onChange(merged);
  };

  const clearSelection = () => onChange([]);

  const selectedLabel =
    selectedIds.length === 0
      ? "All documents"
      : `${selectedIds.length} selected`;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleOpen}
        className="px-3 py-2 border border-gray-300 rounded-md text-sm flex items-center gap-2 hover:bg-gray-50"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-gray-700">Documents:</span>
        <span className="font-medium text-gray-900">{selectedLabel}</span>
        <ChevronDown className="w-4 h-4 text-gray-500" />
      </button>

      {open && (
        <div className="absolute z-20 mt-2 w-[280px] sm:w-[320px] md:w-[360px] bg-white border border-gray-200 rounded-md shadow-lg right-0">
          <div className="p-2 border-b flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search documents..."
                className="w-full pl-8 pr-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Search className="w-4 h-4 text-gray-400 absolute left-2 top-2.5" />
            </div>
            <button
              type="button"
              onClick={selectAllVisible}
              className="px-2 py-1 text-xs border rounded hover:bg-gray-50"
            >
              Select all
            </button>
            <button
              type="button"
              onClick={clearSelection}
              className="px-2 py-1 text-xs border rounded hover:bg-gray-50"
            >
              Clear selection
            </button>
          </div>

          <ul className="max-h-60 overflow-y-auto p-2 space-y-1" role="listbox">
            {loading && (
              <li className="px-2 py-2 text-xs text-gray-500">
                Loading documents...
              </li>
            )}
            {!loading && error && (
              <li className="px-2 py-2 text-xs text-red-600">{error}</li>
            )}
            {filtered.length === 0 && (
              <li className="text-xs text-gray-500 px-2 py-3">
                No documents found
              </li>
            )}
            {filtered.map((d: any) => (
              <li key={d.id}>
                <label className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isSelected(d.id)}
                    onChange={() => toggleId(d.id)}
                  />
                  <span className="text-sm text-gray-800 line-clamp-1">
                    {d.file_name}
                  </span>
                </label>
              </li>
            ))}
          </ul>

          <div className="border-t p-2 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {selectedIds.length === 0
                ? "use all documents"
                : `${selectedIds.length} documents selected`}
            </span>
            <button
              type="button"
              onClick={close}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-full sm:max-w-3xl ${
          isUser ? "ml-0 sm:ml-12" : "mr-0 sm:mr-12"
        }`}
      >
        <div
          className={`rounded-lg p-3 sm:p-4 ${
            isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
          }`}
        >
          <div
            dangerouslySetInnerHTML={{
              __html: formatLLMResponse(message.content),
            }}
          />
        </div>

        {/* Metrics Display */}
        {message.metrics && (
          <div className="mt-3 bg-white border border-gray-200 rounded-lg p-3 sm:p-4">
            <h4 className="font-semibold text-sm text-gray-700 mb-2">
              Calculated Metrics
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(message.metrics).map(([key, value]) => {
                if (value === null || value === undefined) return null;

                let displayValue: string;
                if (typeof value === "number" && key.includes("irr")) {
                  displayValue = `${value.toFixed(2)}%`;
                } else if (typeof value === "number") {
                  displayValue = formatCurrency(value);
                } else {
                  displayValue = String(value);
                }

                return (
                  <div key={key} className="text-sm">
                    <span className="text-gray-600">{key.toUpperCase()}:</span>{" "}
                    <span className="font-semibold">{displayValue}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Sources Display */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3">
            <details className="bg-white border border-gray-200 rounded-lg">
              <summary className="px-3 sm:px-4 py-2 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50">
                View Sources ({message.sources.length})
              </summary>
              <div className="px-3 sm:px-4 py-3 space-y-2 border-t">
                {message.sources.slice(0, 5).map((source, idx) => (
                  <div key={idx} className="text-xs bg-gray-50 p-2 rounded">
                    <p className="text-gray-700 line-clamp-3">
                      {source.content}
                    </p>
                    <div className="mt-1 text-gray-600 flex flex-wrap gap-2 sm:gap-3">
                      {source.score !== undefined && (
                        <span>
                          Relevance: {(source.score * 100).toFixed(0)}%
                        </span>
                      )}
                      {source.metadata?.page && (
                        <span>Page: {source.metadata.page}</span>
                      )}
                      {source.metadata?.section && (
                        <span>Section: {source.metadata.section}</span>
                      )}
                      {source.metadata?.table_type && (
                        <span>Table: {source.metadata.table_type}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        <p className="text-xs text-gray-500 mt-2">
          {message.timestamp.toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

function SampleQuestion({
  question,
  onClick,
}: {
  question: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 sm:px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition"
    >
      &quot;{question}&quot;
    </button>
  );
}
