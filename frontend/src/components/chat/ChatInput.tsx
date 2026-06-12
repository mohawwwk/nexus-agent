import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Paperclip, X, Send, Mic, Image as ImageIcon, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ChatInputProps {
  onSend: (text: string, files: File[]) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleSubmit = () => {
    if ((!text.trim() && files.length === 0) || disabled) return;
    onSend(text, files);
    setText("");
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (type: string) => {
    if (type.startsWith("image/")) return <ImageIcon className="w-3 h-3 mr-1" />;
    if (type.startsWith("audio/")) return <Mic className="w-3 h-3 mr-1" />;
    return <FileText className="w-3 h-3 mr-1" />;
  };

  return (
    <div className="relative rounded-xl border bg-card text-card-foreground shadow-sm focus-within:ring-1 focus-within:ring-primary transition-all">
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 p-3 pb-0">
          {files.map((file, i) => (
            <Badge key={i} variant="secondary" className="flex items-center gap-1 pl-2 pr-1 py-1 text-xs">
              {getFileIcon(file.type)}
              <span className="truncate max-w-[150px]">{file.name}</span>
              <button
                type="button"
                onClick={() => removeFile(i)}
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      
      <div className="flex items-end gap-2 p-2">
        <div className="flex-1 min-h-[44px]">
          <Textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything or upload files..."
            className="min-h-[44px] max-h-[200px] w-full resize-none border-0 focus-visible:ring-0 px-3 py-3 bg-transparent text-sm placeholder:text-muted-foreground"
            disabled={disabled}
          />
        </div>
        
        <div className="flex items-center gap-2 p-1">
          <input
            type="file"
            multiple
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*,application/pdf,audio/*"
            disabled={disabled}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            <Paperclip className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            className="h-8 w-8 shrink-0 transition-all active:scale-95"
            onClick={handleSubmit}
            disabled={(text.trim() === "" && files.length === 0) || disabled}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
