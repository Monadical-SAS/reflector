import React from "react";
import {
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Icon,
} from "@chakra-ui/react";
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
    <Menu closeOnSelect={true} isLazy={true}>
      <MenuButton
        as={IconButton}
        icon={<Icon as={FaEllipsisVertical} />}
        variant="outline"
        aria-label="Options"
      />
      <MenuList>
        <MenuItem onClick={onDelete(transcriptId)}>Delete</MenuItem>
        <MenuItem onClick={onReprocess(transcriptId)}>Reprocess</MenuItem>
      </MenuList>
    </Menu>
  );
}
