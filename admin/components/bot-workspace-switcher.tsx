"use client";

import { useMemo, useState } from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { selectAdminBot, type AdminPrincipal } from "@/lib/api";
import { toast } from "sonner";

type BotWorkspaceSwitcherProps = {
  principal: AdminPrincipal;
};

const BOT_LABELS: Record<string, string> = {
  tanjah: "Tanjah",
  adarkwa: "Adarkwa",
};

export function BotWorkspaceSwitcher({ principal }: BotWorkspaceSwitcherProps) {
  const queryClient = useQueryClient();
  const [isPending, setIsPending] = useState(false);

  const activeLabel = useMemo(() => {
    const activeBot = principal.active_bot_id ?? principal.bot_access[0] ?? null;
    if (!activeBot) {
      return "Workspace";
    }
    return BOT_LABELS[activeBot] ?? activeBot;
  }, [principal.active_bot_id, principal.bot_access]);

  if ((principal.bot_access?.length ?? 0) <= 1) {
    return null;
  }

  function handleSelect(botId: string) {
    if (botId === principal.active_bot_id) {
      return;
    }

    setIsPending(true);
    void (async () => {
      try {
        await selectAdminBot(botId);
        await queryClient.invalidateQueries({ queryKey: ["admin-principal"] });
        await queryClient.invalidateQueries({ queryKey: ["staff-users"] });
        await queryClient.invalidateQueries({ queryKey: ["catalog-tree"] });
        await queryClient.invalidateQueries({ queryKey: ["questions"] });
        toast.success(`Switched to ${BOT_LABELS[botId] ?? botId} workspace.`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Unable to switch workspace.");
      } finally {
        setIsPending(false);
      }
    })();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="outline" size="sm" className="gap-2">
            {isPending ? <Loader2 className="size-3.5 animate-spin" /> : null}
            <span className="hidden sm:inline">Workspace:</span>
            <span className="font-medium">{activeLabel}</span>
            <ChevronsUpDown className="size-3.5 opacity-60" />
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="min-w-48">
        <DropdownMenuLabel>Select workspace</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {principal.bot_access.map((botId) => (
          <DropdownMenuItem key={botId} onClick={() => handleSelect(botId)}>
            <span>{BOT_LABELS[botId] ?? botId}</span>
            {botId === principal.active_bot_id ? (
              <Check className="ml-auto size-4" />
            ) : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
