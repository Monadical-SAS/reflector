import React from "react";
import { IconButton, Menu } from "@chakra-ui/react";
import { LuMenu, LuPen, LuTrash } from "react-icons/lu";

interface RoomActionsMenuProps {
  roomId: string;
  roomData: any;
  onEdit: (roomId: string, roomData: any) => void;
  onDelete: (roomId: string) => void;
  size?: "sm" | "md" | "lg";
  variant?: string;
}

export function RoomActionsMenu({
  roomId,
  roomData,
  onEdit,
  onDelete,
  size = "sm",
  variant = "ghost",
}: RoomActionsMenuProps) {
  return (
    <Menu.Root closeOnSelect={true} lazyMount={true}>
      <Menu.Trigger asChild>
        <IconButton aria-label="actions" size={size} variant={variant}>
          <LuMenu />
        </IconButton>
      </Menu.Trigger>
      <Menu.Positioner>
        <Menu.Content>
          <Menu.Item value="edit" onClick={() => onEdit(roomId, roomData)}>
            <LuPen /> Edit
          </Menu.Item>
          <Menu.Item value="delete" onClick={() => onDelete(roomId)}>
            <LuTrash /> Delete
          </Menu.Item>
        </Menu.Content>
      </Menu.Positioner>
    </Menu.Root>
  );
}
