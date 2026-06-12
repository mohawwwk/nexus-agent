import { useState } from "react";
import type { PlanStep } from "@workspace/api-client-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Code2, Database, Globe, Layers, Search, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

interface PlanTraceProps {
  steps: PlanStep[];
  defaultOpen?: boolean;
}

export function PlanTrace({ steps, defaultOpen = false }: PlanTraceProps) {
  const [open, setOpen] = useState(defaultOpen);

  const getToolIcon = (toolName: string) => {
    const name = toolName.toLowerCase();
    if (name.includes("search") || name.includes("youtube")) return <Search className="w-3.5 h-3.5" />;
    if (name.includes("db") || name.includes("sql")) return <Database className="w-3.5 h-3.5" />;
    if (name.includes("web") || name.includes("fetch") || name.includes("http")) return <Globe className="w-3.5 h-3.5" />;
    if (name.includes("code") || name.includes("python") || name.includes("run")) return <Code2 className="w-3.5 h-3.5" />;
    if (name.includes("ocr") || name.includes("parse")) return <Layers className="w-3.5 h-3.5" />;
    return <Cpu className="w-3.5 h-3.5" />;
  };

  return (
    <div className="border-b border-border/50 bg-muted/20">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex items-center justify-between w-full px-5 py-3 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            Execution Trace
            <Badge className="ml-1 px-1.5 py-0 text-[10px] h-4 rounded-sm bg-border text-muted-foreground">{steps.length} steps</Badge>
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="px-6 pb-5 pt-1 space-y-4">
            {steps.map((step, idx) => (
              <div key={idx} className="relative flex gap-4 animate-in fade-in slide-in-from-top-2" style={{ animationDelay: `${idx * 100}ms`}}>
                {/* Timeline line */}
                {idx !== steps.length - 1 && (
                  <div className="absolute left-[11px] top-6 bottom-[-24px] w-[1px] bg-border" />
                )}
                
                {/* Icon/Status Indicator */}
                <div className="relative mt-1 z-10 flex flex-col items-center">
                  <div className={cn(
                    "w-[22px] h-[22px] rounded-full flex items-center justify-center shadow-sm border",
                    step.success ? "bg-card border-green-500/30 text-green-500" : "bg-card border-destructive/30 text-destructive"
                  )}>
                    {step.success ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  </div>
                </div>
                
                {/* Content */}
                <div className="flex-1 bg-card border rounded-xl p-3 shadow-sm">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="flex items-center gap-1.5 text-xs font-semibold font-mono bg-muted px-2 py-0.5 rounded-md text-foreground">
                      {getToolIcon(step.tool)}
                      {step.tool}
                    </span>
                    <span className="text-xs text-muted-foreground line-clamp-1">{step.description}</span>
                  </div>
                  
                  {step.result_preview && (
                    <div className="mt-2 bg-muted/50 rounded-md p-2 border border-border/50">
                      <p className="text-[11px] font-mono text-muted-foreground line-clamp-3 whitespace-pre-wrap">
                        {step.result_preview}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

// Inline badge component just for this file to avoid extra imports if we don't need full badge variants
function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cn("inline-flex items-center rounded-full font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2", className)}>{children}</span>;
}
