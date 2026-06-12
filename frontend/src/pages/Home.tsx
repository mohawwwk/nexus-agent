import { useState, useRef, useEffect, useCallback } from "react";
import { useRunAgent, useSendClarification } from "@workspace/api-client-react";
import type { ConversationEntry } from "@workspace/api-client-react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { Loader2, Trash2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

// Extended type for locally tracked messages (includes agent result fields)
type LocalMessage = ConversationEntry & {
  status?: string;
  clarification_question?: string;
  extracted_text?: string;
  cost_estimate?: string;
  duration_seconds?: number;
};

export default function Home() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const { toast } = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);

  // All messages are tracked locally — no history endpoint driving state
  // (history overwrites caused messages to disappear on refetch)
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [isPending, setIsPending] = useState(false);

  const runAgent = useRunAgent();
  const sendClarification = useSendClarification();

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  const addMessages = useCallback((...msgs: LocalMessage[]) => {
    setMessages(prev => [...prev, ...msgs]);
  }, []);

  const handleSend = useCallback(async (query: string, files: File[]) => {
    if ((!query.trim() && files.length === 0) || isPending) return;

    // Immediately show user message (optimistic)
    const userMsg: LocalMessage = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: "user",
      content: query,
      files: files.map(f => f.name),
      plan_trace: [],
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsPending(true);

    const formData = new FormData();
    formData.append("query", query);
    formData.append("session_id", sessionId);
    files.forEach(f => formData.append("files", f));

    try {
      const result = await runAgent.mutateAsync({ data: formData as any });

      const assistantMsg: LocalMessage = {
        id: crypto.randomUUID(),
        session_id: sessionId,
        role: "assistant",
        content: result.final_answer || result.clarification_question || "",
        files: [],
        plan_trace: result.plan_trace || [],
        timestamp: new Date().toISOString(),
        status: result.status,
        clarification_question: result.clarification_question ?? undefined,
        extracted_text: result.extracted_text ?? undefined,
        cost_estimate: result.cost_estimate ?? undefined,
        duration_seconds: result.duration_seconds ?? undefined,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      toast({
        title: "Error",
        description: "Failed to reach the agent. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsPending(false);
    }
  }, [sessionId, isPending, runAgent, toast]);

  const handleClarification = useCallback(async (clarification: string) => {
    if (!clarification.trim() || isPending) return;

    const userMsg: LocalMessage = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: "user",
      content: clarification,
      files: [],
      plan_trace: [],
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsPending(true);

    try {
      const result = await sendClarification.mutateAsync({
        data: { session_id: sessionId, clarification },
      });

      const assistantMsg: LocalMessage = {
        id: crypto.randomUUID(),
        session_id: sessionId,
        role: "assistant",
        content: result.final_answer || result.clarification_question || "",
        files: [],
        plan_trace: result.plan_trace || [],
        timestamp: new Date().toISOString(),
        status: result.status,
        clarification_question: result.clarification_question ?? undefined,
        extracted_text: result.extracted_text ?? undefined,
        cost_estimate: result.cost_estimate ?? undefined,
        duration_seconds: result.duration_seconds ?? undefined,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      toast({
        title: "Error",
        description: "Failed to send clarification.",
        variant: "destructive",
      });
    } finally {
      setIsPending(false);
    }
  }, [sessionId, isPending, sendClarification, toast]);

  const handleClear = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      <header className="flex-none h-14 border-b flex items-center justify-between px-6 bg-card/50 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <h1 className="font-semibold tracking-tight">Nexus Agent</h1>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear chat
            </Button>
          )}
          <ThemeToggle />
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8"
      >
        {messages.length === 0 && !isPending ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center text-primary mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold tracking-tight">How can I help you today?</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Upload documents, images, or audio files. Ask complex questions. I'll plan the steps and find the answers.
            </p>
            <div className="grid grid-cols-2 gap-2 w-full mt-2">
              {[
                { label: "Summarize a PDF", action: () => handleSend("Summarize this document", []) },
                { label: "Analyze sentiment", action: () => handleSend("Analyze the sentiment of: This product is amazing! I love it.", []) },
                { label: "Explain code", action: () => handleSend("Explain this code:\ndef fib(n):\n  return n if n <= 1 else fib(n-1)+fib(n-2)", []) },
                { label: "What can you do?", action: () => handleSend("What tasks can you help me with?", []) },
              ].map(({ label, action }) => (
                <button
                  key={label}
                  onClick={action}
                  disabled={isPending}
                  className="text-left px-3 py-2.5 rounded-lg border bg-card hover:bg-muted/50 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id || i}
                message={msg}
                onClarify={handleClarification}
                isLast={i === messages.length - 1 && msg.role === "assistant"}
              />
            ))}

            {isPending && (
              <div className="flex items-center gap-3 text-muted-foreground animate-in fade-in slide-in-from-bottom-2 pl-2">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                </div>
                <span className="text-xs font-medium uppercase tracking-wider">Processing</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex-none p-4 md:p-6 bg-gradient-to-t from-background via-background to-transparent pt-10">
        <div className="max-w-4xl mx-auto">
          <ChatInput onSend={handleSend} disabled={isPending} />
        </div>
      </div>
    </div>
  );
}
