import React from "react";
import { IconButton, Icon, Menu } from "@chakra-ui/react";
import { LuMenu, LuTrash, LuRotateCw } from "react-icons/lu";

interface TranscriptActionsMenuProps {
  transcriptId: string;
  onDelete: (transcriptId: string) => (e: any) => void;
  onReprocess: (transcriptId: string) => (e: any) => void;
}

export default function TranscriptActionsMenu({
  transcriptId,
  onDelete,
  onReprocess,
}: TranscriptActionsMenuProps) {
  return (
    <Menu.Root closeOnSelect={true} lazyMount={true}>
      <Menu.Trigger asChild>
        <IconButton aria-label="Options" size="sm" variant="ghost">
          <LuMenu />
        </IconButton>
      </Menu.Trigger>
      <Menu.Positioner>
        <Menu.Content>
          <Menu.Item
            value="reprocess"
            onClick={(e) => onReprocess(transcriptId)(e)}
          >
            <LuRotateCw /> Reprocess
          </Menu.Item>
          <Menu.Item value="delete" onClick={(e) => onDelete(transcriptId)(e)}>
            <LuTrash /> Delete
          </Menu.Item>
        </Menu.Content>
      </Menu.Positioner>
    </Menu.Root>
  );
}
