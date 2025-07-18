import React from "react";
import { IconButton, Icon, Menu } from "@chakra-ui/react";
import { FaEllipsisVertical } from "react-icons/fa6";

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
        <IconButton variant="ghost" aria-label="Options">
          <FaEllipsisVertical />
        </IconButton>
      </Menu.Trigger>
      <Menu.Positioner>
        <Menu.Content>
          <Menu.Item value="delete" onClick={(e) => onDelete(transcriptId)(e)}>
            Delete
          </Menu.Item>
          <Menu.Item
            value="reprocess"
            onClick={(e) => onReprocess(transcriptId)(e)}
          >
            Reprocess
          </Menu.Item>
        </Menu.Content>
      </Menu.Positioner>
    </Menu.Root>
  );
}
