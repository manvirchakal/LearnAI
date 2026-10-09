"use client";
import { FileTextIcon, Gamepad2Icon, MessagesSquareIcon, WorkflowIcon } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUIStore, type StudyTab } from "@/store/uiStore";

const TABS = [
  { value: "chat", label: "Chat", icon: MessagesSquareIcon },
  { value: "game", label: "Game", icon: Gamepad2Icon },
  { value: "diagram", label: "Diagrams", icon: WorkflowIcon },
  { value: "pdf", label: "PDF", icon: FileTextIcon },
] as const;

export default function StudyTabs() {
  const { activeTab, setActiveTab } = useUIStore();
  return (
    <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as StudyTab)} className="border-b p-2">
      <TabsList className="w-full">
        {TABS.map(({ value, label, icon: Icon }) => (
          <TabsTrigger key={value} value={value} className="gap-1.5">
            <Icon />
            <span className="hidden sm:inline">{label}</span>
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
