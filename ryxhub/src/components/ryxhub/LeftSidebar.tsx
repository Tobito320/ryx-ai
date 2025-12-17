import { useMemo, useState, type ElementType, type MouseEvent } from "react";
import {
	BookMarked,
	FileText,
	ListChecks,
	Menu,
	MessageSquare,
	MoreHorizontal,
	PanelRightClose,
	Plus,
	Search,
	Settings,
	Trash2,
	Edit,
	Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export type SidebarTab = "study" | "exams" | "documents";

type Props = {
	collapsed: boolean;
	onToggleCollapsed: () => void;
	onOpenSettings: () => void;
	activeTab: SidebarTab;
	onTabChange: (tab: SidebarTab) => void;
	setActiveView: (view: "chat" | "school" | "documents" | "dashboard") => void;
};

export function LeftSidebar({
	collapsed,
	onToggleCollapsed,
	onOpenSettings,
	activeTab,
	onTabChange,
	setActiveView,
}: Props) {
	const {
		sessions,
		selectedSessionId,
		selectSession,
		deleteSession,
		renameSession,
	} = useRyxHub();

	const [searchQuery, setSearchQuery] = useState("");
	const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
	const [renameValue, setRenameValue] = useState("");
	const [chatsVisible, setChatsVisible] = useState(true);

	const filteredSessions = useMemo(() => {
		if (!searchQuery.trim()) return sessions;
		const q = searchQuery.toLowerCase();
		return sessions.filter((s) => s.name.toLowerCase().includes(q));
	}, [sessions, searchQuery]);

	const groupedSessions = useMemo(
		() => [
			{ label: "RECENT", sessions: filteredSessions.slice(0, 10) },
			{ label: "OLDER", sessions: filteredSessions.slice(10) },
		],
		[filteredSessions]
	);

	const handleSessionClick = (sessionId: string) => {
		selectSession(sessionId);
		localStorage.setItem(`session-lastused-${sessionId}`, Date.now().toString());
		setActiveView("chat");
	};

	const handleDeleteSession = (sessionId: string, e: MouseEvent) => {
		e.stopPropagation();
		deleteSession(sessionId);
		toast.success("Session deleted");
	};

	const handleRenameStart = (sessionId: string, currentName: string, e: MouseEvent) => {
		e.stopPropagation();
		setRenamingSessionId(sessionId);
		setRenameValue(currentName);
	};

	const handleRenameSubmit = (sessionId: string) => {
		if (!renameValue.trim()) {
			setRenamingSessionId(null);
			return;
		}
		renameSession(sessionId, renameValue);
		toast.success("Session renamed");
		setRenamingSessionId(null);
	};

	const handleNewSession = () => {
		window.dispatchEvent(new CustomEvent("new-session-click"));
	};

	const tabItems: { id: SidebarTab; label: string; icon: ElementType; view: Props["setActiveView"] extends (view: infer V) => any ? V : never }[] = [
		{ id: "study", label: "Study", icon: BookMarked, view: "chat" as const },
		{ id: "exams", label: "Exams", icon: ListChecks, view: "school" as const },
		{ id: "documents", label: "Documents", icon: FileText, view: "documents" as const },
	];

	return (
		<aside
			className={cn(
				"h-full bg-[hsl(var(--sidebar-background))] border-r border-[hsl(var(--sidebar-border))] flex flex-col transition-[width] duration-300 ease-in-out",
				collapsed ? "w-16" : "w-64"
			)}
		>
			<div className="flex items-center justify-between gap-2 px-3 py-3 border-b border-[hsl(var(--sidebar-border))]">
				{!collapsed && (
					<button
						onClick={onToggleCollapsed}
						className="h-9 w-9 rounded-lg flex items-center justify-center hover:bg-[hsl(var(--sidebar-accent))] transition-colors"
						aria-label="Close sidebar"
						title="Close sidebar"
					>
						<Menu className="w-4 h-4" />
					</button>
				)}
			</div>

			<div className="px-3 py-3 space-y-3 border-b border-[hsl(var(--sidebar-border))]">
				<Button
					onClick={handleNewSession}
					size="sm"
					variant="outline"
					className={cn(
						"w-full justify-start gap-2 h-10 border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.08]",
						collapsed && "justify-center"
					)}
					title="New chat"
				>
					<Plus className="w-4 h-4" />
					{!collapsed && <span className="text-sm font-medium">New chat</span>}
				</Button>

				<div className="relative">
					<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
					<Input
						placeholder="Search chats"
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className={cn(
							"pl-9 h-9 bg-[hsl(var(--sidebar-accent))] border-[hsl(var(--sidebar-border))] text-sm placeholder:text-[hsl(var(--muted-foreground))] focus-visible:ring-[hsl(var(--primary))]",
							collapsed && "pl-9"
						)}
					/>
				</div>

				<div className="space-y-1">
					{!collapsed && (
						<div className="text-[11px] font-semibold tracking-[0.08em] text-[hsl(var(--muted-foreground))]">
							SECTIONS
						</div>
					)}
					{tabItems.map((tab) => {
						const Icon = tab.icon;
						const active = activeTab === tab.id;
						return (
							<button
								key={tab.id}
								onClick={() => {
									onTabChange(tab.id);
									setActiveView(tab.view);
								}}
								className={cn(
									"w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
									active
										? "bg-[hsl(var(--primary))/0.12] text-[hsl(var(--primary-foreground))] border border-[hsl(var(--primary))]"
										: "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--sidebar-accent))] border border-transparent",
									collapsed && "justify-center px-0"
								)}
								title={tab.label}
							>
								<Icon className="w-4 h-4" />
								{!collapsed && <span className="font-medium">{tab.label}</span>}
							</button>
						);
					})}
				</div>
			</div>

			{!collapsed && (
				<div className="px-3 py-2 border-b border-[hsl(var(--sidebar-border))]">
					<button
						onClick={() => setChatsVisible(!chatsVisible)}
						className="w-full text-left text-[11px] font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide hover:text-[hsl(var(--foreground))] transition-colors"
					>
						Your chats {chatsVisible ? "▼" : "▶"}
					</button>
				</div>
			)}
			<ScrollArea className="flex-1 px-2 py-3">
				{!collapsed && chatsVisible && (
					<div className="space-y-3">
						{groupedSessions.map((group) => (
							<div key={group.label}>
								<div className="px-2 py-1 text-[11px] font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
									{group.label}
								</div>
								<div className="space-y-1">
									{group.sessions.map((session, idx) => (
										<div
											key={session.id}
											className={cn(
												"group relative flex items-center gap-3 rounded-lg border border-transparent px-2 py-2 transition-all duration-200",
												session.id === selectedSessionId
													? "bg-[hsl(var(--sidebar-accent))] border-[hsl(var(--sidebar-border))]"
													: "hover:bg-[hsl(var(--sidebar-accent))]"
											)}
											onClick={() => handleSessionClick(session.id)}
											style={{ animationDelay: `${idx * 30}ms` }}
										>
											<div className="h-8 w-8 rounded-md bg-[hsl(var(--sidebar-border))] flex items-center justify-center text-[hsl(var(--foreground))]">
												<MessageSquare className="w-4 h-4" />
											</div>

											{!collapsed && (
												<div className="flex-1 min-w-0">
													{renamingSessionId === session.id ? (
														<Input
															value={renameValue}
															onChange={(e) => setRenameValue(e.target.value)}
															onBlur={() => handleRenameSubmit(session.id)}
															onKeyDown={(e) => {
																if (e.key === "Enter") handleRenameSubmit(session.id);
																if (e.key === "Escape") setRenamingSessionId(null);
															}}
															className="h-8 text-sm bg-transparent border-[hsl(var(--primary))]"
															autoFocus
															onClick={(e) => e.stopPropagation()}
														/>
													) : (
														<div className="flex items-center gap-2">
															<span className="text-sm text-[hsl(var(--foreground))] truncate">
																{session.name.length > 28 ? `${session.name.slice(0, 28)}...` : session.name}
															</span>
														</div>
													)}
												</div>
											)}

											{!collapsed && (
												<DropdownMenu>
													<DropdownMenuTrigger asChild>
														<button
															className="h-7 w-7 flex items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--sidebar-border))]"
															onClick={(e) => e.stopPropagation()}
														>
															<MoreHorizontal className="h-4 w-4" />
														</button>
													</DropdownMenuTrigger>
													<DropdownMenuContent align="end" className="w-40">
														<DropdownMenuItem onClick={(e) => handleRenameStart(session.id, session.name, e as any)}>
															<Edit className="mr-2 h-3.5 w-3.5" />
															Rename
														</DropdownMenuItem>
														<DropdownMenuItem
															onClick={(e) => handleDeleteSession(session.id, e as any)}
															className="text-destructive focus:text-destructive"
														>
															<Trash2 className="mr-2 h-3.5 w-3.5" />
															Delete
														</DropdownMenuItem>
													</DropdownMenuContent>
												</DropdownMenu>
											)}
										</div>
									))}
								</div>
							</div>
						))}

						{filteredSessions.length === 0 && (
							<div className="px-2 py-6 text-center text-[hsl(var(--muted-foreground))]">
								<MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-60" />
								<p className="text-sm">No chats</p>
								<p className="text-xs text-[hsl(var(--muted-foreground))]">Start a new conversation</p>
							</div>
						)}
					</div>
				)}
			</ScrollArea>

			<div className="p-3 border-t border-[hsl(var(--sidebar-border))]">
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<button
							className={cn(
								"w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-[hsl(var(--sidebar-accent))] transition-colors",
								collapsed && "justify-center"
							)}
						>
							<Avatar className="h-9 w-9 border border-[hsl(var(--sidebar-border))] bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary-foreground))]">
								<AvatarFallback>T</AvatarFallback>
							</Avatar>
							{!collapsed && (
								<div className="flex-1 text-left">
									<div className="text-sm font-semibold text-[hsl(var(--foreground))]">Tobi</div>
								</div>
							)}
						</button>
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" className="w-56">
						<DropdownMenuItem onClick={() => { onOpenSettings(); window.dispatchEvent(new CustomEvent('settings-tab', { detail: 'personalizations' })); }}>
							<User className="mr-2 h-4 w-4" />
							Personalization
						</DropdownMenuItem>
						<DropdownMenuItem onClick={onOpenSettings}>
							<Settings className="mr-2 h-4 w-4" />
							Settings
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
			</div>
		</aside>
	);
}
// File intentionally overwritten below
