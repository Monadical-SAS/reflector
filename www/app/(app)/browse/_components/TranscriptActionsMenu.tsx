import React from "react";
import { IconButton, Icon, Menu } from "@chakra-ui/react";
import { LuMenu, LuTrash, LuRotateCw } from "react-icons/lu";

interface TranscriptActionsMenuProps {
  transcriptId: string;
  onDelete: (transcriptId: string) => void;
  onReprocess: (transcriptId: string) => void;
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
            onClick={() => onReprocess(transcriptId)}
          >
            <LuRotateCw /> Reprocess
          </Menu.Item>
          <Menu.Item
            value="delete"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(transcriptId);
            }}
          >
            <LuTrash /> Delete
          </Menu.Item>
        </Menu.Content>
      </Menu.Positioner>
    </Menu.Root>
  );
}
